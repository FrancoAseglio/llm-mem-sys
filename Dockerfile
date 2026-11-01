# One image for the whole project except Ollama (see docker-compose.yml): the memory system, the
# evaluation, the tests, the results notebook and the dashboard, with every dependency group.
# Also: make, psql (make db, make snapshot-load) and Chromium (the static charts of the notebook
# and make figures).
#
# The repository is mounted over /app when the containers run, so code changes need no rebuild;
# rebuild (make up) only after a change to pyproject.toml or poetry.lock.
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends make postgresql-client chromium \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONPATH=/app/src:/app \
    BROWSER_PATH=/usr/bin/chromium

WORKDIR /app

RUN pip install "poetry==2.5.1"
COPY pyproject.toml poetry.lock ./
RUN poetry install --with dev,analysis,dashboard --no-root --no-interaction

# A copy of the code, so the image also works on its own (without the mount).
COPY . .

EXPOSE 8000
CMD ["uvicorn", "dashboard.app:app", "--host", "0.0.0.0", "--port", "8000"]
