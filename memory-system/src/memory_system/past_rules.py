"""Pure rules for questions about the past (no database, no model)."""

import re

# Words that make a question about the user's past. English only, whole words. A keyword
# list: "How long was I at my job before it closed?" fires, "Where was home as a student?" does not.
_PAST = re.compile(
    r"\b(used to|did i use to|before|previously|formerly|originally|in the past|back then|prior to)\b",
    re.IGNORECASE,
)


def is_past_question(query: str) -> bool:
    """True if the question asks about something that used to be true."""
    return _PAST.search(query) is not None


def drop_active_values(past: list, active_values: set[tuple[str, str]]) -> list:
    """Remove past facts whose (relation, value) is also active now (a user who moved back):
    they are not 'earlier' anything. Compared case-insensitively."""
    return [
        m
        for m in past
        if (m.relation, m.value.lower()) not in {(r, v.lower()) for r, v in active_values}
    ]
