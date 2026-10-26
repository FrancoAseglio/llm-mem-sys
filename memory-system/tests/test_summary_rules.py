"""Pure tests for the summaries layer's text rules (no database, no model).

    poetry run pytest tests/test_summary_rules.py -v
"""

from datetime import datetime

import pytest

from memory_system.summary_rules import (
    SummaryRow,
    adds_information,
    is_chatter,
    is_faithful,
    select_summaries,
)

TRIP = "Last spring I went hiking in Norway with my cousin Ingrid, and we saw the northern lights."


@pytest.mark.parametrize(
    "statement, sources",
    [
        (
            "The user went hiking in Norway with their cousin Ingrid last spring and saw the northern lights.",
            [TRIP],
        ),
        (
            "The user fixed the kitchen tap themselves yesterday and it took two hours.",
            ["Yesterday I fixed the kitchen tap myself, it took two hours."],
        ),
        # several messages, one story
        (
            "The user signed up for the Tuesday pottery class after thinking about it.",
            [
                "I'm thinking about taking a pottery class.",
                "I signed up for the Tuesday pottery class!",
            ],
        ),
        # an inflected stopword in the sentence ("works") matches the message ("work")
        (
            "The user works at Brightline Logistics.",
            ["I work at Brightline Logistics."],
        ),
        # a person other than the user is kept as such
        (
            "The user's colleague Dana is moving to Oslo next week.",
            ["My colleague Dana is moving to Oslo next week."],
        ),
    ],
)
def test_faithful_sentences_pass(statement, sources):
    assert is_faithful(statement, sources)


@pytest.mark.parametrize(
    "statement, why",
    [
        ("The user went hiking in Japan with their cousin Ingrid.", "invented place"),
        ("The user went hiking in Norway with their cousin Astrid.", "invented name"),
        ("The user went hiking in Norway for 12 days.", "invented number"),
        ("The user planned a skiing holiday in the Alps.", "mostly invented words"),
        ("The user.", "nothing to check"),
    ],
)
def test_invented_details_are_rejected(statement, why):
    assert not is_faithful(statement, [TRIP]), why


def test_a_number_must_match_exactly():
    sources = ["I bought a second-hand scooter for 900 euros."]
    assert is_faithful("The user bought a second-hand scooter for 900 euros.", sources)
    assert not is_faithful("The user bought a second-hand scooter for 90 euros.", sources)


def test_a_restated_fact_adds_nothing():
    lines = ["Lives in: Milan (since 2026-10-24)"]
    assert not adds_information("The user lives in Milan.", lines)


def test_a_new_detail_adds_information():
    lines = ["Family member: Marta (since 2026-08-27)"]
    assert adds_information("The user's sister Marta is getting married in Lisbon.", lines)


def row(id, content, similarity, fresh=True):
    return SummaryRow(id, content, datetime(2026, 1, 1), similarity, fresh)


def pick(rows, lines=(), max_lines=2, floor=0.42, window=0.08):
    return [r.id for r in select_summaries(rows, list(lines), max_lines, floor, window)]


def test_the_floor_drops_weak_matches():
    assert pick([row(1, "The user baked bread.", 0.41)]) == []
    assert pick([row(1, "The user baked bread.", 0.43)]) == [1]


def test_the_window_drops_neighbours_of_the_best_match():
    rows = [row(1, "The user baked bread.", 0.70), row(2, "The user painted a fence.", 0.60)]
    assert pick(rows) == [1]


def test_best_first_and_at_most_max_lines():
    rows = [
        row(1, "The user baked bread.", 0.60),
        row(2, "The user painted a fence.", 0.64),
        row(3, "The user planted tulips.", 0.62),
    ]
    assert pick(rows, max_lines=2) == [2, 3]


def test_a_summary_with_an_outdated_source_is_skipped():
    assert pick([row(1, "The user lives in Turin.", 0.9, fresh=False)]) == []


def test_a_summary_that_restates_a_chosen_fact_is_skipped():
    rows = [row(1, "The user lives in Milan.", 0.80), row(2, "The user baked bread.", 0.78)]
    assert pick(rows, lines=["Lives in: Milan (since 2026-10-24)"]) == [2]


def test_two_summaries_that_say_the_same_keep_one():
    rows = [
        row(1, "The user baked a loaf of bread.", 0.70),
        row(2, "The user baked a loaf of bread.", 0.69),
    ]
    assert pick(rows) == [1]


@pytest.mark.parametrize(
    "text",
    [
        "How do I remove a coffee stain?",
        "Can you suggest a pasta sauce for tonight?",
        "What's the capital of Australia?",
        "Any tips for staying focused while studying?",
        "Give me a tip for sleeping better.",
        "Explain how tides work.",
        "Thanks, that was helpful!",
        "Thanks!",
    ],
)
def test_questions_requests_and_thanks_are_chatter(text):
    assert is_chatter(text)


@pytest.mark.parametrize(
    "text",
    [
        "I moved to Rome, can you suggest places to visit?",  # a statement comes first
        "I bought a new desk lamp yesterday.",
        "Last month I built a bookshelf with my dad.",
        "My sister asked me how to bake bread.",
        "I'm thinking about adopting a rescue dog.",
        "Big day today, I finally got the promotion I'd been chasing!",
    ],
)
def test_statements_are_not_chatter(text):
    assert not is_chatter(text)
