# memory-system

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
psql memory_db -f schema.sql            # fresh DB; creates the vector and pg_trgm extensions

# Ollama
brew install ollama
brew services start ollama
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

Create `.env` in this folder (copy `.env.example`):

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
poetry run python scripts/evaluate.py --set A

# retrieval only, on already ingested data (seconds, deterministic)
poetry run python scripts/evaluate.py --set A B C D E F --retrieval-only --no-ingest

# why was each fact kept or dropped?
poetry run python scripts/inspect_scores.py --scenario b_stale_flood
```

Results are also written to `eval_results.json`. All scenario sets (A–F) have been seen,
so they cannot validate further tuning; a change needs a new set written beforehand.
The status of each set is in `scripts/scenarios/__init__.py`.

Tests (`tests/` only; the DB tests need the Postgres database from `.env`):

```bash
poetry run pytest -q
```

Other script: `scripts/chat.py` (interactive chat, `/mode smart|baseline|none`, `/facts`).

## Layout

| Path | What |
|---|---|
| `src/memory_system/` | write path: `extract` (LLM), `actions` (pure rules: grounding, assert/retract checks), `conflicts` (DB decisions), `events` (audit log), `manager`; read path: `retrieve` (gate and ranking), `assistant` (prompt); shared: `llm`, `db`, `config` |
| `scripts/` | `evaluate.py` (+ `eval_metrics.py`, `eval_report.py`), `inspect_scores.py`, `chat.py`, `smoke_test.py`; `scenarios/` holds the test sets A–F |
| `tests/` | `test_actions.py` and `test_gate.py` (pure), `test_write_path.py` and `test_manager.py` (need the DB) |
| `schema.sql` | full schema for a fresh database; after a schema change, drop and recreate the database from it |
| `docs/` | Numbered documentation, start at [`docs/README.md`](docs/README.md) |
