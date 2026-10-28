from datetime import datetime

from memory_system.core.config import ABOUT_USER
from memory_system.core.db import get_pool
from memory_system.core.events import log_event
from memory_system.core.llm import embed
from memory_system.write.actions import about_user, is_grounded, normalize_actions
from memory_system.write.conflicts import apply_fact
from memory_system.write.extract import extract_facts, load_relation_types


def ingest_user_message(
    user_id: str, text: str, at: datetime | None = None
) -> list[tuple[str, str, str]]:
    """Store a message, extract facts, and update memory. Returns (outcome, relation, value),
    outcome as in conflicts.apply_fact, or
    [("extraction_failed", "", "")] if the model could not read the message (the message is kept).

    `at` is when the user said it (None = now). Used to replay past conversations.
    """
    with get_pool().connection() as conn:
        conn.execute(
            "INSERT INTO users (id) VALUES (%s) ON CONFLICT DO NOTHING", (user_id,)
        )
        message_id = conn.execute(
            "INSERT INTO messages (user_id, role, content, embedding, created_at) "
            "VALUES (%s, 'user', %s, %s, COALESCE(%s::timestamptz, now())) RETURNING id",
            (user_id, text, embed(text), at),
        ).fetchone()[0]

        relations = load_relation_types(conn)
        single = frozenset(n for n, (card, _) in relations.items() if card == "single")
        try:
            extracted = extract_facts(text, relations)
        except Exception as error:  # model down, timeout or malformed JSON
            # keep the message (it is still searchable) and say that no facts were read from it
            log_event(
                conn,
                user_id,
                "reject",
                None,
                {"reason": "extraction failed", "error": repr(error)[:200]},
            )
            return [("extraction_failed", "", "")]
        facts = normalize_actions(extracted, text, single)
        # relations this message really sets (a rejected value does not count)
        asserted = {
            f.relation
            for f in facts
            if f.action == "assert"
            and is_grounded(f.value, text, f.relation)
            and (not ABOUT_USER or about_user(f.value, f.relation, text))
        }
        results = []
        for fact in facts:
            outcome = apply_fact(
                conn,
                user_id,
                fact.relation,
                fact.value,
                message_id,
                at,
                action=fact.action,
                source_text=text,
                message_relations=asserted,
            )
            results.append((outcome, fact.relation, fact.value))
        return results


def list_facts(user_id: str, include_history: bool = True) -> list[tuple]:
    """Return (relation, value, status, importance, confidence, valid_from) rows for a user."""
    where = "" if include_history else "AND status = 'active'"
    with get_pool().connection() as conn:
        return conn.execute(
            f"""SELECT relation, value, status, importance, confidence,
                       to_char(valid_from, 'YYYY-MM-DD HH24:MI') AS valid_from
                FROM facts WHERE user_id = %s {where}
                ORDER BY relation, valid_from""",
            (user_id,),
        ).fetchall()
