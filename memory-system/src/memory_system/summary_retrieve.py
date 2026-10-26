"""Read side of the summaries layer: the summary lines that pass the gate for a question."""

from memory_system.config import (
    MIN_RELEVANCE,
    RELATIVE_WINDOW,
    SUMMARIES,
    SUMMARY_MAX_LINES,
)
from memory_system.db import get_pool
from memory_system.events import log_event
from memory_system.llm import embed
from memory_system.summary_rules import SummaryRow, select_summaries


def retrieve_summaries(
    user_id: str, query: str, lines: list[str], k: int = 4, touch: bool = True
) -> list[str]:
    """Summary lines for this question, to add after the fact lines already chosen (`lines`).

    Same floor and window as facts, no routing. Facts keep priority: summaries only fill the
    remaining room among k lines, at most SUMMARY_MAX_LINES, and a summary that adds nothing to
    `lines` is skipped. A summary whose source message produced a fact that is no longer active
    (superseded, archived or conflicted) is skipped, so outdated values cannot come back.
    """
    room = min(SUMMARY_MAX_LINES, k - len(lines))
    if not SUMMARIES or room <= 0:
        return []
    q = embed(query)
    with get_pool().connection() as conn:
        rows = [
            SummaryRow(*row)
            for row in conn.execute(
                """SELECT s.id, s.content, COALESCE(s.period_end, s.created_at),
                          1 - (s.embedding <=> %s) AS similarity,
                          NOT EXISTS (
                              SELECT 1 FROM messages m JOIN facts f ON f.source_message_id = m.id
                              WHERE m.summary_id = s.id AND f.status <> 'active') AS fresh
                   FROM summaries s
                   WHERE s.user_id = %s AND s.embedding IS NOT NULL""",
                (q, user_id),
            ).fetchall()
        ]
        chosen = select_summaries(rows, lines, room, MIN_RELEVANCE, RELATIVE_WINDOW)
        if touch and chosen:
            log_event(
                conn,
                user_id,
                "retrieve",
                None,
                {"query": query, "summaries": [r.id for r in chosen]},
            )
    return [f"Note from {r.since:%Y-%m-%d}: {r.content}" for r in chosen]
