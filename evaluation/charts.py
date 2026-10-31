"""Interactive charts of the results, one function per chart, for notebooks/results.ipynb.

Each function loads the result tables once (cached), builds its table with
evaluation.analysis and returns a Plotly figure. Charts that print their values on the marks
are static; the others show the numbers on hover:

    from evaluation import charts as ch
    ch.headline()

export_figures() (make figures) saves every chart as a PDF in report/figures/ for the report.
Static export (PDF, and the PNG copy GitHub shows) needs Chrome; if it is missing,
run `poetry run plotly_get_chrome` once.
Needs the optional analysis group (poetry install --with analysis).
"""

from pathlib import Path

import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

from evaluation import analysis

FIGURES = Path(__file__).resolve().parents[1] / "report" / "figures"

# Each mode keeps one fixed colour in every chart (checked for colour-blind separation on all
# pairs and at least 3:1 contrast on white; `full` is a neutral reference). Colour scales are
# used only where colour encodes a quantity: Viridis for shares, a diverging scale for gaps.
COLOR = {
    "baseline": "#2b5ca8",
    "smart": "#c46f22",
    "hybrid": "#139a74",
    "full": "#8a9099",
}
LABEL = {
    "baseline": "baseline (vector search)",
    "smart": "smart (facts only)",
    "hybrid": "hybrid (final design)",
    "full": "full history (reference)",
}
INK, MUTED, GRID = "#1d2127", "#5b616b", "#e6e8eb"
SEQUENTIAL = "Viridis"
# Smart minus baseline: baseline colour (raw messages better), white, smart colour (facts better).
DIVERGING = [[0, COLOR["baseline"]], [0.5, "#ffffff"], [1, COLOR["smart"]]]

pio.templates["memory"] = go.layout.Template(
    layout=dict(
        font=dict(family="Inter, Helvetica, Arial, sans-serif", size=13, color=INK),
        paper_bgcolor="white",
        plot_bgcolor="white",
        colorway=[COLOR[m] for m in analysis.MODES],
        hoverlabel=dict(font_size=13, bgcolor="white"),
        xaxis=dict(gridcolor=GRID, zeroline=False, linecolor="#c9cdd2", ticks=""),
        yaxis=dict(gridcolor=GRID, zeroline=False, linecolor="#c9cdd2", ticks=""),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0),
    )
)
pio.templates.default = "plotly_white+memory"

_CACHE: dict = {}


def results() -> analysis.Results:
    """The result tables, loaded once per session."""
    if "res" not in _CACHE:
        _CACHE["res"] = analysis.load()
    return _CACHE["res"]


def _layout(
    fig: go.Figure,
    title: str,
    subtitle: str,
    source: str,
    height: int,
    bottom: int = 90,
) -> go.Figure:
    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b>",
            subtitle=dict(text=subtitle, font=dict(size=13, color=MUTED)),
            x=0,
            xanchor="left",
            xref="paper",
            y=1,
            yref="container",
            yanchor="top",
            pad=dict(t=20),
            font=dict(size=20),
        ),
        height=height,
        margin=dict(t=125, l=20, r=30, b=bottom),
    )
    fig.add_annotation(
        text=f"Source: {source}",
        xref="paper",
        x=0,
        y=0,
        yref="paper",
        yanchor="bottom",
        yshift=12 - bottom,
        showarrow=False,
        xanchor="left",
        font=dict(size=11, color="#9aa0a8"),
    )
    return fig


# ---- 1. The first design on short histories ----


def short_sets() -> go.Figure:
    """Share answered right per short set: facts only against vector search (dumbbells)."""
    table = analysis.short_sets(results())
    sets = [
        f"Set {s} ({n})" for s, n in zip(table.index, table.questions, strict=True)
    ][::-1]
    rows = table.iloc[::-1]
    fig = go.Figure()
    for y, (b, s) in zip(
        sets, zip(rows.baseline, rows.smart, strict=True), strict=True
    ):
        better = COLOR["smart"] if s > b else COLOR["baseline"] if b > s else "#c9cdd2"
        fig.add_shape(type="line", x0=b, x1=s, y0=y, y1=y, line=dict(color=better, width=5),
                      opacity=0.35, layer="below")  # fmt: skip
    for mode in ("baseline", "smart"):
        fig.add_trace(
            go.Scatter(
                x=rows[mode],
                y=sets,
                mode="markers",
                name=LABEL[mode],
                marker=dict(
                    size=15, color=COLOR[mode], line=dict(color="white", width=2)
                ),
                hovertemplate="<b>%{y}</b><br>"
                + LABEL[mode]
                + ": %{x:.0f}% right<extra></extra>",
            )
        )
    fig.add_hrect(y0=4.5, y1=10.5, fillcolor="#f3f5f7", line_width=0, layer="below")
    fig.add_annotation(text="<i>fact sets</i>", x=50, y=sets[-1], showarrow=False,
                       xanchor="left", font=dict(color=MUTED, size=12))  # fmt: skip
    fig.update_xaxes(title="answered right (%)", range=[48, 104], ticksuffix="%")
    fig.update_yaxes(showgrid=False)
    return _layout(
        fig,
        "Short histories: the first design holds its own",
        "Share answered right per test set (4 to 18 messages per story); "
        "sets A to F were built around the 13 fact types",
        "results/totals.csv, last run of each short set before the hybrid step",
        580,
        bottom=110,
    )


def development_map() -> go.Figure:
    """Smart minus baseline per short set and regression run: a diverging heatmap."""
    table = analysis.development_map(results())
    runs = [c.removeprefix("A_to_").replace("_", " ") for c in table.columns]
    sets = [f"Set {s}" for s in table.index]
    text = table.map(lambda v: "" if v != v else f"{v:+.0f}" if v else "0")
    fig = go.Figure(
        go.Heatmap(
            z=table.values,
            x=runs,
            y=sets,
            text=text.values,
            texttemplate="<b>%{text}</b>",
            textfont=dict(size=12),
            colorscale=DIVERGING,
            zmid=0,
            zmin=-35,
            zmax=35,
            xgap=3,
            ygap=3,
            colorbar=dict(
                title=dict(text="points", side="right"), thickness=14, len=0.8
            ),
            hovertemplate="<b>%{y}</b>, run %{x}<br>smart minus baseline: %{z:+.0f} points"
            "<extra></extra>",
        )
    )
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(showgrid=False, tickangle=-35)
    return _layout(
        fig,
        "Across the development: where facts beat raw messages",
        "Smart minus baseline, in points of share answered right; orange: facts better, "
        "blue: raw messages better; one column per regression run, in order",
        "results/totals.csv, the regression runs over sets A to J",
        620,
        bottom=150,
    )


# ---- 2. The setback on long histories ----


def set_m() -> go.Figure:
    """Right answers on set M at each step of the long-history work."""
    table = analysis.set_m_steps(results())
    fig = go.Figure()
    fig.add_vrect(x0=-0.4, x1=0.4, fillcolor="#f3f5f7", line_width=0, layer="below")
    fig.add_annotation(text="<i>blind</i>", x=0, y=53, showarrow=False,
                       font=dict(color=MUTED, size=12))  # fmt: skip
    for mode in analysis.MODES:
        s = table[mode].dropna()
        fig.add_trace(
            go.Scatter(
                x=list(s.index),
                y=s.values,
                name=LABEL[mode],
                mode="lines+markers+text",
                text=[""] * (len(s) - 1) + [f"<b>{s.iloc[-1]:.0f}</b>"],
                textposition="middle right",
                textfont=dict(color=COLOR[mode]),
                line=dict(
                    color=COLOR[mode],
                    width=3.5,
                    dash="dash" if mode == "full" else None,
                ),
                marker=dict(size=10, line=dict(color="white", width=2)),
                hovertemplate="<b>%{x}</b><br>"
                + LABEL[mode]
                + ": %{y:.0f} of 57<extra></extra>",
            )
        )
    fig.update_yaxes(title="right answers (of 57)", range=[33, 54], dtick=3)
    fig.update_xaxes(showgrid=False)
    fig.update_layout(hovermode="x unified")
    return _layout(
        fig,
        "Long histories: facts alone fall behind",
        "Set M, 57 questions, 92 to 100 messages per user; "
        "only the first run is blind, the rest is development",
        "results/totals.csv, runs M_full to M_fixes",
        500,
    )


# ---- 3. The result on blind tests ----


def headline() -> go.Figure:
    """Right answers per mode on the two blind long-history sets."""
    table = analysis.headline(results())
    groups = ["Set N (57)", "Set O (57)", "N + O (114)"]
    fig = go.Figure()
    for mode in analysis.MODES:
        values = table.loc[mode].values
        bold = mode == "hybrid"
        fig.add_trace(
            go.Bar(
                x=groups,
                y=values,
                name=LABEL[mode],
                marker=dict(color=COLOR[mode], line=dict(width=0)),
                text=[f"<b>{v}</b>" if bold else f"{v}" for v in values],
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>"
                + LABEL[mode]
                + ": %{y} right<extra></extra>",
            )
        )
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.06)
    fig.update_yaxes(title="right answers", range=[0, 114])
    fig.update_xaxes(showgrid=False)
    fig.update_traces(hoverinfo="skip", hovertemplate=None)
    fig.update_layout(hovermode=False)
    return _layout(
        fig,
        "Blind tests: hybrid answers more than vector search",
        "Right answers on the two blind long-history sets; full history shown as a reference",
        "results/totals.csv, runs N_full and O_full",
        520,
    )


def significance() -> go.Figure:
    """The questions where only one of hybrid and the baseline was right, with the sign test."""
    table = analysis.sign_tests(results())
    rows = [f"Set {s}" if len(s) == 1 else s for s in table.index][::-1]
    t = table.iloc[::-1]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=rows,
            x=-t["only baseline"],
            orientation="h",
            name="only the baseline right",
            marker_color=COLOR["baseline"],
            text=[f"<b>{v}</b>" for v in t["only baseline"]],
            textposition="outside",
            customdata=t["only baseline"],
            hovertemplate="<b>%{y}</b><br>only the baseline right: %{customdata}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            y=rows,
            x=t["only hybrid"],
            orientation="h",
            name="only hybrid right",
            marker_color=COLOR["hybrid"],
            text=[f"<b>{v}</b>" for v in t["only hybrid"]],
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>only hybrid right: %{x}<extra></extra>",
        )
    )
    for y, p in zip(rows, t["p (sign test)"], strict=True):
        fig.add_annotation(x=20.5, y=y, text=f"p = {p:.2f}", showarrow=False, xanchor="left",
                           font=dict(color=MUTED))  # fmt: skip
    fig.update_layout(barmode="relative", bargap=0.35)
    fig.update_xaxes(range=[-10, 24], tickvals=[-8, -4, 0, 4, 8, 12, 16],
                     ticktext=["8", "4", "0", "4", "8", "12", "16"],
                     zeroline=True, zerolinecolor="#9aa0a8",
                     title="only the baseline right   |   only hybrid right")  # fmt: skip
    fig.update_yaxes(showgrid=False)
    fig.update_traces(hoverinfo="skip", hovertemplate=None)
    fig.update_layout(hovermode=False)
    return _layout(
        fig,
        "Consistent, not yet significant",
        "Questions answered right by only one of the two modes, and the two-sided sign test",
        "results/answers.csv, runs N_full and O_full",
        420,
        bottom=110,
    )


# ---- 4. Where the facts help, and where they hurt ----


def by_type() -> go.Figure:
    """Share answered right per question type and mode: one row of dots per type."""
    table = analysis.by_type(results())
    types = [
        f"{t}  ({n:.0f})" for t, n in zip(table.index, table.questions, strict=True)
    ]
    fig = go.Figure()
    for i, mode in enumerate(analysis.MODES):
        offset = (i - 1.5) * 0.17
        y = [k + offset for k in range(len(types))]
        fig.add_trace(
            go.Scatter(
                x=table[mode],
                y=y,
                name=LABEL[mode],
                mode="markers",
                marker=dict(
                    size=13,
                    color="white" if mode == "full" else COLOR[mode],
                    line=dict(color=COLOR[mode], width=2.5 if mode == "full" else 1.5),
                ),
                customdata=types,
                hovertemplate="<b>%{customdata}</b><br>"
                + LABEL[mode]
                + ": %{x:.0f}% right<extra></extra>",
            )
        )
        for k, v in enumerate(table[mode]):
            fig.add_shape(type="line", x0=0, x1=v, y0=y[k], y1=y[k], layer="below",
                          line=dict(color=COLOR[mode], width=1.5), opacity=0.35)  # fmt: skip
    for k in range(1, len(types), 2):
        fig.add_hrect(
            y0=k - 0.5, y1=k + 0.5, fillcolor="#f5f6f8", line_width=0, layer="below"
        )
    fig.update_yaxes(tickvals=list(range(len(types))), ticktext=types, autorange="reversed",
                     showgrid=False)  # fmt: skip
    fig.update_xaxes(title="answered right (%)", range=[-2, 104], ticksuffix="%")
    return _layout(
        fig,
        "Where the facts help, and where they hurt",
        "Share answered right per question type, blind sets N and O together "
        "(114 questions; count per type in brackets)",
        "results/answers.csv, question types fixed in the sets' design",
        740,
        bottom=110,
    )


# ---- 5. The cost ----


def cost() -> go.Figure:
    """Outdated answers per mode, and right answers against prompt size."""
    table = analysis.cost(results())
    fig = make_subplots(
        rows=1,
        cols=2,
        horizontal_spacing=0.14,
        subplot_titles=(
            "<b>Answers with an outdated value</b>",
            "<b>Right answers against prompt size</b>",
        ),  # fmt: skip
    )
    modes = analysis.MODES[::-1]
    fig.add_trace(
        go.Bar(
            y=[m for m in modes],
            x=table.loc[modes, "outdated"],
            orientation="h",
            marker_color=[COLOR[m] for m in modes],
            text=[f"<b>{v}</b>" for v in table.loc[modes, "outdated"]],
            textposition="outside",
            showlegend=False,
            hovertemplate="<b>%{y}</b><br>%{x} answers with an outdated value<extra></extra>",
        ),
        row=1,
        col=1,
    )
    for m in analysis.MODES:
        fig.add_trace(
            go.Scatter(
                x=[table.loc[m, "lines"]],
                y=[table.loc[m, "right"]],
                mode="markers+text",
                text=[f"<b>{m}</b>"],
                textposition="middle right" if m != "full" else "middle left",
                textfont=dict(color=COLOR[m]),
                marker=dict(size=18, color=COLOR[m], line=dict(color="white", width=2)),
                showlegend=False,
                hovertemplate=f"<b>{LABEL[m]}</b><br>%{{y}} right of 114<br>"
                "%{x:.1f} memory lines per question<extra></extra>",
            ),
            row=1,
            col=2,
        )
    fig.update_xaxes(title="answers (of 114)", range=[0, 16], row=1, col=1)
    fig.update_yaxes(showgrid=False, ticksuffix="  ", row=1, col=1)
    fig.update_xaxes(title="memory lines per question (log scale)", type="log",
                     range=[0.2, 2.25], tickvals=[2, 5, 10, 20, 50, 100], row=1, col=2)  # fmt: skip
    fig.update_yaxes(title="right answers (of 114)", range=[76, 106], row=1, col=2)
    fig.update_traces(hoverinfo="skip", hovertemplate=None, selector=dict(type="bar"))
    return _layout(
        fig,
        "What it costs: outdated answers and prompt size",
        "Blind sets N and O together; full history reads about 95 lines per question",
        "results/totals.csv, runs N_full and O_full",
        500,
        bottom=110,
    )


# ---- Appendix ----


def blind_runs() -> go.Figure:
    """Share answered right per mode on the first and only run of every blind set."""
    table = analysis.blind_share(results())
    rows = [f"{i}  ({n})" for i, n in zip(table.index, table.questions, strict=True)]
    data = table[analysis.MODES]
    text = data.map(lambda v: "not run" if v != v else f"{v:.0f}%")
    fig = go.Figure(
        go.Heatmap(
            z=data.values,
            x=[LABEL[m] for m in analysis.MODES],
            y=rows,
            text=text.values,
            texttemplate="<b>%{text}</b>",
            textfont=dict(size=13),
            colorscale=SEQUENTIAL,
            zmin=40,
            zmax=100,
            xgap=4,
            ygap=4,
            colorbar=dict(
                title=dict(text="% right", side="right"),
                thickness=14,
                len=0.8,
                ticksuffix="%",
            ),  # fmt: skip
            hovertemplate="<b>%{y}</b><br>%{x}: %{z:.1f}% right<extra></extra>",
        )
    )
    fig.update_xaxes(side="top", showgrid=False)
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_layout(plot_bgcolor="#eef0f2")
    fig.update_traces(hoverinfo="skip", hovertemplate=None)
    fig.update_layout(hovermode=False)
    return _layout(
        fig,
        "Every blind run",
        "Share answered right on the first and only run of each blind set "
        "(questions with an answer check in brackets)",
        "results/totals.csv, runs with phase 'blind'",
        620,
    )


# ---- export ----

FIGURE_FUNCTIONS = {
    "fig1_short_sets": short_sets,
    "fig2_development_map": development_map,
    "fig3_set_m": set_m,
    "fig4_headline": headline,
    "fig5_significance": significance,
    "fig6_by_type": by_type,
    "fig7_cost": cost,
    "fig8_blind_runs": blind_runs,
}


def export_figures(directory: Path = FIGURES) -> None:
    """Save every chart as a PDF for the report, then print one line."""
    directory.mkdir(parents=True, exist_ok=True)
    try:
        for name, draw in FIGURE_FUNCTIONS.items():
            draw().write_image(directory / f"{name}.pdf", width=1000)
    except Exception as error:  # static export needs Chrome
        print(
            f"Figures not saved ({type(error).__name__}): run `poetry run plotly_get_chrome`."
        )
        return
    print(f"Saved {len(FIGURE_FUNCTIONS)} figures to report/figures/ (PDF).")


def use_static_copy() -> None:
    """Also store a PNG of every chart in the notebook, so GitHub shows the figures too
    (GitHub does not run the interactive version). Skipped quietly if Chrome is missing."""
    try:
        go.Figure().to_image(format="png", width=10, height=10)
    except Exception:  # no Chrome for static export: keep the interactive version only
        return
    pio.renderers.default = "plotly_mimetype+notebook_connected+png"
    pio.renderers["png"].width = 1000
