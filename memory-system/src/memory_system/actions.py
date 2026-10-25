"""Pure text rules for the write path (no database): is a value grounded in the message,
and are the extractor's assert/retract labels consistent with it."""

import re

# Values of these relations are names, places or dates: they can be short (Ana, Li, Rio, 5 May),
# so grounding also accepts a value whose words all appear in the message.
VERBATIM_RELATIONS = frozenset(
    {"name", "family_member", "partner", "lives_in", "works_at", "birthday"}
)


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
