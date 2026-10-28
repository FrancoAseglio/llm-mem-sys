"""Read side of the summaries layer: the summary lines that pass the gate for a question."""

from memory_system.core.config import (
    CONSOLIDATE,
    MIN_RELEVANCE,
    RELATIVE_WINDOW,
    SUMMARIES,
    SUMMARY_MAX_LINES,
)
from memory_system.core.db import get_pool
from memory_system.core.events import log_event
from memory_system.core.llm import embed
from memory_system.summaries.rules import SummaryRow, select_summaries


def retrieve_summaries(
    user_id: str,
    query: str,
    lines: list[str],
    k: int = 4,
    touch: bool = True,
    fact_best: float | None = None,
) -> list[str]:
    """Summary lines for this question, to add after the fact lines already chosen (`lines`).

    Same floor and window as facts, no routing. `fact_best`, the raw similarity of the best
    chosen fact, also counts as the top of the window (rules.select_summaries). Facts keep priority: summaries only fill the
    remaining room among k lines, at most SUMMARY_MAX_LINES, and a summary that adds nothing to
    `lines` is skipped. A summary whose source message produced a fact that is no longer active
    (superseded, archived or conflicted) is skipped, so outdated values cannot come back.

    With consolidation on, the candidates are digests and the notes no digest has replaced; a
    digest is checked through the source messages of all its notes. With CONSOLIDATE=0 only notes
    are read, all of them, as before consolidation existed.
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
                              WHERE (m.summary_id = s.id
                                     OR m.summary_id IN (SELECT n.id FROM summaries n
                                                         WHERE n.digest_id = s.id))
                                AND f.status <> 'active') AS fresh
                   FROM summaries s
                   WHERE s.user_id = %s AND s.embedding IS NOT NULL
                     AND CASE WHEN %s THEN s.digest_id IS NULL ELSE s.kind = 'note' END""",
                (q, user_id, CONSOLIDATE),
            ).fetchall()
        ]
        chosen = select_summaries(
            rows, lines, room, MIN_RELEVANCE, RELATIVE_WINDOW, fact_best
        )
        if touch and chosen:
            log_event(
                conn,
                user_id,
                "retrieve",
                None,
                {"query": query, "summaries": [r.id for r in chosen]},
            )
    return [f"Note from {r.since:%Y-%m-%d}: {r.content}" for r in chosen]
