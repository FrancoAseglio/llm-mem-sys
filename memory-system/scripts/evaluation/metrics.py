"""Scoring helpers for evaluate.py: each takes the recalled lines (or the answer) and one
question dict from the scenarios. None means "this question does not test that"."""


def normalise(text: str) -> str:
    return text.lower().replace("’", "'")


def is_correct(answer: str, question: dict) -> bool | None:
    if not question.get("expect"):
        return None  # retrieval-only question
    a = normalise(answer)
    return all(any(word in a for word in group) for group in question["expect"])


def contains_any(text: str, words: list[str]) -> bool:
    t = normalise(text)
    return any(word in t for word in words)


def needed_fact_present(lines: list[str], question: dict) -> bool | None:
    needs = question.get("needs")
    if not needs:
        return None
    text = normalise(" ".join(lines))
    return all(word in text for word in needs)


def noise_present(lines: list[str], question: dict) -> bool | None:
    avoid = question.get("avoid")
    if not avoid:
        return None
    return contains_any(" ".join(lines), avoid)


def tally(rows: list[dict], mode: str, key: str) -> str:
    """'passed/total' of a boolean metric over the questions that test it."""
    values = [r[mode][key] for r in rows if r[mode].get(key) is not None]
    return f"{sum(values)}/{len(values)}" if values else "-"
