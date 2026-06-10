"""
Retriever: Semantic search over FAISS indices built from content.json / exercise.json.
Supports chapter filtering and pronoun resolution.
"""
import re

import faiss
import numpy as np

from config.settings import CONFIG
from core.indexer import get_embedding_model, get_subject_bundle
from core.session import SessionState

PRONOUN_PATTERN = re.compile(r"\b(it|this|that|these|those)\b", re.IGNORECASE)
DIGIT_TO_WORD = {
    "1": "one", "2": "two", "3": "three", "4": "four", "5": "five",
    "6": "six", "7": "seven", "8": "eight", "9": "nine", "10": "ten",
}


def _normalise(text: str) -> str:
    t = text.lower()
    for digit, word in DIGIT_TO_WORD.items():
        t = re.sub(rf"\b{re.escape(digit)}\b", word, t)
    return t


def resolve_query(query: str, state: SessionState) -> str:
    """Expand pronouns using conversation context."""
    if PRONOUN_PATTERN.search(query):
        ctx = state.last_answer_entity or state.active_concept
        if ctx:
            return f"{ctx}. {query}"
    return query


def _search_index(
    query_emb: np.ndarray,
    index,
    meta: list[dict],
    chapter: str | None,
    top_k: int,
) -> list[dict]:
    """Search a single FAISS index, optionally filtering by chapter."""
    if not meta:
        return []

    if chapter:
        fetch_k = min(top_k * 15, len(meta))
        _, indices = index.search(query_emb, fetch_k)
        norm_chapter = _normalise(chapter)
        results = []
        for i in indices[0]:
            if i < 0:
                continue
            item = meta[i]
            if norm_chapter in _normalise(item.get("chapter", "")):
                results.append(item)
            if len(results) >= top_k:
                break
        return results

    actual_k = min(top_k, len(meta))
    _, indices = index.search(query_emb, actual_k)
    return [meta[i] for i in indices[0] if i >= 0]


def search(
    query: str,
    chapter: str | None = None,
    mode: str = "content",
    subject: str | None = None,
    k: int | None = None,
) -> list[dict]:
    if not subject:
        raise ValueError("subject is required for retrieval")

    bundle = get_subject_bundle(subject)
    model = get_embedding_model()
    query_emb = np.array(model.encode([query]), dtype="float32")
    faiss.normalize_L2(query_emb)

    top_k = k or CONFIG["retrieval"]["top_k"]

    if mode == "exercise":
        # exercise.json only has questions, not answers or theory.
        # We must also pull from content.json so Gemini has the concepts,
        # formulas, and definitions needed to actually solve the exercises.
        exercise_results = _search_index(
            query_emb, bundle["exercise_index"], bundle["exercise_meta"], chapter, top_k
        )
        content_results = _search_index(
            query_emb, bundle["content_index"], bundle["content_meta"], chapter, top_k #// 2
        )
        return exercise_results + content_results

    return _search_index(
        query_emb, bundle["content_index"], bundle["content_meta"], chapter, top_k
    )
