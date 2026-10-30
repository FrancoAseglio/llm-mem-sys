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


def content_words(text: str) -> set[str]:
    return {
        w
        for w in re.findall(r"\w+", text.lower())
        if len(w) >= 3 and w not in STOPWORDS
    }


def same_word(a: str, b: str) -> bool:
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
    check and is rejected. Words match as in same_word (walnut/walnuts, sail/sailing).

    For names, places and dates (VERBATIM_RELATIONS) it is enough that every word of the
    value appears in the message, so Ana, Li, Rio or 5 May are accepted.

    It only catches values invented out of nothing. Junk made of message words
    ("new position") still passes, and paraphrases ("dev" -> "developer") are rejected.
    """
    if relation in VERBATIM_RELATIONS:
        value_words = re.findall(r"\w+", value.lower())
        if value_words and set(value_words) <= set(re.findall(r"\w+", text.lower())):
            return True
    message = content_words(text)
    return any(same_word(v, m) for v in content_words(value) for m in message)


# ---- Is the fact about the user? (set L: a sister's city, a friend as partner) ----

# Facts that can only describe the user: a value for them must be said about the user.
SELF_RELATIONS = frozenset({"lives_in", "works_at", "job_title", "birthday"})

# Subjects that point to the user, and words that point to someone or something else.
_FIRST_PERSON = frozenset(
    "i i'm im i've ive i'd i'll we we're we've we'd we'll".split()
)
# Subjects only: possessives (his, her, their, its) do not say whose fact it is ("transferred
# me to their office in Kristiansand", "her name is Odile"; set M, fixed 2026-10-30).
_THIRD_PERSON = frozenset("he she they it who he's she's they're it's they've".split())
# Words that name the partner relation itself; they do not mark someone else for `partner`.
_PARTNER_NOUNS = frozenset(
    "partner wife husband boyfriend girlfriend fiance fiancee".split()
)
_OTHER_PEOPLE = frozenset(
    "sister brother mother mum mom father dad parents parent friend friends colleague "
    "colleagues coworker boss partner wife husband boyfriend girlfriend fiance fiancee son "
    "daughter kids children cousin aunt uncle niece nephew grandmother grandfather grandma "
    "grandpa granny neighbour neighbor flatmate roommate housemate".split()
)
# A message that gives the user a fact names the user somewhere ("Margit quit the band to move
# to Canada" does not).
_ANY_FIRST_PERSON = re.compile(
    r"\b(?:i|i'm|im|i've|ive|i'd|i'll|me|my|mine|myself|we|we're|we've|we'd|we'll|us|our|ours)\b"
)
# A partner is named with one of these words somewhere in the message.
_PARTNER_WORDS = re.compile(
    r"\b(?:boyfriend|girlfriend|partner|wife|husband|fianc\w*|spouse|seeing|dating|"
    r"married|engaged|going out with|together with|i'?m with|split up|broke up)\b"
)


def _speaker(
    tokens: list[str], others: frozenset = frozenset(), ignore: frozenset = frozenset()
) -> str | None:
    """'user' or 'other' for the last subject word in tokens, None if there is none.
    `others` are names of people the user already told about (partner, family); words in
    `ignore` are skipped (the partner nouns, when the fact is the partner)."""
    for token in reversed(tokens):
        word = token.removesuffix("'s")
        if word in ignore:
            continue
        if token in _FIRST_PERSON:
            return "user"
        if token in _THIRD_PERSON or word in _OTHER_PEOPLE or word in others:
            return "other"
    return None


def _marries_someone_else(value: str, lower: str) -> bool:
    """ "Callum is getting married in Dublin": the value is the one marrying, so it is news about
    them, not the user's partner. "Priya and I are getting married" is the user's (set M)."""
    name = re.escape(value.lower())
    return bool(
        re.search(
            rf"\b{name}\b(?:\s+(?:is|was|has|just|got|'s))*\s+(?:getting\s+)?"
            r"(?:married|engaged)\b",
            lower,
        )
    ) and not re.search(rf"\b{name}\s+and\s+(?:i|me)\b", lower)


def about_user(
    value: str, relation: str, text: str, others: frozenset = frozenset()
) -> bool:
    """True unless the message gives this value to someone or something other than the user.

    Only for asserted facts that can describe the user alone (SELF_RELATIONS) and for
    `partner`. The 8B extractor gives the user what the message says about others:
    "My sister Agathe lives in Montreal and works as a pilot" -> lives_in = Montreal,
    job_title = pilot; "my suitcase ... it had ended up in Frankfurt" -> lives_in = Frankfurt.

    - SELF_RELATIONS: in each clause that mentions the value, the last subject word before it
      decides. "I", "I'm", "we" ... -> the user; "he", "she", "it", "who", "my sister" ...
      -> someone else; no subject word ("My birthday is 5 May") -> the user. The value is
      kept if any clause gives it to the user. A value not found is left to grounding.
    - partner: the message must contain a partner word (boyfriend, wife, seeing, dating ...),
      so "my friend Pieter" is not a partner, and the clause rule above applies too, with the
      partner nouns themselves ignored: "My sister Ingvild got engaged to her partner Jonas"
      is the sister's partner, "My wife is called Ines" is the user's.

    - Both: the message must have a first-person word somewhere (I, me, my, we, our ...).
      "Margit quit the band to move to Canada" names no subject word before Canada, so the
      clause rule alone would give Canada to the user (set J, found 2026-10-28).

    - `others`: lower-case names of the user's partner and family already stored. They count
      as someone else, so "Priya got a job at the hospital" (Priya being the user's wife) does
      not give the user a new employer (set M, added 2026-10-29).

    English only, word lists. It can be wrong both ways: "I visited my sister, she lives in
    Lyon" is blocked as intended, but "I live with my sister in Lyon" is kept only because
    "I" comes first.
    """
    lower = text.lower().replace("\u2019", "'")
    if relation in SELF_RELATIONS | {"partner"} and not _ANY_FIRST_PERSON.search(lower):
        return False
    if relation == "partner" and not _PARTNER_WORDS.search(lower):
        return False
    if relation == "partner" and _marries_someone_else(value, lower):
        return False
    if relation not in SELF_RELATIONS | {"partner"}:
        return True
    ignore = _PARTNER_NOUNS if relation == "partner" else frozenset()
    words = re.findall(r"\w+", value.lower())
    # locate the value by its content words ("St Veit Hospital in Linz": not by "in")
    value_words = {w for w in words if len(w) >= 3 and w not in STOPWORDS} or set(words)
    found = False
    for clause in _CLAUSE_SPLIT.split(lower):
        tokens = re.findall(r"[\w']+", clause)
        index = next(
            (
                i
                for i, token in enumerate(tokens)
                if (word := token.removesuffix("'s")) in value_words
                or any(len(v) >= 4 and same_word(v, word) for v in value_words)
            ),
            None,
        )
        if index is None:
            continue
        found = True
        if _speaker(tokens[:index], others, ignore) != "other":
            return True
    return not found


# ---- Did the message say the value changed? (set M: a commute, a house viewing) ----

# Words that say a single value changed, per relation. A new value replaces an active one only
# if the message has one of them (and is not only a plan). The user's first value needs none.
_CHANGE = {
    "lives_in": re.compile(
        r"\b(?:mov(?:e|ed|ing)|relocat\w*|transferr?\w*|live in|living in|lives in|"
        r"settled in|based in|new (?:flat|house|home|apartment|place) in|got a house|"
        r"bought a (?:flat|house|home|apartment))\b"
    ),
    "works_at": re.compile(
        r"\b(?:started (?:at|working)|new (?:job|position|role)|joined|work(?:s|ing)? (?:at|for)|"
        r"now (?:at|with|for)|i'?m (?:now )?at|i'?m now|hired|transferr?\w*|acquired|left|quit|"
        r"switch\w*|changed (?:jobs|employers))\b"
    ),
    "job_title": re.compile(
        r"\b(?:promot\w*|became|become|work(?:s|ing)? as|started as|new (?:job|role|position)|"
        r"i'?m now|now an?|i'?m an?|i am an?|as an?|head of|retrained)\b"
    ),
}
CHANGE_RELATIONS = frozenset(_CHANGE) | {"partner"}
# A change that has not happened yet: "we're moving to Bristol in the summer".
_FUTURE = re.compile(
    r"\b(?:will|going to|planning|plan to|thinking (?:about|of)|looking at|might|hope to|"
    r"soon|next (?:week|month|year|spring|summer|autumn|winter)|in the (?:spring|summer|"
    r"autumn|winter))\b"
)


def signals_change(value: str, relation: str, text: str) -> bool:
    """True if the message says this single value changed, so it may replace the current one.

    Checked only when the user already has a different active value. "We've started looking at
    houses in Rotterdam" (no change word, and a plan), "I now commute to Utrecht", "Peatline
    has no office" and "I've joined a choir" do not replace a city or a job title; "I've moved
    to Oslo", "Fjordline transferred me to Kristiansand" and "I've been promoted to head of
    the department" do. For `partner` the message needs a partner word (as in about_user).
    A sentence that only plans the change ("in the summer", "next year", "going to") does not
    count yet. English only, word lists.
    """
    lower = text.lower().replace("\u2019", "'")
    if relation == "partner":
        return bool(_PARTNER_WORDS.search(lower))
    pattern = _CHANGE.get(relation)
    if pattern is None:
        return True
    value_words = {w for w in re.findall(r"\w+", value.lower()) if len(w) >= 3} or set(
        re.findall(r"\w+", value.lower())
    )
    for sentence in re.split(r"[.!?;]+", lower):
        words = set(re.findall(r"\w+", sentence))
        if value_words & words or any(
            same_word(v, w) for v in value_words for w in words if len(v) >= 4
        ):
            if pattern.search(sentence) and not _FUTURE.search(sentence):
                return True
    return False


# Relations whose values are names: "Fjordline" and "Fjordline Aquaculture" are one employer.
NAME_RELATIONS = frozenset({"lives_in", "works_at", "partner", "name"})


def same_name(a: str, b: str) -> bool:
    """True if one name is the other plus more words ("Fjordline" in "Fjordline Aquaculture")."""
    x, y = sorted((a.lower().strip(), b.lower().strip()), key=len)
    return bool(x) and re.search(rf"\b{re.escape(x)}\b", y) is not None


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
