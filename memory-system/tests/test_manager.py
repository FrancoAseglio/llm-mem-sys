"""manager.ingest_user_message when the model fails: the message is kept, no facts are written,
and the caller is told. Needs the Postgres database from .env; no model calls.

    poetry run pytest tests/test_manager.py -v
"""

import numpy as np
import pytest

from memory_system import manager
from memory_system.db import get_pool

USER = "test_manager"


@pytest.fixture
def clean_user(monkeypatch):
    monkeypatch.setattr(manager, "embed", lambda text: np.ones(768, dtype=np.float32))
    with get_pool().connection() as c:
        c.execute("DELETE FROM users WHERE id = %s", (USER,))
    yield
    with get_pool().connection() as c:
        c.execute("DELETE FROM users WHERE id = %s", (USER,))


def test_extraction_failure_keeps_the_message_and_reports_it(monkeypatch, clean_user):
    def broken(text, relations):
        raise ValueError("model returned invalid JSON")

    monkeypatch.setattr(manager, "extract_facts", broken)

    assert manager.ingest_user_message(USER, "I live in Turin") == [
        ("extraction_failed", "", "")
    ]
    with get_pool().connection() as c:
        messages = c.execute(
            "SELECT count(*) FROM messages WHERE user_id = %s", (USER,)
        ).fetchone()[0]
        facts = c.execute(
            "SELECT count(*) FROM facts WHERE user_id = %s", (USER,)
        ).fetchone()[0]
        reason = c.execute(
            "SELECT details->>'reason' FROM memory_events WHERE user_id = %s", (USER,)
        ).fetchone()[0]
    assert (messages, facts, reason) == (1, 0, "extraction failed")
