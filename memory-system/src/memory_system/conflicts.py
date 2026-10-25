from datetime import datetime

from psycopg.types.json import Jsonb

from memory_system.config import DEFAULT_IMPORTANCE, DUPLICATE_SIMILARITY
from memory_system.llm import embed


def log_event(
    conn, user_id: str, event_type: str, fact_id: int | None, details: dict
) -> None:
    """Append one row to the memory_events audit log."""
    conn.execute(
        "INSERT INTO memory_events (user_id, event_type, fact_id, details) VALUES (%s, %s, %s, %s)",
        (user_id, event_type, fact_id, Jsonb(details)),
    )


def apply_fact(
    conn,
    user_id: str,
    relation: str,
    value: str,
    source_message_id: int | None,
    at: datetime | None = None,
) -> str:
    """Compare a new fact with stored ones. Returns 'add', 'duplicate' or 'update'.

    `at` is the moment the user said it. Normally None (= now); the evaluation
    uses it to replay conversations that happened months ago.
    """
    cardinality = conn.execute(
        "SELECT cardinality FROM relation_types WHERE name = %s", (relation,)
    ).fetchone()[0]

    existing = conn.execute(
        """SELECT id, value, similarity(lower(value), lower(%s))
           FROM facts
           WHERE user_id = %s AND subject = 'user' AND relation = %s AND status = 'active'""",
        (value, user_id, relation),
    ).fetchall()

    # 1) Duplicate: already known, so just strengthen confidence.
    for fact_id, old_value, sim in existing:
        if old_value.lower() == value.lower() or sim >= DUPLICATE_SIMILARITY:
            conn.execute(
                """UPDATE facts SET confidence = LEAST(1, confidence + 0.05),
                                    updated_at = COALESCE(%s::timestamptz, now())
                   WHERE id = %s""",
                (at, fact_id),
            )
            log_event(
                conn,
                user_id,
                "duplicate",
                fact_id,
                {"relation": relation, "value": value},
            )
            return "duplicate"

    # 2) New fact: insert it.
    new_id = conn.execute(
        """INSERT INTO facts (user_id, relation, value, importance, source_message_id, embedding,
                              valid_from, created_at, updated_at)
           VALUES (%s, %s, %s, %s, %s, %s,
                   COALESCE(%s::timestamptz, now()),
                   COALESCE(%s::timestamptz, now()),
                   COALESCE(%s::timestamptz, now()))
           RETURNING id""",
        (
            user_id,
            relation,
            value,
            DEFAULT_IMPORTANCE.get(relation, 0.5),
            source_message_id,
            embed(f"{relation.replace('_', ' ')}: {value}"),
            at,
            at,
            at,
        ),
    ).fetchone()[0]

    # 3) Single-valued relation with an older value: supersede it (kept as history).
    if cardinality == "single" and existing:
        old_ids = [row[0] for row in existing]
        conn.execute(
            """UPDATE facts SET status = 'superseded',
                                valid_to = COALESCE(%s::timestamptz, now()),
                                superseded_by = %s,
                                updated_at = COALESCE(%s::timestamptz, now())
               WHERE id = ANY(%s)""",
            (at, new_id, at, old_ids),
        )
        log_event(
            conn,
            user_id,
            "update",
            new_id,
            {"relation": relation, "old": [row[1] for row in existing], "new": value},
        )
        return "update"

    log_event(conn, user_id, "add", new_id, {"relation": relation, "value": value})
    return "add"
