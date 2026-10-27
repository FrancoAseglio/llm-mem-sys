"""List the evaluation scenarios, grouped by set (no database or model needed).

    poetry run python scripts/list_scenarios.py            # every set
    poetry run python scripts/list_scenarios.py --set J    # one or more sets
    make scenarios  /  make scenarios SET=J

The ids are what `inspect_scores.py --scenario <id>` and `evaluate.py --only <id>` take.
"""

import argparse

from evaluation.scenarios import SCENARIOS, SET_LABELS, SETS

from memory_system.core.style import paint, set_enabled


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", nargs="+", help="set letters, e.g. A J")
    parser.add_argument("--no-color", action="store_true")
    args = parser.parse_args()
    if args.no_color:
        set_enabled(False)

    letters = [s.upper() for s in args.set] if args.set else list(SETS)
    unknown = [s for s in letters if s not in SETS]
    if unknown:
        parser.error(f"unknown set {unknown}, available: {' '.join(SETS)}")

    idw = max(len(sc["id"]) for sc in SCENARIOS) + 2  # same widths for every set
    kw = max(len(sc["kind"]) for sc in SCENARIOS) + 2
    for letter in letters:
        scenarios = SETS[letter]
        questions = sum(len(sc["questions"]) for sc in scenarios)
        print(paint(f"\nSET {SET_LABELS[letter]}", "bold", "cyan"))
        print(
            paint(
                f"  {len(scenarios)} scenarios, {questions} questions",
                "dim",
            )
        )
        print(
            paint(
                f"  {'id':<{idw}}{'kind':<{kw}}{'messages':>9}{'questions':>11}", "bold"
            )
        )
        for sc in scenarios:
            print(
                f"  {sc['id']:<{idw}}"
                + paint(f"{sc['kind']:<{kw}}", "blue")
                + f"{len(sc['messages']):>9}{len(sc['questions']):>11}"
            )
    print(
        paint(
            f"\n{len(SCENARIOS)} scenarios in {len(SETS)} sets. "
            "Use an id with: make inspect SCENARIO=<id>",
            "dim",
        )
    )


if __name__ == "__main__":
    main()
