import pytest

pytest.importorskip("plotly")

from evaluation import charts  # noqa: E402


@pytest.mark.parametrize("name", list(charts.FIGURE_FUNCTIONS))
def test_every_chart_builds_a_figure_with_data(name):
    fig = charts.FIGURE_FUNCTIONS[name]()
    assert fig.data
    assert fig.layout.title.text
