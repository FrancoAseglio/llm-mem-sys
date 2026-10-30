"""Hybrid and full modes: the pure rules, the evaluation's stale split, and the database path
(needs Postgres). No model calls: every embedding is the same constant vector."""

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from evaluation.metrics import stale_split
from evaluation.report import _compare
from memory_system import assistant
from memory_system.core.db import get_pool
from memory_system.read import hybrid, retrieve
from memory_system.read.hybrid_rules import (
    fact_marker,
    is_marked,
    marked_message,
    timeline_line,
)
from memory_system.read.retrieve import Memory
from memory_system.write import conflicts

# ---- pure rules ----


def test_superseded_fact_is_marked_with_the_current_value():
    end = ("lives_in", "Kristiansand", "active")
    assert (
        fact_marker("lives_in", "Oslo", end)
        == "[outdated: Lives in: Oslo -> now Kristiansand]"
    )


def test_a_flip_to_another_relation_names_it():
    end = ("dislikes", "coffee", "active")
    assert (
        fact_marker("likes", "coffee", end)
        == "[outdated: Likes: coffee -> now Dislikes: coffee]"
    )


def test_retracted_fact_is_no_longer_true():
    assert fact_marker("hobby", "bass", None) == "[no longer true: Hobby: bass]"


def test_chain_ending_in_a_retraction_is_no_longer_true():
    end = ("lives_in", "Oslo", "archived")
    assert (
        fact_marker("lives_in", "Bergen", end) == "[no longer true: Lives in: Bergen]"
    )


def test_moved_back_gives_no_marker():
    assert fact_marker("lives_in", "Bergen", ("lives_in", "bergen", "active")) is None


def test_marked_message():
    assert marked_message('"x"', []) == '"x"'
    assert marked_message('"x"', ["[a]", "[b]"]) == '"x" [a] [b]'


def test_timeline_oldest_first_with_now():
    values = [
        ("Stavanger", "superseded"),
        ("Oslo", "superseded"),
        ("Kristiansand", "active"),
    ]
    assert (
        timeline_line("lives_in", values)
        == "Lives in, oldest first: Stavanger -> Oslo -> Kristiansand (now)"
    )


def test_timeline_merges_repeats_and_tags_ended_values():
    values = [("Halvorsen", "superseded"), ("halvorsen", "archived")]
    assert (
        timeline_line("works_at", values) == "Works at, oldest first: Halvorsen (ended)"
    )


def test_timeline_needs_a_history():
    assert timeline_line("lives_in", []) is None
    assert timeline_line("lives_in", [("Oslo", "active")]) is None


@pytest.mark.parametrize(
    "line, marked",
    [
        (
            '[2025-01-01] "I moved to Oslo" [outdated: Lives in: Oslo -> now Bergen]',
            True,
        ),
        ('[2025-01-01] "I play bass" [no longer true: Hobby: bass]', True),
        ("Lives in, oldest first: Oslo -> Bergen (now)", True),
        ('[2025-01-01] "I moved to Oslo"', False),
        # smart's lines are not marked: its metrics stay as they were
        ("Earlier: Lives in: Oslo (until 2025-01-01)", False),
    ],
)
def test_is_marked(line, marked):
    assert is_marked(line) is marked


def test_stale_split():
    question = {"stale": ["oslo"]}
    marked = [
        '"I moved to Oslo" [outdated: Lives in: Oslo -> now Bergen]',
        '"I love Bergen"',
    ]
    plain = ['"I moved to Oslo"', '"I love Bergen"']
    assert stale_split(marked, question) == (False, True)
    assert stale_split(plain, question) == (True, False)
    assert stale_split(marked + plain, question) == (True, False)
    assert stale_split(['"I love Bergen"'], question) == (False, False)
    assert stale_split(marked, {}) == (False, False)


def test_compare_best_and_worst():
    assert _compare(["48/57", "43/57", "50/57"], True) == ["", "red", "green"]
    assert _compare(["4.0", "2.2", "6.1"], False) == ["", "green", "red"]
    assert _compare(["3", "3", "3"], False) == ["", "", ""]
    assert _compare(["-", "2/3"], True) == ["", ""]


# ---- database path ----

USER = "test_hybrid"
START = datetime(2025, 1, 1, tzinfo=UTC)


def fake_embed(text: str) -> np.ndarray:
    return np.ones(768, dtype=np.float32)


@pytest.fixture
def conn(monkeypatch):
    monkeypatch.setattr(conflicts, "embed", fake_embed)
    monkeypatch.setattr(retrieve, "embed", fake_embed)
    monkeypatch.setattr(retrieve, "_relation_vecs", None)
    monkeypatch.setattr(
        retrieve, "ROUTING_TOP_N", 0
    )  # identical vectors make routing a tie
    with get_pool().connection() as c:
        c.execute("DELETE FROM users WHERE id = %s", (USER,))
        c.execute("INSERT INTO users (id) VALUES (%s)", (USER,))
        try:
            yield c
        finally:
            c.rollback()
            c.execute("DELETE FROM users WHERE id = %s", (USER,))
            c.commit()


def say(conn, day: int, text: str, relation=None, value=None, action="assert"):
    """Store one user message on day `day`, and the fact it gives, if any."""
    at = START + timedelta(days=day)
    message_id = conn.execute(
        "INSERT INTO messages (user_id, role, content, embedding, created_at) "
        "VALUES (%s, 'user', %s, %s, %s) RETURNING id",
        (USER, text, fake_embed(text), at),
    ).fetchone()[0]
    if relation:
        conflicts.apply_fact(
            conn, USER, relation, value, message_id, at=at, action=action
        )
    return message_id


def lines_for(question: str, k: int = 4) -> list[str]:
    return assistant.recall("hybrid", USER, question, k, touch=False)


def message_line(lines: list[str], text: str) -> str:
    return next(line for line in lines if f'"{text}"' in line)


def test_old_message_is_marked_with_the_current_value(conn):
    say(conn, 0, "I live in Bergen", "lives_in", "Bergen")
    say(conn, 30, "I moved to Oslo", "lives_in", "Oslo")
    say(conn, 60, "I moved to Tallinn", "lives_in", "Tallinn")
    conn.commit()
    lines = lines_for("Where do I live?")
    assert message_line(lines, "I live in Bergen").endswith(
        "[outdated: Lives in: Bergen -> now Tallinn]"
    )
    assert message_line(lines, "I moved to Oslo").endswith(
        "[outdated: Lives in: Oslo -> now Tallinn]"
    )
    assert message_line(lines, "I moved to Tallinn").endswith('"I moved to Tallinn"')


def test_facts_come_first_two_kinds_at_most(conn):
    say(conn, 0, "I live in Bergen", "lives_in", "Bergen")
    say(conn, 1, "I work at Kiwibyte", "works_at", "Kiwibyte")
    say(conn, 2, "I play chess", "hobby", "chess")
    conn.commit()
    lines = lines_for("Tell me about me")
    facts = [line for line in lines if not line.startswith("[")]
    assert len(facts) == 2  # three kinds of fact pass, two are shown
    assert lines[:2] == facts
    assert all(line.startswith("[2025-") for line in lines[2:])


def test_every_value_of_a_shown_kind(conn):
    say(conn, 0, "I speak German, English and Danish", "speaks", "German")
    conflicts.apply_fact(conn, USER, "speaks", "English", None)
    conflicts.apply_fact(conn, USER, "speaks", "Danish", None)
    conn.commit()
    facts = [
        line for line in lines_for("Which languages?") if line.startswith("Speaks")
    ]
    assert len(facts) == 3  # set N: a cap of two lines dropped Danish


def test_top_relations():
    def m(relation, value):
        return Memory(0, relation, value, START, 0.0, False, {})

    facts = [m("speaks", "a"), m("lives_in", "b"), m("speaks", "c"), m("hobby", "d")]
    got = hybrid.top_relations(facts, 2, 4)
    assert [x.value for x in got] == ["a", "b", "c"]
    assert [x.value for x in hybrid.top_relations(facts, 2, 2)] == ["a", "b"]


def test_top_relations_one_line_for_a_kind_that_is_not_a_list():
    def m(relation, value):
        return Memory(0, relation, value, START, 0.0, False, {})

    # fixes_N: three family names filled the prompt for "Where does my sister live?"
    facts = [
        m("family_member", "Lucia"),
        m("lives_in", "Grenoble"),
        m("family_member", "dad"),
        m("family_member", "Bastien"),
    ]
    got = hybrid.top_relations(facts, 2, 4)
    assert [x.value for x in got] == ["Lucia", "Grenoble"]


def test_retracted_value_is_marked(conn):
    say(conn, 0, "I play bass in a covers band", "hobby", "bass")
    say(conn, 30, "I quit the band, no more bass", "hobby", "bass", action="retract")
    conn.commit()
    lines = lines_for("What are my hobbies?")
    line = message_line(lines, "I play bass in a covers band")
    assert line.endswith("[no longer true: Hobby: bass]")


def test_moved_back_is_not_marked(conn):
    say(conn, 0, "I live in Bergen", "lives_in", "Bergen")
    say(conn, 30, "I moved to Oslo", "lives_in", "Oslo")
    say(conn, 60, "Back in Bergen again", "lives_in", "Bergen")
    conn.commit()
    lines = lines_for("Where do I live?")
    assert message_line(lines, "I live in Bergen").endswith('"I live in Bergen"')
    assert message_line(lines, "I moved to Oslo").endswith(
        "[outdated: Lives in: Oslo -> now Bergen]"
    )


def test_timeline_for_a_past_question_only(conn):
    say(conn, 0, "I live in Stavanger", "lives_in", "Stavanger")
    say(conn, 30, "I moved to Oslo", "lives_in", "Oslo")
    say(conn, 60, "Transferred to Kristiansand", "lives_in", "Kristiansand")
    conn.commit()
    timeline = "Lives in, oldest first: Stavanger -> Oslo -> Kristiansand (now)"
    past = lines_for("Where did I live before Oslo?")
    assert past[1] == timeline  # after the one fact line, before the messages
    assert timeline not in lines_for("Where do I live?")


def test_timeline_includes_a_retracted_employer(conn):
    say(conn, 0, "I work at Halvorsen Marine", "works_at", "Halvorsen Marine")
    say(conn, 30, "I left Halvorsen", "works_at", "Halvorsen Marine", action="retract")
    conn.commit()
    lines = lines_for("Where did I work previously?")
    assert "Works at, oldest first: Halvorsen Marine (ended)" in lines


def test_switches(conn, monkeypatch):
    say(conn, 0, "I live in Bergen", "lives_in", "Bergen")
    say(conn, 30, "I moved to Oslo", "lives_in", "Oslo")
    conn.commit()
    monkeypatch.setattr(hybrid, "HYBRID_MARKERS", False)
    monkeypatch.setattr(hybrid, "HYBRID_TIMELINE", False)
    lines = lines_for("Where did I live before?")
    assert not any(is_marked(line) for line in lines)


def test_baseline_unchanged_by_the_refactor(conn):
    say(conn, 0, "first")
    say(conn, 1, "second")
    conn.commit()
    rows = retrieve.retrieve_baseline(USER, "anything", 4)
    assert sorted(r[0] for r in rows) == ["first", "second"]
    assert all(len(r) == 3 for r in rows)


def test_full_is_every_message_oldest_first(conn):
    say(conn, 5, "later")
    say(conn, 0, "earliest")
    conn.commit()
    assert assistant.recall("full", USER, "anything", touch=False) == [
        '[2025-01-01] "earliest"',
        '[2025-01-06] "later"',
    ]


def test_prompt_headers():
    for mode in ("hybrid", "full"):
        system = assistant.build_messages(mode, ["x"], [], "q")[0]["content"]
        assert assistant.HEADERS[mode] in system
