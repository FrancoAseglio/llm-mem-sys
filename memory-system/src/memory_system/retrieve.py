import math
from dataclasses import dataclass
from datetime import datetime, timezone

from memory_system.config import (
    MIN_SCORE,
    PIN_IMPORTANCE,
    RECENCY_HALF_LIFE_DAYS,
    SIM_CEIL,
    SIM_FLOOR,
    WEIGHTS,
)
from memory_system.conflicts import log_event
from memory_system.db import get_pool
from memory_system.llm import embed


@dataclass
class Memory:
    id: int
    relation: str
    value: str
    since: datetime
    score: float
    pinned: bool
    parts: dict[str, float]


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def retrieve(user_id: str, query: str, k: int = 4, touch: bool = True) -> list[Memory]:
    """Smart retrieval: only ACTIVE facts, ranked by a blend of similarity, importance,
    recency, usage and confidence. Very important facts (allergies) are always pinned."""
    q = embed(query)
    now = datetime.now(timezone.utc)

    with get_pool().connection() as conn:
        rows = conn.execute(
            """SELECT id, relation, value, importance, confidence, access_count,
                      GREATEST(updated_at, COALESCE(last_accessed_at, updated_at)) AS last_touch,
                      valid_from,
                      1 - (embedding <=> %s) AS similarity
               FROM facts
               WHERE user_id = %s AND subject = 'user' AND status = 'active'""",
            (q, user_id),
        ).fetchall()

        scored: list[Memory] = []
        for fid, relation, value, importance, confidence, access_count, last_touch, since, sim in rows:
            age_days = max(0.0, (now - last_touch).total_seconds() / 86400)
            parts = {
                "similarity": _clamp((sim - SIM_FLOOR) / (SIM_CEIL - SIM_FLOOR)),
                "importance": importance,
                "recency": 0.5 ** (age_days / RECENCY_HALF_LIFE_DAYS),
                "usage": min(1.0, math.log1p(access_count) / math.log1p(10)),
                "confidence": confidence,
            }
            score = sum(WEIGHTS[name] * value_ for name, value_ in parts.items())
            scored.append(
                Memory(fid, relation, value, since, score, importance >= PIN_IMPORTANCE, parts)
            )

        scored.sort(key=lambda m: m.score, reverse=True)
        pinned = [m for m in scored if m.pinned]
        relevant = [m for m in scored if not m.pinned and m.score >= MIN_SCORE][:k]
        chosen = pinned + relevant

        if touch and chosen:
            # Reinforcement: facts that get used stay "fresh". Pinned facts are excluded
            # so they don't reinforce themselves forever.
            used_ids = [m.id for m in relevant]
            if used_ids:
                conn.execute(
                    "UPDATE facts SET access_count = access_count + 1, last_accessed_at = now() "
                    "WHERE id = ANY(%s)",
                    (used_ids,),
                )
            log_event(conn, user_id, "retrieve", None,
                      {"query": query, "returned": [m.id for m in chosen]})
        return chosen


def retrieve_baseline(user_id: str, query: str, k: int = 4):
    """Traditional vector memory: top-k past user messages by cosine similarity. Nothing else."""
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
