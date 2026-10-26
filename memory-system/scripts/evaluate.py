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
SUMMARIES=0 in the environment switches the summaries layer off (nothing written or shown).

Scoring lives in eval_metrics.py, printing in eval_report.py, the scenarios in scenarios/.
"""

import argparse
import json
import time
from datetime import datetime, timedelta, timezone

from eval_metrics import contains_any, is_correct, needed_fact_present, noise_present
from eval_report import (
    MODES,
    print_retrieval_problems,
    print_summaries,
    print_table,
    print_wrong_answers,
)
from scenarios import SCENARIOS, SETS

from memory_system.assistant import build_messages, recall
from memory_system.config import SUMMARIES
from memory_system.db import get_pool
from memory_system.llm import chat
from memory_system.manager import ingest_user_message, list_facts
from memory_system.summarize import summarize_pending


def user_of(scenario: dict) -> str:
    return f"eval_{scenario['id']}"


def ingest(scenario: dict) -> None:
    """Replace the scenario's user with a fresh one and replay its messages."""
    user = user_of(scenario)
    with get_pool().connection() as conn:
        conn.execute("DELETE FROM users WHERE id = %s", (user,))  # cascades
    now = datetime.now(timezone.utc)
    for days_ago, text in sorted(scenario["messages"], key=lambda m: -m[0]):
        ingest_user_message(user, text, at=now - timedelta(days=days_ago))


def print_stored_summaries(user: str) -> None:
    with get_pool().connection() as conn:
        rows = conn.execute(
            "SELECT content FROM summaries WHERE user_id = %s ORDER BY id", (user,)
        ).fetchall()
    print(f"--- summaries stored for {user} ---")
    for (content,) in rows:
        print(f"  {content}")


def print_stored_facts(scenario: dict) -> None:
    print(f"\n--- facts stored for {scenario['id']} ---")
    for relation, value, status, imp, conf, since in list_facts(user_of(scenario)):
        print(f"  {relation:<14}{value:<22}{status:<12}{since}")


def ask(scenario: dict, question: dict, args: argparse.Namespace) -> dict:
    """Ask one question in every mode and score it. Returns one result row."""
    row = {
        "set": scenario["set"],
        "scenario": scenario["id"],
        "kind": scenario["kind"],
        "question": question["q"],
        "messages_in_history": len(scenario["messages"]),
    }
    for mode in MODES:
        lines = recall(mode, user_of(scenario), question["q"], args.k, touch=False)
        entry = {
            "lines": len(lines),
            "memory": lines,
            "needed_present": needed_fact_present(lines, question),
            "noise_present": noise_present(lines, question),
            "stale_in_prompt": contains_any(" ".join(lines), question.get("stale", [])),
        }
        if not args.retrieval_only:
            answer = chat(build_messages(mode, lines, [], question["q"]), temperature=0)
            entry.update(
                answer=answer,
                correct=is_correct(answer, question),
                stale=contains_any(answer, question.get("stale", [])),
            )
        row[mode] = entry
        if args.verbose:
            print(f"\n[{mode}] {question['q']}")
            for line in lines:
                print(f"    recalled: {line}")
            if "answer" in entry:
                print(f"    answer: {entry['answer']}")
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--set", nargs="+", choices=list(SETS), help="scenario sets to run"
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
        if SUMMARIES:  # only new messages are summarised, so re-runs change nothing
            kept = summarize_pending(user_of(sc))
            print(f"  summaries written: {len(kept)}", flush=True)
        if args.verbose:
            print_stored_facts(sc)
            if SUMMARIES:
                print_stored_summaries(user_of(sc))
        for q in sc["questions"]:
            results.append(ask(sc, q, args))
            print(f"  done: {sc['id']}: {q['q'][:60]}", flush=True)

    print_table(results)
    print_summaries(results)
    print_retrieval_problems(results)
    if not args.retrieval_only:
        print_wrong_answers(results)

    with open("eval_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str, ensure_ascii=False)
    print(f"\nsaved eval_results.json   ({time.perf_counter() - started:.0f}s)")


if __name__ == "__main__":
    main()
