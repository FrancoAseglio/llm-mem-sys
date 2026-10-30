"""Show how EVERY fact scores for a question, so you can see why each was kept or dropped.

    poetry run python scripts/inspect_scores.py --scenario b_stale_flood
    poetry run python scripts/inspect_scores.py --all
    poetry run python scripts/inspect_scores.py --user demo --question "Where do I live?"

Needs data from a previous evaluation run (python -m evaluation.run) (users are named eval_<scenario>).

Columns
  pick   PIN = pinned, yes = passed the relevance gate (and is in the top k), - = dropped
  raw    raw cosine similarity between the question and the fact  (the GATE uses this)
  score  blended ranking score (only decides order among facts that pass the gate)
  sim..con  the five ranking components after rescaling, each 0 to 1
  age    days since the fact was last created, repeated or used
  ★      the fact this question actually needs
"""

import argparse

from evaluation.scenarios import SCENARIOS
from memory_system.core.config import (
    MIN_RELEVANCE,
    PIN_IMPORTANCE,
    RELATIVE_WINDOW,
    ROUTING_TOP_N,
    SAFETY_BYPASS,
    SAFETY_RELATIONS,
)
from memory_system.core.style import paint, set_enabled
from memory_system.read.retrieve import (
    best_raw,
    gate_failure,
    retrieve_baseline,
    score_facts,
    select_memories,
)

NEAR = 0.05  # a fact this close to being let in (or out) is shown yellow


def light(failure: tuple[str, float] | None) -> str:
    """Traffic light for the gate: green passes, yellow misses by NEAR or less, red is out."""
    if failure is None:
        return "green"
    stage, amount = failure
    return "yellow" if stage in ("floor", "window") and amount <= NEAR else "red"


def why(failure: tuple[str, float] | None, picked: bool) -> str:
    """The gate result in words, for the 'gate' column."""
    if failure is None:
        return "passes" if picked else "cut by k"
    stage, amount = failure
    if stage == "routing":
        return f"rank {int(amount)}>{ROUTING_TOP_N}"
    return f"{stage} -{amount:.2f}"


def show(user: str, question: str, needs: list[str], k: int) -> None:
    scored = score_facts(user, question)
    pinned, relevant = select_memories(scored, k)
    picked = {m.id: ("PIN" if m.pinned else "yes") for m in pinned + relevant}

    def needed(text: str) -> bool:
        return any(n in text.lower() for n in needs)

    print(paint(f"\n{'=' * 96}", "dim"))
    print(paint(f"Q: {question}", "bold"), paint(f"  [user={user}]", "dim"))
    pinning = "off" if PIN_IMPORTANCE > 1 else f"importance >= {PIN_IMPORTANCE}"
    bypass = sorted(SAFETY_RELATIONS) if SAFETY_BYPASS and ROUTING_TOP_N else "off"
    for line in (
        f"needs: {needs or '-'}   k={k}   (★ marks a row that contains a needs word)",
        f"gate: raw >= {MIN_RELEVANCE} and within {RELATIVE_WINDOW} of the best",
        f"relation rank <= {ROUTING_TOP_N or 'off'}",
        f"pinning: {pinning}",
        f"safety bypass: {bypass}",
    ):
        print(paint("   " + line, "cyan"))
    if not scored:
        print(paint("   (no active facts, run the evaluation first)", "yellow"))
    else:
        print(paint("\n   FACTS (smart memory)", "bold"))
        print(
            paint(
                f"   {'pick':<5}{'raw':>6}{'score':>7}{'sim':>6}{'imp':>6}{'rec':>6}"
                f"{'use':>6}{'con':>6}{'age':>6}{'rel#':>5}  {'gate':<14}fact",
                "bold",
            )
        )
        best = best_raw(scored)
        for m in sorted(scored, key=lambda m: -m.raw_similarity):
            p = m.parts
            star = paint("★ ", "yellow") if needed(m.value) else "  "
            pick = picked.get(m.id, "-")
            pick_style = {"yes": "green", "PIN": "cyan"}.get(pick, "dim")
            failure = gate_failure(m, best)
            raw_style = light(failure)
            rest = (
                f"{m.score:>7.2f}"
                f"{p['similarity']:>6.2f}{p['importance']:>6.2f}{p['recency']:>6.2f}"
                f"{p['usage']:>6.2f}{p['confidence']:>6.2f}{m.age_days:>6.0f}{m.relation_rank:>5}  "
                f"{why(failure, pick != '-'):<14}"
            )
            fact = f"{m.relation} = {m.value}"
            dropped = pick == "-"  # dropped rows go grey, the raw light stays
            print(
                f"   {paint(f'{pick:<5}', pick_style)}"
                f"{paint(f'{m.raw_similarity:>6.2f}', raw_style)}"
                f"{paint(rest, 'dim') if dropped else rest}"
                f"{star}{paint(fact, 'dim') if dropped else fact}"
            )

        wanted = [m.raw_similarity for m in scored if needed(m.value)]
        others = [m.raw_similarity for m in scored if not needed(m.value)]
        if wanted and others:
            margin = min(wanted) - max(others)
            verdict = (
                "a similarity gate can separate them"
                if margin > 0
                else "similarity ALONE cannot separate them"
            )
            print(
                f"\n   raw similarity: needed {min(wanted):.2f} to {max(wanted):.2f} | "
                f"best other {max(others):.2f} | margin "
                + paint(f"{margin:+.2f} -> {verdict}", "green" if margin > 0 else "red")
            )
        for m in scored:
            if needed(m.value) and m.id not in picked:
                what = paint(f"MISSED: {m.relation}={m.value}:", "bold", "red")
                failure = gate_failure(m, best)
                if failure is None:
                    print(f"   {what} passed the gate but cut by k={k}")
                    continue
                stage, amount = failure
                if stage == "floor":
                    print(
                        f"   {what} raw {m.raw_similarity:.2f} is "
                        f"{amount:.2f} below the gate"
                    )
                elif stage == "window":
                    print(
                        f"   {what} raw {m.raw_similarity:.2f} is "
                        f"{amount:.2f} below the best fact (window {RELATIVE_WINDOW})"
                    )
                else:
                    print(
                        f"   {what} routed out, this relation ranks "
                        f"{m.relation_rank} for the question (top {ROUTING_TOP_N} allowed)"
                    )

    rows = retrieve_baseline(user, question, 10)
    print(f"\n   MESSAGES (baseline memory, top {len(rows)} by similarity)")
    for i, (content, _created, sim) in enumerate(rows, 1):
        star = paint("★", "yellow") if needed(content) else " "
        # below the top-k cut the row goes grey; raw and star keep their colour
        below = i > k
        cut = paint("   (below the top-k cut)", "dim") if below else ""
        # baseline has no gate: green = in the top k, yellow = above the floor but cut, red = below it
        raw_style = "green" if i <= k else "yellow" if sim >= MIN_RELEVANCE else "red"
        raw = paint(f"{sim:.2f}", raw_style)
        head = paint(f"   {i:>2}  raw ", "dim") if below else f"   {i:>2}  raw "
        text = paint(content[:62], "dim") if below else content[:62]
        print(f"{head}{raw}  {star}  {text}{cut}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", nargs="+", help="scenario ids")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--user")
    parser.add_argument("--question")
    parser.add_argument("--k", type=int, default=4)
    parser.add_argument(
        "--no-color", action="store_true", help="plain text (also: NO_COLOR=1)"
    )
    args = parser.parse_args()
    if args.no_color:
        set_enabled(False)

    if args.user and args.question:
        show(args.user, args.question, [], args.k)
        return

    chosen = [
        s for s in SCENARIOS if args.all or (args.scenario and s["id"] in args.scenario)
    ]
    if not chosen:
        parser.error("use --scenario <id>, --all, or --user with --question")
    for sc in chosen:
        for q in sc["questions"]:
            show(f"eval_{sc['id']}", q["q"], q.get("needs", []), args.k)


if __name__ == "__main__":
    main()
