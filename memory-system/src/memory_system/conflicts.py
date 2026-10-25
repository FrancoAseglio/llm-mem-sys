import re
from datetime import datetime

from psycopg.types.json import Jsonb

from memory_system.config import DEFAULT_IMPORTANCE, DUPLICATE_SIMILARITY
from memory_system.llm import embed

# A new value for one of these relations contradicts an active value of the other.
OPPOSITES = {"likes": "dislikes", "dislikes": "likes"}

# When the key relation changes, the value relation may no longer hold (a new employer can
# mean a new title), so it is marked 'conflicted' unless the same message restates it.
DEPENDENTS = {"works_at": "job_title"}

# Words of 4+ letters that carry no content, so they cannot ground a value.
STOPWORDS = frozenset(
    "about actually after again also been before being could does doing from have having here "
    "into just like love more most much only other over really some still such than that their "
    "them then there these they this very want were what when where which while will with "
    "would your yours".split()
)


def log_event(
    conn, user_id: str, event_type: str, fact_id: int | None, details: dict
) -> None:
    """Append one row to the memory_events audit log."""
    conn.execute(
        "INSERT INTO memory_events (user_id, event_type, fact_id, details) VALUES (%s, %s, %s, %s)",
        (user_id, event_type, fact_id, Jsonb(details)),
    )


def _content_words(text: str) -> set[str]:
    return {w for w in re.findall(r"\w+", text.lower()) if len(w) >= 4 and w not in STOPWORDS}


def is_grounded(value: str, text: str) -> bool:
    """True if the value shares at least one content word with the message it came from.

    A content word has 4+ letters and is not a stopword. Two words match when one is a
    prefix of the other or they share the first 5 letters, so walnut/walnuts, sail/sailing
    and anchovy/anchovies match. A value with no content word at all ("new job", "egg")
    is rejected: there is nothing in it to check.

    It only catches values invented out of nothing. Junk made of message words
    ("new position") still passes, and paraphrases ("dev" -> "developer") are rejected.
    """
    message = _content_words(text)
    return any(
        v.startswith(m) or m.startswith(v) or v[:5] == m[:5]
        for v in _content_words(value)
        for m in message
    )


def _matching(rows: list[tuple], value: str) -> list[tuple]:
    """Rows (id, value, similarity, ...) holding the same value: equal ignoring case, or close by trigram."""
    return [r for r in rows if r[1].lower() == value.lower() or r[2] >= DUPLICATE_SIMILARITY]


def _end(conn, ids: list[int], status: str, at: datetime | None, superseded_by: int | None = None) -> None:
    """Close facts with a final status. They stay in the table as history."""
    conn.execute(
        """UPDATE facts SET status = %s,
                            valid_to = COALESCE(%s::timestamptz, now()),
                            superseded_by = %s,
                            updated_at = COALESCE(%s::timestamptz, now())
           WHERE id = ANY(%s)""",
        (status, at, superseded_by, at, ids),
    )


def _conflict_dependent(
    conn, user_id: str, relation: str, message_relations: set[str], at: datetime | None
) -> None:
    """After `relation` changed, mark its dependent relation 'conflicted' unless the same
    message also gave it. Not superseded: we cannot tell whether it is still true."""
    dependent = DEPENDENTS.get(relation)
    if dependent is None or dependent in message_relations:
        return
    marked = conn.execute(
        """UPDATE facts SET status = 'conflicted', updated_at = COALESCE(%s::timestamptz, now())
           WHERE user_id = %s AND subject = 'user' AND relation = %s AND status = 'active'
           RETURNING id, value""",
        (at, user_id, dependent),
    ).fetchall()
    for fact_id, value in marked:
        log_event(conn, user_id, "conflict", fact_id,
                  {"relation": dependent, "value": value, "because": relation})


def apply_fact(
    conn,
    user_id: str,
    relation: str,
    value: str,
    source_message_id: int | None,
    at: datetime | None = None,
    *,
    action: str = "assert",
    source_text: str | None = None,
    message_relations: set[str] | None = None,
) -> str:
    """Compare a new fact with stored ones and write the result.

    Returns 'add', 'duplicate', 'update', 'contradiction', 'retract', 'retract_miss' or 'rejected'.

    `at` is the moment the user said it. Normally None (= now); the evaluation
    uses it to replay conversations that happened months ago.
    `action` is 'assert' or 'retract' (the user said it is not true).
    `source_text` is the message the fact came from; if given, the value must be grounded in it.
    `message_relations` are the relations the same message asserts (see DEPENDENTS).
    """
    message_relations = message_relations or set()

    # 0) Grounding: a value with nothing in common with the message was made up.
    if source_text is not None and not is_grounded(value, source_text):
        log_event(conn, user_id, "reject", None,
                  {"relation": relation, "value": value, "action": action,
                   "reason": "no content word in common with the message"})
        return "rejected"

    cardinality = conn.execute(
        "SELECT cardinality FROM relation_types WHERE name = %s", (relation,)
    ).fetchone()[0]

    # active rows, plus conflicted ones so that a new value can supersede them
    existing = conn.execute(
        """SELECT id, value, similarity(lower(value), lower(%s)), status
           FROM facts
           WHERE user_id = %s AND subject = 'user' AND relation = %s
             AND status IN ('active', 'conflicted')""",
        (value, user_id, relation),
    ).fetchall()
    active = [r for r in existing if r[3] == "active"]

    # 1) Retraction: archive the matching active fact, never delete it.
    if action == "retract":
        matched = _matching(active, value)
        if not matched:
            log_event(conn, user_id, "retract", None,
                      {"relation": relation, "value": value, "matched": False})
            return "retract_miss"
        _end(conn, [r[0] for r in matched], "archived", at)
        for fact_id, old_value, *_ in matched:
            log_event(conn, user_id, "retract", fact_id,
                      {"relation": relation, "value": old_value})
        _conflict_dependent(conn, user_id, relation, message_relations, at)
        return "retract"

    # 2) Duplicate: already known, so just strengthen confidence.
    for fact_id, *_ in _matching(active, value):
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

    # 3) New fact: insert it.
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

    # 4) Likes vs dislikes of the same thing: the newer statement wins.
    if relation in OPPOSITES:
        opposite = conn.execute(
            """SELECT id, value, similarity(lower(value), lower(%s))
               FROM facts
               WHERE user_id = %s AND subject = 'user' AND relation = %s AND status = 'active'""",
            (value, user_id, OPPOSITES[relation]),
        ).fetchall()
        contradicted = _matching(opposite, value)
        if contradicted:
            _end(conn, [r[0] for r in contradicted], "superseded", at, superseded_by=new_id)
            log_event(
                conn,
                user_id,
                "contradiction",
                new_id,
                {"relation": relation, "value": value,
                 "old_relation": OPPOSITES[relation], "old": [r[1] for r in contradicted]},
            )
            return "contradiction"

    # 5) Single-valued relation with an older value: supersede it (kept as history).
    if cardinality == "single" and existing:
        _end(conn, [row[0] for row in existing], "superseded", at, superseded_by=new_id)
        log_event(
            conn,
            user_id,
            "update",
            new_id,
            {"relation": relation, "old": [row[1] for row in existing], "new": value},
        )
        _conflict_dependent(conn, user_id, relation, message_relations, at)
        return "update"

    log_event(conn, user_id, "add", new_id, {"relation": relation, "value": value})
    return "add"
