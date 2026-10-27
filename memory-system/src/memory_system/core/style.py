"""Terminal colours for the scripts (no dependency, nothing printed by the library itself).

Colour is used only when stdout is a terminal, so output that is piped or saved (`tee`,
`> file`) stays plain text. `NO_COLOR` (any value) switches it off, `FORCE_COLOR` switches
it on, and `set_enabled()` overrides both (the scripts' `--no-color` flag uses it).

Padding must be applied to the plain text BEFORE painting: escape codes count as characters
and would break the alignment of tables.
"""

import os
import sys

_CODES = {
    "bold": "1",
    "dim": "2",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
}
_override: bool | None = None


def set_enabled(value: bool | None) -> None:
    """Force colour on or off; None goes back to the automatic choice."""
    global _override
    _override = value


def enabled() -> bool:
    if _override is not None:
        return _override
    if "NO_COLOR" in os.environ:
        return False
    if "FORCE_COLOR" in os.environ:
        return True
    return sys.stdout.isatty()


def paint(text: str, *styles: str) -> str:
    """Wrap text in the given styles (names from _CODES); plain text when colour is off."""
    if not styles or not text or not enabled():
        return text
    codes = ";".join(_CODES[s] for s in styles)
    return f"\033[{codes}m{text}\033[0m"


def colour_marks(text: str) -> str:
    """Paint every tick green and every cross red (apply after padding a table cell)."""
    return paint_all(text, {"✓": "green", "✗": "red"})


def paint_all(text: str, styles_by_char: dict[str, str]) -> str:
    if not enabled():
        return text
    return "".join(
        paint(c, styles_by_char[c]) if c in styles_by_char else c for c in text
    )


# What the chat shows for each kind of memory event and fact status.
OUTCOME_STYLE = {
    "add": "green",
    "duplicate": "dim",
    "update": "yellow",
    "contradiction": "yellow",
    "retract": "red",
    "retract_miss": "red",
    "rejected": "red",
}
STATUS_STYLE = {
    "active": "green",
    "superseded": "dim",
    "conflicted": "yellow",
    "archived": "red",
}


def memory_line(line: str) -> str:
    """Colour one recalled line by its kind: past facts, notes, digests, plain facts."""
    if line.startswith("Earlier:"):
        return paint(line, "magenta")
    if line.startswith(("Note from", "Digest")):
        return paint(line, "blue")
    return line


def status(text: str) -> None:
    """Progress text: rewrites one line on a terminal, prints a plain dim line otherwise."""
    if enabled() and sys.stdout.isatty():
        print("\r\033[K" + paint(text, "dim"), end="", flush=True)
    else:
        print(paint(text, "dim"), flush=True)


def status_clear() -> None:
    """Wipe the progress line (terminal only)."""
    if enabled() and sys.stdout.isatty():
        print("\r\033[K", end="", flush=True)
