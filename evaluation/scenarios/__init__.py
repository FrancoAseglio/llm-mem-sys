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

Session sets ("format": "sessions", e.g. set K) hold multi-session stories instead, for
consistency across turns. They are loaded into SESSION_SETS and not into SETS or SCENARIOS,
so evaluation/run.py never sees them. A session scenario has
  id, kind  : as above
  sessions  : [{"days_ago": N, "turns": [turn, ...]}, ...], oldest first
A turn is {"user": text} and, if it is scored, also "probe":
  fact     : what it checks; probes of one fact after its last change form a stability group
  type     : "direct" (asks for the fact) or "indirect" (the fact matters but is not asked)
  expect   : as above (every group needs one of its words in the answer)
  forbid   : words that must NOT be in the answer (an outdated or wrong value)

A blind set can be run once. After that it is spent: write a new one to validate a change.
Once a set's predictions are committed its file is frozen: its SHA-256 goes into `frozen.json`
and tests/evaluation/test_scenarios.py fails if the file changes afterwards.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).with_name("sets")

SETS: dict[str, list[dict]] = {}
SESSION_SETS: dict[str, list[dict]] = {}
SET_LABELS: dict[str, str] = {}

for _path in sorted(DATA_DIR.glob("set_*.json")):
    _doc = json.loads(_path.read_text(encoding="utf-8"))
    _letter = _doc["set"]
    (SESSION_SETS if _doc.get("format") == "sessions" else SETS)[_letter] = _doc[
        "scenarios"
    ]
    SET_LABELS[_letter] = _doc["label"]
    for _scenario in _doc["scenarios"]:
        _scenario["set"] = _letter

SCENARIOS = [scenario for scenarios in SETS.values() for scenario in scenarios]
