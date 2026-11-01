"""The question tables of the results page, checked against the committed result data.

Pure Python (csv module), so these run in CI without the dashboard group.
"""

import pytest

from dashboard import data


@pytest.fixture(scope="module")
def runs():
    return data.runs()


def test_line_kinds():
    assert data.line_kind('[2025-08-07] "I moved to Lyon."') == "message"
    assert data.line_kind("Works at: Clinica Albereda (since 2025-04-26)") == "fact"
    assert data.line_kind("Note from 2026-04-07: The user left.") == "note"
    marked = '[2025-08-07] "I live in Oslo." [outdated: Lives in: Oslo -> now Bergen]'
    assert data.line_kind(marked) == "marked"
    assert data.line_kind("Lives in, oldest first: Oslo -> Bergen (now)") == "marked"


def test_parse_memory_splits_on_the_separator():
    lines = data.parse_memory('Hobby: chess || [2026-01-02] "Hi"')
    assert [(x.text, x.kind) for x in lines] == [
        ("Hobby: chess", "fact"),
        ('[2026-01-02] "Hi"', "message"),
    ]
    assert data.parse_memory("") == []


def test_every_run_with_answers_is_loaded_in_order(runs):
    assert len(runs) == 26
    orders = [r.order for r in runs.values()]
    assert orders == sorted(orders)
    assert sum(len(r.questions) for r in runs.values()) == 1345


def test_modes_not_run_are_left_out(runs):
    # The long sets skip the no-memory mode: its empty rows are not shown as answers.
    assert runs["N_full"].modes == ["baseline", "smart", "hybrid", "full"]
    assert runs["A_to_G_after_fix2"].modes == ["none", "baseline", "smart"]


def test_tally_matches_the_headline(runs):
    n = runs["N_full"]
    tally = data.tally(n.questions, n.modes)
    assert tally["hybrid"] == (50, 57)
    assert tally["baseline"] == (45, 57)


def test_modes_pick_columns_not_questions(runs):
    n = runs["N_full"]
    f = data.clean(data.Filters(modes=("hybrid", "baseline")), runs)
    assert f.modes == ("baseline", "hybrid")  # in the run's order
    assert data.shown_modes(n, f) == ["baseline", "hybrid"]
    assert len(data.select(n, f)) == 57  # every question is still listed
    assert f.query() == [("run", "N_full"), ("mode", "baseline"), ("mode", "hybrid")]


def test_every_mode_or_none_means_all(runs):
    n = runs["N_full"]
    every = data.clean(data.Filters(modes=tuple(n.modes)), runs)
    unknown = data.clean(data.Filters(modes=("nope",)), runs)
    assert every.modes == unknown.modes == ()
    assert data.shown_modes(n, every) == n.modes


def test_filters_by_set_and_type(runs):
    r = runs["A_to_J_change_rule_1b"]
    only_c = data.select(r, data.Filters(run=r.run, set="C"))
    assert only_c and {q.set for q in only_c} == {"C"}
    past = data.select(runs["N_full"], data.Filters(qtype="past"))
    assert past and {q.qtype for q in past} == {"past"}
    assert data.qtypes(r) == []  # question types start with set M


def test_clean_drops_unknown_values(runs):
    f = data.clean(data.Filters(run="nope", set="Z", qtype="x", modes=("?",)), runs)
    assert f == data.Filters()
    assert f.query() == [("run", data.DEFAULT_RUN)]


def test_describe_says_what_is_shown(runs):
    n = runs["N_full"]
    assert data.describe(n, data.Filters(qtype="past"), 7) == (
        "Showing 7 of 57 questions of run N_full (set N): value before a change."
    )


def test_problems_are_the_checks_that_went_the_bad_way():
    answer = data.Answer(
        mode="smart",
        correct=False,
        checks={
            "needed_present": False,
            "noise_present": False,
            "stale_in_answer": True,
        },
        lines=1,
        answer="",
        memory=[],
    )
    assert answer.problems() == ["needed_present", "stale_in_answer"]
