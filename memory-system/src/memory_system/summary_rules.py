"""Pure text rules for the summaries layer (no database, no model): is a summary sentence
faithful to the messages it was written from, and does it add anything to the lines
already chosen for the prompt."""

import re
from dataclasses import dataclass
from datetime import datetime

from memory_system.actions import STOPWORDS, content_words, same_word

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


def _words(text: str) -> set[str]:
    return content_words(text) - SUMMARY_WORDS


def is_faithful(statement: str, sources: list[str], min_share: float = 0.75) -> bool:
    """True if the sentence can be traced to its source messages.

    Every number must appear in the sources, and so must every capitalised word that does not
    start the sentence (a name or a place). At least `min_share` of the remaining content words
    must match a source word (same_word: egg/eggs, ski/skiing). This catches invented details
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
    source_content = content_words(source_text)
    matched = sum(any(same_word(w, s) for s in source_content) for w in words)
    return matched / len(words) >= min_share


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
