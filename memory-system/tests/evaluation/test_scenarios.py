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


def test_loader_adds_the_set_letter():
    for letter, items in scenarios.SETS.items():
        assert all(sc["set"] == letter for sc in items)
    assert len(scenarios.SCENARIOS) == sum(len(v) for v in scenarios.SETS.values())
