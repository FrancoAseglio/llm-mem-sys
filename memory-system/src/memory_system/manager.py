from datetime import datetime

from memory_system.conflicts import apply_fact
from memory_system.db import get_pool
from memory_system.extract import extract_facts, load_relation_types
from memory_system.llm import embed


def ingest_user_message(
    user_id: str, text: str, at: datetime | None = None
) -> list[tuple[str, str, str]]:
    """Store a message, extract facts, and update memory. Returns (outcome, relation, value).

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
        results = []
        for fact in extract_facts(text, relations):
            outcome = apply_fact(
                conn, user_id, fact.relation, fact.value, message_id, at
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
