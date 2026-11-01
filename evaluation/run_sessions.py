"""Consistency across turns: replay multi-session stories (set K) in three modes at once.

The design is frozen in docs/predictions/set_K.md, section 1 (git tag docs-archive). Per story: a fresh user. For each
user turn, in order, every mode (none, baseline, smart) recalls its memory lines for the turn and
the model answers at temperature 0 with that mode's chat history of the current session (the last
6 messages, as in the chat). Then the turn is ingested once: the write path does not depend on the
mode, and replies are never stored. Each session starts with an empty history, so between
sessions only memory carries anything. At the end of a session the notes are written and
consolidation runs, as configured.

    poetry run python -m evaluation.run_sessions                  # set K, every story
    poetry run python -m evaluation.run_sessions --only k_move --verbose
    poetry run python -m evaluation.run_sessions --no-cache       # a fresh run

Results are written to eval_sessions.json. Keyword scores are printed; the hand review (rules in
set_K.md) is done afterwards on the listed answers.
"""

import argparse
import json
import time
from datetime import UTC, datetime, timedelta

from evaluation.scenarios import SESSION_SETS, SET_LABELS
from evaluation.session_metrics import score_probe, stability_groups, totals
from memory_system.assistant import build_messages, recall
from memory_system.core.config import CONSOLIDATE, SUMMARIES
from memory_system.core.db import get_pool
from memory_system.core.llm import cache_stats, chat, enable_cache
from memory_system.core.style import (
    colour_marks,
    memory_line,
    paint,
    paint_all,
    set_enabled,
    status,
    status_clear,
)
from memory_system.summaries.consolidate import consolidate
from memory_system.summaries.summarize import summarize_pending
from memory_system.write.manager import ingest_user_message

MODES = ["none", "baseline", "smart"]
HISTORY = (
    6  # messages of the current session passed to the model, as in scripts/chat.py
)
K = 4


def user_of(scenario: dict) -> str:
    return f"eval_{scenario['id']}"


def run_story(scenario: dict, verbose: bool) -> list[dict]:
    """Replay one story. Returns one record per probe, with every mode's lines and answer."""
    user = user_of(scenario)
    with get_pool().connection() as conn:
        conn.execute("DELETE FROM users WHERE id = %s", (user,))  # cascades
    now = datetime.now(UTC)
    probes = []
    for s_index, session in enumerate(scenario["sessions"], 1):
        day = now - timedelta(days=session["days_ago"])
        history = {mode: [] for mode in MODES}
        if verbose:
            status_clear()
            print(
                paint(
                    f"\n--- {scenario['id']}, session {s_index} "
                    f"({session['days_ago']} days ago)",
                    "bold",
                )
            )
        for t_index, turn in enumerate(session["turns"]):
            text = turn["user"]
            status(f"{scenario['id']} s{s_index}: {text[:60]}")
            record = {"user": text}
            for mode in MODES:
                lines = recall(mode, user, text, K, touch=False)
                answer = chat(
                    build_messages(mode, lines, history[mode][-HISTORY:], text),
                    temperature=0,
                )
                history[mode] += [
                    {"role": "user", "content": text},
                    {"role": "assistant", "content": answer},
                ]
                record[mode] = {"lines": lines, "answer": answer}
            probe = turn.get("probe")
            if probe:
                for mode in MODES:
                    record[mode].update(
                        score_probe(
                            record[mode]["answer"], record[mode]["lines"], probe
                        )
                    )
                probes.append(
                    {
                        "set": scenario["set"],
                        "scenario": scenario["id"],
                        "session": s_index,
                        "fact": probe["fact"],
                        "type": probe["type"],
                        "expect": probe.get("expect", []),
                        "forbid": probe.get("forbid", []),
                        **record,
                    }
                )
            if verbose:
                print_turn(record, probe)
            ingest_user_message(user, text, at=day + timedelta(minutes=t_index))
        if SUMMARIES:
            summarize_pending(user)
            if CONSOLIDATE:
                consolidate(user)
    return probes


def print_turn(record: dict, probe: dict | None) -> None:
    status_clear()
    tag = paint(f"  [probe: {probe['fact']}, {probe['type']}]", "cyan") if probe else ""
    print(f"\nyou> {record['user']}{tag}")
    for mode in MODES:
        entry = record[mode]
        for line in entry["lines"]:
            print(f"    {paint(mode, 'purple')} recalled: {memory_line(line)}")
        marks = ""
        if probe:
            marks = " " + colour_marks("✓" if entry["correct"] else "✗")
            if entry["forbid_raw"]:
                marks += paint(" FORBID", "red")
        answer = " ".join(entry["answer"].split())
        print(f"  {paint(mode, 'purple')}>{marks} {answer[:300]}")


def mark(value) -> str:
    if value is None:
        return "-"
    return "✓" if value else "✗"


LEGEND = (
    "n = none (no memory)   b = baseline vector memory   s = smart (this system)",
    "CORRECT  ✓ right answer   ✗ wrong   bold name = smart has a ✗",
    "FORBID   ! outdated or wrong value in the answer   . clean   - not tested",
)


def print_table(probes: list[dict]) -> None:
    status_clear()
    print()
    for line in LEGEND:
        print(paint("  " + line, "dim"))
    head = f"{'story / probe':<52}{'type':<10}{'correct n/b/s':>15}{'forbid n/b/s':>15}"
    print(paint(head, "bold"))
    for p in probes:
        name = f"{p['scenario']}: {p['user']}"[:50]
        correct = "/".join(mark(p[m]["correct"]) for m in MODES)
        forbid = "/".join(
            "-" if p[m]["forbid_raw"] is None else ("!" if p[m]["forbid_raw"] else ".")
            for m in MODES
        )
        miss = not p["smart"]["correct"] or bool(p["smart"]["forbid_raw"])
        cells = colour_marks(f"{correct:>15}") + paint_all(
            f"{forbid:>15}", {"!": "red"}
        )
        print(
            f"{paint(f'{name:<52}', *(('bold',) if miss else ()))}{p['type']:<10}{cells}"
        )


def print_totals(probes: list[dict], label: str) -> dict:
    t = {mode: totals(probes, mode) for mode in MODES}
    print(paint(f"\nSET {label}", "bold", "cyan"))
    print(paint("  keyword scores, before the hand review (rules in set_K.md)", "dim"))
    rows = [
        ("correct", "correct", "probes"),
        ("contradictions, raw", "contradictions_raw", "forbid_probes"),
        ("forbidden word in prompt", "forbid_in_prompt", "forbid_probes"),
        ("stable facts", "stable", "groups"),
        ("indirect correct", "indirect_correct", "indirect"),
    ]
    print(paint(f"  {'':<28}" + "".join(f"{m:>12}" for m in MODES), "bold"))
    for label_, key, of in rows:
        higher_is_better = key in ("correct", "stable", "indirect_correct")
        styles = _better(t["baseline"][key], t["smart"][key], higher_is_better)
        cells = paint(f"{t['none'][key]}/{t['none'][of]}".rjust(12), "dim")
        for m, style in zip(("baseline", "smart"), styles, strict=True):
            cells += paint(
                f"{t[m][key]}/{t[m][of]}".rjust(12), *([style] if style else [])
            )
        print(f"  {label_:<28}{cells}")
    print(
        paint("  ", "dim")
        + paint("green", "green")
        + paint(" = better than the other memory mode, ", "dim")
        + paint("red", "red")
        + paint(" = worse; none is shown for reference", "dim")
    )
    print(
        paint("  lower is better for: contradictions, forbidden word in prompt", "dim")
    )
    return t


def _better(base: int, smart: int, higher_is_better: bool) -> tuple[str, str]:
    """Styles for baseline and smart in one row: the better value green, the worse red."""
    if base == smart:
        return "", ""
    base_wins = (base > smart) == higher_is_better
    return ("green", "red") if base_wins else ("red", "green")


def print_review(probes: list[dict]) -> None:
    """Every answer the hand review must read: forbidden-word hits and the hand-scored probes."""
    print(paint("\nTo review by hand", "bold"))
    for p in probes:
        hand = p["fact"] == "allergy" and p["type"] == "indirect"
        for mode in MODES:
            entry = p[mode]
            if not (entry["forbid_raw"] or hand):
                continue
            why = "scored by hand" if hand else f"forbidden word {p['forbid']}"
            answer = " ".join(entry["answer"].split())
            print(f"  [{paint(mode, 'purple')}] {p['scenario']}: {p['user']}  ({why})")
            print(f"      {answer}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", nargs="+", default=list(SESSION_SETS))
    parser.add_argument("--only", nargs="+", help="story ids to run")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--no-color", action="store_true")
    args = parser.parse_args()
    if args.no_color:
        set_enabled(False)
    if not args.no_cache:
        enable_cache()
    unknown = [s for s in args.set if s not in SESSION_SETS]
    if unknown:
        parser.error(f"unknown session set {unknown}, available: {list(SESSION_SETS)}")

    started = time.perf_counter()
    results = {}
    for letter in args.set:
        stories = [
            s for s in SESSION_SETS[letter] if not args.only or s["id"] in args.only
        ]
        probes = [p for s in stories for p in run_story(s, args.verbose)]
        print_table(probes)
        groups = stability_groups(probes)
        print(paint(f"\nstable facts ({len(groups)} groups)", "bold"))
        for (story, fact), group in groups.items():
            cells = "/".join(
                mark(all(p[m]["correct"] and not p[m]["forbid_raw"] for p in group))
                for m in MODES
            )
            print(f"  {story + ': ' + fact:<40}{colour_marks(cells)}")
        t = print_totals(probes, SET_LABELS[letter])
        print_review(probes)
        results[letter] = {"probes": probes, "totals": t}

    with open("eval_sessions.json", "w") as f:
        json.dump(results, f, indent=2, default=str, ensure_ascii=False)
    stats = cache_stats()
    note = f"   cache: {stats[0]} hits, {stats[1]} misses" if stats else "   cache: off"
    print(f"\nsaved eval_sessions.json   ({time.perf_counter() - started:.0f}s){note}")


if __name__ == "__main__":
    main()
