"""Read side of the hybrid mode and the full reference mode (docs/06_read_path.md, section 11).

hybrid: the current facts of the best two kinds (smart's gate; every value of a list kind such as
        languages), one timeline line for a question
        about the past, then the baseline's top-k messages word for word, each marked when a fact
        it produced has since changed or was retracted.
full:   every user message, oldest first.
"""

from memory_system.core.config import (
    HYBRID_FACT_MAX,
    HYBRID_FACT_RELATIONS,
    HYBRID_LIST_RELATIONS,
    HYBRID_MARKERS,
    HYBRID_TIMELINE,
    PAST_FACTS,
)
from memory_system.core.db import get_pool
from memory_system.read.hybrid_rules import fact_marker, marked_message, timeline_line
from memory_system.read.past_rules import is_past_question
from memory_system.read.retrieve import (
    Memory,
    baseline_messages,
    best_raw,
    gate_failure,
    retrieve,
    score_facts,
)

MAX_CHAIN = 50  # guard against a cycle in superseded_by (should never happen)


def _chain_end(conn, fact_id: int) -> tuple[str, str, str] | None:
    """(relation, value, status) of the last fact in a superseded_by chain, or None if the
    chain does not continue past this fact."""
    end = None
    current = fact_id
    for _ in range(MAX_CHAIN):
        row = conn.execute(
            "SELECT superseded_by FROM facts WHERE id = %s", (current,)
        ).fetchone()
        if row is None or row[0] is None:
            break
        current = row[0]
        end = conn.execute(
            "SELECT relation, value, status FROM facts WHERE id = %s", (current,)
        ).fetchone()
    return end


def outdated_markers(user_id: str, message_ids: list[int]) -> dict[int, list[str]]:
    """{message id: markers} for messages that produced a user fact that is no longer active:
    superseded (marked with the current value) or archived by a retraction. Facts still active,
    and conflicted ones (we cannot tell whether they are true), give no marker."""
    if not message_ids:
        return {}
    markers: dict[int, list[str]] = {}
    with get_pool().connection() as conn:
        rows = conn.execute(
            """SELECT id, source_message_id, relation, value, status FROM facts
               WHERE user_id = %s AND subject = 'user'
                 AND source_message_id = ANY(%s)
                 AND status IN ('superseded', 'archived')
               ORDER BY id""",
            (user_id, message_ids),
        ).fetchall()
        for fact_id, message_id, relation, value, status in rows:
            end = _chain_end(conn, fact_id) if status == "superseded" else None
            marker = fact_marker(relation, value, end)
            if marker and marker not in markers.get(message_id, []):
                markers.setdefault(message_id, []).append(marker)
    return markers


def past_relation(scored: list[Memory]) -> str | None:
    """The relation of the best replaced or retracted fact that passes the gate (floor, window,
    routing; no allergy bypass), or None."""
    best = best_raw(scored)
    passed = [m for m in scored if gate_failure(m, best, safety=False) is None]
    if not passed:
        return None
    return max(passed, key=lambda m: m.raw_similarity).relation


def timeline(user_id: str, query: str) -> str | None:
    """One line with every value of the relation the past question is about, oldest first."""
    if not (HYBRID_TIMELINE and PAST_FACTS and is_past_question(query)):
        return None
    scored = score_facts(user_id, query, status="superseded") + score_facts(
        user_id, query, status="archived"
    )
    relation = past_relation(scored)
    if relation is None:
        return None
    with get_pool().connection() as conn:
        values = conn.execute(
            """SELECT value, status FROM facts
               WHERE user_id = %s AND subject = 'user' AND relation = %s
               ORDER BY valid_from, id""",
            (user_id, relation),
        ).fetchall()
    return timeline_line(relation, values)


def top_relations(
    facts: list[Memory],
    relations: int,
    most: int,
    lists: frozenset = HYBRID_LIST_RELATIONS,
) -> list[Memory]:
    """Facts of the first `relations` relations in `facts` (best first): every value of a list
    relation (all three languages, not two), the best value of any other (one family member,
    not every name), at most `most` lines."""
    kept: list[str] = []
    out: list[Memory] = []
    for m in facts:
        if m.relation not in kept:
            if len(kept) == relations:
                continue
            kept.append(m.relation)
            out.append(m)
        elif m.relation in lists:
            out.append(m)
    return out[:most]


def hybrid_lines(
    user_id: str, query: str, k: int = 4, touch: bool = True
) -> tuple[list[Memory], str | None, list[str]]:
    """(facts, timeline line or None, message lines) for the hybrid mode."""
    facts = top_relations(
        retrieve(user_id, query, HYBRID_FACT_MAX, touch),
        HYBRID_FACT_RELATIONS,
        HYBRID_FACT_MAX,
    )
    past = timeline(user_id, query)
    rows = baseline_messages(user_id, query, k)
    markers = outdated_markers(user_id, [r[0] for r in rows]) if HYBRID_MARKERS else {}
    messages = [
        marked_message(f'[{created:%Y-%m-%d}] "{content}"', markers.get(mid, []))
        for mid, content, created, _ in rows
    ]
    return facts, past, messages


def all_messages(user_id: str) -> list[str]:
    """Every user message, oldest first, as baseline-style lines (the full reference mode)."""
    with get_pool().connection() as conn:
        rows = conn.execute(
            """SELECT content, created_at FROM messages
               WHERE user_id = %s AND role = 'user'
               ORDER BY created_at, id""",
            (user_id,),
        ).fetchall()
    return [f'[{created:%Y-%m-%d}] "{content}"' for content, created in rows]
