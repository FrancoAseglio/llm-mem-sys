"""Database side of the write path: compare a new fact with the stored ones and write the result."""

from datetime import datetime

from memory_system.core.config import (
    ABOUT_USER,
    CHANGE_RULE,
    DEFAULT_IMPORTANCE,
    DUPLICATE_SIMILARITY,
)
from memory_system.core.events import log_event
from memory_system.core.llm import embed
from memory_system.write.actions import (
    CHANGE_RELATIONS,
    NAME_RELATIONS,
    about_user,
    is_grounded,
    same_name,
    signals_change,
)

# A new value for one of these relations contradicts an active value of the relations listed
# (hobby counts as a positive statement, like likes).
OPPOSITES = {
    "likes": ("dislikes",),
    "hobby": ("dislikes",),
    "dislikes": ("likes", "hobby"),
}

# When the key relation changes, the value relation may no longer hold (a new employer can
# mean a new title), so it is marked 'conflicted' unless the same message restates it.
DEPENDENTS = {"works_at": "job_title"}


def _matching(
    rows: list[tuple], value: str, relation: str | None = None
) -> list[tuple]:
    """Rows (id, value, similarity, ...) holding the same value: equal ignoring case, close by
    trigram, or, for names, one containing the other ("Fjordline" and "Fjordline Aquaculture")."""
    return [
        r
        for r in rows
        if r[1].lower() == value.lower()
        or r[2] >= DUPLICATE_SIMILARITY
        or (relation in NAME_RELATIONS and same_name(r[1], value))
    ]


def known_people(conn, user_id: str) -> frozenset:
    """Lower-case names of the user's stored partner and family (any status), for about_user."""
    rows = conn.execute(
        "SELECT value FROM facts WHERE user_id = %s AND relation IN ('partner', 'family_member')",
        (user_id,),
    ).fetchall()
    return frozenset(w for (v,) in rows for w in v.lower().split() if len(w) >= 3)


def _end(
    conn,
    ids: list[int],
    status: str,
    at: datetime | None,
    superseded_by: int | None = None,
) -> None:
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
        log_event(
            conn,
            user_id,
            "conflict",
            fact_id,
            {"relation": dependent, "value": value, "because": relation},
        )


def _retract(
    conn,
    user_id: str,
    relation: str,
    value: str,
    active: list[tuple],
    message_relations: set[str],
    at: datetime | None,
) -> str:
    """Archive the matching active fact, never delete it."""
    matched = _matching(active, value, relation)
    if not matched:
        log_event(
            conn,
            user_id,
            "retract",
            None,
            {"relation": relation, "value": value, "matched": False},
        )
        return "retract_miss"
    _end(conn, [r[0] for r in matched], "archived", at)
    for fact_id, old_value, *_ in matched:
        log_event(
            conn,
            user_id,
            "retract",
            fact_id,
            {"relation": relation, "value": old_value},
        )
    _conflict_dependent(conn, user_id, relation, message_relations, at)
    return "retract"


def _strengthen_duplicate(
    conn,
    user_id: str,
    relation: str,
    value: str,
    active: list[tuple],
    at: datetime | None,
) -> bool:
    """Already known: just raise confidence. True if a duplicate was found."""
    for fact_id, *_ in _matching(active, value, relation):
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
        return True
    return False


def _insert_fact(
    conn,
    user_id: str,
    relation: str,
    value: str,
    source_message_id: int | None,
    at: datetime | None,
) -> int:
    """Insert a new active fact and return its id."""
    return conn.execute(
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


def _supersede_opposites(
    conn,
    user_id: str,
    relation: str,
    value: str,
    new_id: int,
    at: datetime | None,
) -> bool:
    """Positive vs negative statement about the same thing (likes/hobby vs dislikes):
    the newer statement wins. True if something was superseded."""
    opposite = conn.execute(
        """SELECT id, value, similarity(lower(value), lower(%s)), relation
           FROM facts
           WHERE user_id = %s AND subject = 'user' AND relation = ANY(%s)
             AND status = 'active'""",
        (value, user_id, list(OPPOSITES[relation])),
    ).fetchall()
    contradicted = _matching(opposite, value)
    if not contradicted:
        return False
    _end(conn, [r[0] for r in contradicted], "superseded", at, superseded_by=new_id)
    log_event(
        conn,
        user_id,
        "contradiction",
        new_id,
        {
            "relation": relation,
            "value": value,
            "old": [f"{r[3]}={r[1]}" for r in contradicted],
        },
    )
    return True


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
    if source_text is not None and not is_grounded(value, source_text, relation):
        log_event(
            conn,
            user_id,
            "reject",
            None,
            {
                "relation": relation,
                "value": value,
                "action": action,
                "reason": "no content word in common with the message",
            },
        )
        return "rejected"

    # 0b) About someone else: "My sister lives in Montreal" is not the user's city.
    if (
        ABOUT_USER
        and action == "assert"
        and source_text is not None
        and not about_user(value, relation, source_text, known_people(conn, user_id))
    ):
        log_event(
            conn,
            user_id,
            "reject",
            None,
            {
                "relation": relation,
                "value": value,
                "action": action,
                "reason": "about someone else",
            },
        )
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

    # 1) Retraction
    if action == "retract":
        return _retract(conn, user_id, relation, value, active, message_relations, at)

    # 2) Duplicate
    if _strengthen_duplicate(conn, user_id, relation, value, active, at):
        return "duplicate"

    # 2b) A new value for a single-valued fact must be said to have changed: "I now commute to
    # Utrecht" does not move the user (write/actions.signals_change).
    if (
        CHANGE_RULE
        and source_text is not None
        and cardinality == "single"
        and relation in CHANGE_RELATIONS
        and active
        and not signals_change(value, relation, source_text)
    ):
        log_event(
            conn,
            user_id,
            "reject",
            None,
            {
                "relation": relation,
                "value": value,
                "action": action,
                "reason": "no change signalled",
                "current": [r[1] for r in active],
            },
        )
        return "rejected"

    # 3) New fact
    new_id = _insert_fact(conn, user_id, relation, value, source_message_id, at)

    # 4) Opposite statement: the newer one wins
    if relation in OPPOSITES and _supersede_opposites(
        conn, user_id, relation, value, new_id, at
    ):
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
