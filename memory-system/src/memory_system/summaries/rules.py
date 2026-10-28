"""Pure text rules for the summaries layer (no database, no model): is a summary sentence
faithful to the messages it was written from, and does it add anything to the lines
already chosen for the prompt."""

import re
from dataclasses import dataclass
from datetime import datetime

from memory_system.write.actions import STOPWORDS, content_words, same_word

# Words a summary sentence uses about the user or the telling itself; they say nothing about
# the content, so they neither need to be in the sources nor count as new information.
SUMMARY_WORDS = frozenset(
    "user users they their them his her him she who said says mentioned told stated shared "
    "noted talked discussed later earlier recently currently".split()
)


@dataclass
class SummaryRow:
    id: int
    content: str
    since: datetime
    similarity: float  # raw cosine similarity to the question
    fresh: bool  # False if a source message produced a fact that is no longer active


def tag_message(number: int, text: str, stored: list[tuple[str, str]]) -> str:
    """One numbered line for the notes model: the message and the facts stored from it.

    `1. "I live in Rome." [stored: lives_in = Rome]`, or `[stored: nothing]` when the write
    path kept no fact from it, so the model knows what facts already hold.
    """
    tag = "; ".join(f"{relation} = {value}" for relation, value in stored) or "nothing"
    return f'{number}. "{text}" [stored: {tag}]'


_QUESTION_START = re.compile(
    r"^(?:what|how|why|when|where|who|which|can|could|would|should|do|does|did|is|are|will|any)\b"
)
_REQUEST_START = re.compile(
    r"^(?:give me|tell me|show me|help me|explain|recommend|suggest|thanks|thank you)\b"
)


def is_chatter(text: str) -> bool:
    """True for a message that is only a question, a request or thanks, so it holds nothing to
    remember about the user. A question starts with a question word and ends with "?"; a request
    starts with "give me", "explain", "suggest" and the like; thanks start with "thanks".
    A statement followed by a question ("I moved to Rome, can you suggest places?") is kept."""
    t = text.strip().lower()
    if _REQUEST_START.match(t):
        return True
    return t.endswith("?") and bool(_QUESTION_START.match(t))


def _words(text: str) -> set[str]:
    return content_words(text) - SUMMARY_WORDS


def is_faithful(statement: str, sources: list[str], min_share: float = 0.75) -> bool:
    """True if the sentence can be traced to its source messages.

    Every number must appear in the sources, and so must every capitalised word that does not
    start the sentence (a name or a place). At least `min_share` of the remaining content words
    must match some word of the sources, stopwords included (same_word: egg/eggs, ski/skiing,
    work/works). This catches invented details
    ("Japan", "900"); a wrong statement made only of source words still passes.
    """
    source_text = " ".join(sources)
    source_numbers = set(re.findall(r"\d+", source_text))
    if any(n not in source_numbers for n in re.findall(r"\d+", statement)):
        return False
    source_words = re.findall(r"\w+", source_text.lower())
    for token in statement.split()[1:]:
        word = re.sub(r"\W+", "", token)
        if (
            word[:1].isupper()
            and word.lower() not in STOPWORDS | SUMMARY_WORDS
            and not any(same_word(word.lower(), w) for w in source_words)
        ):
            return False
    words = _words(statement)
    if not words:
        return False
    # match against every source word, not only its content words: "works" in a sentence must
    # match "work" in the message, although "work" is a stopword
    matched = sum(any(same_word(w, s) for s in source_words) for w in words)
    return matched / len(words) >= min_share


# Month and weekday names may change between notes and their digest: a plan moved from
# "December 12" to "February" keeps only the final month (set_J.md, design point 3b).
MONTHS_AND_DAYS = frozenset(
    "january february march april may june july august september october november december "
    "monday tuesday wednesday thursday friday saturday sunday".split()
)


def _numbers(text: str) -> set[str]:
    """Numbers with their separators removed, so "21,500" and "21500" are the same number."""
    return {re.sub(r"[.,]", "", n) for n in re.findall(r"\d+(?:[.,]\d+)*", text)}


def _is_month_or_day(word: str) -> bool:
    """January, Tuesday, and plurals such as Tuesdays."""
    w = word.lower()
    return w in MONTHS_AND_DAYS or (w.endswith("s") and w[:-1] in MONTHS_AND_DAYS)


def _names(text: str) -> set[str]:
    """Capitalised words that do not start a sentence (names and places), lower-case, without
    a possessive ending ("Tobias's" -> "tobias"). Stopwords, the summary words and month and
    weekday names are not names here."""
    names = set()
    starts_sentence = True
    for token in text.split():
        word = re.sub(r"\W+", "", re.split(r"['\u2019]", token)[0])
        if (
            not starts_sentence
            and word[:1].isupper()
            and word.lower() not in STOPWORDS | SUMMARY_WORDS
            and not _is_month_or_day(word)
        ):
            names.add(word.lower())
        starts_sentence = token.endswith((".", "!", "?"))
    return names


def missing_details(digest: str, notes: list[str]) -> list[str]:
    """Numbers and names of the notes that the digest left out (empty if it kept them all).

    The retention check of consolidation: a digest must keep every number and every capitalised
    name of the notes it merges, except month and weekday names. Names match with same_word,
    so "Tobias" in a note is kept by "Tobias's" in the digest.
    """
    digest_numbers = _numbers(digest)
    digest_words = re.findall(r"\w+", digest.lower())
    numbers = set().union(*(_numbers(n) for n in notes))
    names = set().union(*(_names(n) for n in notes))
    missing = sorted(n for n in numbers if n not in digest_numbers)
    missing += sorted(
        n for n in names if not any(same_word(n, w) for w in digest_words)
    )
    return missing


def adds_information(statement: str, lines: list[str]) -> bool:
    """True if the sentence has a content word that none of the lines already has, so a
    summary that only restates a chosen fact ("The user lives in Milan") is left out."""
    known = content_words(" ".join(lines))
    return any(not any(same_word(w, k) for k in known) for w in _words(statement))


def select_summaries(
    rows: list[SummaryRow],
    lines: list[str],
    max_lines: int,
    floor: float,
    window: float,
) -> list[SummaryRow]:
    """The relevance gate for summaries: fresh rows with similarity >= floor, within `window` of
    the best of them, best first, skipping any that add nothing to `lines`. At most max_lines."""
    candidates = [r for r in rows if r.fresh and r.similarity >= floor]
    if not candidates:
        return []
    best = max(r.similarity for r in candidates)
    chosen: list[SummaryRow] = []
    context = list(lines)
    for row in sorted(candidates, key=lambda r: r.similarity, reverse=True):
        if len(chosen) >= max_lines or row.similarity < best - window:
            break
        if adds_information(row.content, context):
            chosen.append(row)
            context.append(row.content)
    return chosen
