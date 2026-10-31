"""Tables behind the results notebook, computed from the CSV files in results/.

Every function takes the loaded tables and returns a pandas DataFrame, ready to show or to
plot with evaluation.plots. Needs the optional analysis group (poetry install --with analysis).
"""

from dataclasses import dataclass
from math import comb
from pathlib import Path

import pandas as pd

RESULTS = Path(__file__).resolve().parents[1] / "results"

MODES = ["baseline", "smart", "hybrid", "full"]
BLIND_LONG = {"N": "N_full", "O": "O_full"}
SHORT_RUNS = ["A_to_J_change_rule_1b", "L_change_rule_1b"]
M_STEPS = {
    "M_full": "blind run",
    "M_change_rule": "change rule",
    "M_change_rule_1b": "change rule 1b",
    "M_hybrid": "hybrid added",
    "M_fixes": "fixes from N",
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


@dataclass
class Results:
    runs: pd.DataFrame
    totals: pd.DataFrame
    answers: pd.DataFrame


def load(directory: Path = RESULTS) -> Results:
    """The three tables of results/ (sessions.csv is not used here)."""
    return Results(
        runs=pd.read_csv(directory / "runs.csv"),
        totals=pd.read_csv(directory / "totals.csv"),
        answers=pd.read_csv(directory / "answers.csv"),
    )


def sign_test(wins: int, losses: int) -> float:
    """Two-sided exact binomial test on the questions where two modes differ."""
    n, k = wins + losses, max(wins, losses)
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(comb(n, i) for i in range(k, n + 1)) / 2**n)


def short_sets(res: Results) -> pd.DataFrame:
    """Share answered right (%) per short set, baseline and smart, with the question count."""
    t = res.totals
    t = t[t.run.isin(SHORT_RUNS) & t["mode"].isin(["baseline", "smart"])]
    share = t.assign(share=100 * t.correct / t.answered).pivot_table(
        index="set", columns="mode", values="share"
    )
    asked = t[t["mode"] == "baseline"].set_index("set").answered.astype(int)
    return share[["baseline", "smart"]].assign(questions=asked)


def set_m_steps(res: Results) -> pd.DataFrame:
    """Right answers on set M per development step (rows in order), per mode."""
    t = res.totals
    t = t[t.run.isin(M_STEPS) & (t.set == "M") & t["mode"].isin(MODES)]
    table = t.pivot_table(index="run", columns="mode", values="correct").reindex(
        list(M_STEPS)
    )
    table.index = [M_STEPS[r] for r in table.index]
    return table[[m for m in MODES if m in table]]


def headline(res: Results) -> pd.DataFrame:
    """Right answers per mode on the blind long-history sets N and O, and both together."""
    t = res.totals
    t = t[t.run.isin(BLIND_LONG.values()) & t["mode"].isin(MODES)]
    table = t.pivot_table(index="mode", columns="set", values="correct", aggfunc="sum")
    table = table.reindex(MODES)[list(BLIND_LONG)]
    table["N + O"] = table.sum(axis=1)
    return table.astype(int)


def differing(res: Results, run: str, a: str = "hybrid", b: str = "baseline") -> tuple:
    """(questions only `a` got right, questions only `b` got right) in one run."""
    q = res.answers[res.answers.run == run].pivot_table(
        index=["scenario", "question"],
        columns="mode",
        values="correct",
        aggfunc="first",
    )
    q = q.dropna(subset=[a, b])
    return int(((q[a] == 1) & (q[b] == 0)).sum()), int(
        ((q[a] == 0) & (q[b] == 1)).sum()
    )


def sign_tests(res: Results, a: str = "hybrid", b: str = "baseline") -> pd.DataFrame:
    """Per blind long set and pooled: questions only `a` or only `b` got right, and p."""
    rows = []
    for name, run in BLIND_LONG.items():
        won, lost = differing(res, run, a, b)
        rows.append({"set": name, f"only {a}": won, f"only {b}": lost})
    rows.append(
        {
            "set": "N + O",
            f"only {a}": sum(r[f"only {a}"] for r in rows),
            f"only {b}": sum(r[f"only {b}"] for r in rows),
        }
    )
    table = pd.DataFrame(rows).set_index("set")
    table["p (sign test)"] = [
        round(sign_test(won, lost), 3)
        for won, lost in zip(table[f"only {a}"], table[f"only {b}"], strict=True)
    ]
    return table


def by_type(res: Results) -> pd.DataFrame:
    """Share answered right (%) per question type and mode, blind sets N and O together."""
    a = res.answers
    a = a[a.run.isin(BLIND_LONG.values()) & a["mode"].isin(MODES)]
    share = 100 * a.pivot_table(
        index="qtype", columns="mode", values="correct", aggfunc="mean"
    )
    count = a[a["mode"] == "baseline"].groupby("qtype").size()
    table = share.reindex(list(QTYPES))[MODES].assign(questions=count)
    table.index = [QTYPES[q] for q in table.index]
    return table.round(0)


def cost(res: Results) -> pd.DataFrame:
    """Per mode on N and O together: right answers, outdated answers, memory lines."""
    t = res.totals
    t = t[t.run.isin(BLIND_LONG.values()) & t["mode"].isin(MODES)]
    table = t.groupby("mode").agg(
        right=("correct", "sum"),
        outdated=("stale_answer", "sum"),
        lines=("avg_lines", "mean"),
    )
    return table.reindex(MODES).astype({"right": int, "outdated": int}).round(1)


def blind_runs(res: Results) -> pd.DataFrame:
    """Right answers per mode on the first and only run of every blind set."""
    blind = res.runs[res.runs.phase == "blind"].run
    t = res.totals[res.totals.run.isin(blind) & res.totals["mode"].isin(MODES)]
    table = t.pivot_table(
        index=["set", "run"], columns="mode", values="correct", aggfunc="sum"
    )
    return table.reindex(columns=MODES)


REGRESSION_RUNS = [
    "A_to_G_after_fix2",
    "A_to_H_past_rule",
    "A_to_I_consolidation",
    "A_to_J_nocache",
    "A_to_J_about_user",
    "A_to_J_note_tags",
    "A_to_J_note_tags_v2",
    "A_to_J_note_tags_v2b",
    "A_to_J_note_window",
    "A_to_J_first_person",
    "A_to_J_change_rule",
    "A_to_J_change_rule_1b",
]


def development_map(res: Results) -> pd.DataFrame:
    """Smart minus baseline, in points of share answered right, per short set (rows) and
    regression run (columns, in the order they were made)."""
    t = res.totals[res.totals.run.isin(REGRESSION_RUNS)]
    t = t[t["mode"].isin(["baseline", "smart"]) & (t.answered > 0)]
    share = t.assign(share=100 * t.correct / t.answered).pivot_table(
        index=["set", "run"], columns="mode", values="share"
    )
    diff = (share.smart - share.baseline).unstack("run")
    return diff.reindex(columns=REGRESSION_RUNS).round(0)


def blind_share(res: Results) -> pd.DataFrame:
    """Share answered right (%) per mode on the first and only run of every blind set, and the
    number of questions with an answer check."""
    blind = res.runs[res.runs.phase == "blind"].run
    t = res.totals[res.totals.run.isin(blind) & res.totals["mode"].isin(MODES)]
    t = t.copy()
    # One row per set; set J was run twice blind (summaries off and on), so its rows say which.
    extra = t.run.str.extract(r"_(on|off)$", expand=False)
    t["label"] = "Set " + t.set + ("  summaries " + extra).fillna("")
    share = t.assign(share=100 * t.correct / t.answered).pivot_table(
        index="label", columns="mode", values="share"
    )
    count = t[t["mode"] == "baseline"].set_index("label").answered.astype(int)
    return share.reindex(columns=MODES).assign(questions=count)
