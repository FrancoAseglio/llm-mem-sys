"""Add one evaluation run to the result tables in results/ (see results/README.md).

    poetry run python -m evaluation.export --run M_new --phase development \
        --description "set M after change X" eval_results.json
    poetry run python -m evaluation.export --run K_new --phase regression eval_sessions.json

Appends to results/runs.csv, results/totals.csv and, for evaluation/run.py runs, results/answers.csv
(one row per question and mode) or, for set K runs, results/sessions.csv (one row per probe and
mode). A run id that is already in runs.csv is refused, so a run is never counted twice.
`make eval` and `make sessions` call this after the run.
"""

import argparse
import csv
import json
from pathlib import Path

RESULTS = Path(__file__).resolve().parents[1] / "results"
MODES = ("none", "baseline", "smart", "hybrid", "full")
PHASES = ("blind", "development", "regression", "ablation", "noise check", "rerun")

ANSWER_FIELDS = [
    "run", "set", "scenario", "kind", "qtype", "question", "mode", "correct",
    "needed_present", "noise_present", "stale_in_prompt", "stale_marked",
    "stale_in_answer", "lines", "answer", "memory",
]  # fmt: skip
SESSION_FIELDS = [
    "run", "scenario", "session", "fact", "type", "probe", "mode", "correct",
    "forbid_in_answer", "forbid_in_prompt", "lines", "answer", "memory",
]  # fmt: skip
TOTAL_FIELDS = [
    "order", "run", "phase", "set", "mode", "questions", "correct", "answered",
    "needed", "needed_of", "noise", "noise_of", "stale_in_prompt", "stale_marked",
    "stale_answer", "avg_lines", "source",
]  # fmt: skip


def flag(value) -> int | str:
    """1, 0, or empty when the metric does not apply."""
    return "" if value is None else int(bool(value))


def answer_rows(data: list[dict], run: str) -> list[dict]:
    """One row per question and mode of an evaluation/run.py run (eval_results.json)."""
    rows = []
    for r in data:
        for mode in MODES:
            if mode not in r:
                continue
            e = r[mode]
            rows.append(
                {
                    "run": run,
                    "set": r["set"],
                    "scenario": r["scenario"],
                    "kind": r["kind"],
                    "qtype": "",
                    "question": r["question"],
                    "mode": mode,
                    "correct": flag(e.get("correct")),
                    "needed_present": flag(e.get("needed_present")),
                    "noise_present": flag(e.get("noise_present")),
                    "stale_in_prompt": flag(e.get("stale_in_prompt")),
                    "stale_marked": flag(e.get("stale_marked")),
                    "stale_in_answer": flag(e.get("stale")),
                    "lines": e["lines"],
                    "answer": e.get("answer", ""),
                    "memory": " || ".join(e.get("memory", [])),
                }
            )
    return rows


def total_rows(data: list[dict], run: str, phase: str, order: int) -> list[dict]:
    """One row per set and mode with the counts the evaluation summary prints."""
    groups: dict[tuple[str, str], list[dict]] = {}
    for r in data:
        for mode in MODES:
            if mode in r:
                groups.setdefault((r["set"], mode), []).append(r[mode])
    rows = []
    for (set_, mode), entries in sorted(groups.items()):

        def tally(key: str, entries: list[dict] = entries) -> tuple[int, int]:
            values = [e.get(key) for e in entries if e.get(key) is not None]
            return sum(map(bool, values)), len(values)

        correct, answered = tally("correct")
        rows.append(
            {
                "order": order,
                "run": run,
                "phase": phase,
                "set": set_,
                "mode": mode,
                "questions": len(entries),
                "correct": correct if answered else "",
                "answered": answered or "",
                "needed": tally("needed_present")[0],
                "needed_of": tally("needed_present")[1],
                "noise": tally("noise_present")[0],
                "noise_of": tally("noise_present")[1],
                "stale_in_prompt": sum(bool(e.get("stale_in_prompt")) for e in entries),
                "stale_marked": sum(bool(e.get("stale_marked")) for e in entries),
                "stale_answer": tally("stale")[0] if answered else "",
                "avg_lines": round(sum(e["lines"] for e in entries) / len(entries), 2),
                "source": "json",
            }
        )
    return rows


def session_rows(data: dict, run: str, phase: str, order: int) -> tuple[list, list]:
    """Probe rows and totals of a set K run (eval_sessions.json)."""
    probes, totals = [], []
    for set_, block in data.items():
        for p in block["probes"]:
            for mode in MODES:
                if mode not in p:
                    continue
                e = p[mode]
                probes.append(
                    {
                        "run": run,
                        "scenario": p["scenario"],
                        "session": p["session"],
                        "fact": p["fact"],
                        "type": p["type"],
                        "probe": p["user"],
                        "mode": mode,
                        "correct": flag(e["correct"]),
                        "forbid_in_answer": flag(e.get("forbid_raw")),
                        "forbid_in_prompt": flag(e.get("forbid_in_prompt")),
                        "lines": len(e["lines"]),
                        "answer": e["answer"],
                        "memory": " || ".join(e["lines"]),
                    }
                )
        for mode, t in block["totals"].items():
            totals.append(
                {
                    "order": order,
                    "run": run,
                    "phase": phase,
                    "set": set_,
                    "mode": mode,
                    "questions": t["probes"],
                    "correct": t["correct"],
                    "answered": t["probes"],
                    "stale_answer": t["contradictions_raw"],
                    "stale_in_prompt": t["forbid_in_prompt"],
                    "source": "json",
                }
            )
    return probes, totals


def append(name: str, rows: list[dict], fields: list[str]) -> None:
    path = RESULTS / name
    new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if new:
            writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="eval_results.json or eval_sessions.json")
    parser.add_argument("--run", required=True, help="a new run id, e.g. M_after_fix")
    parser.add_argument("--phase", required=True, choices=PHASES)
    parser.add_argument("--description", default="")
    args = parser.parse_args()

    runs_path = RESULTS / "runs.csv"
    runs = list(csv.DictReader(open(runs_path, encoding="utf-8")))
    if any(r["run"] == args.run for r in runs):
        raise SystemExit(f"run {args.run} is already in {runs_path}")
    order = max((int(r["order"]) for r in runs), default=0) + 1
    data = json.loads(Path(args.source).read_text(encoding="utf-8"))

    if isinstance(data, dict):
        probes, totals = session_rows(data, args.run, args.phase, order)
        append("sessions.csv", probes, SESSION_FIELDS)
    else:
        append("answers.csv", answer_rows(data, args.run), ANSWER_FIELDS)
        totals = total_rows(data, args.run, args.phase, order)
    append("totals.csv", totals, TOTAL_FIELDS)
    append(
        "runs.csv",
        [
            {
                "order": order,
                "run": args.run,
                "phase": args.phase,
                "description": args.description,
            }
        ],
        ["order", "run", "phase", "description"],
    )
    print(f"added run {args.run} (order {order}) to {RESULTS}")


if __name__ == "__main__":
    main()
