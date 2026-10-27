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
Deterministic model calls (embeddings, extraction, summaries, temperature-0 answers) are cached in
.cache/llm.sqlite, so a second run of an unchanged set takes seconds; --no-cache forces fresh calls.
By default only baseline and smart answers are generated (--answers none baseline smart for all).

Scoring lives in evaluation/metrics.py, printing in evaluation/report.py, the scenarios in evaluation/scenarios/.
"""

import argparse
import json
import time
from datetime import UTC, datetime, timedelta

from evaluation.metrics import (
    contains_any,
    is_correct,
    needed_fact_present,
    noise_present,
)
from evaluation.report import (
    MODES,
    print_retrieval_problems,
    print_summaries,
    print_table,
    print_wrong_answers,
)
from evaluation.scenarios import SCENARIOS, SETS

from memory_system.assistant import build_messages, recall
from memory_system.core.config import CONSOLIDATE, SUMMARIES
from memory_system.core.db import get_pool
from memory_system.core.llm import cache_stats, chat, enable_cache
from memory_system.core.style import paint, set_enabled, status, status_clear
from memory_system.summaries.consolidate import consolidate
from memory_system.summaries.summarize import summarize_pending
from memory_system.write.manager import ingest_user_message, list_facts


def user_of(scenario: dict) -> str:
    return f"eval_{scenario['id']}"


def ingest(scenario: dict) -> None:
    """Replace the scenario's user with a fresh one and replay its messages."""
    user = user_of(scenario)
    with get_pool().connection() as conn:
        conn.execute("DELETE FROM users WHERE id = %s", (user,))  # cascades
    now = datetime.now(UTC)
    for days_ago, text in sorted(scenario["messages"], key=lambda m: -m[0]):
        ingest_user_message(user, text, at=now - timedelta(days=days_ago))


def print_stored_summaries(user: str) -> None:
    """Notes in order, each marked [merged into #id] once a digest replaced it; digests last."""
    with get_pool().connection() as conn:
        rows = conn.execute(
            "SELECT id, kind, content, digest_id FROM summaries WHERE user_id = %s "
            "ORDER BY kind DESC, id",
            (user,),
        ).fetchall()
    print(f"--- summaries stored for {user} ---")
    for summary_id, kind, content, digest_id in rows:
        if kind == "digest":
            print(f"  DIGEST #{summary_id}: {content}")
        else:
            merged = f" [merged into #{digest_id}]" if digest_id else ""
            print(f"  {content}{merged}")


def print_compression(users: list[str]) -> None:
    """Characters of summary text against the messages it came from, per user and in total.

    sources:  the user messages linked to a note (messages.summary_id)
    notes:    all notes (what the prompt could hold with consolidation off)
    merged:   the notes a digest replaced, and the digests that replaced them
    live:     digests plus the notes no digest replaced (what the prompt can hold now)
    """
    query = """
        SELECT
          (SELECT COALESCE(SUM(LENGTH(content)), 0) FROM messages
            WHERE user_id = %(u)s AND summary_id IS NOT NULL),
          COALESCE(SUM(LENGTH(content)) FILTER (WHERE kind = 'note'), 0),
          COALESCE(SUM(LENGTH(content)) FILTER (WHERE kind = 'note' AND digest_id IS NOT NULL), 0),
          COALESCE(SUM(LENGTH(content)) FILTER (WHERE kind = 'digest'), 0),
          COUNT(*) FILTER (WHERE kind = 'digest'),
          COUNT(*) FILTER (WHERE kind = 'note' AND digest_id IS NOT NULL)
        FROM summaries WHERE user_id = %(u)s"""
    totals = [0] * 6
    print(paint("\nCompression (characters)", "bold"))
    print(
        paint(
            f"{'user':<28}{'sources':>8}{'notes':>7}{'merged':>8}{'digests':>8}"
            f"{'live':>7}   digest/merged  notes/src  live/src",
            "bold",
        )
    )
    empty = 0
    with get_pool().connection() as conn:
        for user in users:
            row = conn.execute(query, {"u": user}).fetchone()
            totals = [t + v for t, v in zip(totals, row, strict=True)]
            if row[0] == 0 and row[1] == 0:  # no notes for this user: nothing to show
                empty += 1
                continue
            _print_compression_row(user, row)
    _print_compression_row("TOTAL", totals, bold=True)
    if empty:
        print(paint(f"  ({empty} users without notes not listed)", "dim"))


def _ratio(a: int, b: int) -> str:
    return f"{a / b:.2f}" if b else "-"


def _ratio_cell(a: int, b: int, width: int) -> str:
    """Ratio padded first, then coloured: green below 1.0 (shorter than the source), red above."""
    text = f"{_ratio(a, b):>{width}}"
    if not b:
        return paint(text, "dim")
    return paint(text, "green" if a < b else "red")


def _print_compression_row(label: str, row, bold: bool = False) -> None:
    sources, notes, merged, digests, n_digests, n_merged = row
    live = notes - merged + digests
    left = f"{label:<28}{sources:>8}{notes:>7}{merged:>8}{digests:>8}{live:>7}"
    tail = (
        paint(f"   ({n_digests} digests from {n_merged} notes)", "dim")
        if n_digests
        else ""
    )
    print(
        paint(left, "bold") if bold else left,
        f"   {_ratio(digests, merged):>13}  ",
        _ratio_cell(notes, sources, 9),
        "  ",
        _ratio_cell(live, sources, 8),
        tail,
        sep="",
    )


def print_stored_facts(scenario: dict) -> None:
    print(f"\n--- facts stored for {scenario['id']} ---")
    for relation, value, state, _imp, _conf, since in list_facts(user_of(scenario)):
        print(f"  {relation:<14}{value:<22}{state:<12}{since}")


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
        if not args.retrieval_only and mode in args.answers:
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
    parser.add_argument(
        "--answers",
        nargs="+",
        choices=MODES,
        default=["baseline", "smart"],
        help="modes whose answers are generated (default: baseline smart; the no-memory "
        "answers never depend on memory, so they rarely need recomputing)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="ask the model every time (use for a final, fresh run); by default "
        "deterministic calls are cached in .cache/llm.sqlite",
    )
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--k", type=int, default=4)
    parser.add_argument(
        "--no-color", action="store_true", help="plain text (also: NO_COLOR=1)"
    )
    args = parser.parse_args()
    if args.no_color:
        set_enabled(False)
    if not args.no_cache:
        enable_cache()

    scenarios = [
        s
        for s in SCENARIOS
        if (not args.only or s["id"] in args.only)
        and (not args.set or s["set"] in args.set)
    ]
    results = []
    total = sum(len(sc["questions"]) for sc in scenarios)
    started = time.perf_counter()

    for sc in scenarios:
        if not args.no_ingest:
            status(f"ingesting {sc['id']} ({len(sc['messages'])} messages)...")
            ingest(sc)
        if SUMMARIES:  # only new messages are summarised, so re-runs change nothing
            kept = summarize_pending(user_of(sc))
            if kept:  # silent when nothing is new
                status(f"{sc['id']}: {len(kept)} summaries written")
            if CONSOLIDATE:
                digests = consolidate(user_of(sc))
                if digests:
                    status(f"{sc['id']}: {len(digests)} digests written")
        if args.verbose:
            status_clear()
            print_stored_facts(sc)
            if SUMMARIES:
                print_stored_summaries(user_of(sc))
        for q in sc["questions"]:
            results.append(ask(sc, q, args))
            status(f"[{len(results)}/{total}] {sc['id']}: {q['q'][:60]}")
            if args.verbose:
                status_clear()

    status_clear()
    print_table(results)
    print_summaries(results)
    print_retrieval_problems(results)
    if not args.retrieval_only:
        print_wrong_answers(results)
    if SUMMARIES:
        print_compression([user_of(sc) for sc in scenarios])

    with open("eval_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str, ensure_ascii=False)
    stats = cache_stats()
    cache_note = (
        f"   cache: {stats[0]} hits, {stats[1]} misses" if stats else "   cache: off"
    )
    print(
        paint(
            f"\nsaved eval_results.json   ({time.perf_counter() - started:.0f}s){cache_note}",
            "dim",
        )
    )


if __name__ == "__main__":
    main()
