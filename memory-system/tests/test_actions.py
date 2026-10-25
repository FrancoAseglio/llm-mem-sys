"""Pure tests (no database, no model): grounding and the assert/retract label check.

    poetry run pytest tests/test_actions.py -v
"""
import pytest

from memory_system.conflicts import is_grounded, normalize_actions
from memory_system.extract import ExtractedFact


def F(action, relation, value):
    return ExtractedFact(relation=relation, value=value, action=action)


def pairs(facts):
    return [(f.action, f.relation, f.value) for f in facts]


# ---- grounding ----

@pytest.mark.parametrize("value, text, relation", [
    ("Ana", "Hi, my name is Ana.", "name"),
    ("Li", "I'm Li and I live in Rome.", "name"),
    ("Max", "My brother is Max.", "family_member"),
    ("Rio", "I just moved to Rio.", "lives_in"),
    ("5 May", "My birthday is on 5 May.", "birthday"),
    ("egg", "I'm allergic to eggs.", "allergic_to"),
    ("soy", "I can't eat soy.", "allergic_to"),
    ("ski", "I love skiing in winter.", "hobby"),
    ("walnut", "I'm allergic to walnuts.", "allergic_to"),
    ("anchovy", "I really hate anchovies, the smell is awful.", "dislikes"),
])
def test_grounded(value, text, relation):
    assert is_grounded(value, text, relation)


@pytest.mark.parametrize("value, text, relation", [
    ("new job", "Exciting news, I just started a new position at Delta Labs!", "job_title"),
    ("new job", "I just started a new job at Globex!", "job_title"),
    ("really nice food", "I really like this one.", "likes"),
    ("Max", "My brother is Luca.", "family_member"),
    ("Eva", "My sister is Evangeline.", "family_member"),
    ("tea", "I like to travel by train.", "likes"),
])
def test_not_grounded(value, text, relation):
    assert not is_grounded(value, text, relation)


def test_short_name_needs_a_name_relation():
    # a lower-case junk word is not rescued by the verbatim rule
    assert not is_grounded("job", "I just started a new job.", "job_title")


# ---- label check: replacement wrongly labelled as retract ----

def test_replacement_labelled_retract_becomes_assert():
    text = "I'm not a teacher anymore, I became a pilot."
    got = normalize_actions([F("retract", "job_title", "pilot"),
                             F("retract", "job_title", "teacher")], text)
    assert pairs(got) == [("retract", "job_title", "teacher"), ("assert", "job_title", "pilot")]


def test_correction_form():
    text = "Correction: my sister's name is Elena, not Elisa."
    got = normalize_actions([F("retract", "family_member", "Elena"),
                             F("retract", "family_member", "Elisa")], text)
    assert pairs(got) == [("retract", "family_member", "Elisa"),
                          ("assert", "family_member", "Elena")]


def test_walnuts_case():
    text = "I'm not allergic to peanuts, I'm allergic to walnuts."
    got = normalize_actions([F("retract", "allergic_to", "peanuts"),
                             F("retract", "allergic_to", "walnuts")], text)
    assert pairs(got) == [("retract", "allergic_to", "peanuts"),
                          ("assert", "allergic_to", "walnuts")]


def test_wrong_value_in_retract_is_deduplicated():
    text = "It's not Turin, I live in Genoa."
    got = normalize_actions([F("retract", "lives_in", "Genoa"),
                             F("assert", "lives_in", "Genoa")], text)
    assert pairs(got) == [("assert", "lives_in", "Genoa")]


def test_correct_labels_are_untouched():
    text = "I don't speak German, I speak Dutch."
    facts = [F("retract", "speaks", "German"), F("assert", "speaks", "Dutch")]
    assert pairs(normalize_actions(facts, text)) == pairs(facts)


def test_list_continuation_stays_retract():
    text = "I'm not allergic to peanuts, shellfish or soy."
    facts = [F("retract", "allergic_to", "peanuts"), F("retract", "allergic_to", "shellfish"),
             F("retract", "allergic_to", "soy")]
    assert all(f.action == "retract" for f in normalize_actions(facts, text))


@pytest.mark.parametrize("text, value", [
    ("Forget what I said about hiking, I only go swimming.", "hiking"),
    ("Never mind what I said about shellfish.", "shellfish"),
    ("I used to speak French, now I speak Spanish.", "French"),
    ("I no longer work at Acme, I joined Globex last week.", "Acme"),
    ("I stopped playing chess, I play tennis now.", "chess"),
])
def test_real_retractions_stay(text, value):
    relation = {"hiking": "hobby", "shellfish": "allergic_to", "French": "speaks",
                "Acme": "works_at", "chess": "hobby"}[value]
    got = normalize_actions([F("retract", relation, value)], text)
    assert pairs(got) == [("retract", relation, value)]


def test_value_not_in_message_is_left_alone():
    got = normalize_actions([F("retract", "speaks", "Klingon")], "I speak Dutch.")
    assert pairs(got) == [("retract", "speaks", "Klingon")]


def test_retractions_come_first():
    text = "I don't speak German, I speak Dutch."
    got = normalize_actions([F("assert", "speaks", "Dutch"), F("retract", "speaks", "German")], text)
    assert [f.action for f in got] == ["retract", "assert"]


def test_repeats_removed():
    got = normalize_actions([F("assert", "speaks", "Dutch"), F("assert", "speaks", "dutch")],
                            "I speak Dutch.")
    assert len(got) == 1


# ---- observed model outputs (real raw labels from the probes) ----

SINGLE = frozenset({"lives_in", "works_at", "job_title", "name"})


def run(text, facts):
    return pairs(normalize_actions(facts, text, SINGLE))


def test_observed_moved_out_of_keeps_real_retract():
    # the first version of the guard turned "retract Berlin" into an assert and broke this
    got = run("I moved out of Berlin, I live in Vienna now.",
              [F("assert", "lives_in", "Vienna"), F("retract", "lives_in", "Berlin")])
    assert got == [("retract", "lives_in", "Berlin"), ("assert", "lives_in", "Vienna")]


def test_observed_quit_job_both_asserted():
    got = run("I quit my job at Initech, I work at Hooli now.",
              [F("assert", "works_at", "Hooli"), F("assert", "works_at", "Initech")])
    assert got == [("retract", "works_at", "Initech"), ("assert", "works_at", "Hooli")]


def test_observed_name_retract_and_assert_same_value():
    got = run("My name is not Marco, it's Mario.",
              [F("retract", "name", "Mario"), F("assert", "name", "Mario")])
    assert got == [("assert", "name", "Mario")]


def test_observed_not_turin_both_asserted():
    got = run("It's not Turin, I live in Genoa.",
              [F("assert", "lives_in", "Turin"), F("assert", "lives_in", "Genoa")])
    assert got == [("retract", "lives_in", "Turin"), ("assert", "lives_in", "Genoa")]


def test_lone_retract_without_negation_word_is_never_flipped():
    got = run("I'm done with chess.", [F("retract", "hobby", "chess")])
    assert got == [("retract", "hobby", "chess")]


def test_two_values_in_one_clause_are_not_promoted():
    got = run("I'm done with chess and golf.",
              [F("retract", "hobby", "chess"), F("retract", "hobby", "golf")])
    assert [a for a, _, _ in got] == ["retract", "retract"]


def test_two_independent_asserts_are_untouched():
    text = "I live in Rome and I work at Acme."
    got = run(text, [F("assert", "lives_in", "Rome"), F("assert", "works_at", "Acme")])
    assert got == [("assert", "lives_in", "Rome"), ("assert", "works_at", "Acme")]


def test_multi_valued_asserts_are_untouched():
    # "can't stand" has a negation-looking ending but both items are plain statements
    text = "I can't stand mushrooms, I love olives."
    got = run(text, [F("assert", "dislikes", "mushrooms"), F("assert", "likes", "olives")])
    assert got == [("assert", "dislikes", "mushrooms"), ("assert", "likes", "olives")]
