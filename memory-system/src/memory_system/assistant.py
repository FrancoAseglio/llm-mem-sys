from datetime import date

from memory_system.retrieve import Memory, retrieve, retrieve_baseline

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
    return f"{LABELS.get(m.relation, m.relation)}: {m.value} (since {m.since:%Y-%m-%d})"


def recall(mode: str, user_id: str, query: str, k: int = 4, touch: bool = True) -> list[str]:
    """Return the memory lines to inject into the prompt for the given mode."""
    if mode == "smart":
        return [format_memory(m) for m in retrieve(user_id, query, k, touch)]
    if mode == "baseline":
        return [f'[{created:%Y-%m-%d}] "{content}"'
                for content, created, _ in retrieve_baseline(user_id, query, k)]
    return []


def build_messages(mode: str, memory_lines: list[str], history: list[dict], user_text: str):
    system = (
        "You are a friendly, concise assistant that remembers the user across conversations. "
        f"Today is {date.today():%A %d %B %Y}."
    )
    if memory_lines:
        system += "\n\n" + HEADERS[mode] + "\n" + "\n".join(f"- {line}" for line in memory_lines)
        system += (
            "\n\nUse this only when it is relevant to the question. Do not list it unprompted "
            "and do not mention having a memory system."
        )
    return [{"role": "system", "content": system}, *history, {"role": "user", "content": user_text}]
