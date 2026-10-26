"""The summaries layer against the database, with the model and the embeddings replaced.
Needs the Postgres database from .env. Every test runs against a throwaway user.

    poetry run pytest tests/test_summarize.py -v
"""

import numpy as np
import pytest

from memory_system import summarize, summary_retrieve
from memory_system.db import get_pool
from memory_system.summarize import Episode, EpisodeList

USER = "test_summarize"
TRIP = "Last spring I went hiking in Norway with my cousin Ingrid."
FILLER = "Thanks, that was helpful!"


def fake_embed(text: str) -> np.ndarray:
    return np.ones(768, dtype=np.float32)


@pytest.fixture
def user(monkeypatch):
    monkeypatch.setattr(summarize, "embed", fake_embed)
    monkeypatch.setattr(summary_retrieve, "embed", fake_embed)
    with get_pool().connection() as c:
        c.execute("DELETE FROM users WHERE id = %s", (USER,))
        c.execute("INSERT INTO users (id) VALUES (%s)", (USER,))
    yield USER
    with get_pool().connection() as c:
        c.execute("DELETE FROM users WHERE id = %s", (USER,))


def add_message(text: str) -> int:
    with get_pool().connection() as c:
        return c.execute(
            "INSERT INTO messages (user_id, role, content, embedding) "
            "VALUES (%s, 'user', %s, %s) RETURNING id",
            (USER, text, fake_embed(text)),
        ).fetchone()[0]


def model_says(monkeypatch, *episodes: Episode):
    calls = []

    def fake(system, prompt, schema):
        calls.append(prompt)
        return EpisodeList(episodes=list(episodes))

    monkeypatch.setattr(summarize, "chat_structured", fake)
    return calls


def summaries():
    with get_pool().connection() as c:
        return c.execute(
            "SELECT id, content FROM summaries WHERE user_id = %s ORDER BY id", (USER,)
        ).fetchall()


def test_a_faithful_episode_is_stored_and_linked_to_its_message(user, monkeypatch):
    trip_id = add_message(TRIP)
    add_message(FILLER)
    model_says(
        monkeypatch,
        Episode(text="The user went hiking in Norway with their cousin Ingrid.", messages=[1]),
    )
    kept = summarize.summarize_pending(user)
    assert kept == ["The user went hiking in Norway with their cousin Ingrid."]
    with get_pool().connection() as c:
        linked = c.execute(
            "SELECT summary_id FROM messages WHERE id = %s", (trip_id,)
        ).fetchone()[0]
    assert linked == summaries()[0][0]


def test_an_invented_detail_is_dropped_and_logged(user, monkeypatch):
    add_message(TRIP)
    model_says(
        monkeypatch,
        Episode(text="The user went hiking in Japan with their cousin Ingrid.", messages=[1]),
    )
    assert summarize.summarize_pending(user) == []
    assert summaries() == []
    with get_pool().connection() as c:
        details = c.execute(
            "SELECT details FROM memory_events WHERE user_id = %s AND event_type = 'summarize'",
            (USER,),
        ).fetchone()[0]
    assert details["dropped"][0]["reason"] == "not faithful"


def test_an_episode_without_a_valid_source_is_dropped(user, monkeypatch):
    add_message(TRIP)
    model_says(
        monkeypatch,
        Episode(text="The user went hiking in Norway with their cousin Ingrid.", messages=[7]),
    )
    assert summarize.summarize_pending(user) == []


def test_messages_are_only_summarised_once(user, monkeypatch):
    add_message(TRIP)
    calls = model_says(monkeypatch)  # the model finds nothing
    summarize.summarize_pending(user)
    summarize.summarize_pending(user)
    assert len(calls) == 1  # the second run found nothing new, so no model call
    assert summarize.pending_count(user) == 0
    add_message(FILLER)
    assert summarize.pending_count(user) == 1


def test_a_model_failure_leaves_the_messages_pending(user, monkeypatch):
    add_message(TRIP)

    def broken(system, prompt, schema):
        raise ValueError("model returned invalid JSON")

    monkeypatch.setattr(summarize, "chat_structured", broken)
    assert summarize.summarize_pending(user) == []
    assert summarize.pending_count(user) == 1
    with get_pool().connection() as c:
        reason = c.execute(
            "SELECT details->>'reason' FROM memory_events "
            "WHERE user_id = %s AND event_type = 'reject'",
            (USER,),
        ).fetchone()[0]
    assert reason == "summarization failed"


def test_a_stored_summary_is_retrieved_for_a_question(user, monkeypatch):
    add_message(TRIP)
    model_says(
        monkeypatch,
        Episode(text="The user went hiking in Norway with their cousin Ingrid.", messages=[1]),
    )
    summarize.summarize_pending(user)
    lines = summary_retrieve.retrieve_summaries(user, "What trip did I take?", [], touch=False)
    assert len(lines) == 1 and "Norway" in lines[0]


def test_a_summary_whose_source_fact_is_outdated_is_not_retrieved(user, monkeypatch):
    message_id = add_message("I live in Turin and I went hiking in Norway last spring.")
    model_says(
        monkeypatch,
        Episode(text="The user went hiking in Norway last spring.", messages=[1]),
    )
    summarize.summarize_pending(user)
    with get_pool().connection() as c:  # the fact from that message is later replaced
        c.execute(
            "INSERT INTO facts (user_id, relation, value, status, source_message_id, embedding) "
            "VALUES (%s, 'lives_in', 'Turin', 'superseded', %s, %s)",
            (USER, message_id, fake_embed("x")),
        )
    assert summary_retrieve.retrieve_summaries(user, "Where did I hike?", [], touch=False) == []


def test_summaries_do_not_use_up_the_room_of_facts(user, monkeypatch):
    add_message(TRIP)
    model_says(
        monkeypatch,
        Episode(text="The user went hiking in Norway with their cousin Ingrid.", messages=[1]),
    )
    summarize.summarize_pending(user)
    four_facts = [f"Fact {i}" for i in range(4)]
    assert summary_retrieve.retrieve_summaries(user, "q", four_facts, k=4, touch=False) == []


def test_questions_and_thanks_are_not_sent_to_the_model(user, monkeypatch):
    add_message("How do I remove a coffee stain?")
    add_message(TRIP)
    add_message(FILLER)
    calls = model_says(monkeypatch)
    summarize.summarize_pending(user)
    assert "coffee" not in calls[0] and "helpful" not in calls[0]
    assert "Norway" in calls[0] and calls[0].count("\n") >= 1
    assert summarize.pending_count(user) == 0  # all three count as seen


def test_a_batch_of_only_questions_makes_no_model_call(user, monkeypatch):
    add_message("How do I remove a coffee stain?")
    calls = model_says(monkeypatch)
    summarize.summarize_pending(user)
    assert calls == []
    assert summarize.pending_count(user) == 0
