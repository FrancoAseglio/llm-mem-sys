"""Pure tests for the scoring of session sets (set K): no database, no model."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from evaluation.session_metrics import (  # noqa: E402
    score_probe,
    stability_groups,
    totals,
)

CITY = {
    "fact": "city",
    "type": "direct",
    "expect": [["bilbao"]],
    "forbid": ["ljubljana"],
}


def test_a_correct_answer_without_the_old_value():
    s = score_probe("You live in Bilbao.", ["Lives in: Bilbao"], CITY)
    assert s == {"correct": True, "forbid_raw": False, "forbid_in_prompt": False}


def test_the_old_value_in_the_answer_and_in_the_prompt_is_flagged():
    s = score_probe(
        "You live in Ljubljana.",
        ['"I live in Ljubljana."', '"I moved to Bilbao"'],
        CITY,
    )
    assert s == {"correct": False, "forbid_raw": True, "forbid_in_prompt": True}


def test_a_past_mention_is_flagged_for_the_hand_review():
    # the keyword check cannot tell "you moved from Ljubljana" from a contradiction
    s = score_probe("You moved from Ljubljana to Bilbao.", [], CITY)
    assert s["correct"] and s["forbid_raw"]


def test_a_probe_without_forbid_words_is_not_tested_for_them():
    probe = {"fact": "name", "type": "direct", "expect": [["oriane"]]}
    s = score_probe("Your name is Oriane.", [], probe)
    assert s["forbid_raw"] is None and s["forbid_in_prompt"] is None


def test_every_expect_group_needs_a_word():
    probe = {"fact": "languages", "type": "direct", "expect": [["french"], ["breton"]]}
    assert not score_probe("You speak French.", [], probe)["correct"]
    assert score_probe("French and Breton.", [], probe)["correct"]


def probe(story, fact, correct, forbid=False, kind="direct"):
    entry = {"correct": correct, "forbid_raw": forbid, "forbid_in_prompt": forbid}
    return {"scenario": story, "fact": fact, "type": kind, "smart": entry}


def test_groups_need_two_probes_of_one_fact_in_one_story():
    probes = [
        probe("k_move", "city_before", True),
        probe("k_move", "city", True),
        probe("k_move", "city", True),
        probe("k_same", "city", True),
    ]
    assert list(stability_groups(probes)) == [("k_move", "city")]


def test_a_fact_is_stable_only_if_every_probe_is_right_and_clean():
    probes = [
        probe("a", "city", True),
        probe("a", "city", True),
        probe("b", "city", True),
        probe("b", "city", False),
        probe("c", "job", True),
        probe("c", "job", True, forbid=True),
    ]
    t = totals(probes, "smart")
    assert (t["stable"], t["groups"]) == (1, 3)
    assert (t["correct"], t["probes"]) == (5, 6)
    assert (t["contradictions_raw"], t["forbid_probes"]) == (1, 6)


def test_indirect_probes_are_counted_apart():
    probes = [
        probe("a", "x", True, kind="indirect"),
        probe("a", "y", False, kind="indirect"),
    ]
    t = totals(probes, "smart")
    assert (t["indirect_correct"], t["indirect"]) == (1, 2)
