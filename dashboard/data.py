"""The questions of every evaluation run, read from results/answers.csv for the results page.

Uses the csv module only (no pandas), so the dashboard group stays small. The tables are read
once and kept: they change only when a new run is exported, and the dashboard is restarted then.

A question is one (run, scenario, question) with the answer of every mode it was asked in. Its
id is its position in the run, in the order of answers.csv, so a link stays valid as long as
the run's rows do not change.
"""

import csv
import re
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from memory_system.read.hybrid_rules import is_marked

RESULTS = Path(__file__).resolve().parents[1] / "results"

# Every mode, in the order the dashboard shows them.
MODES = ["none", "baseline", "smart", "hybrid", "full"]
MODE_LABELS = {
    "none": "none (no memory)",
    "baseline": "baseline (vector search)",
    "smart": "smart (facts only)",
    "hybrid": "hybrid (final design)",
    "full": "full history",
}
QTYPES = {
    "change": "current value after a change",
    "past": "value before a change",
    "episode": "episode",
    "detail": "numeric detail",
    "plan": "changed plan",
    "other": "other people",
    "indirect": "indirect (allergy, signature)",
    "direct": "direct fact",
    "trap": "trap",
    "abstain": "abstain",
}
# The 1/0 checks of answers.csv after `correct`, with the words the page shows for them.
CHECKS = {
    "needed_present": "needed words in prompt",
    "noise_present": "noise in prompt",
    "stale_in_prompt": "outdated value, unmarked",
    "stale_marked": "outdated value, marked",
    "stale_in_answer": "outdated value in answer",
}
# A check is good news when it is 1 (needed words present) or when it is 0 (all the others).
GOOD_WHEN_SET = {"needed_present"}
DEFAULT_RUN = "N_full"
SEPARATOR = " || "
MESSAGE = re.compile(r"^\[\d{4}-\d{2}-\d{2}\] ")


@dataclass
class Line:
    """One memory line of a prompt and what it is: a raw message, a fact, an episode note, or
    a line hybrid marks as no longer current (a marked message or a timeline)."""

    text: str
    kind: str


@dataclass
class Answer:
    mode: str
    correct: bool | None  # None: the question has no answer check
    checks: dict[str, bool]  # only the checks this question tests
    lines: int
    answer: str
    memory: list[Line]

    def problems(self) -> list[str]:
        """The checks that came out the bad way (needed words missing, anything else present)."""
        return [c for c, v in self.checks.items() if v != (c in GOOD_WHEN_SET)]


@dataclass
class Question:
    id: int
    run: str
    set: str
    scenario: str
    kind: str
    qtype: str
    question: str
    answers: dict[str, Answer] = field(default_factory=dict)

    def result(self, mode: str) -> bool | None:
        """True or False when `mode` answered and was scored, else None."""
        answer = self.answers.get(mode)
        return answer.correct if answer else None


@dataclass
class Run:
    order: int
    run: str
    phase: str
    description: str
    sets: list[str]
    modes: list[str]
    questions: list[Question]


def line_kind(text: str) -> str:
    if is_marked(text):
        return "marked"
    if MESSAGE.match(text):
        return "message"
    if text.startswith("Note from "):
        return "note"
    return "fact"


def parse_memory(memory: str) -> list[Line]:
    return [Line(t, line_kind(t)) for t in memory.split(SEPARATOR) if t.strip()]


def _flag(value: str) -> bool | None:
    return None if value == "" else value == "1"


@cache
def runs(directory: Path = RESULTS) -> dict[str, Run]:
    """Every run that has per-question rows, keyed by id, in the order the runs were made."""
    with open(directory / "runs.csv", newline="") as f:
        info = {r["run"]: r for r in csv.DictReader(f)}

    grouped: dict[str, dict[tuple[str, str], Question]] = {}
    with open(directory / "answers.csv", newline="") as f:
        for row in csv.DictReader(f):
            if not row["answer"] and not row["correct"]:
                continue  # a mode that was not run (later runs skip `none`): no answer
            questions = grouped.setdefault(row["run"], {})
            key = (row["scenario"], row["question"])
            if key not in questions:
                questions[key] = Question(
                    id=len(questions),
                    run=row["run"],
                    set=row["set"],
                    scenario=row["scenario"],
                    kind=row["kind"],
                    qtype=row["qtype"],
                    question=row["question"],
                )
            checks = {c: _flag(row[c]) for c in CHECKS}
            questions[key].answers[row["mode"]] = Answer(
                mode=row["mode"],
                correct=_flag(row["correct"]),
                checks={c: v for c, v in checks.items() if v is not None},
                lines=int(row["lines"] or 0),
                answer=row["answer"],
                memory=parse_memory(row["memory"]),
            )

    result = {}
    for name, questions in grouped.items():
        qs = list(questions.values())
        present = {m for q in qs for m in q.answers}
        meta = info.get(name, {})
        result[name] = Run(
            order=int(meta.get("order", 0)),
            run=name,
            phase=meta.get("phase", ""),
            description=meta.get("description", ""),
            sets=sorted({q.set for q in qs}),
            modes=[m for m in MODES if m in present],
            questions=qs,
        )
    return dict(sorted(result.items(), key=lambda item: item[1].order))


@dataclass
class Filters:
    """What the results page shows: which questions (run, set, type) and which modes' columns.
    Empty strings and an empty `modes` mean "all"."""

    run: str = DEFAULT_RUN
    set: str = ""
    qtype: str = ""
    modes: tuple[str, ...] = ()

    def query(self) -> list[tuple[str, str]]:
        """The filters as URL parameters (one `mode` per shown mode), without the empty ones."""
        pairs = [(k, getattr(self, k)) for k in ("run", "set", "qtype")]
        return [(k, v) for k, v in pairs if v] + [("mode", m) for m in self.modes]


def qtypes(run: Run) -> list[str]:
    """The question types the run has, in the order of QTYPES (empty before set M)."""
    present = {q.qtype for q in run.questions}
    return [t for t in QTYPES if t in present]


def clean(filters: Filters, all_runs: dict[str, Run]) -> Filters:
    """The same filters with unknown values dropped: a run that does not exist falls back to
    the default; a set or type the run does not have to "all"; modes the run does not have are
    dropped, and choosing every mode (or none of the run's) is the same as "all"."""
    run = filters.run if filters.run in all_runs else DEFAULT_RUN
    r = all_runs[run]
    modes = tuple(m for m in r.modes if m in filters.modes)
    return Filters(
        run=run,
        set=filters.set if filters.set in r.sets else "",
        qtype=filters.qtype if filters.qtype in qtypes(r) else "",
        modes=() if len(modes) in (0, len(r.modes)) else modes,
    )


def shown_modes(run: Run, f: Filters) -> list[str]:
    """The modes whose columns and cards are shown."""
    return list(f.modes) or run.modes


def select(run: Run, f: Filters) -> list[Question]:
    """The questions of `run` in the chosen set and question type (the modes only change which
    columns are shown, never which questions)."""
    return [
        q
        for q in run.questions
        if (not f.set or q.set == f.set) and (not f.qtype or q.qtype == f.qtype)
    ]


def describe(run: Run, f: Filters, shown: int) -> str:
    """The filters in words, e.g. 'Showing 8 of 57 questions of run N_full (set N): value
    before a change.'"""
    parts = []
    if f.set and len(run.sets) > 1:
        parts.append(f"set {f.set}")
    if f.qtype:
        parts.append(QTYPES[f.qtype])
    what = f": {', '.join(parts)}" if parts else ""
    sets = run.sets[0] if len(run.sets) == 1 else f"{run.sets[0]} to {run.sets[-1]}"
    return (
        f"Showing {shown} of {len(run.questions)} questions of run {run.run} "
        f"(set{'s' if len(run.sets) > 1 else ''} {sets}){what}."
    )


def tally(questions: list[Question], modes: list[str]) -> dict[str, tuple[int, int]]:
    """(right, scored) per mode over the given questions."""
    result = {}
    for m in modes:
        marks = [q.result(m) for q in questions]
        scored = [v for v in marks if v is not None]
        result[m] = (sum(scored), len(scored))
    return result
