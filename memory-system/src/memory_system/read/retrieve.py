import math
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np

from memory_system.core.config import (
    MIN_RELEVANCE,
    PIN_IMPORTANCE,
    RECENCY_HALF_LIFE_DAYS,
    RELATIVE_WINDOW,
    ROUTING_TOP_N,
    SAFETY_BYPASS,
    SAFETY_RELATIONS,
    SIM_CEIL,
    SIM_FLOOR,
    WEIGHTS,
)
from memory_system.core.db import get_pool
from memory_system.core.events import log_event
from memory_system.core.llm import embed


@dataclass
class Memory:
    id: int
    relation: str
    value: str
    since: datetime
    score: float
    pinned: bool
    parts: dict[str, float]
    raw_similarity: float = (
        0.0  # cosine similarity before rescaling (what the gate uses)
    )
    age_days: float = 0.0  # days since the fact was last created, repeated or used
    relation_rank: int = 0  # 1 = the relation type that best matches the question
    relation_sim: float = 0.0  # similarity of the question to that relation type
    until: datetime | None = None  # when a superseded fact was replaced (valid_to)


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


_relation_vecs: dict[str, np.ndarray] | None = None


def _relation_vectors() -> dict[str, np.ndarray]:
    """Unit vector for each relation type's routing text. Computed once per process
    (restart the script after editing relation_types)."""
    global _relation_vecs
    if _relation_vecs is None:
        with get_pool().connection() as conn:
            rows = conn.execute(
                "SELECT name, description, routing_hint FROM relation_types"
            ).fetchall()
        vecs = {}
        for name, description, hint in rows:
            text = f"{name.replace('_', ' ')}: {description or ''}" + (
                f" {hint}" if hint else ""
            )
            v = embed(text)
            vecs[name] = v / np.linalg.norm(v)
        _relation_vecs = vecs
    return _relation_vecs


def relation_ranks(q: np.ndarray) -> dict[str, tuple[int, float]]:
    """Rank every relation type by how well the question matches it: {name: (rank, similarity)}."""
    qn = q / np.linalg.norm(q)
    sims = sorted(
        ((float(np.dot(qn, v)), name) for name, v in _relation_vectors().items()),
        reverse=True,
    )
    return {name: (rank, sim) for rank, (sim, name) in enumerate(sims, 1)}


def score_facts(user_id: str, query: str, status: str = "active") -> list[Memory]:
    """Score EVERY fact of this status (default active) for the query, best first.
    Changes nothing in the database."""
    q = embed(query)
    ranks = relation_ranks(q)
    now = datetime.now(timezone.utc)

    with get_pool().connection() as conn:
        rows = conn.execute(
            """SELECT id, relation, value, importance, confidence, access_count,
                      GREATEST(updated_at, COALESCE(last_accessed_at, updated_at)) AS last_touch,
                      valid_from, valid_to,
                      1 - (embedding <=> %s) AS similarity
               FROM facts
               WHERE user_id = %s AND subject = 'user' AND status = %s""",
            (q, user_id, status),
        ).fetchall()

    scored: list[Memory] = []
    for (
        fid,
        relation,
        value,
        importance,
        confidence,
        access_count,
        last_touch,
        since,
        until,
        sim,
    ) in rows:
        age_days = max(0.0, (now - last_touch).total_seconds() / 86400)
        parts = {
            "similarity": _clamp((sim - SIM_FLOOR) / (SIM_CEIL - SIM_FLOOR)),
            "importance": importance,
            "recency": 0.5 ** (age_days / RECENCY_HALF_LIFE_DAYS),
            "usage": min(1.0, math.log1p(access_count) / math.log1p(10)),
            "confidence": confidence,
        }
        score = sum(WEIGHTS[name] * value_ for name, value_ in parts.items())
        rank, rsim = ranks.get(relation, (len(ranks) + 1, 0.0))
        scored.append(
            Memory(
                fid,
                relation,
                value,
                since,
                score,
                importance >= PIN_IMPORTANCE,
                parts,
                raw_similarity=sim,
                age_days=age_days,
                relation_rank=rank,
                relation_sim=rsim,
                until=until,
            )
        )
    scored.sort(key=lambda m: m.score, reverse=True)
    return scored


def best_raw(scored: list[Memory]) -> float:
    """Best raw similarity among the unpinned facts that pass the floor (0.0 if none do).
    The relative window is measured from this value."""
    return max(
        (
            m.raw_similarity
            for m in scored
            if not m.pinned and m.raw_similarity >= MIN_RELEVANCE
        ),
        default=0.0,
    )


def gate_failure(
    m: Memory, best: float, safety: bool = True
) -> tuple[str, float] | None:
    """Why the relevance gate drops this fact, or None if it passes.

    Returns ("floor", gap below MIN_RELEVANCE), ("window", gap below the best fact) or
    ("routing", the fact's relation rank). `best` comes from best_raw(scored).
    The checks run in that order. SAFETY_RELATIONS skip the floor and window when
    routing ranks them in the top ROUTING_TOP_N (SAFETY_BYPASS, needs routing on).
    """
    routed = ROUTING_TOP_N <= 0 or m.relation_rank <= ROUTING_TOP_N
    if (
        safety
        and ROUTING_TOP_N > 0
        and SAFETY_BYPASS
        and m.relation in SAFETY_RELATIONS
        and routed
    ):
        return None
    if m.raw_similarity < MIN_RELEVANCE:
        return "floor", MIN_RELEVANCE - m.raw_similarity
    if m.raw_similarity < best - RELATIVE_WINDOW:
        return "window", best - m.raw_similarity
    if not routed:
        return "routing", float(m.relation_rank)
    return None


def select_memories(scored: list[Memory], k: int) -> tuple[list[Memory], list[Memory]]:
    """Gate, then rank. Returns (pinned, relevant).

    pinned   : facts important enough to always include (off by default)
    relevant : facts that pass the gate (see gate_failure), best score first, at most k
                 floor   : raw similarity >= MIN_RELEVANCE
                 window  : raw similarity within RELATIVE_WINDOW of the best fact that passed the floor
                 routing : the fact's relation type is among the ROUTING_TOP_N best matches
                           for the question (0 = off)
               SAFETY_RELATIONS skip the floor and window when routing passes them.
    """
    pinned = [m for m in scored if m.pinned]
    best = best_raw(scored)
    relevant = [
        m for m in scored if not m.pinned and gate_failure(m, best) is None
    ]
    return pinned, relevant[:k]


def retrieve(user_id: str, query: str, k: int = 4, touch: bool = True) -> list[Memory]:
    """Smart retrieval: only ACTIVE facts that are relevant to the question, best first."""
    scored = score_facts(user_id, query)
    pinned, relevant = select_memories(scored, k)
    chosen = pinned + relevant

    if touch and chosen:
        # Reinforcement: facts that get used stay "fresh". Pinned facts are excluded
        # so they don't reinforce themselves forever.
        with get_pool().connection() as conn:
            used_ids = [m.id for m in relevant]
            if used_ids:
                conn.execute(
                    "UPDATE facts SET access_count = access_count + 1, last_accessed_at = now() "
                    "WHERE id = ANY(%s)",
                    (used_ids,),
                )
            log_event(
                conn,
                user_id,
                "retrieve",
                None,
                {"query": query, "returned": [m.id for m in chosen]},
            )
    return chosen


def retrieve_baseline(user_id: str, query: str, k: int = 4) -> list[tuple]:
    """Traditional vector memory: top-k past user messages by cosine similarity. Nothing else.

    Returns (content, created_at, similarity) rows.
    """
    q = embed(query)
    with get_pool().connection() as conn:
        return conn.execute(
            """SELECT content, created_at, 1 - (embedding <=> %s) AS similarity
               FROM messages
               WHERE user_id = %s AND role = 'user'
               ORDER BY embedding <=> %s
               LIMIT %s""",
            (q, user_id, q, k),
        ).fetchall()
