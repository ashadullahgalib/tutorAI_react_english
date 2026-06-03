"""
TUTOR AI — FastAPI backend.

Endpoints:
  GET  /health                 — health check
  POST /session/new            — create a new session
  GET  /subjects               — list available subjects
  POST /chat                   — text question (JSON body)
  POST /chat/image             — photo of a problem (multipart form)
  DELETE /session/{session_id} — clear session memory
"""
import uuid
import os
from contextlib import asynccontextmanager

from google import genai as google_genai
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Security, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address
except ImportError:
    Limiter = None
    RateLimitExceeded = None
    _rate_limit_exceeded_handler = None
    get_remote_address = None

from chat.responder import detect_mode, extract_chapter, generate_answer
from chat.retriever import resolve_query, search
from config.settings import API_SECRET_KEY
from core.indexer import get_subjects
from core.logger import get_logger
from core.session_store import session_delete, session_exists, session_get, session_set

log = get_logger("api")
security = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def verify_token(credentials: HTTPAuthorizationCredentials | None = Security(security)):
    if not API_SECRET_KEY:
        raise HTTPException(status_code=500, detail="API_SECRET_KEY not configured.")
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authenticated.")
    if credentials.credentials != API_SECRET_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
    return credentials


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

if Limiter is not None:
    limiter = Limiter(key_func=get_remote_address)
else:
    class _NoopLimiter:
        def limit(self, _rule: str):
            def decorator(func):
                return func
            return decorator
    limiter = _NoopLimiter()


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("TUTOR AI API starting…")
    yield
    log.info("TUTOR AI API stopped.")


# ---------------------------------------------------------------------------
# Gemini client (new google-genai SDK)
# ---------------------------------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    log.warning("GEMINI_API_KEY not set. Gemini features will not work.")
    gemini_client = None
else:
    log.info("GEMINI_API_KEY is set (length: %d)", len(GEMINI_API_KEY))
    gemini_client = google_genai.Client(api_key=GEMINI_API_KEY)


app = FastAPI(title="TUTOR AI API", version="3.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if RateLimitExceeded is not None:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=36, max_length=36)
    message: str = Field(..., min_length=1, max_length=4000)
    subject: str = Field(..., min_length=1, max_length=100)


class ChatResponse(BaseModel):
    answer: str
    mode: str
    session_id: str


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB


def _validate_subject(subject: str):
    subjects = get_subjects()
    if subject not in subjects:
        raise HTTPException(
            status_code=404,
            detail=f"Subject '{subject}' not found. Available: {subjects}",
        )


def _get_session(session_id: str):
    state = session_get(session_id)
    if state is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found. Call /session/new first.",
        )
    return state


def _run_chat(
    session_id: str,
    message: str,
    subject: str,
    image_data: bytes | None = None,
    image_mime: str = "image/jpeg",
) -> ChatResponse:
    _validate_subject(subject)
    state = _get_session(session_id)
    state.current_subject = subject
    state.trim_history(limit=50)

    expanded = resolve_query(message, state)
    mode = detect_mode(expanded)
    chapter = extract_chapter(expanded)
    from config.settings import CONFIG as _CFG
    k = _CFG["retrieval"].get("top_k_exercise", 12) if mode == "exercise" else _CFG["retrieval"].get("top_k", 8)
    retrieved = search(expanded, chapter=chapter, mode=mode, subject=subject, k=k)
    state.update_from_retrieved(retrieved)

    answer = generate_answer(
        message, retrieved, mode, state,
        image_data=image_data, image_mime=image_mime,
        client=gemini_client,
    )
    session_set(session_id, state)

    log.info(
        "session=%s | mode=%s | subject=%s | image=%s",
        session_id[:8], mode, subject, image_data is not None,
    )
    return ChatResponse(answer=answer, mode=mode, session_id=session_id)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    llm_ok = False
    model_used = None
    if gemini_client is None:
        error_msg = "GEMINI_API_KEY not set"
    else:
        try:
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents="Hello",
            )
            llm_ok = True
            model_used = "gemini-2.5-flash"
            log.info("Gemini health check passed")
        except Exception as e:
            error_msg = str(e)
            log.error("Gemini health check failed: %s", e)

    subjects = get_subjects()
    result = {
        "status": "ok" if llm_ok else "degraded",
        "gemini": "up" if llm_ok else f"down — {error_msg if not llm_ok else ''}",
        "subjects_loaded": len(subjects),
        "subjects": subjects,
    }
    if model_used:
        result["model"] = model_used
    return result


@app.post("/session/new", dependencies=[Depends(verify_token)])
@limiter.limit("20/minute")
def new_session(request: Request):
    sid = str(uuid.uuid4())
    session_set(sid)
    return {"session_id": sid}


@app.get("/subjects", dependencies=[Depends(verify_token)])
def list_subjects():
    return {"subjects": get_subjects()}


@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_token)])
@limiter.limit("30/minute")
def chat(request: Request, req: ChatRequest):
    return _run_chat(req.session_id, req.message, req.subject)


@app.post("/chat/image", response_model=ChatResponse, dependencies=[Depends(verify_token)])
@limiter.limit("15/minute")
async def chat_image(
    request: Request,
    session_id: str = Form(...),
    message: str = Form(default="Please solve this problem from my photo."),
    subject: str = Form(...),
    image: UploadFile = File(...),
):
    content_type = image.content_type or "image/jpeg"
    if content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type: {content_type}. Use JPEG, PNG, WEBP, or GIF.",
        )

    image_bytes = await image.read()
    if len(image_bytes) > _MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image too large. Maximum size is 10 MB.")
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty image file.")

    return _run_chat(session_id, message, subject, image_data=image_bytes, image_mime=content_type)


@app.delete("/session/{session_id}", dependencies=[Depends(verify_token)])
def clear_session(session_id: str):
    state = session_get(session_id)
    if state is not None:
        state.reset()
        session_set(session_id, state)
    else:
        session_delete(session_id)
    return {"status": "cleared"}