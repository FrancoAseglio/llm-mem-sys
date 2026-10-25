"""Show how EVERY fact scores for a question, so you can see why each was kept or dropped.

    poetry run python scripts/inspect_scores.py --scenario b_stale_flood
    poetry run python scripts/inspect_scores.py --all
    poetry run python scripts/inspect_scores.py --user demo --question "Where do I live?"

Needs data from a previous evaluate.py run (users are named eval_<scenario>).

Columns
  pick   PIN = pinned, yes = passed the relevance gate (and is in the top k), - = dropped
  raw    raw cosine similarity between the question and the fact  (the GATE uses this)
  score  blended ranking score (only decides order among facts that pass the gate)
  sim..con  the five ranking components after rescaling, each 0 to 1
  age    days since the fact was last created, repeated or used
  ★      the fact this question actually needs
"""

import argparse

from scenarios import SCENARIOS

from memory_system.config import (
    MIN_RELEVANCE,
    PIN_IMPORTANCE,
    RELATIVE_WINDOW,
    ROUTING_TOP_N,
    SAFETY_BYPASS,
    SAFETY_RELATIONS,
)
from memory_system.retrieve import (
    best_raw,
    gate_failure,
    retrieve_baseline,
    score_facts,
    select_memories,
)


def show(user: str, question: str, needs: list[str], k: int) -> None:
    scored = score_facts(user, question)
    pinned, relevant = select_memories(scored, k)
    picked = {m.id: ("PIN" if m.pinned else "yes") for m in pinned + relevant}

    def needed(text: str) -> bool:
        return any(n in text.lower() for n in needs)

    print(f"\n{'=' * 96}\nQ: {question}   [user={user}]")
    print(
        f"   needs: {needs or '-'}   k={k}   gate: raw >= {MIN_RELEVANCE} and within {RELATIVE_WINDOW} of the best, relation rank <= {ROUTING_TOP_N or 'off'}   "
        f"pinning: {'off' if PIN_IMPORTANCE > 1 else f'importance >= {PIN_IMPORTANCE}'}   "
        f"safety bypass: {sorted(SAFETY_RELATIONS) if SAFETY_BYPASS and ROUTING_TOP_N else 'off'}"
    )
    if not scored:
        print("   (no active facts, run evaluate.py first)")
    else:
        print("\n   FACTS (smart memory)")
        print(
            f"   {'pick':<5}{'raw':>6}{'score':>7}{'sim':>6}{'imp':>6}{'rec':>6}"
            f"{'use':>6}{'con':>6}{'age':>6}{'rel#':>5}   fact"
        )
        for m in sorted(scored, key=lambda m: -m.raw_similarity):
            p = m.parts
            star = "★ " if needed(m.value) else "  "
            print(
                f"   {picked.get(m.id, '-'):<5}{m.raw_similarity:>6.2f}{m.score:>7.2f}"
                f"{p['similarity']:>6.2f}{p['importance']:>6.2f}{p['recency']:>6.2f}"
                f"{p['usage']:>6.2f}{p['confidence']:>6.2f}{m.age_days:>6.0f}{m.relation_rank:>5}   "
                f"{star}{m.relation} = {m.value}"
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
                f"best other {max(others):.2f} | margin {margin:+.2f} -> {verdict}"
            )
        best = best_raw(scored)
        for m in scored:
            if needed(m.value) and m.id not in picked:
                what = f"MISSED: {m.relation}={m.value}:"
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
    for i, (content, created, sim) in enumerate(rows, 1):
        star = "★" if needed(content) else " "
        cut = "" if i <= k else "   (below the top-k cut)"
        print(f"   {i:>2}  raw {sim:.2f}  {star}  {content[:62]}{cut}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", nargs="+", help="scenario ids")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--user")
    parser.add_argument("--question")
    parser.add_argument("--k", type=int, default=4)
    args = parser.parse_args()

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
