"""Printing for evaluate.py: the per-question table, one summary block per set, and the
lists of retrieval problems and wrong answers."""

from memory_system.core.style import colour_marks, paint

from .metrics import tally
from .scenarios import SET_LABELS

MODES = ["none", "baseline", "smart"]


def mark(value: bool | None, bad_is_true: bool = False) -> str:
    if value is None:
        return "-"
    good = (not value) if bad_is_true else value
    return "✓" if good else "✗"


W = 6  # width of one mark column
BAR = paint(" │ ", "dim")


def _cells(values: list[str], width: int = W) -> str:
    """Centre plain text first, then colour the marks (escape codes would break the padding)."""
    return colour_marks("".join(f"{v:^{width}}" for v in values))


def _group(title: str, columns: int) -> str:
    return f"{title:^{W * columns}}"


def print_table(results: list[dict]) -> None:
    """One row per question; every metric has one column per mode.

    A column that holds only "-" (nothing measured) is left out, and a question that has any
    bad mark gets a bold name.
    """
    columns = [  # group, mode, value of one result row
        ("NEEDED", "base", lambda r: mark(r["baseline"]["needed_present"])),
        ("NEEDED", "smart", lambda r: mark(r["smart"]["needed_present"])),
        ("NOISE", "base", lambda r: mark(r["baseline"]["noise_present"], True)),
        ("NOISE", "smart", lambda r: mark(r["smart"]["noise_present"], True)),
        ("ANSWER", "none", lambda r: mark(r["none"].get("correct"))),
        ("ANSWER", "base", lambda r: mark(r["baseline"].get("correct"))),
        ("ANSWER", "smart", lambda r: mark(r["smart"].get("correct"))),
        ("LINES", "base", lambda r: str(r["baseline"]["lines"])),
        ("LINES", "smart", lambda r: str(r["smart"]["lines"])),
    ]
    cells = [[get(r) for get in (c[2] for c in columns)] for r in results]
    keep = [
        i for i in range(len(columns)) if any(row[i] != "-" for row in cells)
    ]  # drop empty columns
    groups: dict[str, list[int]] = {}
    for i in keep:
        groups.setdefault(columns[i][0], []).append(i)

    for line in (
        "base = baseline vector memory   smart = this system   none = no memory",
        "✓ good   ✗ bad   - not measured",
        "NOISE ✓ = no unwanted text   LINES = lines in the prompt",
    ):
        print(paint("  " + line, "dim") if line else "")
    head = f"{'':<48}"
    sub = f"{'scenario / question':<38}{'kind':<10}"
    for title, idx in groups.items():
        head += BAR + _group(title, len(idx))
        sub += BAR + "".join(f"{columns[i][1]:^{W}}" for i in idx)
    print()
    print(paint(head, "bold"))
    print(paint(sub, "bold"))
    last_set = None
    for r, row in zip(results, cells, strict=True):
        if last_set is not None and r["set"] != last_set:
            print(
                paint("-" * (48 + sum(3 + W * len(v) for v in groups.values())), "dim")
            )
        last_set = r["set"]
        label = f"{r['scenario']}: {r['question']}"[:36]
        bad = any(row[i] == "✗" for i in keep)
        line = paint(f"{label:<38}", "bold") if bad else f"{label:<38}"
        line += paint(f"{r['kind']:<10}", "dim")
        for idx in groups.values():
            line += BAR + _cells([row[i] for i in idx])
        print(line)


def _count(text: str) -> float | None:
    """'8/9' -> 8/9 as a fraction; '-' -> None."""
    if "/" not in text:
        return None
    done, total = text.split("/")
    return int(done) / int(total)


def _compare(base: str, smart: str, higher_is_better: bool) -> tuple[str, str]:
    """Styles for the two cells of one column: the better value green, the worse red."""
    a, b = (_count(base), _count(smart)) if "/" in base + smart else (None, None)
    if a is None or b is None:
        try:
            a, b = float(base), float(smart)
        except ValueError:
            return "", ""
    if a == b:
        return "", ""
    base_wins = (a > b) == higher_is_better
    return ("green", "red") if base_wins else ("red", "green")


def print_summaries(results: list[dict]) -> None:
    """One block per set; in each column the better mode is green and the worse one red."""
    columns = [  # title, width, higher_is_better
        ("needed", 9, True),
        ("noise", 8, False),
        ("stale in", 10, False),
        ("avg", 7, False),
        ("answers", 10, True),
        ("stale in", 10, False),
    ]
    for set_name in sorted({r["set"] for r in results}):
        rows = [r for r in results if r["set"] == set_name]
        print(
            paint(
                f"\nSET {SET_LABELS[set_name]}: {len(rows)} questions", "bold", "cyan"
            )
        )
        print(
            paint(
                f"{'mode':<10}{'needed':>9}{'noise':>8}{'stale in':>10}{'avg':>7}"
                f"{'answers':>10}{'stale in':>10}",
                "bold",
            )
        )
        print(
            paint(
                f"{'':<10}{'present':>9}{'present':>8}{'prompt':>10}{'lines':>7}"
                f"{'correct':>10}{'answer':>10}",
                "bold",
            )
        )
        values = {}
        for m in ("baseline", "smart"):
            values[m] = [
                tally(rows, m, "needed_present"),
                tally(rows, m, "noise_present"),
                str(sum(r[m]["stale_in_prompt"] for r in rows)),
                f"{sum(r[m]['lines'] for r in rows) / len(rows):.1f}",
                tally(rows, m, "correct"),
                tally(rows, m, "stale"),
            ]
        verdicts = [
            _compare(values["baseline"][i], values["smart"][i], columns[i][2])
            for i in range(len(columns))
        ]
        for side, m in enumerate(("baseline", "smart")):
            line = f"{m:<10}"
            for i, (_, width, _) in enumerate(columns):
                line += paint(f"{values[m][i]:>{width}}", verdicts[i][side] or "dim")  # noqa: E501
            print(line)
        print(
            paint("  ", "dim")
            + paint("green", "green")
            + paint(" = better than the other mode, ", "dim")
            + paint("red", "red")
            + paint(" = worse", "dim")
        )
        print(paint("  lower is better for: noise, stale, lines", "dim"))


def print_retrieval_problems(results: list[dict]) -> None:
    misses = [
        (r, m, why)
        for r in results
        for m in ("baseline", "smart")
        for why, bad in (
            ("needed fact missing", r[m]["needed_present"] is False),
            ("noise in prompt", r[m]["noise_present"] is True),
        )
        if bad
    ]
    if misses:
        print(paint("\nRetrieval problems", "bold", "red"))
        for r, m, why in misses:
            style = "red" if why.startswith("needed") else "yellow"
            print(f"  [{m}] {r['scenario']}:", paint(why, style))
            print(paint("      recalled:", "dim"), "" if r[m]["memory"] else "nothing")
            for line in r[m]["memory"]:
                print(f"        - {line[:100]}")


def print_wrong_answers(results: list[dict]) -> None:
    wrong = [
        (r, m)
        for r in results
        for m in ("baseline", "smart")
        if r[m].get("correct") is False
    ]
    if wrong:
        print(paint("\nWrong answers (baseline and smart)", "bold", "red"))
        for r, m in wrong:
            note = "   <-- fact WAS in the prompt" if r[m]["needed_present"] else ""
            print(
                f"  [{m}] {r['scenario']}: {r['question'][:60]}",
                paint(note.strip(), "yellow"),
            )
            print(f"      answer: {r[m]['answer'][:200]!r}")
