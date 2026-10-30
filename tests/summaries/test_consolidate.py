"""Consolidation against the database, with the model and the embeddings replaced.
Needs the Postgres database from .env. Every test runs against a throwaway user.

    poetry run pytest tests/summaries/test_consolidate.py -v
"""

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from memory_system.core.db import get_pool
from memory_system.summaries import consolidate as consolidate_module
from memory_system.summaries import retrieve as summary_retrieve
from memory_system.summaries.consolidate import Digest, DigestList, consolidate

USER = "test_consolidate"

# (source message, note written from it); every note is about the same kitchen story
KITCHEN = [
    (
        "The contractor, a guy named Tobias, quoted us 18,000 euros for the kitchen.",
        "The user was quoted 18,000 euros for the kitchen by contractor Tobias.",
    ),
    (
        "The final bill for the kitchen came to 21,500 euros, more than the quote.",
        "The final bill for the kitchen came to 21,500 euros, more than the quote.",
    ),
    (
        "We went with oak cabinets for the kitchen.",
        "The user went with oak cabinets for the kitchen.",
    ),
    (
        "The kitchen countertop is a slab of grey granite.",
        "The user's kitchen countertop is a slab of grey granite.",
    ),
    (
        "The new oven arrived with a big dent, so we sent it back.",
        "The user sent back a new oven that arrived with a big dent.",
    ),
    (
        "We hosted our first dinner in the new kitchen for eight friends.",
        "The user hosted the first dinner in the new kitchen for eight friends.",
    ),
]
GOOD_DIGEST = (
    "The user's kitchen, quoted at 18,000 euros by Tobias and billed 21,500 euros, has oak "
    "cabinets and a granite countertop."
)


def fake_embed(text: str) -> np.ndarray:
    return np.ones(768, dtype=np.float32)


@pytest.fixture
def user(monkeypatch):
    monkeypatch.setattr(consolidate_module, "embed", fake_embed)
    monkeypatch.setattr(summary_retrieve, "embed", fake_embed)
    monkeypatch.setattr(summary_retrieve, "CONSOLIDATE", True)
    with get_pool().connection() as c:
        c.execute("DELETE FROM users WHERE id = %s", (USER,))
        c.execute("INSERT INTO users (id) VALUES (%s)", (USER,))
    yield USER
    with get_pool().connection() as c:
        c.execute("DELETE FROM users WHERE id = %s", (USER,))


def add_note(message: str, note: str, days_ago: int) -> tuple[int, int]:
    """Store a message and the note written from it, both dated days_ago. Returns their ids."""
    at = datetime.now(UTC) - timedelta(days=days_ago)
    with get_pool().connection() as c:
        note_id = c.execute(
            "INSERT INTO summaries (user_id, content, period_start, period_end, embedding) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (USER, note, at, at, fake_embed(note)),
        ).fetchone()[0]
        message_id = c.execute(
            "INSERT INTO messages (user_id, role, content, embedding, summary_id, created_at) "
            "VALUES (%s, 'user', %s, %s, %s, %s) RETURNING id",
            (USER, message, fake_embed(message), note_id, at),
        ).fetchone()[0]
    return message_id, note_id


def add_kitchen(days_ago: int = 60) -> list[tuple[int, int]]:
    """The kitchen notes, the first one oldest: the model numbers old notes oldest first, so
    note 1 in a fake Digest is KITCHEN[0]."""
    last = len(KITCHEN) - 1
    return [add_note(m, n, days_ago + last - i) for i, (m, n) in enumerate(KITCHEN)]


def model_says(monkeypatch, *digests: Digest):
    calls = []

    def fake(system, prompt, schema):
        calls.append(prompt)
        return DigestList(digests=list(digests))

    monkeypatch.setattr(consolidate_module, "chat_structured", fake)
    return calls


def rows():
    with get_pool().connection() as c:
        return c.execute(
            "SELECT id, kind, content, digest_id FROM summaries WHERE user_id = %s ORDER BY id",
            (USER,),
        ).fetchall()


def last_event():
    with get_pool().connection() as c:
        return c.execute(
            "SELECT details FROM memory_events WHERE user_id = %s AND event_type = 'consolidate' "
            "ORDER BY id DESC LIMIT 1",
            (USER,),
        ).fetchone()[0]


def test_a_good_digest_replaces_its_notes(user, monkeypatch):
    add_kitchen()
    model_says(monkeypatch, Digest(text=GOOD_DIGEST, notes=[1, 2, 3, 4]))
    assert consolidate(user) == [GOOD_DIGEST]
    stored = rows()
    digest = [r for r in stored if r[1] == "digest"]
    assert len(digest) == 1
    merged = [r for r in stored if r[3] == digest[0][0]]
    assert len(merged) == 4  # the four cited notes point to it and are kept
    assert last_event()["kept"] == [digest[0][0]]


def test_retrieval_reads_the_digest_and_the_notes_it_did_not_replace(user, monkeypatch):
    add_kitchen()
    model_says(monkeypatch, Digest(text=GOOD_DIGEST, notes=[1, 2, 3, 4]))
    consolidate(user)
    lines = summary_retrieve.retrieve_summaries(
        user, "q", [], k=4, touch=False
    )  # all similarities are equal, so the first two candidates are shown
    texts = " ".join(lines)
    assert "quoted us" not in texts and "was quoted 18,000" not in texts
    with get_pool().connection() as c:
        live = c.execute(
            "SELECT count(*) FROM summaries WHERE user_id = %s AND digest_id IS NULL",
            (USER,),
        ).fetchone()[0]
    assert live == 3  # the digest and the two notes it did not cite


def test_with_consolidation_off_retrieval_reads_the_plain_notes(user, monkeypatch):
    add_kitchen()
    model_says(monkeypatch, Digest(text=GOOD_DIGEST, notes=[1, 2, 3, 4]))
    consolidate(user)
    monkeypatch.setattr(summary_retrieve, "CONSOLIDATE", False)
    lines = summary_retrieve.retrieve_summaries(user, "q", [], k=4, touch=False)
    assert lines and all(GOOD_DIGEST not in line for line in lines)


def test_too_few_old_notes_make_no_model_call(user, monkeypatch):
    for message, note in KITCHEN[:5]:
        add_note(message, note, 60)
    calls = model_says(monkeypatch)
    assert consolidate(user) == []
    assert calls == []


def test_recent_notes_are_never_sent_to_the_model(user, monkeypatch):
    add_kitchen(days_ago=60)
    add_note("Last week I planted tomatoes.", "The user planted tomatoes last week.", 7)
    calls = model_says(monkeypatch)
    consolidate(user)
    assert len(calls) == 1 and "tomatoes" not in calls[0]


def test_a_digest_that_drops_a_number_is_dropped_and_its_notes_stay(user, monkeypatch):
    add_kitchen()
    short = "The user's kitchen by Tobias cost 21,500 euros and has oak cabinets."
    model_says(monkeypatch, Digest(text=short, notes=[1, 2, 3]))
    assert consolidate(user) == []
    assert all(r[1] == "note" and r[3] is None for r in rows())
    dropped = last_event()["dropped"][0]
    assert dropped["reason"] == "dropped details" and dropped["missing"] == ["18000"]


def test_an_invented_name_is_not_faithful(user, monkeypatch):
    add_kitchen()
    # an invented lowercase word ("marble" for "granite") would pass: the check is word-level
    invented = GOOD_DIGEST.replace("by Tobias", "by Tobias and Greta")
    model_says(monkeypatch, Digest(text=invented, notes=[1, 2, 3, 4]))
    assert consolidate(user) == []
    assert last_event()["dropped"][0]["reason"] == "not faithful"


def test_a_digest_longer_than_its_notes_is_dropped(user, monkeypatch):
    add_kitchen()
    long_digest = (
        "The user's kitchen countertop is a slab of grey granite, and the user went with oak "
        "cabinets for the kitchen, a choice made for the kitchen."
    )
    model_says(monkeypatch, Digest(text=long_digest, notes=[3, 4]))
    assert consolidate(user) == []
    assert last_event()["dropped"][0]["reason"] == "not shorter"


def test_a_digest_of_one_note_and_an_overlapping_digest_are_dropped(user, monkeypatch):
    add_kitchen()
    model_says(
        monkeypatch,
        Digest(text=GOOD_DIGEST, notes=[1, 2, 3, 4]),
        Digest(text="The user went with oak cabinets.", notes=[3]),
        Digest(text="The user's kitchen has oak cabinets and granite.", notes=[3, 4]),
    )
    assert consolidate(user) == [GOOD_DIGEST]
    reasons = [d["reason"] for d in last_event()["dropped"]]
    assert reasons == ["fewer than 2 notes", "note already merged"]


def test_the_same_notes_are_not_sent_twice(user, monkeypatch):
    add_kitchen()
    calls = model_says(monkeypatch)  # the model merges nothing
    consolidate(user)
    consolidate(user)
    assert len(calls) == 1


def test_a_model_failure_logs_a_reject_and_stores_nothing(user, monkeypatch):
    add_kitchen()

    def broken(system, prompt, schema):
        raise ValueError("model returned invalid JSON")

    monkeypatch.setattr(consolidate_module, "chat_structured", broken)
    assert consolidate(user) == []
    assert all(r[1] == "note" for r in rows())
    with get_pool().connection() as c:
        reason = c.execute(
            "SELECT details->>'reason' FROM memory_events "
            "WHERE user_id = %s AND event_type = 'reject'",
            (USER,),
        ).fetchone()[0]
    assert reason == "consolidation failed"


def test_a_digest_is_hidden_when_a_source_fact_of_its_notes_is_outdated(
    user, monkeypatch
):
    ids = add_kitchen()
    model_says(monkeypatch, Digest(text=GOOD_DIGEST, notes=[1, 2, 3, 4]))
    consolidate(user)
    with get_pool().connection() as c:  # the second message's fact is later replaced
        c.execute(
            "INSERT INTO facts (user_id, relation, value, status, source_message_id, embedding) "
            "VALUES (%s, 'likes', 'oak cabinets', 'superseded', %s, %s)",
            (USER, ids[2][0], fake_embed("x")),
        )
    lines = summary_retrieve.retrieve_summaries(user, "q", [], k=4, touch=False)
    assert all(GOOD_DIGEST not in line for line in lines)
