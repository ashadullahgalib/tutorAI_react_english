import json
import math
import sqlite3
import threading
from pathlib import Path

from core.logger import get_logger


log = get_logger("semantic_cache")

CACHE_DIR = Path(__file__).resolve().parent
CACHE_DB = CACHE_DIR / "cache.db"
SIMILARITY_THRESHOLD = 0.85
MODEL_NAME = "all-MiniLM-L6-v2"

_model = None
_model_lock = threading.Lock()


def _get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                try:
                    from sentence_transformers import SentenceTransformer
                except ImportError:
                    log.warning("sentence-transformers is not installed; semantic cache disabled.")
                    return None
                try:
                    _model = SentenceTransformer(MODEL_NAME)
                except Exception as exc:
                    log.warning("Could not load semantic cache model: %s", exc)
                    return None
    return _model


def _connect() -> sqlite3.Connection:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(CACHE_DB)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS qa_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_text TEXT NOT NULL,
            answer_text TEXT NOT NULL,
            embedding TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    return conn


def _embedding_for(text: str) -> list[float] | None:
    model = _get_model()
    if model is None:
        return None
    embedding = model.encode(text)
    if hasattr(embedding, "tolist"):
        embedding = embedding.tolist()
    return [float(value) for value in embedding]


def _cosine_similarity(first: list[float], second: list[float]) -> float:
    dot = sum(a * b for a, b in zip(first, second))
    first_norm = math.sqrt(sum(a * a for a in first))
    second_norm = math.sqrt(sum(b * b for b in second))
    if first_norm == 0 or second_norm == 0:
        return 0.0
    return dot / (first_norm * second_norm)


def get_cached_answer(question: str) -> str | None:
    try:
        conn = _connect()
        conn.close()
        incoming_embedding = _embedding_for(question)
        if incoming_embedding is None:
            return None

        with _connect() as conn:
            rows = conn.execute("SELECT answer_text, embedding FROM qa_cache").fetchall()

        best_answer = None
        best_score = 0.0
        for answer_text, stored_embedding_json in rows:
            try:
                stored_embedding = json.loads(stored_embedding_json)
            except json.JSONDecodeError:
                continue
            score = _cosine_similarity(incoming_embedding, stored_embedding)
            if score > best_score:
                best_score = score
                best_answer = answer_text

        if best_score >= SIMILARITY_THRESHOLD:
            return best_answer
    except Exception as exc:
        log.warning("Semantic cache lookup failed: %s", exc)
    return None


def save_to_cache(question: str, answer: str) -> None:
    try:
        conn = _connect()
        conn.close()
        embedding = _embedding_for(question)
        if embedding is None:
            return

        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO qa_cache (question_text, answer_text, embedding)
                VALUES (?, ?, ?)
                """,
                (question, answer, json.dumps(embedding)),
            )
            conn.commit()
    except Exception as exc:
        log.warning("Semantic cache save failed: %s", exc)
