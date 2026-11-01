"""The dashboard application: `make dashboard`, then open http://localhost:8000.

Local only. The landing page (/) explains the rest. Page 1 (/results) browses the result tables and needs nothing else; page 2
(/inspector) reads the live memory and needs Postgres and Ollama. Needs the optional dashboard group (poetry install --with dashboard).
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from dashboard.routes import home, inspector, results

HERE = Path(__file__).resolve().parent


def create_app() -> FastAPI:
    app = FastAPI(title="Memory system dashboard", docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    app.include_router(home.router)
    app.include_router(results.router)
    app.include_router(inspector.router)

    return app


app = create_app()
