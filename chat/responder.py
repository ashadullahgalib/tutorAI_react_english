"""
Responder: Generates answers using Gemini (google-genai SDK v1+).
- Supports text questions and image uploads (students can photograph problems).
- Uses content.json / exercise.json context retrieved via FAISS.
- Strictly answers from the provided syllabus context only.
"""
import os
import re

from google import genai as google_genai
from fastapi import HTTPException

from cache.semantic_cache import get_cached_answer, save_to_cache
from config.settings import CONFIG
from core.logger import get_logger
from core.session import SessionState

log = get_logger("responder")


# ---------------------------------------------------------------------------
# Query analysis helpers
# ---------------------------------------------------------------------------

_EXERCISE_KEYWORDS = {
    "mcq", "multiple choice", "cq", "creative question", "exercise",
    "practice", "quiz", "solve", "answer the question", "বহু নির্বাচনী",
    "সৃজনশীল", "practice problem", "short question", "broad question",
}

_CHAPTER_WORDS = [
    "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "এক", "দুই", "তিন", "চার", "পাঁচ",
]


def detect_mode(query: str) -> str:
    q = query.lower()
    if any(kw in q for kw in _EXERCISE_KEYWORDS):
        return "exercise"
    return "content"


def extract_chapter(query: str) -> str | None:
    q = query.lower()
    m = re.search(r"chapter\s+(\d+)", q)
    if m:
        return f"chapter {m.group(1)}"
    word_pat = "|".join(_CHAPTER_WORDS)
    m = re.search(rf"chapter\s+({word_pat})", q)
    return m.group(0) if m else None


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------

def _build_context(retrieved: list[dict]) -> str:
    if not retrieved:
        return "No relevant content found in the book."
    parts = []
    for r in retrieved:
        chunk = (
            f"Chapter: {r.get('chapter', 'Unknown')}\n"
            f"Topic: {r.get('topic', '')}\n"
            f"Subtopic: {r.get('subtopic', '')}\n"
            f"Type: {r.get('type') or r.get('exercise_type', 'concept')}\n"
            f"Content:\n{r.get('content', '').strip()}"
        )
        parts.append(chunk)
    return "\n\n---\n\n".join(parts)


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

_SYSTEM_CONTENT = """You are TUTOR AI — a friendly, expert tutor for SSC students in Bangladesh.

RULES:
1. PREFER the CONTEXT provided — it comes from the student's actual textbook. Always cite from it when possible.
2. If the context covers the topic, explain using it as the primary source.
3. If the context does NOT fully cover the topic, use your general knowledge to give a correct, helpful answer — do NOT refuse. Mention briefly that the specific section may not be in the retrieved context.
4. Never make up false facts. If genuinely unsure, say so.
5. Explain clearly and simply for the student's level.
6. Use structure: definition → explanation → example.
7. If the student writes in Bangla/Bengali, respond in Bangla. If in English, respond in English.
8. Be encouraging and patient."""

_SYSTEM_EXERCISE = """You are TUTOR AI — an expert exam assistant for SSC students in Bangladesh.

RULES:
1. PREFER the CONTEXT provided — it comes from the student's actual textbook.
2. For MCQs: always identify the correct answer option (e.g. "Answer: b. Bandwidth") and explain why.
   - Use the context if it contains the answer.
   - If the context is insufficient, use your subject knowledge to give the correct answer — do NOT say "I cannot determine". SSC students need definitive answers.
3. For CQ/creative questions: answer each part (Ka/Kha/Ga/Gha) step by step.
4. For math/physics problems: show every step with units.
5. For Bangla literature questions: answer from the context provided.
6. Always give a direct, confident answer. Never leave a student without a solution.
7. If the student writes in Bangla/Bengali, respond in Bangla. If in English, respond in English."""

_SYSTEM_IMAGE = """You are TUTOR AI — an expert tutor helping SSC students solve problems from photos.

The student has uploaded a photo of a problem (from their textbook or notebook).

RULES:
1. First, read and describe what you see in the image (the question/problem).
2. Solve it using the CONTEXT provided from their textbook when relevant.
3. If the context doesn't cover it, solve using your subject knowledge — do NOT refuse.
4. Show every step clearly.
5. If you cannot read part of the image, say so and ask the student to retype that part.
6. For math/science: show all workings with proper units and formulas.
7. If the student writes in Bangla/Bengali, respond in Bangla. If in English, respond in English."""


# ---------------------------------------------------------------------------
# Main answer generator
# ---------------------------------------------------------------------------

def generate_answer(
    query: str,
    retrieved: list[dict],
    mode: str,
    state: SessionState,
    image_data: bytes | None = None,
    image_mime: str = "image/jpeg",
    client: google_genai.Client | None = None,
) -> str:
    """
    Generate a syllabus-grounded answer via Gemini (new google-genai SDK).

    Parameters
    ----------
    query       : The student's text question.
    retrieved   : Context chunks from FAISS search.
    mode        : 'content' or 'exercise'.
    state       : Current session state (chat history etc.).
    image_data  : Raw bytes of an uploaded image (optional).
    image_mime  : MIME type of the image, e.g. 'image/jpeg'.
    client      : Shared google_genai.Client instance (passed from app.py).
    """
    context = _build_context(retrieved)
    has_image = image_data is not None and len(image_data) > 0
    if not has_image:
        cached_answer = get_cached_answer(query)
        if cached_answer is not None:
            log.info("Cache hit")
            return cached_answer

    if has_image:
        system_prompt = _SYSTEM_IMAGE
        llm_model = CONFIG["models"]["vision"]
    elif mode == "exercise":
        system_prompt = _SYSTEM_EXERCISE
        llm_model = CONFIG["models"]["llm"]
    else:
        system_prompt = _SYSTEM_CONTENT
        llm_model = CONFIG["models"]["llm"]

    # Build the client if not passed in (fallback — prefers the shared client from app.py)
    if client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=503, detail="GEMINI_API_KEY not configured.")
        client = google_genai.Client(api_key=api_key)

    # Build the text portion of the prompt
    prompt_parts_text = [system_prompt]

    # Add chat history if available
    history_limit = CONFIG["retrieval"]["chat_history_send_limit"]
    if state.chat_history:
        prompt_parts_text.append("Previous conversation:")
        for msg in state.chat_history[-history_limit:]:
            prompt_parts_text.append(f"{msg['role']}: {msg['content']}")
        prompt_parts_text.append("")  # blank separator

    prompt_parts_text.append(f"TEXTBOOK CONTEXT:\n{context}")
    prompt_parts_text.append(f"STUDENT QUESTION:\n{query}")

    prompt_text = "\n\n".join(prompt_parts_text)

    # Build contents list for the new SDK
    # new SDK: client.models.generate_content(model=..., contents=[...], config=...)
    try:
        if has_image:
            # Pass image as inline_data dict — works across all google-genai SDK versions
            import base64
            image_part = {
                "inline_data": {
                    "mime_type": image_mime,
                    "data": base64.b64encode(image_data).decode("utf-8"),
                }
            }
            contents = [prompt_text, image_part]
        else:
            contents = prompt_text

        response = client.models.generate_content(
            model=llm_model,
            contents=contents,
        )
        answer = response.text
        if not has_image:
            save_to_cache(query, answer)
            log.info("Cache miss — saved to cache")

    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Gemini error: {exc}") from exc

    # Update session history
    history_limit_store = CONFIG["retrieval"]["chat_history_limit"]
    state.remember("user", query, history_limit_store)
    state.remember("assistant", answer, history_limit_store)

    return answer
