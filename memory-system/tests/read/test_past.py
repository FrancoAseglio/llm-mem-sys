"""Past-question rules (pure) and the database path (needs Postgres)."""

from datetime import datetime, timezone

import pytest

from memory_system.read.past_retrieve import select_past
from memory_system.read.past_rules import drop_active_values, is_past_question
from memory_system.read.retrieve import Memory


@pytest.mark.parametrize(
    "q",
    [
        "Which city did I live in before Tallinn?",
        "What food did I use to dislike?",
        "Where did I work previously?",
        "Where did I live originally?",
        "Who did I date back then?",
        "What was I doing in the past?",
        "Where did I live prior to Rome?",
        "Which food did I use to hate?",
        "BEFORE the move, where was I?",
    ],
)
def test_past_questions_fire(q):
    assert is_past_question(q)


@pytest.mark.parametrize(
    "q",
    [
        "Which city do I live in now?",
        "What's my name?",
        "Is it safe to take aspirin?",  # no trigger word
        "Where was home when I was a student?",  # a known miss of the keyword list
        "Tell me about the beforehand preparations",  # 'before' inside a longer word
        "What do I use to cook rice?",  # "use to" alone is not a trigger
        "",
    ],
)
def test_other_questions_do_not_fire(q):
    assert not is_past_question(q)


def _mem(relation, value, raw, until=None):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return Memory(1, relation, value, now, raw, False, {}, raw_similarity=raw,
                  relation_rank=1, until=until or now)


def test_drop_active_values():
    past = [_mem("lives_in", "Turin", 0.6), _mem("lives_in", "Milan", 0.6)]
    kept = drop_active_values(past, {("lives_in", "milan")})
    assert [m.value for m in kept] == ["Turin"]


def test_select_past_gate_and_limit():
    scored = [
        _mem("lives_in", "A", 0.70),
        _mem("lives_in", "B", 0.66),
        _mem("lives_in", "C", 0.64),  # within the window but over the line limit
        _mem("lives_in", "D", 0.30),  # under the floor
        _mem("hobby", "E", 0.50),  # outside the window
    ]
    assert [m.value for m in select_past(scored, set(), 2)] == ["A", "B"]


def test_select_past_nothing_relevant():
    assert select_past([_mem("lives_in", "A", 0.30)], set(), 2) == []


def test_allergy_gets_no_bypass_in_the_past():
    scored = [_mem("lives_in", "A", 0.70), _mem("allergic_to", "peanuts", 0.20)]
    assert [m.value for m in select_past(scored, set(), 2)] == ["A"]


# ---- database path ----

import numpy as np

from memory_system.core.db import get_pool
from memory_system.read import past_retrieve, retrieve
from memory_system.write import conflicts

USER = "test_past"


def fake_embed(text: str) -> np.ndarray:
    return np.ones(768, dtype=np.float32)


@pytest.fixture
def conn(monkeypatch):
    monkeypatch.setattr(conflicts, "embed", fake_embed)
    monkeypatch.setattr(retrieve, "embed", fake_embed)
    monkeypatch.setattr(retrieve, "_relation_vecs", None)
    monkeypatch.setattr(retrieve, "ROUTING_TOP_N", 0)  # identical vectors make routing a tie
    with get_pool().connection() as c:
        c.execute("DELETE FROM users WHERE id = %s", (USER,))
        c.execute("INSERT INTO users (id) VALUES (%s)", (USER,))
        try:
            yield c
        finally:
            c.rollback()
            c.execute("DELETE FROM users WHERE id = %s", (USER,))
            c.commit()


def _moved(conn):
    conflicts.apply_fact(conn, USER, "lives_in", "Bergen", None)
    conflicts.apply_fact(conn, USER, "lives_in", "Tallinn", None)
    conn.commit()  # the retrieval functions read through their own connections


def test_replaced_value_is_returned_for_a_past_question(conn):
    _moved(conn)
    got = past_retrieve.retrieve_past(USER, "Where did I live before?", touch=False)
    assert [(m.value, m.until is not None) for m in got] == [("Bergen", True)]


def test_nothing_for_a_present_question(conn):
    _moved(conn)
    assert past_retrieve.retrieve_past(USER, "Where do I live now?", touch=False) == []


def test_nothing_when_nothing_was_replaced(conn):
    conflicts.apply_fact(conn, USER, "lives_in", "Leiden", None)
    conn.commit()
    assert past_retrieve.retrieve_past(USER, "Where did I live before?", touch=False) == []


def test_switch_off(conn, monkeypatch):
    _moved(conn)
    monkeypatch.setattr(past_retrieve, "PAST_FACTS", False)
    assert past_retrieve.retrieve_past(USER, "Where did I live before?", touch=False) == []


def test_archived_fact_is_not_a_past_value(conn):
    conflicts.apply_fact(conn, USER, "lives_in", "Bergen", None)
    conn.execute(
        "UPDATE facts SET status = 'archived' WHERE user_id = %s", (USER,)
    )
    conn.commit()
    assert past_retrieve.retrieve_past(USER, "Where did I live before?", touch=False) == []
