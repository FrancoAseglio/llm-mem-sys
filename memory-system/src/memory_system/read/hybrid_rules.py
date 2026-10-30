"""Pure rules for the hybrid mode (no database, no model): the markers on outdated messages,
the timeline line for past questions, and how the evaluation recognises a marked line."""

from memory_system.read.labels import label

# Every line the hybrid mode marks as no longer current contains one of these. The evaluation
# counts an outdated value on such a line as "stale, marked", not as plain "stale in prompt".
OUTDATED = "[outdated: "
ENDED = "[no longer true: "
TIMELINE = ", oldest first: "


def is_marked(line: str) -> bool:
    """True for a line that says its old values are old: a marked message or a timeline."""
    return OUTDATED in line or ENDED in line or TIMELINE in line


def fact_marker(
    relation: str, value: str, end: tuple[str, str, str] | None
) -> str | None:
    """Marker for one fact a message produced that is no longer active.

    `end` is (relation, value, status) of the last fact in its superseded_by chain, or None when
    the fact was archived (retracted) or the chain has no successor. Returns None when the chain
    ends on the same value again (a user who moved back): the message is current once more.
    The marker names the old value and its kind, so the rest of the message stays usable:
    "[outdated: Lives in: Oslo -> now Kristiansand]", "[no longer true: Hobby: bass]" (set M:
    a marker that named only the new value hid the user's still-true name in a bio).
    """
    old = f"{label(relation)}: {value}"
    if end is not None and end[2] == "active":
        end_relation, end_value, _ = end
        if end_relation == relation and end_value.lower() == value.lower():
            return None
        now = (
            end_value
            if end_relation == relation
            else f"{label(end_relation)}: {end_value}"
        )
        return f"{OUTDATED}{old} -> now {now}]"
    return f"{ENDED}{old}]"


def marked_message(text: str, markers: list[str]) -> str:
    """A baseline line with its markers after it, e.g. '[2025-03-01] "..." [outdated: now X]'."""
    return " ".join([text, *markers]) if markers else text


def timeline_line(relation: str, values: list[tuple[str, str]]) -> str | None:
    """One line with every value a relation had, oldest first.

    `values` are (value, status) in date order. Repeats in a row are merged (a duplicate kept as
    two rows). Current values get "(now)", retracted ones "(ended)", uncertain ones "(unsure)".
    None when there is no history to show (fewer than two values and nothing ended).
    """
    merged: list[tuple[str, str]] = []
    for value, status in values:
        if merged and merged[-1][0].lower() == value.lower():
            merged[-1] = (merged[-1][0], status)  # the later status wins
        else:
            merged.append((value, status))
    if not merged or (len(merged) == 1 and merged[0][1] == "active"):
        return None
    tags = {"active": " (now)", "archived": " (ended)", "conflicted": " (unsure)"}
    chain = " -> ".join(f"{value}{tags.get(status, '')}" for value, status in merged)
    return f"{label(relation)}{TIMELINE}{chain}"
