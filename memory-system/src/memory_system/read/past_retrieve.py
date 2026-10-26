"""Read side for questions about the past: replaced facts, with the date they were replaced."""

from memory_system.core.config import PAST_FACTS, PAST_MAX_LINES
from memory_system.core.db import get_pool
from memory_system.core.events import log_event
from memory_system.read.past_rules import drop_active_values, is_past_question
from memory_system.read.retrieve import Memory, best_raw, gate_failure, score_facts


def select_past(
    scored: list[Memory], active_values: set[tuple[str, str]], max_lines: int
) -> list[Memory]:
    """Superseded facts that pass the gate (floor, window among themselves, routing; no allergy
    bypass), not equal to a current value, best raw similarity first, at most max_lines."""
    best = best_raw(scored)
    passed = [m for m in scored if gate_failure(m, best, safety=False) is None]
    passed = drop_active_values(passed, active_values)
    passed.sort(key=lambda m: (m.raw_similarity, m.until or m.since), reverse=True)
    return passed[:max_lines]


def retrieve_past(user_id: str, query: str, touch: bool = True) -> list[Memory]:
    """Past facts for this question; empty unless the question is about the past."""
    if not PAST_FACTS or not is_past_question(query):
        return []
    scored = score_facts(user_id, query, status="superseded")
    if not scored:
        return []
    with get_pool().connection() as conn:
        active = {
            (r, v)
            for r, v in conn.execute(
                "SELECT relation, value FROM facts "
                "WHERE user_id = %s AND subject = 'user' AND status = 'active'",
                (user_id,),
            )
        }
        chosen = select_past(scored, active, PAST_MAX_LINES)
        if touch and chosen:
            log_event(
                conn,
                user_id,
                "retrieve",
                None,
                {"query": query, "past": [m.id for m in chosen]},
            )
    return chosen
