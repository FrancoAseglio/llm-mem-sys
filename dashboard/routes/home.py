"""The landing page: what the dashboard is for, what each page and mode is, and a few
ready-made views of the results to start from (with their live question counts)."""

from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from dashboard import data
from dashboard.templating import templates

router = APIRouter()

# (title, what it shows, filters). Runs or choices missing from the data are skipped.
STARTING_POINTS = [
    (
        "The headline run",
        "Blind set N, every question and every mode.",
        data.Filters(run="N_full"),
    ),
    (
        "Hybrid against the baseline",
        "Blind set O, the two columns side by side.",
        data.Filters(run="O_full", modes=("baseline", "hybrid")),
    ),
    (
        "Values before a change",
        "Blind set N, questions about the past.",
        data.Filters(run="N_full", qtype="past"),
    ),
    (
        "Plans that changed",
        "Blind set O, plans whose date or companion moved.",
        data.Filters(run="O_full", qtype="plan"),
    ),
    (
        "Every short set, A to J",
        "The last full re-run of the short sets.",
        data.Filters(run="A_to_J_change_rule_1b"),
    ),
    (
        "Facts only against raw messages",
        "Blind set N: smart and the baseline side by side.",
        data.Filters(run="N_full", modes=("baseline", "smart")),
    ),
]

MODE_TEXT = {
    "none": "no memory at all; a floor for comparison.",
    "baseline": "the four past messages closest to the question \nuses plain vector search.",
    "smart": "extracted facts over a relevance gate, plus episode notes; \nno raw "
    "messages.",
    "hybrid": "the final design: the best facts first, then the baseline's messages, with "
    "outdated ones marked as such.",
    "full": "the user's whole history in the prompt; \na reference ceiling, not a design.",
}


def starting_points() -> list[dict]:
    all_runs = data.runs()
    points = []
    for title, text, f in STARTING_POINTS:
        if f.run not in all_runs or data.clean(f, all_runs) != f:
            continue
        points.append(
            {
                "title": title,
                "text": text,
                "href": f"/results?{urlencode(f.query())}",
                "count": len(data.select(all_runs[f.run], f)),
            }
        )
    return points


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    all_runs = data.runs()
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "points": starting_points(),
            "mode_text": MODE_TEXT,
            "run_count": len(all_runs),
            "question_count": sum(len(r.questions) for r in all_runs.values()),
        },
    )
