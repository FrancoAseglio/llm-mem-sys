"""The Jinja2 environment every page shares, with the labels the templates need."""

import re
from pathlib import Path

from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape

from dashboard import data

templates = Jinja2Templates(directory=Path(__file__).resolve().parent / "templates")
templates.env.globals.update(
    MODE_LABELS=data.MODE_LABELS,
    QTYPES=data.QTYPES,
    CHECKS=data.CHECKS,
    GOOD_WHEN_SET=data.GOOD_WHEN_SET,
)


def code_spans(text: str) -> Markup:
    """The text, escaped, with `backticked` parts shown as code (commands in a message)."""
    return Markup(re.sub(r"`([^`]+)`", r"<code>\1</code>", str(escape(text))))


templates.env.filters["code"] = code_spans
