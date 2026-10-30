"""The exporter that adds a run to results/*.csv: pure functions, no files written."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import export_results as ex  # noqa: E402

RUN = [
    {
        "set": "Z",
        "scenario": "z_one",
        "kind": "stale",
        "question": "Where do I live?",
        "none": {"lines": 0, "memory": [], "correct": False, "stale": False},
        "baseline": {
            "lines": 2,
            "memory": ["a", "b"],
            "needed_present": True,
            "noise_present": None,
            "stale_in_prompt": True,
            "stale_marked": False,
            "answer": "Oslo",
            "correct": False,
            "stale": True,
        },
        "hybrid": {
            "lines": 3,
            "memory": ["x"],
            "needed_present": True,
            "noise_present": None,
            "stale_in_prompt": False,
            "stale_marked": True,
            "answer": "Bergen",
            "correct": True,
            "stale": False,
        },
    }
]


def test_answer_rows():
    rows = ex.answer_rows(RUN, "r1")
    assert [r["mode"] for r in rows] == ["none", "baseline", "hybrid"]
    base = rows[1]
    assert (base["correct"], base["stale_in_answer"], base["noise_present"]) == (
        0,
        1,
        "",
    )
    assert base["memory"] == "a || b"
    assert set(base) == set(ex.ANSWER_FIELDS)


def test_total_rows():
    rows = {r["mode"]: r for r in ex.total_rows(RUN, "r1", "development", 7)}
    assert rows["hybrid"]["correct"] == 1 and rows["hybrid"]["stale_marked"] == 1
    assert rows["baseline"]["stale_answer"] == 1 and rows["baseline"]["avg_lines"] == 2
    assert rows["baseline"]["needed"] == 1 and rows["baseline"]["noise_of"] == 0
    assert all(r["order"] == 7 and r["phase"] == "development" for r in rows.values())
