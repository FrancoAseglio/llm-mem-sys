"""Page 1, the results browser: the questions of a run, one column per mode.

/results                     the question list of one run, filtered by set and question
                             type; mode=... picks the mode columns shown (all by default)
/results/{run}/{question}    one question: each shown mode's memory lines and answer
"""

from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from dashboard import data
from dashboard.templating import templates

router = APIRouter(prefix="/results")

# Runs are grouped by phase in the run menu, in this order.
PHASES = ["blind", "development", "regression", "ablation", "noise check", "rerun"]

SetParam = Annotated[str, Query(alias="set")]


ModeParam = Annotated[list[str] | None, Query()]


def _filters(run: str, set_: str, qtype: str, mode: list[str] | None) -> data.Filters:
    return data.clean(data.Filters(run, set_, qtype, tuple(mode or ())), data.runs())


def _item_query(f: data.Filters) -> str:
    """The filters for a link to one question: the run is in the path, so it is left out."""
    rest = [(k, v) for k, v in f.query() if k != "run"]
    return f"?{urlencode(rest)}" if rest else ""


def _run_menu(all_runs: dict[str, data.Run]) -> list[tuple[str, list[data.Run]]]:
    groups = {p: [r for r in all_runs.values() if r.phase == p] for p in PHASES}
    other = [r for r in all_runs.values() if r.phase not in PHASES]
    if other:
        groups["other"] = other
    return [(p, rs) for p, rs in groups.items() if rs]


@router.get("", response_class=HTMLResponse)
def question_list(
    request: Request,
    run: str = data.DEFAULT_RUN,
    set_: SetParam = "",
    qtype: str = "",
    mode: ModeParam = None,
):
    f = _filters(run, set_, qtype, mode)
    all_runs = data.runs()
    r = all_runs[f.run]
    questions = data.select(r, f)
    return templates.TemplateResponse(
        request,
        "results/list.html",
        {
            "filters": f,
            "is_default": f == data.Filters(),
            "item_query": _item_query(f),
            "run": r,
            "run_menu": _run_menu(all_runs),
            "shown": data.shown_modes(r, f),
            "qtypes": data.qtypes(r),
            "description": data.describe(r, f, len(questions)),
            "questions": questions,
            "tally": data.tally(questions, r.modes),
        },
    )


@router.get("/{run}/{question_id}", response_class=HTMLResponse)
def question_detail(
    request: Request,
    run: str,
    question_id: int,
    set_: SetParam = "",
    qtype: str = "",
    mode: ModeParam = None,
):
    all_runs = data.runs()
    if run not in all_runs or not 0 <= question_id < len(all_runs[run].questions):
        raise HTTPException(status_code=404, detail="No such question")
    r = all_runs[run]
    q = r.questions[question_id]
    # Previous and next follow the list the user came from (same filters), when q is in it.
    f = _filters(run, set_, qtype, mode)
    ids = [x.id for x in data.select(r, f)]
    at = ids.index(q.id) if q.id in ids else None
    prev_id = ids[at - 1] if at is not None and at > 0 else None
    next_id = ids[at + 1] if at is not None and at + 1 < len(ids) else None
    return templates.TemplateResponse(
        request,
        "results/question.html",
        {
            "list_query": urlencode(f.query()),
            "item_query": _item_query(f),
            "run": r,
            "shown": data.shown_modes(r, f),
            "q": q,
            "position": (at + 1, len(ids)) if at is not None else None,
            "prev_id": prev_id,
            "next_id": next_id,
        },
    )
