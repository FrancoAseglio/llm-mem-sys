"""Printing for evaluate.py: the per-question table, one summary block per set, and the
lists of retrieval problems and wrong answers."""

from .metrics import tally
from .scenarios import SET_LABELS

MODES = ["none", "baseline", "smart"]


def mark(value: bool | None, bad_is_true: bool = False) -> str:
    if value is None:
        return "-"
    good = (not value) if bad_is_true else value
    return "✓" if good else "✗"


def print_table(results: list[dict]) -> None:
    print(
        f"\n{'scenario / question':<40}{'kind':<11}{'hist':>5} |"
        f"{'need b/s':>10}{'noise b/s':>11} |{'answer n/b/s':>16} |{'lines b/s':>10}"
    )
    for r in results:
        label = f"{r['scenario']}: {r['question']}"[:38]
        need = f"{mark(r['baseline']['needed_present'])}/{mark(r['smart']['needed_present'])}"
        noise = (
            f"{mark(r['baseline']['noise_present'], True)}/"
            f"{mark(r['smart']['noise_present'], True)}"
        )
        ans = "/".join(mark(r[m].get("correct")) for m in MODES)
        lines = f"{r['baseline']['lines']}/{r['smart']['lines']}"
        print(
            f"{label:<40}{r['kind']:<11}{r['messages_in_history']:>5} |"
            f"{need:>10}{noise:>11} |{ans:>16} |{lines:>10}"
        )


def print_summaries(results: list[dict]) -> None:
    """One block per set."""
    for set_name in sorted({r["set"] for r in results}):
        rows = [r for r in results if r["set"] == set_name]
        print(f"\nSET {SET_LABELS[set_name]}: {len(rows)} questions")
        print(
            f"{'mode':<10}{'needed':>9}{'noise':>8}{'stale in':>10}{'avg':>7}"
            f"{'answers':>10}{'stale in':>10}"
        )
        print(
            f"{'':<10}{'present':>9}{'present':>8}{'prompt':>10}{'lines':>7}"
            f"{'correct':>10}{'answer':>10}"
        )
        for m in ("baseline", "smart"):
            stale_prompt = sum(r[m]["stale_in_prompt"] for r in rows)
            avg = sum(r[m]["lines"] for r in rows) / len(rows)
            print(
                f"{m:<10}{tally(rows, m, 'needed_present'):>9}"
                f"{tally(rows, m, 'noise_present'):>8}{stale_prompt:>10}{avg:>7.1f}"
                f"{tally(rows, m, 'correct'):>10}{tally(rows, m, 'stale'):>10}"
            )
        print("  (noise present: lower is better; stale in prompt: lower is better)")


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
        print("\nRetrieval problems")
        for r, m, why in misses:
            print(f"  [{m}] {r['scenario']}: {why}")
            print(f"      recalled: {r[m]['memory'] or 'nothing'}")


def print_wrong_answers(results: list[dict]) -> None:
    wrong = [
        (r, m)
        for r in results
        for m in ("baseline", "smart")
        if r[m].get("correct") is False
    ]
    if wrong:
        print("\nWrong answers (baseline and smart)")
        for r, m in wrong:
            note = "   <-- fact WAS in the prompt" if r[m]["needed_present"] else ""
            print(f"  [{m}] {r['scenario']}: {r['question'][:60]}{note}")
            print(f"      answer: {r[m]['answer'][:200]!r}")
