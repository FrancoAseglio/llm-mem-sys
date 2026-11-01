# LLM long-term memory system

Prototype long-term memory for an LLM assistant, running fully locally.

- **Write path**: each user message is stored, and a local LLM extracts structured facts
  (`lives_in = Milan`, `allergic_to = peanuts`). New values supersede old ones for
  single-valued relations, so stale facts never reach the prompt.
- **Read path**: facts pass a relevance gate (similarity floor, relative window,
  relation routing) and are then ranked. Often nothing passes, so the prompt stays clean.
- **Baseline**: plain top-k vector search over past messages, for comparison.

Stack: Python 3.12 + Poetry, Postgres 17 + pgvector + pg_trgm, Ollama
(`llama3.1:8b` for chat and extraction, `nomic-embed-text` for embeddings).

## Setup

```bash
# Python
poetry install

# Postgres (macOS / Homebrew)
brew install postgresql@17 pgvector
brew services start postgresql@17
createdb memory_db
psql memory_db -f db/schema.sql         # fresh DB; creates the vector and pg_trgm extensions

# Ollama
brew install ollama
brew services start ollama
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

Create `.env` in the repository root (copy `.env.example`):

```
DATABASE_URL=postgresql://<user>@localhost:5432/memory_db
CHAT_MODEL=llama3.1:8b
EMBED_MODEL=nomic-embed-text
```

Check everything is wired up:

```bash
poetry run python scripts/smoke_test.py
```

## Evaluate

```bash
# ingest the scenarios (backdated messages) and run everything, including LLM answers
poetry run python -m evaluation.run --set A

# retrieval only, on already ingested data (seconds, deterministic)
poetry run python -m evaluation.run --set A B C D E F --retrieval-only --no-ingest

# why was each fact kept or dropped?
poetry run python scripts/inspect_scores.py --scenario b_stale_flood
```

Results are also written to `eval_results.json`; `make eval` adds a run to the tables in `results/`. All scenario sets (A to O) have been seen,
so they cannot validate further tuning; a change needs a new set written beforehand.
The status of each set is the `label` in its file under `evaluation/scenarios/sets/`.

`make help` lists shortcuts (`make db`, `make chat`, `make test`, `make format`, `make scenarios`, `make inspect SCENARIO=dislike_noise`, `make quick`, `make eval SET=I RUN=id PHASE=development`, ...); the evaluation caches deterministic model calls in `.cache/` so repeated runs take seconds (`docs/architecture/02_setup.md`, "Keeping the Mac cool").

Tests (`tests/` only; the DB tests need the Postgres database from `.env`):

```bash
poetry run pytest -q
```

Other script: `scripts/chat.py` (interactive chat, `/mode smart|baseline|none`, `/facts`).

## Layout

| Path | What |
|---|---|
| `src/memory_system/` | the memory system: `core/` (config, database, model calls), `write/` (extraction and conflict rules), `read/` (retrieval: smart, hybrid, baseline), `summaries/` (episode notes), `assistant.py` (prompt building) |
| `evaluation/` | how the system is measured: `run.py` (question sets), `run_sessions.py` (set K), `metrics.py`, `report.py`, `export.py` (adds a run to `results/`), `analysis.py` and `charts.py` (the tables and charts of the results notebook), `scenarios/` (test sets A to O, as JSON) |
| `scripts/` | developer tools: `chat.py`, `inspect_scores.py`, `list_scenarios.py`, `smoke_test.py` |
| `tests/` | mirrors the package: `core/`, `write/`, `read/`, `summaries/`, `evaluation/`, plus `dashboard/`; the pure tests need no services, the rest need Postgres |
| `db/schema.sql` | full schema for a fresh database; after a schema change, drop and recreate the database from it |
| `results/` | every evaluation run as CSV tables, with a data dictionary |
| `notebooks/results.ipynb` | the results told in eight charts; the code is in `evaluation/analysis.py` and `evaluation/charts.py` (`make notebook`) |
| `dashboard/` | local web dashboard (`make dashboard`, http://localhost:8000); its landing page explains it. **Results**: every question of a run, filtered by set and question type, with a column per mode that you can show or hide, and each mode's memory lines and answer side by side (needs only `results/`). **Inspector**: a stored user's current and outdated facts and timelines, and a new question answered by each mode, read-only (needs Postgres and Ollama running: `brew services start postgresql@17` and `brew services start ollama`; the page shows the state of both). `data.py` and `memory.py` (the data of each page), `routes/` (one module per page: home, results, inspector), `templates/`, `static/`; needs `poetry install --with dashboard` |
| `docs/` | documentation: `architecture/` (01 to 07), `evaluation/` (08 to 10), `predictions/`, `history.md`; start at [`docs/README.md`](docs/README.md) |
| `report/` | the project report, its figures (PDFs saved by `make figures`) and the original proposal |
