"""The tables behind the results notebook, checked against the committed result data.

Needs the optional analysis group (pandas); skipped when it is not installed, as in CI.
"""

import pytest

pd = pytest.importorskip("pandas")

from evaluation import analysis  # noqa: E402


@pytest.fixture(scope="module")
def res():
    return analysis.load()


def test_sign_test():
    assert analysis.sign_test(0, 0) == 1.0
    assert round(analysis.sign_test(8, 3), 3) == 0.227
    assert round(analysis.sign_test(15, 7), 3) == 0.134


def test_headline(res):
    table = analysis.headline(res)
    assert table.loc["hybrid"].tolist() == [50, 47, 97]
    assert table.loc["baseline"].tolist() == [45, 44, 89]
    assert table.loc["full", "N + O"] == 102


def test_sign_tests(res):
    table = analysis.sign_tests(res)
    assert table.loc["N + O"].tolist()[:2] == [15, 7]
    assert table.loc["N + O", "p (sign test)"] == 0.134


def test_by_type_counts_every_blind_question(res):
    table = analysis.by_type(res)
    assert table.questions.sum() == 114
    assert table.loc["value before a change", "hybrid"] == 86


def test_set_m_and_short_sets(res):
    m = analysis.set_m_steps(res)
    assert m.loc["blind run", "smart"] == 36 and m.loc["hybrid added", "hybrid"] == 50
    short = analysis.short_sets(res)
    assert set(short.index) == set("ABCDEFGHIJL")


def test_development_map_covers_the_regression_runs(res):
    table = analysis.development_map(res)
    assert list(table.columns) == analysis.REGRESSION_RUNS
    assert table.loc["G"].iloc[0] == pytest.approx(-22, abs=0.5)
    assert table.loc["B"].min() == pytest.approx(33, abs=0.5)


def test_blind_share_lists_every_blind_run(res):
    table = analysis.blind_share(res)
    assert len(table) == 10
    assert table.loc["Set N", "hybrid"] == pytest.approx(87.7, abs=0.1)
    assert table.loc["Set O", "full"] == pytest.approx(91.2, abs=0.1)
