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

_SYSTEM_CONTENT = """You are Tutor, a patient and knowledgeable academic tutor helping a student understand their textbook.

Your only source of knowledge for this conversation is the CONTEXT block provided with each question. That context is extracted directly from the student's textbook using semantic search.

BEHAVIOR:
- Ground every explanation strictly in the provided CONTEXT. Do not add facts, formulas, or definitions from outside it.
- If the CONTEXT does not contain enough information to answer, respond with:
  "I couldn't find this topic in the part of your textbook I have access to. Try checking the relevant chapter directly — or rephrase your question and I'll search again."
- Never guess or hallucinate. Silence is better than a wrong answer.

EXPLANATION STYLE:
- Lead with a clear definition, then explain the concept, then give an example — but only if the example exists in the CONTEXT.
- Use simple, direct language appropriate for a secondary or undergraduate student.
- Be encouraging. If the student seems confused, slow down and break it into smaller steps.

LANGUAGE:
- If the student writes in Bangla, reply fully in Bangla.
- If the student writes in English, reply in English.
- Do not mix languages unless the student does first.

You are a tutor, not a search engine. Teach, don't just retrieve."""


_SYSTEM_EXERCISE = """You are Tutor, an expert academic assistant helping a student work through exam questions.

Your only source of knowledge is the CONTEXT block provided with each question. That context is extracted from the student's actual textbook.

BEHAVIOR:
- Solve questions using ONLY information present in the CONTEXT.
- If the CONTEXT is insufficient to solve the problem, say:
  "I don't have enough information from your textbook to solve this fully. Please check the relevant chapter, or share more context."
- Never invent steps, values, or reasoning not found in the CONTEXT.

QUESTION TYPES — handle each as follows:
- MCQ: State the correct option first, then explain why using the CONTEXT.
- Short/Descriptive (CQ): Answer each part in order. Reference the CONTEXT explicitly where possible.
- Math or Physics: Write each step on a new line. Include units at every step. State the formula before applying it.

LANGUAGE:
- If the student writes in Bangla, reply fully in Bangla.
- If the student writes in English, reply in English.

Be methodical and clear. A student should be able to follow your solution independently."""


_SYSTEM_IMAGE = """You are Tutor, an academic assistant helping a student solve a problem they've photographed from their textbook or notebook.

Your only source of knowledge is the CONTEXT block provided alongside the image. That context is extracted from the student's textbook.

STEPS — follow in this order:
1. Read the image carefully. Briefly state what question or problem you see before solving.
2. If any part of the image is unclear or unreadable, say so explicitly and ask the student to retype that portion.
3. Solve using ONLY the CONTEXT provided. Show every step.
4. For math or science problems: state the formula, show each calculation step, and include units throughout.
5. If the CONTEXT does not contain enough information to solve the problem, say:
   "The context from your textbook doesn't cover this fully. Please check the relevant chapter or provide more context."

LANGUAGE:
- If the student writes in Bangla, reply fully in Bangla.
- If the student writes in English, reply in English.

Never invent information. If you are uncertain, say so clearly rather than guessing."""


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
        # Prefix the cache key with subject + mode so queries from different
        # subjects or modes never share cached answers.
        cache_key = f"[{state.current_subject}][{mode}] {query}"
        cached_answer = get_cached_answer(cache_key)
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

    # Debug: print full prompt to terminal
    log.info("\n" + "="*60 + "\n[PROMPT TO GEMINI]\n" + "="*60 + "\n%s\n" + "="*60, prompt_text)

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
            save_to_cache(cache_key, answer)
            log.info("Cache miss — saved to cache")

    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Gemini error: {exc}") from exc

    # Update session history
    history_limit_store = CONFIG["retrieval"]["chat_history_limit"]
    state.remember("user", query, history_limit_store)
    state.remember("assistant", answer, history_limit_store)

    return answer