"""Page 2, the live memory inspector: pick a stored user, see their facts, ask a question and
compare what each mode puts in the prompt and answers.

    /inspector?user=&q=&mode=...   the user's memory; with a question, each mode's prompt lines
    /inspector/answer?user=&q=&mode=   one mode's answer, as an HTML fragment

Every visit first checks the two services: Postgres for the users and facts, Ollama for the
embeddings and the answers. The page shows the prompt lines at once (retrieval needs only the
embedding model) and static/app.js then asks for the answers one mode at a time, so a slow
model never blocks the page. See dashboard/memory.py.
"""

from typing import Annotated

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse

from dashboard import data, memory
from dashboard.templating import templates

router = APIRouter(prefix="/inspector")


def _modes(mode: list[str] | None) -> list[str]:
    chosen = [m for m in data.MODES if m in (mode or [])]
    return chosen or memory.DEFAULT_MODES


@router.get("", response_class=HTMLResponse)
def inspector(
    request: Request,
    user: str = "",
    q: str = "",
    mode: Annotated[list[str] | None, Query()] = None,
):
    checks = memory.status()
    database, model = checks
    context = {
        "checks": checks,
        "model_ok": model.ok,
        "user": user,
        "q": q.strip(),
        "modes": _modes(mode),
        "error": None,
    }
    if database.ok:
        try:
            users = memory.list_users()
            context["user_menu"] = memory.group_users(users)
            if user in {u.id for u in users}:
                context["memory"] = memory.user_memory(user)
                if context["q"] and model.ok:
                    context["prompts"] = [
                        memory.prompt(m, user, context["q"]) for m in context["modes"]
                    ]
            elif user:
                context["error"] = f"No stored user called {user!r}."
        except memory.Unavailable as e:
            context["error"] = str(e)
    return templates.TemplateResponse(request, "inspector/page.html", context)


@router.get("/answer", response_class=HTMLResponse)
def answer(request: Request, user: str, q: str, mode: str):
    context = {"mode": mode, "answer": None, "seconds": None, "error": None}
    if mode not in data.MODES:
        context["error"] = f"Unknown mode {mode!r}."
    else:
        try:
            context["answer"], context["seconds"] = memory.answer(mode, user, q)
        except memory.Unavailable as e:
            context["error"] = str(e)
    return templates.TemplateResponse(request, "inspector/answer.html", context)
