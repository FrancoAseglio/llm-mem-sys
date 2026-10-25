import re
from datetime import datetime

from psycopg.types.json import Jsonb

from memory_system.config import DEFAULT_IMPORTANCE, DUPLICATE_SIMILARITY
from memory_system.llm import embed

# A new value for one of these relations contradicts an active value of the relations listed
# (hobby counts as a positive statement, like likes).
OPPOSITES = {
    "likes": ("dislikes",),
    "hobby": ("dislikes",),
    "dislikes": ("likes", "hobby"),
}

# Values of these relations are names, places or dates: they can be short (Ana, Li, Rio, 5 May),
# so grounding also accepts a value whose words all appear in the message.
VERBATIM_RELATIONS = frozenset(
    {"name", "family_member", "partner", "lives_in", "works_at", "birthday"}
)

# When the key relation changes, the value relation may no longer hold (a new employer can
# mean a new title), so it is marked 'conflicted' unless the same message restates it.
DEPENDENTS = {"works_at": "job_title"}

# Words that carry no content, so they cannot ground a value: function words, and generic
# words that say nothing about a value on their own ("new job").
STOPWORDS = frozenset(
    "about actually after again also been before being could does doing from have having here "
    "into just like love more most much only other over really some still such than that their "
    "them then there these they this very want were what when where which while will with "
    "would your yours "
    "and are but can did for get got had has her him his how its let may not nor now off old "
    "our out own put say see she the too use was who why yes yet you "
    "new job one work thing things stuff something".split()
)

# Clause-level checks used by normalize_actions.
_CLAUSE_SPLIT = re.compile(r"[,;:.!?\u2014\u2013]+|\bbut\b")
_NEGATION = re.compile(
    r"n't\b|\b(?:not|no longer|no more|anymore|any more|never|used to|stopped|quit|gave up|"
    r"forget|ignore|scratch that|wrong|mistake|quit|left|moved out of|switched from)\b"
)
_FILLERS = re.compile(
    r"^(?:(?:actually|well|so|and|now|then|also|oh|yes|yeah|okay|ok|correction|anyway)\b[\s,]*)+"
)
_OWN_STATEMENT = re.compile(r"^(?:i|my|it|we)\b")


def log_event(
    conn, user_id: str, event_type: str, fact_id: int | None, details: dict
) -> None:
    """Append one row to the memory_events audit log."""
    conn.execute(
        "INSERT INTO memory_events (user_id, event_type, fact_id, details) VALUES (%s, %s, %s, %s)",
        (user_id, event_type, fact_id, Jsonb(details)),
    )


def _content_words(text: str) -> set[str]:
    return {
        w
        for w in re.findall(r"\w+", text.lower())
        if len(w) >= 3 and w not in STOPWORDS
    }


def _same_word(a: str, b: str) -> bool:
    """Equal, or one is the other plus a short ending (egg/eggs, sail/sailing), or both long
    words share their first 5 letters (anchovy/anchovies)."""
    short, long_ = sorted((a, b), key=len)
    if long_.startswith(short) and (len(short) >= 5 or len(long_) - len(short) <= 4):
        return True
    return len(a) >= 5 and len(b) >= 5 and a[:5] == b[:5]


def is_grounded(value: str, text: str, relation: str | None = None) -> bool:
    """True if the value can be traced to the message it came from.

    Normally: the value shares at least one content word with the message. A content word has
    3+ letters and is not a stopword, so egg, soy and ski count but "new job" has nothing to
    check and is rejected. Words match as in _same_word (walnut/walnuts, sail/sailing).

    For names, places and dates (VERBATIM_RELATIONS) it is enough that every word of the
    value appears in the message, so Ana, Li, Rio or 5 May are accepted.

    It only catches values invented out of nothing. Junk made of message words
    ("new position") still passes, and paraphrases ("dev" -> "developer") are rejected.
    """
    if relation in VERBATIM_RELATIONS:
        value_words = re.findall(r"\w+", value.lower())
        if value_words and set(value_words) <= set(re.findall(r"\w+", text.lower())):
            return True
    message = _content_words(text)
    return any(_same_word(v, m) for v in _content_words(value) for m in message)


def _clause_of(value: str, relation: str, text: str) -> str | None:
    """The first clause of the message that mentions the value (lower-case), or None."""
    for clause in _CLAUSE_SPLIT.split(text.lower().replace("\u2019", "'")):
        if clause.strip() and is_grounded(value, clause, relation):
            return clause.strip()
    return None


def normalize_actions(
    facts: list, text: str, single_relations: frozenset = frozenset()
) -> list:
    """Check the extractor's assert/retract labels against the message and fix clear errors.

    The 8B model makes three kinds of slip with "not X, but Y" (observed on ~30 messages):
      1. It lists the same value as retract AND assert ("It's not Turin, I live in Genoa" ->
         retract Genoa, assert Genoa). The retract is dropped.
      2. It labels EVERY item a retract, so the replacement is lost ("I'm not a teacher anymore,
         I became a pilot" -> retract teacher, retract pilot). When a relation has 2+ retracts
         and no assert, one of them sits in a clause with a negation word and another in a
         different clause that is a statement of its own without one ("I became a pilot"), that
         one becomes an assert. A lone retract is never touched, because a missing negation
         word ("I moved out of Berlin") would otherwise turn a real retraction into a fact.
      3. For a single-valued relation it asserts both the old and the new value ("I quit my job
         at Initech, I work at Hooli now"). Only one can be true, so the one whose clause has a
         negation or "quit/left" word becomes the retract.
    Values not found in the message are left alone. Repeats are removed and retractions come
    first, so a retraction can never archive a fact asserted by the same message.
    """
    facts = list(facts)

    # 1) a retract of a value the same message asserts
    asserted = {(f.relation, f.value.lower()) for f in facts if f.action == "assert"}
    facts = [
        f
        for f in facts
        if not (f.action == "retract" and (f.relation, f.value.lower()) in asserted)
    ]

    # 2) every item of a relation labelled retract
    for relation in {f.relation for f in facts}:
        same = [f for f in facts if f.relation == relation]
        retracts = [f for f in same if f.action == "retract"]
        if len(retracts) < 2 or len(retracts) != len(same):
            continue
        clauses = {id(f): _clause_of(f.value, relation, text) for f in retracts}
        if not any(c and _NEGATION.search(c) for c in clauses.values()):
            continue
        for f in retracts:
            clause = clauses[id(f)]
            if (
                clause
                and not _NEGATION.search(clause)
                and _OWN_STATEMENT.match(_FILLERS.sub("", clause))
            ):
                facts[facts.index(f)] = f.model_copy(update={"action": "assert"})

    # 3) several asserts for a single-valued relation
    for relation in single_relations:
        asserts = [f for f in facts if f.relation == relation and f.action == "assert"]
        if len(asserts) < 2:
            continue
        ended = [
            f
            for f in asserts
            if (c := _clause_of(f.value, relation, text)) and _NEGATION.search(c)
        ]
        if ended and len(ended) < len(asserts):
            for f in ended:
                facts[facts.index(f)] = f.model_copy(update={"action": "retract"})

    unique, seen = [], set()
    for fact in facts:
        key = (fact.relation, fact.value.lower(), fact.action)
        if key not in seen:
            seen.add(key)
            unique.append(fact)
    return sorted(
        unique, key=lambda f: f.action != "retract"
    )  # stable: retractions first


def _matching(rows: list[tuple], value: str) -> list[tuple]:
    """Rows (id, value, similarity, ...) holding the same value: equal ignoring case, or close by trigram."""
    return [
        r for r in rows if r[1].lower() == value.lower() or r[2] >= DUPLICATE_SIMILARITY
    ]


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

    # 4) Positive vs negative statement about the same thing (likes/hobby vs dislikes):
    #    the newer statement wins.
    if relation in OPPOSITES:
        opposite = conn.execute(
            """SELECT id, value, similarity(lower(value), lower(%s)), relation
               FROM facts
               WHERE user_id = %s AND subject = 'user' AND relation = ANY(%s)
                 AND status = 'active'""",
            (value, user_id, list(OPPOSITES[relation])),
        ).fetchall()
        contradicted = _matching(opposite, value)
        if contradicted:
            _end(
                conn,
                [r[0] for r in contradicted],
                "superseded",
                at,
                superseded_by=new_id,
            )
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
