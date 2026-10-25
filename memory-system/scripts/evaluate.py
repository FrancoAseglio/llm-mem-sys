"""Replay scenarios with backdated messages, then ask each question with
no memory, baseline vector memory and smart memory.

Measured without the LLM (fast, objective):
  needed fact in prompt  did the memory lines contain what the question needs?
  noise in prompt        did they contain words that should NOT be there?
  stale value in prompt  did an outdated value reach the prompt?
Measured with the LLM (slower, noisier):
  answers correct        did the reply contain the right words?

    poetry run python scripts/evaluate.py --set B                        # ingest + everything
    poetry run python scripts/evaluate.py --set A --no-ingest --retrieval-only   # seconds
    poetry run python scripts/evaluate.py --only b_stale_flood --verbose
Results are also written to eval_results.json.
"""

import argparse
import json
import time
from datetime import datetime, timedelta, timezone

from scenarios import SCENARIOS

from memory_system.assistant import build_messages, recall
from memory_system.db import get_pool
from memory_system.llm import chat
from memory_system.manager import ingest_user_message, list_facts

MODES = ["none", "baseline", "smart"]


def user_of(scenario: dict) -> str:
    return f"eval_{scenario['id']}"


def ingest(scenario: dict) -> None:
    user = user_of(scenario)
    with get_pool().connection() as conn:
        conn.execute("DELETE FROM users WHERE id = %s", (user,))  # cascades
    now = datetime.now(timezone.utc)
    for days_ago, text in sorted(scenario["messages"], key=lambda m: -m[0]):
        ingest_user_message(user, text, at=now - timedelta(days=days_ago))


def normalise(text: str) -> str:
    return text.lower().replace("\u2019", "'")


def is_correct(answer: str, question: dict) -> bool | None:
    if not question.get("expect"):
        return None  # retrieval-only question
    a = normalise(answer)
    return all(any(word in a for word in group) for group in question["expect"])


def contains_any(text: str, words: list[str]) -> bool:
    t = normalise(text)
    return any(word in t for word in words)


def needed_fact_present(lines: list[str], question: dict) -> bool | None:
    needs = question.get("needs")
    if not needs:
        return None
    text = normalise(" ".join(lines))
    return all(word in text for word in needs)


def noise_present(lines: list[str], question: dict) -> bool | None:
    avoid = question.get("avoid")
    if not avoid:
        return None
    return contains_any(" ".join(lines), avoid)


def mark(value: bool | None, bad_is_true: bool = False) -> str:
    if value is None:
        return "-"
    good = (not value) if bad_is_true else value
    return "✓" if good else "✗"


def tally(rows: list[dict], mode: str, key: str) -> str:
    values = [r[mode][key] for r in rows if r[mode].get(key) is not None]
    return f"{sum(values)}/{len(values)}" if values else "-"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--set",
        nargs="+",
        choices=["A", "B", "C", "D", "E", "F"],
        help="scenario sets to run",
    )
    parser.add_argument("--only", nargs="+", help="scenario ids to run")
    parser.add_argument(
        "--no-ingest", action="store_true", help="reuse existing eval data"
    )
    parser.add_argument(
        "--retrieval-only", action="store_true", help="skip the LLM answers"
    )
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--k", type=int, default=4)
    args = parser.parse_args()

    scenarios = [
        s
        for s in SCENARIOS
        if (not args.only or s["id"] in args.only)
        and (not args.set or s["set"] in args.set)
    ]
    results = []
    started = time.perf_counter()

    for sc in scenarios:
        if not args.no_ingest:
            print(
                f"ingesting {sc['id']} ({len(sc['messages'])} messages)...", flush=True
            )
            ingest(sc)
        if args.verbose:
            print(f"\n--- facts stored for {sc['id']} ---")
            for relation, value, status, imp, conf, since in list_facts(user_of(sc)):
                print(f"  {relation:<14}{value:<22}{status:<12}{since}")

        for q in sc["questions"]:
            row = {
                "set": sc["set"],
                "scenario": sc["id"],
                "kind": sc["kind"],
                "question": q["q"],
                "messages_in_history": len(sc["messages"]),
            }
            for mode in MODES:
                lines = recall(mode, user_of(sc), q["q"], args.k, touch=False)
                entry = {
                    "lines": len(lines),
                    "memory": lines,
                    "needed_present": needed_fact_present(lines, q),
                    "noise_present": noise_present(lines, q),
                    "stale_in_prompt": contains_any(
                        " ".join(lines), q.get("stale", [])
                    ),
                }
                if not args.retrieval_only:
                    answer = chat(
                        build_messages(mode, lines, [], q["q"]), temperature=0
                    )
                    entry.update(
                        answer=answer,
                        correct=is_correct(answer, q),
                        stale=contains_any(answer, q.get("stale", [])),
                    )
                row[mode] = entry
                if args.verbose:
                    print(f"\n[{mode}] {q['q']}")
                    for line in lines:
                        print(f"    recalled: {line}")
                    if "answer" in entry:
                        print(f"    answer: {entry['answer']}")
            results.append(row)
            print(f"  done: {sc['id']}: {q['q'][:60]}", flush=True)

    # ---- table ----
    print(
        f"\n{'scenario / question':<40}{'kind':<11}{'hist':>5} |"
        f"{'need b/s':>10}{'noise b/s':>11} |{'answer n/b/s':>16} |{'lines b/s':>10}"
    )
    for r in results:
        label = f"{r['scenario']}: {r['question']}"[:38]
        need = f"{mark(r['baseline']['needed_present'])}/{mark(r['smart']['needed_present'])}"
        noise = (
            f"{mark(r['baseline']['noise_present'], True)}/"
            f"{mark(r['smart']['noise_present'], True)}"
        )
        ans = "/".join(mark(r[m].get("correct")) for m in MODES)
        lines = f"{r['baseline']['lines']}/{r['smart']['lines']}"
        print(
            f"{label:<40}{r['kind']:<11}{r['messages_in_history']:>5} |"
            f"{need:>10}{noise:>11} |{ans:>16} |{lines:>10}"
        )

    # ---- summary, one block per set ----
    for set_name in sorted({r["set"] for r in results}):
        rows = [r for r in results if r["set"] == set_name]
        label = {
            "A": "A (tuning set, cannot validate)",
            "B": "B (spent: the floor and window were chosen after seeing it)",
            "C": "C (spent: written before the relative window ran on it)",
            "D": "D (BLIND: written before routing existed in the pipeline; run once)",
            "E": "E (BLIND: written before the safety bypass and goal prompt; run once)",
            "F": "F (BLIND: write path only, written after the write-path fixes; run once)",
        }[set_name]
        print(f"\nSET {label}: {len(rows)} questions")
        print(
            f"{'mode':<10}{'needed':>9}{'noise':>8}{'stale in':>10}{'avg':>7}"
            f"{'answers':>10}{'stale in':>10}"
        )
        print(
            f"{'':<10}{'present':>9}{'present':>8}{'prompt':>10}{'lines':>7}"
            f"{'correct':>10}{'answer':>10}"
        )
        for m in ("baseline", "smart"):
            stale_prompt = sum(r[m]["stale_in_prompt"] for r in rows)
            avg = sum(r[m]["lines"] for r in rows) / len(rows)
            print(
                f"{m:<10}{tally(rows, m, 'needed_present'):>9}"
                f"{tally(rows, m, 'noise_present'):>8}{stale_prompt:>10}{avg:>7.1f}"
                f"{tally(rows, m, 'correct'):>10}{tally(rows, m, 'stale'):>10}"
            )
        print("  (noise present: lower is better; stale in prompt: lower is better)")

    # ---- misses ----
    misses = [
        (r, m, why)
        for r in results
        for m in ("baseline", "smart")
        for why, bad in (
            ("needed fact missing", r[m]["needed_present"] is False),
            ("noise in prompt", r[m]["noise_present"] is True),
        )
        if bad
    ]
    if misses:
        print("\nRetrieval problems")
        for r, m, why in misses:
            print(f"  [{m}] {r['scenario']}: {why}")
            print(f"      recalled: {r[m]['memory'] or 'nothing'}")

    if not args.retrieval_only:
        wrong = [
            (r, m)
            for r in results
            for m in ("baseline", "smart")
            if r[m]["correct"] is False
        ]
        if wrong:
            print("\nWrong answers (baseline and smart)")
            for r, m in wrong:
                note = "   <-- fact WAS in the prompt" if r[m]["needed_present"] else ""
                print(f"  [{m}] {r['scenario']}: {r['question'][:60]}{note}")
                print(f"      answer: {r[m]['answer'][:200]!r}")

    with open("eval_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str, ensure_ascii=False)
    print(f"\nsaved eval_results.json   ({time.perf_counter() - started:.0f}s)")


if __name__ == "__main__":
    main()
