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
# existing DB created before routing hints: psql memory_db -f migrations/001_routing_hint.sql

# Ollama
brew install ollama
brew services start ollama
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

Create `.env` in this folder:

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
poetry run python scripts/evaluate.py --set A B C --retrieval-only --no-ingest

# why was each fact kept or dropped?
poetry run python scripts/inspect_scores.py --scenario b_stale_flood
```

Results are also written to `eval_results.json`. All scenario sets (A–D) have been seen,
so they cannot validate further tuning.

Other scripts: `scripts/chat.py` (interactive chat, `/mode smart|baseline|none`) and
`scripts/demo_ingest.py` (write-path demo).

## Layout

| Path | What |
|---|---|
| `src/memory_system/` | `extract`, `conflicts`, `manager` (write path); `retrieve`, `assistant` (read path); `llm`, `db`, `config` |
| `scripts/` | evaluation, inspection, chat, demo, smoke test; `scenarios.py` holds the test sets |
| `schema.sql` | full schema for a fresh database; `migrations/` only for existing ones |
| `docs/` | A environment, B storage, C model access, D write path, E read path, `findings.md` |
