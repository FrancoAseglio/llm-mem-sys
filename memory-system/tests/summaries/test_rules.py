"""Pure tests for the summaries layer's text rules (no database, no model).

poetry run pytest tests/summaries/test_rules.py -v
"""

from datetime import datetime

import pytest

from memory_system.summaries.rules import (
    SummaryRow,
    adds_information,
    is_chatter,
    is_faithful,
    missing_details,
    only_stored,
    select_summaries,
    tag_message,
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
    assert not is_faithful(
        "The user bought a second-hand scooter for 90 euros.", sources
    )


def test_a_restated_fact_adds_nothing():
    lines = ["Lives in: Milan (since 2026-10-24)"]
    assert not adds_information("The user lives in Milan.", lines)


def test_a_new_detail_adds_information():
    lines = ["Family member: Marta (since 2026-08-27)"]
    assert adds_information(
        "The user's sister Marta is getting married in Lisbon.", lines
    )


def row(id, content, similarity, fresh=True):
    return SummaryRow(id, content, datetime(2026, 1, 1), similarity, fresh)


def pick(rows, lines=(), max_lines=2, floor=0.42, window=0.08):
    return [r.id for r in select_summaries(rows, list(lines), max_lines, floor, window)]


def test_the_floor_drops_weak_matches():
    assert pick([row(1, "The user baked bread.", 0.41)]) == []
    assert pick([row(1, "The user baked bread.", 0.43)]) == [1]


def test_the_window_drops_neighbours_of_the_best_match():
    rows = [
        row(1, "The user baked bread.", 0.70),
        row(2, "The user painted a fence.", 0.60),
    ]
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
    rows = [
        row(1, "The user lives in Milan.", 0.80),
        row(2, "The user baked bread.", 0.78),
    ]
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


# ---- missing_details: the retention check of consolidation ----

QUOTE = "The user was quoted 18,000 euros for the kitchen by contractor Tobias."
BILL = "The final bill for the kitchen came to 21,500 euros."


def test_a_digest_that_keeps_every_number_and_name_misses_nothing():
    digest = "Tobias quoted the user 18,000 euros for the kitchen; the final bill was 21,500 euros."
    assert missing_details(digest, [QUOTE, BILL]) == []


def test_numbers_match_with_or_without_separators():
    digest = "Tobias's quote was 18000 euros and the bill 21500 euros."
    assert missing_details(digest, [QUOTE, BILL]) == []


def test_a_dropped_number_and_a_dropped_name_are_reported():
    digest = "The user's kitchen cost 21,500 euros."
    assert missing_details(digest, [QUOTE, BILL]) == ["18000", "tobias"]


def test_a_month_or_weekday_may_change_but_a_day_number_may_not():
    notes = [
        "The user booked the Hanoi flights for December 12.",
        "The user moved the Hanoi trip to February.",
    ]
    assert missing_details("The user moved the Hanoi trip to February.", notes) == [
        "12"
    ]
    weekly = ["The user's lessons were on Thursdays.", "The lessons moved to Tuesdays."]
    assert missing_details("The user's lessons are on Tuesdays.", weekly) == []


def test_capitalised_stopwords_and_the_first_word_are_not_names():
    notes = ["The user's band played at The Copper Kettle.", "Twelve people came."]
    assert missing_details("The user's band played The Copper Kettle.", notes) == []


# ---- the stored-facts tag shown to the notes model ----


def test_a_message_is_tagged_with_the_facts_stored_from_it():
    line = tag_message(
        2,
        "I live in Rome and I'm a nurse.",
        [("lives_in", "Rome"), ("job_title", "nurse")],
    )
    assert (
        line
        == '2. "I live in Rome and I\'m a nurse." [stored: lives_in = Rome; job_title = nurse]'
    )


def test_a_message_without_facts_is_tagged_nothing():
    line = tag_message(1, "I've started taking cello lessons.", [])
    assert line.endswith("[stored: nothing]")


# ---- a message whose stored facts hold everything it says ----


@pytest.mark.parametrize(
    "text, stored",
    [
        ("My wife is called Ines.", [("partner", "Ines")]),
        (
            "I work as an architect at Studio Verdi.",
            [("job_title", "architect"), ("works_at", "Studio Verdi")],
        ),
        (
            "I speak Portuguese, English and a little German.",
            [("speaks", "Portuguese"), ("speaks", "English"), ("speaks", "German")],
        ),
        ("My brother's name is Luca.", [("family_member", "Luca")]),
    ],
)
def test_a_message_held_by_its_facts_is_only_stored(text, stored):
    assert only_stored(text, stored, 0.75)


@pytest.mark.parametrize(
    "text, stored",
    [
        ("I've started taking cello lessons on Thursday evenings.", []),
        ("I love running, I usually go out before sunrise.", [("hobby", "running")]),
        (
            "My brother Fintan is getting married next June.",
            [("family_member", "Fintan")],
        ),
        # a name the facts do not hold (Pieter) means the message says more
        (
            "I'm planning a hiking trip to the Julian Alps next spring with my friend Pieter.",
            [("goal", "hiking trip to the Julian Alps next spring")],
        ),
    ],
)
def test_a_message_that_says_more_is_not_only_stored(text, stored):
    assert not only_stored(text, stored, 0.75)
