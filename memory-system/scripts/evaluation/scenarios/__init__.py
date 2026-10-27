"""Test scenarios for the evaluation, stored as data in `sets/set_<letter>.json`.

Each scenario replays a short life history, with messages dated N days ago,
then asks questions that can be answered from memory alone.

A set file holds:
  set          the letter (A, B, ...)
  label        one line shown in the evaluation summary: what the set is and how it may be used
  description  what the set covers
  scenarios    the list below

Scenario fields
  id, kind : name, and what the scenario is designed to test
  messages : [days_ago, text]  -- order does not matter, the runner sorts them
Question fields
  q        : the question
  expect   : list of groups; every group needs at least one of its words in the ANSWER
             (leave out to skip answer scoring and only check retrieval)
  needs    : words that must appear in the memory lines sent to the model
  avoid    : words that must NOT appear in the memory lines (irrelevant noise)
  stale    : outdated words, reported separately (they never fail an answer)

A blind set can be run once. After that it is spent: write a new one to validate a change.
Once a set's predictions are committed its file is frozen: its SHA-256 goes into `frozen.json`
and tests/evaluation/test_scenarios.py fails if the file changes afterwards.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).with_name("sets")

SETS: dict[str, list[dict]] = {}
SET_LABELS: dict[str, str] = {}

for _path in sorted(DATA_DIR.glob("set_*.json")):
    _doc = json.loads(_path.read_text(encoding="utf-8"))
    _letter = _doc["set"]
    SETS[_letter] = _doc["scenarios"]
    SET_LABELS[_letter] = _doc["label"]
    for _scenario in _doc["scenarios"]:
        _scenario["set"] = _letter

SCENARIOS = [scenario for scenarios in SETS.values() for scenario in scenarios]
