"""The scenario files are data: check their shape and that frozen sets have not changed."""

import hashlib
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from evaluation import scenarios  # noqa: E402

SETS_DIR = scenarios.DATA_DIR
FROZEN = json.loads((SETS_DIR.parent / "frozen.json").read_text(encoding="utf-8"))


def test_frozen_sets_are_unchanged():
    """Once a set's predictions are committed its file must not change.

    A new set is added to frozen.json (shasum -a 256 <file>) when its predictions are committed.
    A deliberate change to a frozen set needs the hash updated in the same commit, and a reason.
    """
    for name, expected in FROZEN.items():
        actual = hashlib.sha256((SETS_DIR / name).read_bytes()).hexdigest()
        assert actual == expected, f"{name} changed after it was frozen"


def test_frozen_files_exist():
    for name in FROZEN:
        assert (SETS_DIR / name).exists(), f"frozen set {name} is missing"


def test_every_set_has_label_and_scenarios():
    for path in SETS_DIR.glob("set_*.json"):
        doc = json.loads(path.read_text(encoding="utf-8"))
        assert doc["set"].isalpha() and len(doc["set"]) == 1, path.name
        assert path.stem == f"set_{doc['set'].lower()}", path.name
        assert doc["label"] and doc["scenarios"], path.name


def test_scenario_shape():
    seen = set()
    for sc in scenarios.SCENARIOS:
        assert sc["id"] not in seen, f"duplicate scenario id {sc['id']}"
        seen.add(sc["id"])
        assert sc["kind"] and sc["messages"] and sc["questions"], sc["id"]
        for days_ago, text in sc["messages"]:
            assert isinstance(days_ago, int) and days_ago >= 0, sc["id"]
            assert isinstance(text, str) and text.strip(), sc["id"]
        for q in sc["questions"]:
            assert isinstance(q["q"], str) and q["q"].strip(), sc["id"]
            for key in ("needs", "avoid", "stale"):
                assert all(isinstance(w, str) for w in q.get(key, [])), sc["id"]
            for group in q.get("expect", []):
                assert group and all(isinstance(w, str) for w in group), sc["id"]
            assert set(q) <= {"q", "expect", "needs", "avoid", "stale"}, sc["id"]


def test_session_scenario_shape():
    """Session sets (consistency across turns): sessions oldest first, turns with optional probes."""
    ids = {sc["id"] for sc in scenarios.SCENARIOS}
    for items in scenarios.SESSION_SETS.values():
        for sc in items:
            assert sc["id"] not in ids, f"duplicate scenario id {sc['id']}"
            ids.add(sc["id"])
            assert set(sc) <= {"id", "kind", "sessions", "set"}, sc["id"]
            days = [s["days_ago"] for s in sc["sessions"]]
            assert days and days == sorted(days, reverse=True), sc["id"]
            for session in sc["sessions"]:
                assert set(session) == {"days_ago", "turns"} and session["turns"]
                for turn in session["turns"]:
                    assert set(turn) <= {"user", "probe"}, sc["id"]
                    assert isinstance(turn["user"], str) and turn["user"].strip()
                    probe = turn.get("probe")
                    if probe is None:
                        continue
                    assert set(probe) <= {"fact", "type", "expect", "forbid"}, sc["id"]
                    assert probe["fact"] and probe["type"] in ("direct", "indirect")
                    assert probe.get("expect") or probe.get("forbid"), sc["id"]
                    for group in probe.get("expect", []):
                        assert group and all(isinstance(w, str) for w in group)
                    assert all(isinstance(w, str) for w in probe.get("forbid", []))


def test_session_sets_are_kept_out_of_the_single_question_sets():
    assert not set(scenarios.SESSION_SETS) & set(scenarios.SETS)


def test_loader_adds_the_set_letter():
    for letter, items in {**scenarios.SETS, **scenarios.SESSION_SETS}.items():
        assert all(sc["set"] == letter for sc in items)
    assert len(scenarios.SCENARIOS) == sum(len(v) for v in scenarios.SETS.values())
