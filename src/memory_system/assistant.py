from datetime import date

from memory_system.core.config import NOTE_FACT_WINDOW
from memory_system.read.hybrid import all_messages, hybrid_lines
from memory_system.read.labels import LABELS
from memory_system.read.past_retrieve import retrieve_past
from memory_system.read.retrieve import Memory, retrieve, retrieve_baseline
from memory_system.summaries.retrieve import retrieve_summaries

HEADERS = {
    "smart": "What you currently know about the user:",
    "baseline": "Past messages from the user that may be relevant:",
    "hybrid": (
        "What you know about the user: current facts first, then past messages that may be "
        "relevant. A message marked [outdated: ...] was true when it was written and has "
        "changed since; one marked [no longer true: ...] is not true any more:"
    ),
    "full": "Everything the user has told you, oldest first:",
}

# Modes, in the order the evaluation prints them.
MODES = ["none", "baseline", "smart", "hybrid", "full"]


def format_memory(m: Memory) -> str:
    """One prompt line for a fact, e.g. 'Lives in: Milan (since 2026-10-24)'."""
    return f"{LABELS.get(m.relation, m.relation)}: {m.value} (since {m.since:%Y-%m-%d})"


def format_past(m: Memory) -> str:
    """One prompt line for a replaced fact, e.g. 'Earlier: Lives in: Bergen (until 2026-09-01)'."""
    when = f" (until {m.until:%Y-%m-%d})" if m.until else ""
    return f"Earlier: {LABELS.get(m.relation, m.relation)}: {m.value}{when}"


def recall(
    mode: str, user_id: str, query: str, k: int = 4, touch: bool = True
) -> list[str]:
    """Return the memory lines to inject into the prompt for the given mode."""
    if mode == "smart":
        past = retrieve_past(
            user_id, query, touch
        )  # empty unless the question is about the past
        facts = retrieve(user_id, query, k - len(past), touch)
        lines = [format_past(m) for m in past] + [format_memory(m) for m in facts]
        chosen = past + facts
        fact_best = (
            max(m.raw_similarity for m in chosen)
            if NOTE_FACT_WINDOW and chosen
            else None
        )
        return lines + retrieve_summaries(user_id, query, lines, k, touch, fact_best)
    if mode == "hybrid":
        facts, past, messages = hybrid_lines(user_id, query, k, touch)
        return [format_memory(m) for m in facts] + ([past] if past else []) + messages
    if mode == "full":
        return all_messages(user_id)
    if mode == "baseline":
        return [
            f'[{created:%Y-%m-%d}] "{content}"'
            for content, created, _ in retrieve_baseline(user_id, query, k)
        ]
    return []


def build_messages(
    mode: str, memory_lines: list[str], history: list[dict], user_text: str
) -> list[dict]:
    """System prompt (with the memory lines, if any), then the history, then the question."""
    system = (
        "You are a friendly, concise assistant that remembers the user across conversations. "
        f"Today is {date.today():%A %d %B %Y}. "
        "You have no access to real-time information such as weather, news or prices, so say so "
        "instead of guessing. If the user asks about themselves and you do not know the answer, "
        "say you don't know instead of guessing."
    )
    if memory_lines:
        system += (
            "\n\n"
            + HEADERS[mode]
            + "\n"
            + "\n".join(f"- {line}" for line in memory_lines)
        )
        system += (
            "\n\nUse this only when it is relevant to the question. Do not list it unprompted "
            "and do not mention having a memory system."
        )
    return [
        {"role": "system", "content": system},
        *history,
        {"role": "user", "content": user_text},
    ]
