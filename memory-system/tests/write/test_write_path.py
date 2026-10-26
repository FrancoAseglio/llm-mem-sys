"""Deterministic tests for the write path: conflicts.apply_fact with hand-written facts.

No model calls: embeddings are replaced by a constant vector. Needs the Postgres database
from .env. Every test runs against a throwaway user that is deleted afterwards.

    poetry run pytest tests/test_write_path.py -v
"""

import numpy as np
import pytest

from memory_system.core.db import get_pool
from memory_system.read import retrieve
from memory_system.write import conflicts

USER = "test_write_path"


def fake_embed(text: str) -> np.ndarray:
    return np.ones(768, dtype=np.float32)


@pytest.fixture
def conn(monkeypatch):
    monkeypatch.setattr(conflicts, "embed", fake_embed)
    with get_pool().connection() as c:
        c.execute("DELETE FROM users WHERE id = %s", (USER,))
        c.execute("INSERT INTO users (id) VALUES (%s)", (USER,))
        try:
            yield c
        finally:
            c.rollback()
            c.execute("DELETE FROM users WHERE id = %s", (USER,))
            c.commit()


def apply(conn, relation, value, **kw):
    return conflicts.apply_fact(conn, USER, relation, value, None, **kw)


def rows(conn, relation):
    """{value: (status, id, superseded_by, valid_to is set)} for every fact of a relation."""
    return {
        value: (status, fid, sup, valid_to is not None)
        for fid, value, status, sup, valid_to in conn.execute(
            """SELECT id, value, status, superseded_by, valid_to FROM facts
               WHERE user_id = %s AND relation = %s""",
            (USER, relation),
        ).fetchall()
    }


def events(conn):
    return conn.execute(
        "SELECT event_type, fact_id, details FROM memory_events WHERE user_id = %s ORDER BY id",
        (USER,),
    ).fetchall()


# ---- existing behaviour ----


def test_duplicate_strengthens_existing(conn):
    assert apply(conn, "hobby", "cycling") == "add"
    assert apply(conn, "hobby", "Cycling") == "duplicate"
    assert list(rows(conn, "hobby")) == ["cycling"]
    conf = conn.execute(
        "SELECT confidence FROM facts WHERE user_id = %s", (USER,)
    ).fetchone()[0]
    assert conf == pytest.approx(0.85)


def test_add_first_value(conn):
    assert apply(conn, "lives_in", "Turin") == "add"
    assert rows(conn, "lives_in")["Turin"][0] == "active"


def test_single_cardinality_supersedes_never_overwrites(conn):
    apply(conn, "lives_in", "Turin")
    assert apply(conn, "lives_in", "Milan") == "update"
    facts = rows(conn, "lives_in")
    assert facts["Milan"][0] == "active"
    status, _, superseded_by, ended = facts["Turin"]
    assert (status, superseded_by, ended) == ("superseded", facts["Milan"][1], True)


def test_multi_cardinality_adds(conn):
    apply(conn, "hobby", "cycling")
    assert apply(conn, "hobby", "climbing") == "add"
    assert {v: s[0] for v, s in rows(conn, "hobby").items()} == {
        "cycling": "active",
        "climbing": "active",
    }


# ---- 1. retraction ----


def test_retract_archives_matching_fact(conn):
    apply(conn, "allergic_to", "peanuts")
    assert apply(conn, "allergic_to", "Peanuts", action="retract") == "retract"
    status, fid, _, ended = rows(conn, "allergic_to")["peanuts"]
    assert (status, ended) == ("archived", True)  # kept, not deleted
    assert events(conn)[-1][:2] == ("retract", fid)


def test_retract_without_match_changes_nothing(conn):
    apply(conn, "allergic_to", "peanuts")
    assert apply(conn, "allergic_to", "shellfish", action="retract") == "retract_miss"
    assert rows(conn, "allergic_to")["peanuts"][0] == "active"
    assert list(rows(conn, "allergic_to")) == ["peanuts"]
    assert events(conn)[-1][:2] == ("retract", None)


def test_not_x_but_y(conn):
    apply(conn, "speaks", "French")
    apply(conn, "speaks", "French", action="retract")
    apply(conn, "speaks", "Spanish")
    assert {v: s[0] for v, s in rows(conn, "speaks").items()} == {
        "French": "archived",
        "Spanish": "active",
    }


# ---- 2. grounding ----


def test_grounding_rejects_value_not_in_message(conn):
    text = "Exciting news, I just started a new position at Delta Labs!"
    assert apply(conn, "job_title", "new job", source_text=text) == "rejected"
    assert rows(conn, "job_title") == {}
    event_type, fact_id, details = events(conn)[-1]
    assert (event_type, fact_id) == ("reject", None)
    assert details["value"] == "new job" and details["reason"]


def test_grounding_rejects_value_without_content_word(conn):
    # "new" and "job" are generic words: nothing to check, so rejected even though present
    assert (
        apply(
            conn,
            "job_title",
            "new job",
            source_text="I just started a new job at Globex!",
        )
        == "rejected"
    )


def test_grounding_accepts_inflected_words(conn):
    assert (
        apply(conn, "allergic_to", "walnut", source_text="I'm allergic to walnuts.")
        == "add"
    )
    assert (
        apply(
            conn,
            "goal",
            "sailing",
            source_text="I'd love to learn how to sail one day.",
        )
        == "add"
    )
    assert (
        apply(
            conn,
            "dislikes",
            "anchovy",
            source_text="I really hate anchovies, the smell is awful.",
        )
        == "add"
    )


def test_grounding_ignores_stopwords(conn):
    # "really" is the only shared word of 4+ letters
    assert (
        apply(conn, "likes", "really nice food", source_text="I really like this one.")
        == "rejected"
    )


def test_grounding_applies_to_retractions(conn):
    apply(conn, "allergic_to", "peanuts")
    assert (
        apply(
            conn,
            "allergic_to",
            "peanuts",
            action="retract",
            source_text="Never mind what I said about shellfish.",
        )
        == "rejected"
    )
    assert rows(conn, "allergic_to")["peanuts"][0] == "active"


# ---- 3. likes vs dislikes ----


def test_like_contradicts_dislike(conn):
    apply(conn, "dislikes", "coriander")
    assert apply(conn, "likes", "Coriander") == "contradiction"
    likes, dislikes = rows(conn, "likes"), rows(conn, "dislikes")
    assert likes["Coriander"][0] == "active"
    assert dislikes["coriander"][:3] == (
        "superseded",
        dislikes["coriander"][1],
        likes["Coriander"][1],
    )
    assert events(conn)[-1][:2] == ("contradiction", likes["Coriander"][1])


def test_dislike_contradicts_like(conn):
    apply(conn, "likes", "jazz")
    assert apply(conn, "dislikes", "jazz") == "contradiction"
    assert rows(conn, "likes")["jazz"][0] == "superseded"
    assert rows(conn, "dislikes")["jazz"][0] == "active"


def test_hobby_contradicts_dislike(conn):
    apply(conn, "dislikes", "opera")
    assert apply(conn, "hobby", "opera") == "contradiction"
    assert rows(conn, "dislikes")["opera"][0] == "superseded"
    assert rows(conn, "hobby")["opera"][0] == "active"


def test_dislike_contradicts_hobby(conn):
    apply(conn, "hobby", "opera")
    assert apply(conn, "dislikes", "opera") == "contradiction"
    assert rows(conn, "hobby")["opera"][0] == "superseded"
    assert rows(conn, "dislikes")["opera"][0] == "active"


def test_unrelated_hobby_does_not_contradict(conn):
    apply(conn, "dislikes", "opera")
    assert apply(conn, "hobby", "chess") == "add"
    assert rows(conn, "dislikes")["opera"][0] == "active"


def test_short_values_are_stored(conn):
    assert apply(conn, "name", "Ana", source_text="Hi, my name is Ana.") == "add"
    assert apply(conn, "allergic_to", "soy", source_text="I can't eat soy.") == "add"
    assert (
        apply(conn, "allergic_to", "egg", source_text="I'm allergic to eggs.") == "add"
    )


# ---- 4. conflicted ----


def test_employer_change_marks_job_title_conflicted(conn):
    apply(conn, "works_at", "Acme")
    apply(conn, "job_title", "engineer")
    assert apply(conn, "works_at", "Globex", message_relations={"works_at"}) == "update"
    status, fid, superseded_by, _ = rows(conn, "job_title")["engineer"]
    assert (status, superseded_by) == ("conflicted", None)
    assert ("conflict", fid) in [e[:2] for e in events(conn)]


def test_employer_retraction_marks_job_title_conflicted(conn):
    apply(conn, "works_at", "Acme")
    apply(conn, "job_title", "engineer")
    apply(conn, "works_at", "Acme", action="retract", message_relations={"works_at"})
    assert rows(conn, "job_title")["engineer"][0] == "conflicted"


def test_no_conflict_when_same_message_sets_title(conn):
    apply(conn, "works_at", "Acme")
    apply(conn, "job_title", "engineer")
    apply(conn, "works_at", "Globex", message_relations={"works_at", "job_title"})
    assert rows(conn, "job_title")["engineer"][0] == "active"
    assert apply(conn, "job_title", "accountant") == "update"
    assert rows(conn, "job_title")["engineer"][0] == "superseded"


def test_first_employer_does_not_conflict(conn):
    apply(conn, "job_title", "nurse")
    assert (
        apply(conn, "works_at", "City Hospital", message_relations={"works_at"})
        == "add"
    )
    assert rows(conn, "job_title")["nurse"][0] == "active"


def test_later_title_supersedes_conflicted(conn):
    apply(conn, "works_at", "Acme")
    apply(conn, "job_title", "engineer")
    apply(conn, "works_at", "Globex", message_relations={"works_at"})
    assert apply(conn, "job_title", "designer") == "update"
    facts = rows(conn, "job_title")
    assert facts["engineer"][:3] == (
        "superseded",
        facts["engineer"][1],
        facts["designer"][1],
    )
    assert facts["designer"][0] == "active"


def test_retrieval_skips_conflicted(conn, monkeypatch):
    monkeypatch.setattr(retrieve, "embed", fake_embed)
    monkeypatch.setattr(retrieve, "_relation_vecs", None)
    apply(conn, "works_at", "Acme")
    apply(conn, "job_title", "engineer")
    apply(conn, "works_at", "Globex", message_relations={"works_at"})
    conn.commit()  # score_facts reads through its own connection
    values = {m.value for m in retrieve.score_facts(USER, "What's my job title?")}
    assert values == {"Globex"}
