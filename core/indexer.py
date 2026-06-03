"""
Indexer: Loads content.json and exercise.json from each book folder.
Builds FAISS vector indices for semantic search.
No OCR, no raw.json, no pass*.json — only the two JSON files matter.
"""
import json
import os
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from config.settings import CONFIG
from core.logger import get_logger

log = get_logger(__name__)
CACHE_SCHEMA_VERSION = 2  # bumped from original to force rebuild

_embedding_model = None
_loaded_subjects: dict[str, dict] = {}


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        log.info("Loading embedding model: %s", CONFIG["models"]["embedding"])
        _embedding_model = SentenceTransformer(CONFIG["models"]["embedding"])
    return _embedding_model


# ---------------------------------------------------------------------------
# Subject discovery — only folders with BOTH content.json AND exercise.json
# ---------------------------------------------------------------------------

def get_subjects() -> list[str]:
    books_dir = Path(CONFIG["paths"]["books_dir"])
    if not books_dir.exists():
        return []
    subjects = []
    for folder in sorted(os.listdir(books_dir)):
        path = books_dir / folder
        has_content = (path / "content.json").exists()
        has_exercise = (path / "exercise.json").exists()
        if path.is_dir() and has_content and has_exercise:
            subjects.append(folder)
    return subjects


def get_subject_display_name(subject: str) -> str:
    """Convert folder name like ssc_physics to SSC Physics."""
    return subject.replace("_", " ").title()


# ---------------------------------------------------------------------------
# JSON loading — only content.json and exercise.json
# ---------------------------------------------------------------------------

def load_subject(subject: str) -> tuple[list, list]:
    base = Path(CONFIG["paths"]["books_dir"]) / subject
    with open(base / "content.json", "r", encoding="utf-8") as f:
        content = json.load(f)
    with open(base / "exercise.json", "r", encoding="utf-8") as f:
        exercise = json.load(f)
    # Normalise: both must be lists of dicts
    if isinstance(content, dict):
        content = list(content.values())
    if isinstance(exercise, dict):
        exercise = list(exercise.values())
    return content, exercise


# ---------------------------------------------------------------------------
# FAISS cache helpers
# ---------------------------------------------------------------------------

def _cache_paths(subject: str) -> dict[str, Path]:
    base = Path(CONFIG["paths"]["books_dir"]) / subject
    return {
        "content_index": base / "content.faiss",
        "exercise_index": base / "exercise.faiss",
        "meta": base / "faiss_meta.json",
    }


def _cache_is_valid(cached: dict) -> bool:
    if cached.get("schema_version") != CACHE_SCHEMA_VERSION:
        log.info("Cache schema mismatch — rebuilding.")
        return False
    if cached.get("embedding_model") != CONFIG["models"]["embedding"]:
        log.info("Embedding model changed — rebuilding.")
        return False
    return bool(cached.get("dim"))


def _cache_is_fresh(subject: str) -> bool:
    paths = _cache_paths(subject)
    required = [paths["content_index"], paths["exercise_index"], paths["meta"]]
    if not all(p.exists() for p in required):
        return False
    base = Path(CONFIG["paths"]["books_dir"]) / subject
    src_mtime = max(
        (base / "content.json").stat().st_mtime,
        (base / "exercise.json").stat().st_mtime,
    )
    if min(p.stat().st_mtime for p in required) < src_mtime:
        return False
    try:
        with open(paths["meta"], "r", encoding="utf-8") as f:
            cached = json.load(f)
        return _cache_is_valid(cached)
    except Exception as exc:
        log.warning("Unreadable cache: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Text representation for embedding
# ---------------------------------------------------------------------------

def _text_for_item(item: dict, item_type: str) -> str:
    parts = [
        f"Chapter: {item.get('chapter', '')}",
        f"Topic: {item.get('topic', '')}",
        f"Subtopic: {item.get('subtopic', '')}",
        f"Type: {item_type}",
        f"Content: {item.get('content', '')}",
    ]
    return "\n".join(p for p in parts if p.split(": ", 1)[1].strip())


# ---------------------------------------------------------------------------
# Build / save / load index
# ---------------------------------------------------------------------------

def _build_faiss_index(texts: list[str]) -> tuple[faiss.Index, np.ndarray]:
    model = get_embedding_model()
    emb = np.array(model.encode(texts, show_progress_bar=False), dtype="float32")
    faiss.normalize_L2(emb)
    index = faiss.IndexFlatIP(emb.shape[1])
    index.add(emb)
    return index, emb


def build_index(content_data: list, exercise_data: list, subject: str | None = None) -> dict:
    if subject and subject in _loaded_subjects:
        return _loaded_subjects[subject]
    if subject and _cache_is_fresh(subject):
        return _load_index_cache(subject)

    log.info("Building FAISS index for subject=%s …", subject)
    content_texts = [_text_for_item(item, "concept") for item in content_data]
    exercise_texts = [_text_for_item(item, "exercise") for item in exercise_data]

    content_index, content_emb = _build_faiss_index(content_texts)
    exercise_index, _ = _build_faiss_index(exercise_texts)

    bundle = {
        "content_index": content_index,
        "exercise_index": exercise_index,
        "content_meta": list(content_data),
        "exercise_meta": list(exercise_data),
    }
    if subject:
        _loaded_subjects[subject] = bundle
        _save_index_cache(subject, bundle, content_emb.shape[1])
    log.info("FAISS ready for subject=%s (%d content, %d exercise)", subject, len(content_data), len(exercise_data))
    return bundle


def _save_index_cache(subject: str, bundle: dict, dim: int):
    paths = _cache_paths(subject)
    faiss.write_index(bundle["content_index"], str(paths["content_index"]))
    faiss.write_index(bundle["exercise_index"], str(paths["exercise_index"]))
    meta = {
        "content_meta": list(bundle["content_meta"]),
        "exercise_meta": list(bundle["exercise_meta"]),
        "embedding_model": CONFIG["models"]["embedding"],
        "schema_version": CACHE_SCHEMA_VERSION,
        "dim": dim,
    }
    with open(paths["meta"], "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)


def _load_index_cache(subject: str) -> dict:
    paths = _cache_paths(subject)
    with open(paths["meta"], "r", encoding="utf-8") as f:
        cached = json.load(f)
    if not _cache_is_valid(cached):
        content, exercise = load_subject(subject)
        return build_index(content, exercise, subject=subject)
    bundle = {
        "content_index": faiss.read_index(str(paths["content_index"])),
        "exercise_index": faiss.read_index(str(paths["exercise_index"])),
        "content_meta": cached["content_meta"],
        "exercise_meta": cached["exercise_meta"],
    }
    _loaded_subjects[subject] = bundle
    log.info("Loaded FAISS cache for subject=%s", subject)
    return bundle


def get_subject_bundle(subject: str) -> dict:
    if subject in _loaded_subjects:
        return _loaded_subjects[subject]
    content, exercise = load_subject(subject)
    return build_index(content, exercise, subject=subject)
