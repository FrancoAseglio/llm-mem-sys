from datetime import date

from memory_system.read.past_retrieve import retrieve_past
from memory_system.read.retrieve import Memory, retrieve, retrieve_baseline
from memory_system.summaries.retrieve import retrieve_summaries

LABELS = {
    "name": "Name",
    "lives_in": "Lives in",
    "works_at": "Works at",
    "job_title": "Job title",
    "partner": "Partner",
    "birthday": "Birthday",
    "hobby": "Hobby",
    "likes": "Likes",
    "dislikes": "Dislikes",
    "allergic_to": "Allergic to",
    "family_member": "Family member",
    "speaks": "Speaks",
    "goal": "Goal",
}

HEADERS = {
    "smart": "What you currently know about the user:",
    "baseline": "Past messages from the user that may be relevant:",
}


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
        past = retrieve_past(user_id, query, touch)  # empty unless the question is about the past
        lines = [format_past(m) for m in past]
        lines += [format_memory(m) for m in retrieve(user_id, query, k - len(past), touch)]
        return lines + retrieve_summaries(user_id, query, lines, k, touch)
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
