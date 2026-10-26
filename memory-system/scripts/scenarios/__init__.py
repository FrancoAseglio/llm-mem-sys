"""Test scenarios for the evaluation.

Each scenario replays a short life history, with messages dated N days ago,
then asks questions that can be answered from memory alone.

Sets (one module each; every scenario gets a "set" letter here):
  A  set_a  TUNING. The retrieval gate was tuned on these, so they can NOT validate it.
  B  set_b  SPENT. Held out when written, but the floor and window were chosen after looking at it.
  C  set_c  SPENT. Blind when written (before the relative window); one rich profile plus abstain questions.
  D  set_d  SPENT. Blind, written before relation routing existed. Second rich profile, safety, job switch.
  E  set_e  SPENT. Blind, written before the safety bypass and the goal-extraction change.
  F  set_f  SPENT. Blind, write path only: corrections, flips, employer changes.
A blind set can be run once. After that it is spent: write a new one to validate a change.

Scenario fields
  id, kind : name, and what the scenario is designed to test
  messages : (days_ago, text)  -- order does not matter, the runner sorts them
Question fields
  q        : the question
  expect   : list of groups; every group needs at least one of its words in the ANSWER
             (leave out to skip answer scoring and only check retrieval)
  needs    : words that must appear in the memory lines sent to the model
  avoid    : words that must NOT appear in the memory lines (irrelevant noise)
  stale    : outdated words, reported separately (they never fail an answer)
"""
from . import set_a, set_b, set_c, set_d, set_e, set_f, set_g, set_h

SETS = {
    "A": set_a.SCENARIOS,
    "B": set_b.SCENARIOS,
    "C": set_c.SCENARIOS,
    "D": set_d.SCENARIOS,
    "E": set_e.SCENARIOS,
    "F": set_f.SCENARIOS,
    "G": set_g.SCENARIOS,
    "H": set_h.SCENARIOS,
}

for _letter, _scenarios in SETS.items():
    for _scenario in _scenarios:
        _scenario["set"] = _letter

SCENARIOS = [scenario for scenarios in SETS.values() for scenario in scenarios]

# One-line status of each set, shown in the evaluation summary.
SET_LABELS = {
    "A": "A (tuning set, cannot validate)",
    "B": "B (spent: the floor and window were chosen after seeing it)",
    "C": "C (spent: written before the relative window ran on it)",
    "D": "D (BLIND: written before routing existed in the pipeline; run once)",
    "E": "E (BLIND: written before the safety bypass and goal prompt; run once)",
    "F": "F (BLIND: write path only, written after the write-path fixes; run once)",
    "G": "G (BLIND: beyond the 13 fact types, written before the summaries layer; run once)",
    "H": "H (BLIND: validation of the summaries layer, written before its code; run once)",
}
