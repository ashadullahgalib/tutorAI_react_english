"""
Tests for TUTOR AI — core logic.
Run with: pytest tests/
"""
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault("API_SECRET_KEY", "test-secret")


# ---------------------------------------------------------------------------
# Session tests
# ---------------------------------------------------------------------------

class TestSessionState:
    def test_remember_trims_history(self):
        from core.session import SessionState
        s = SessionState()
        for i in range(25):
            s.remember("user", f"msg {i}", limit=10)
        assert len(s.chat_history) == 10

    def test_reset_clears_all(self):
        from core.session import SessionState
        s = SessionState()
        s.remember("user", "hello", limit=20)
        s.current_topic = "biology"
        s.reset()
        assert s.chat_history == []
        assert s.current_topic is None

    def test_update_from_retrieved(self):
        from core.session import SessionState
        s = SessionState()
        s.update_from_retrieved([{"topic": "Cell", "subtopic": "Membrane"}])
        assert "cell" in s.current_topic
        assert "membrane" in s.active_concept


# ---------------------------------------------------------------------------
# Retriever / query logic tests
# ---------------------------------------------------------------------------

class TestRetriever:
    def test_resolve_query_no_pronoun(self):
        from chat.retriever import resolve_query
        from core.session import SessionState
        s = SessionState()
        s.active_concept = "photosynthesis"
        result = resolve_query("What is respiration?", s)
        assert result == "What is respiration?"

    def test_resolve_query_with_pronoun(self):
        from chat.retriever import resolve_query
        from core.session import SessionState
        s = SessionState()
        s.last_answer_entity = "mitosis"
        result = resolve_query("How does it work?", s)
        assert "mitosis" in result


# ---------------------------------------------------------------------------
# Responder tests
# ---------------------------------------------------------------------------

class TestResponder:
    def test_detect_mode_exercise(self):
        from chat.responder import detect_mode
        assert detect_mode("Give me an MCQ from chapter 3") == "exercise"
        assert detect_mode("Solve this CQ") == "exercise"

    def test_detect_mode_content(self):
        from chat.responder import detect_mode
        assert detect_mode("What is photosynthesis?") == "content"
        assert detect_mode("Explain Newton's laws") == "content"

    def test_extract_chapter_digit(self):
        from chat.responder import extract_chapter
        assert extract_chapter("Questions from chapter 5") == "chapter 5"

    def test_extract_chapter_word(self):
        from chat.responder import extract_chapter
        assert extract_chapter("chapter three problems") == "chapter three"

    def test_extract_chapter_none(self):
        from chat.responder import extract_chapter
        assert extract_chapter("What is photosynthesis?") is None


# ---------------------------------------------------------------------------
# Indexer tests
# ---------------------------------------------------------------------------

class TestIndexer:
    def test_get_subjects_empty_dir(self, tmp_path):
        from config import settings as cfg_settings
        orig = cfg_settings.CONFIG["paths"]["books_dir"]
        cfg_settings.CONFIG["paths"]["books_dir"] = str(tmp_path)

        from core import indexer
        # clear cached subjects
        indexer._loaded_subjects.clear()
        subjects = indexer.get_subjects()
        assert subjects == []

        cfg_settings.CONFIG["paths"]["books_dir"] = orig

    def test_get_subjects_finds_valid_folder(self, tmp_path):
        from config import settings as cfg_settings
        orig = cfg_settings.CONFIG["paths"]["books_dir"]
        cfg_settings.CONFIG["paths"]["books_dir"] = str(tmp_path)

        book = tmp_path / "test_book"
        book.mkdir()
        (book / "content.json").write_text(json.dumps([{"chapter": "1", "topic": "T", "subtopic": "S", "content": "hello"}]))
        (book / "exercise.json").write_text(json.dumps([{"chapter": "1", "topic": "T", "subtopic": "S", "content": "q1"}]))

        from core import indexer
        indexer._loaded_subjects.clear()
        subjects = indexer.get_subjects()
        assert "test_book" in subjects

        cfg_settings.CONFIG["paths"]["books_dir"] = orig

    def test_get_subjects_skips_folder_without_both_files(self, tmp_path):
        from config import settings as cfg_settings
        orig = cfg_settings.CONFIG["paths"]["books_dir"]
        cfg_settings.CONFIG["paths"]["books_dir"] = str(tmp_path)

        # Only content.json, no exercise.json
        book = tmp_path / "incomplete_book"
        book.mkdir()
        (book / "content.json").write_text("[]")

        from core import indexer
        indexer._loaded_subjects.clear()
        subjects = indexer.get_subjects()
        assert "incomplete_book" not in subjects

        cfg_settings.CONFIG["paths"]["books_dir"] = orig
