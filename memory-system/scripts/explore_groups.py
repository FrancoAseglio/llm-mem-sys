"""EXPLORATION (consolidation version 2, session 1): how would code group a user's old notes?

Read-only: it reads notes and their stored embeddings from the database, calls no model and
changes nothing. Set J is spent, so it is used here as a practice set; nothing seen here is a
result.

Two notes are linked when they share a name (a capitalised word that does not start the
sentence, as in the retention rule) or when their meanings are close (cosine similarity of the
stored embeddings >= --min-sim). A group is a set of notes connected by links.

    poetry run python scripts/explore_groups.py                     # the J users, min-sim 0.75
    poetry run python scripts/explore_groups.py --min-sim 0.70
    poetry run python scripts/explore_groups.py --user eval_b_stale_flood

For each user it prints: the old notes (numbered, with the digest version 1 put them in), the
links with their reason, and the groups code would form.
"""

import argparse

from memory_system.core.db import get_pool
from memory_system.core.style import paint, set_enabled
from memory_system.summaries.rules import _names

J_USERS = [
    "eval_j_renovation",
    "eval_j_travels",
    "eval_j_band",
    "eval_j_control_mix",
    "eval_j_recent",
]


def old_notes(conn, user: str, age_days: int) -> list[tuple]:
    """(id, content, digest_id) of every note older than age_days, oldest first.

    Notes already merged by version 1 are included (digest_id shows where), so the grouping
    is judged on the same notes version 1 saw."""
    return conn.execute(
        """SELECT id, content, digest_id FROM summaries
           WHERE user_id = %s AND kind = 'note'
             AND COALESCE(period_end, created_at) < now() - make_interval(days => %s)
           ORDER BY COALESCE(period_end, created_at), id""",
        (user, age_days),
    ).fetchall()


def similarities(conn, ids: list[int]) -> dict[tuple[int, int], float]:
    """Cosine similarity of every pair of the given notes, from the stored embeddings."""
    rows = conn.execute(
        """SELECT a.id, b.id, 1 - (a.embedding <=> b.embedding)
           FROM summaries a JOIN summaries b ON a.id < b.id
           WHERE a.id = ANY(%s) AND b.id = ANY(%s)""",
        (ids, ids),
    ).fetchall()
    return {(a, b): s for a, b, s in rows}


def groups_of(n: int, links: list[tuple[int, int]]) -> list[list[int]]:
    """Connected groups of 2 or more among positions 0..n-1 (union-find)."""
    parent = list(range(n))

    def root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a, b in links:
        parent[root(a)] = root(b)
    by_root: dict[int, list[int]] = {}
    for i in range(n):
        by_root.setdefault(root(i), []).append(i)
    return [g for g in by_root.values() if len(g) >= 2]


def explore(conn, user: str, min_sim: float, age_days: int) -> tuple[int, int, int]:
    """Print one user's notes, links and groups. Returns (notes, grouped notes, groups)."""
    notes = old_notes(conn, user, age_days)
    print(paint(f"\n=== {user}: {len(notes)} notes older than {age_days} days", "bold"))
    if len(notes) < 2:
        print("  (nothing to group)")
        return len(notes), 0, 0
    for i, (_, content, digest_id) in enumerate(notes, 1):
        v1 = paint(f"  [v1 digest #{digest_id}]", "dim") if digest_id else ""
        print(f"  {i:>2}. {content}{v1}")

    sims = similarities(conn, [n[0] for n in notes])
    names = [_names(n[1]) for n in notes]
    links, shown = [], []
    for i in range(len(notes)):
        for j in range(i + 1, len(notes)):
            sim = sims[(min(notes[i][0], notes[j][0]), max(notes[i][0], notes[j][0]))]
            shared = sorted(names[i] & names[j])
            reasons = []
            if shared:
                reasons.append("names " + ", ".join(shared))
            if sim >= min_sim:
                reasons.append(f"similar {sim:.2f}")
            if reasons:
                links.append((i, j))
                shown.append((i, j, sim, "; ".join(reasons)))
            elif sim >= min_sim - 0.10:  # near misses, to see where the line falls
                shown.append((i, j, sim, paint("no link", "dim")))
    print(paint("  links (and near misses within 0.10 of --min-sim):", "dim"))
    for i, j, sim, why in sorted(shown, key=lambda s: -s[2]):
        print(f"    {i + 1:>2} - {j + 1:<2}  sim {sim:.2f}  {why}")

    groups = groups_of(len(notes), links)
    print(paint("  groups code would form:", "cyan"))
    for g in groups:
        print(f"    [{', '.join(str(i + 1) for i in g)}]")
    alone = [i + 1 for i in range(len(notes)) if not any(i in g for g in groups)]
    print(f"    alone: {alone or 'none'}")
    grouped = sum(len(g) for g in groups)
    return len(notes), grouped, len(groups)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", nargs="+", default=J_USERS)
    parser.add_argument("--min-sim", type=float, default=0.75)
    parser.add_argument("--age-days", type=int, default=30)
    parser.add_argument("--no-color", action="store_true")
    args = parser.parse_args()
    if args.no_color:
        set_enabled(False)

    total = [0, 0, 0]
    with get_pool().connection() as conn:
        for user in args.user:
            for k, v in enumerate(explore(conn, user, args.min_sim, args.age_days)):
                total[k] += v
    print(
        paint(f"\nmin-sim {args.min_sim}: ", "bold")
        + f"{total[1]} of {total[0]} old notes in {total[2]} groups "
        "(version 1 merged 19 of 36 on set J)"
    )


if __name__ == "__main__":
    main()
