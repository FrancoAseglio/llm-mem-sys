from psycopg.types.json import Jsonb


def log_event(
    conn, user_id: str, event_type: str, fact_id: int | None, details: dict
) -> None:
    """Append one row to the memory_events audit log."""
    conn.execute(
        "INSERT INTO memory_events (user_id, event_type, fact_id, details) VALUES (%s, %s, %s, %s)",
        (user_id, event_type, fact_id, Jsonb(details)),
    )
