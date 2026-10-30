"""Printing for evaluate.py: the per-question table, one summary block per set, and the
lists of retrieval problems and wrong answers."""

from memory_system.core.style import colour_marks, paint

from .metrics import tally
from .scenarios import SET_LABELS

# Modes compared in the summaries and lists ("none" has no memory to score).
COMPARED = ["baseline", "smart", "hybrid", "full"]
SHORT = {
    "none": "none",
    "baseline": "base",
    "smart": "smart",
    "hybrid": "hyb",
    "full": "full",
}


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

    def col(group, mode, key, bad_is_true=False, count=False):
        def get(r):
            entry = r.get(mode, {})
            if count:
                return str(entry["lines"]) if "lines" in entry else "-"
            return mark(entry.get(key), bad_is_true)

        return group, SHORT[mode], get

    retrieved = [
        "baseline",
        "smart",
        "hybrid",
    ]  # full holds everything: nothing to score
    columns = (
        [col("NEEDED", m, "needed_present") for m in retrieved]
        + [col("NOISE", m, "noise_present", True) for m in retrieved]
        + [col("ANSWER", m, "correct") for m in ["none", *COMPARED]]
        + [col("LINES", m, "lines", count=True) for m in retrieved]
    )
    cells = [[get(r) for get in (c[2] for c in columns)] for r in results]
    keep = [
        i for i in range(len(columns)) if any(row[i] != "-" for row in cells)
    ]  # drop empty columns
    groups: dict[str, list[int]] = {}
    for i in keep:
        groups.setdefault(columns[i][0], []).append(i)

    for line in (
        "base = baseline vector memory   smart = facts and notes   hyb = hybrid   "
        "full = whole history   none = no memory",
        "✓ good   ✗ bad   - not measured   bold name = smart has a ✗",
        "NOISE ✓ = no unwanted text   LINES = lines in the prompt",
    ):
        print(paint("  " + line, "dim") if line else "")
    kw = max([10] + [len(r["kind"]) + 1 for r in results])  # width of the kind column
    head = f"{'':<{38 + kw}}"
    sub = f"{'scenario / question':<38}{'kind':<{kw}}"
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
                paint(
                    "-" * (38 + kw + sum(3 + W * len(v) for v in groups.values())),
                    "dim",
                )
            )
        last_set = r["set"]
        label = f"{r['scenario']}: {r['question']}"[:36]
        # bold only when the smart column fails: that is the system's own miss
        bad = any(row[i] == "✗" for i in keep if columns[i][1] == "smart")
        line = paint(f"{label:<38}", "bold") if bad else f"{label:<38}"
        line += paint(f"{r['kind']:<{kw}}", "blue")
        for idx in groups.values():
            line += BAR + _cells([row[i] for i in idx])
        print(line)


def _count(text: str) -> float | None:
    """'8/9' -> 8/9 as a fraction; '-' -> None."""
    if "/" not in text:
        return None
    done, total = text.split("/")
    return int(done) / int(total)


def _number(text: str) -> float | None:
    """'8/9' -> 8/9, '2.5' -> 2.5, '-' -> None."""
    if "/" in text:
        return _count(text)
    try:
        return float(text)
    except ValueError:
        return None


def _compare(values: list[str], higher_is_better: bool) -> list[str]:
    """Styles for the cells of one column: the best value green, the worst red, others plain."""
    numbers = [_number(v) for v in values]
    known = [n for n in numbers if n is not None]
    if len(set(known)) < 2:
        return [""] * len(values)
    best = max(known) if higher_is_better else min(known)
    worst = min(known) if higher_is_better else max(known)
    return [
        "" if n is None else "green" if n == best else "red" if n == worst else ""
        for n in numbers
    ]


def print_summaries(results: list[dict]) -> None:
    """One block per set; in each column the better mode is green and the worse one red."""
    columns = [  # title, width, higher_is_better
        ("needed", 9, True),
        ("noise", 8, False),
        ("stale in", 10, False),
        ("stale", 8, False),
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
                f"{'mode':<10}{'needed':>9}{'noise':>8}{'stale in':>10}{'stale':>8}"
                f"{'avg':>7}{'answers':>10}{'stale in':>10}",
                "bold",
            )
        )
        print(
            paint(
                f"{'':<10}{'present':>9}{'present':>8}{'prompt':>10}{'marked':>8}"
                f"{'lines':>7}{'correct':>10}{'answer':>10}",
                "bold",
            )
        )
        modes = [m for m in COMPARED if all(m in r for r in rows)]
        full_note = "full" in modes
        values = {}
        for m in modes:
            values[m] = [
                tally(rows, m, "needed_present") if m != "full" else "-",
                tally(rows, m, "noise_present") if m != "full" else "-",
                str(sum(r[m]["stale_in_prompt"] for r in rows)),
                str(sum(r[m].get("stale_marked", False) for r in rows)),
                f"{sum(r[m]['lines'] for r in rows) / len(rows):.1f}",
                tally(rows, m, "correct"),
                tally(rows, m, "stale"),
            ]
        verdicts = [
            _compare([values[m][i] for m in modes if m != "full"], columns[i][2])
            for i in range(len(columns))
        ]
        compared = [m for m in modes if m != "full"]
        for m in modes:
            line = f"{m:<10}"
            for i, (_, width, _) in enumerate(columns):
                style = verdicts[i][compared.index(m)] if m in compared else ""
                line += paint(f"{values[m][i]:>{width}}", style or "dim")
            print(line)
        print(
            paint("  ", "dim")
            + paint("green", "green")
            + paint(" = best of baseline, smart and hybrid, ", "dim")
            + paint("red", "red")
            + paint(" = worst", "dim")
        )
        print(paint("  lower is better for: noise, stale, lines", "dim"))
        print(
            paint(
                "  stale marked = an outdated value only on lines marked as old (hybrid)",
                "dim",
            )
        )
        if full_note:
            print(paint("  full = the whole history, a reference ceiling", "dim"))


def print_retrieval_problems(results: list[dict]) -> None:
    misses = [
        (r, m, why)
        for r in results
        for m in ("baseline", "smart", "hybrid")
        if m in r
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
            print(f"  {paint(f'[{m}]', 'purple')} {r['scenario']}:", paint(why, style))
            print(paint("      recalled:", "dim"), "" if r[m]["memory"] else "nothing")
            for line in r[m]["memory"]:
                print(f"        - {line[:100]}")


def print_wrong_answers(results: list[dict]) -> None:
    wrong = [
        (r, m)
        for r in results
        for m in COMPARED
        if r.get(m, {}).get("correct") is False
    ]
    if wrong:
        print(paint("\nWrong answers (every mode with memory)", "bold", "red"))
        for r, m in wrong:
            note = "   <-- fact WAS in the prompt" if r[m]["needed_present"] else ""
            print(
                f"  {paint(f'[{m}]', 'purple')} {r['scenario']}: {r['question'][:60]}",
                paint(note.strip(), "yellow"),
            )
            print(f"      answer: {r[m]['answer'][:200]!r}")
