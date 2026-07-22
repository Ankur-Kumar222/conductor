"""Pure-logic units: filter parsing, MIME body extraction, embedding cleanup."""
from __future__ import annotations

import base64
from datetime import datetime

from app.orchestrator.agents.base import filters_from_step
from app.orchestrator.agents.gmail import _extract_body
from app.search.embeddings import _clean
from tests.conftest import make_step


def test_filters_parse_iso_and_blanks():
    step = make_step("s", sender="sarah@co.com", after="2026-07-01T00:00:00Z")
    f = filters_from_step(step)
    assert f.sender == "sarah@co.com"
    assert isinstance(f.after, datetime)
    assert f.before is None  # blank -> None
    assert f.mime_type is None


def test_extract_body_prefers_text_plain_in_nested_mime():
    def b64(s: str) -> str:
        return base64.urlsafe_b64encode(s.encode()).decode()

    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {"mimeType": "text/html", "body": {"data": b64("<p>html</p>")}},
            {"mimeType": "text/plain", "body": {"data": b64("hello plain")}},
        ],
    }
    assert _extract_body(payload) == "hello plain"


def test_clean_truncates_and_handles_empty():
    assert _clean("") == " "
    assert _clean("x" * 10000) == "x" * 8000
    assert _clean("  hi  ") == "hi"
