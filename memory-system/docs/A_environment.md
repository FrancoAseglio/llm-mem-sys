# A. Environment

Everything that has to be installed and running before any project code works.  
This document records what was installed, why, how to check it, and how to fix it when it breaks.

---

## 1. Overview

The project runs entirely on your own Mac, with no cloud services.  
Three pieces cooperate:

```
┌──────────────────────┐        ┌───────────────────────────┐
│  Python app (Poetry) │ ─SQL──▶│ Postgres 17 + pgvector    │
│  src/memory_system   │        │ database: memory_db       │
│  scripts/            │        │ stores facts + messages   │
└──────────┬───────────┘        └───────────────────────────┘
           │ HTTP (localhost:11434)
           ▼
┌──────────────────────┐
│ Ollama               │
│ llama3.1:8b  (chat)  │
│ nomic-embed-text     │
│ (embeddings)         │
└──────────────────────┘
```

| Piece | Role in the project | Runs as |
|---|---|---|
| Postgres 17 | Long-term storage of messages, facts, summaries, event log | Background service (Homebrew) |
| pgvector | Postgres extension that stores embeddings and searches by meaning | Extension inside `memory_db` |
| pg_trgm | Postgres extension for fuzzy text matching (duplicate detection) | Extension inside `memory_db` |
| Ollama | Runs the AI models locally | Background service (Homebrew) |
| Python 3.12 + Poetry | The application code and its dependencies | Virtual environment per project |

---

## 2. Installed versions

| Tool | Version installed |
|---|---|
| Homebrew package: `postgresql@17` | 17.x |
| pgvector (Postgres extension) | 0.8.7 |
| pyenv | 2.8.13 |
| Python | 3.12.15 (via pyenv) |
| Ollama | 0.40.10 (Homebrew; pulled in `mlx` 0.32.4 and `mlx-c` 0.7.0_1 as dependencies) |
| Chat model | `llama3.1:8b` (about 4.9 GB) |
| Embedding model | `nomic-embed-text` (about 274 MB, 768 dimensions) |

Python libraries (resolved by Poetry):

| Library | Version | Used for |
|---|---|---|
| psycopg (+ binary, pool) | 3.3.6 | Talking to Postgres, connection pooling |
| pgvector (Python package) | 0.5.1 | Sending and receiving embeddings through psycopg |
| numpy | 2.5.4 | Holding embedding vectors |
| pydantic | 2.14.1 | Validating the JSON the LLM returns |
| ollama (Python client) | 0.6.3 | Calling chat and embedding models |
| fastapi / uvicorn | 0.162.0 / 0.54.0 | Future API service (not used yet) |
| apscheduler | 3.11.3 | Future background jobs: compression, decay (not used yet) |
| python-dotenv | 1.2.4 | Loading settings from `.env` |

Development-only libraries: pytest 9.1.1, streamlit 1.66.1 (future UI), pandas 3.1.0 and matplotlib 3.11.2 (future evaluation charts), ruff 0.17.2 (code linting).

---

## 3. Postgres and extensions

### 3.1 What was done

```bash
brew install postgresql@17 pgvector
brew services start postgresql@17
createdb memory_db
psql memory_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql memory_db -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
psql memory_db -c "SELECT extversion FROM pg_extension WHERE extname='vector';"   # 0.8.7
```

### 3.2 The embedding dimension rule

Embedding columns are declared as `vector(768)` because `nomic-embed-text` produces 768 numbers per text. **The column size is fixed.**  
If you ever switch to a model with a different dimension (for example 1024 for `mxbai-embed-large` or `bge-m3`), you must change every `vector(768)` in `schema.sql`, recreate the tables, and re-embed all stored text.

### 3.3 Starting from a clean database

If you want to wipe everything and rebuild:

```bash
dropdb memory_db
createdb memory_db
psql memory_db -f schema.sql
```

Deleting a user also deletes their messages, facts, summaries and events, because of `ON DELETE CASCADE` in the schema.

---

## 4. Python environment

### 4.1 Layers and why there are three

| Layer | Tool | Job |
|---|---|---|
| Python versions | **pyenv** | Installs and switches between Python versions without touching the macOS system Python |
| Project environment | **Poetry** | Creates an isolated virtual environment and records exact dependency versions |
| Dependencies | `pyproject.toml` + `poetry.lock` | Declares what the project needs and locks the exact versions |

### 4.2 What was done

```bash
brew install pyenv
pyenv install 3.12 && pyenv local 3.12     # compiles Python 3.12.15 from source (takes minutes)
poetry new memory-system && cd memory-system
poetry env use 3.12
poetry add "psycopg[binary,pool]" pgvector numpy pydantic ollama \
           fastapi "uvicorn[standard]" apscheduler python-dotenv
poetry add --group dev pytest streamlit pandas matplotlib ruff
```

---

## 5. Ollama and the models

### 5.1 What was done

```bash
brew install ollama
brew services start ollama
ollama pull llama3.1:8b
ollama pull nomic-embed-text
ollama run llama3.1:8b "Say hi"       # replied: "Hi! How are you today?"
```

### 5.2 The two models and why two

| Model | Type | Job | Size |
|---|---|---|---|
| `llama3.1:8b` | Chat (language) model | Answers questions and extracts facts as JSON | About 4.9 GB |
| `nomic-embed-text` | Embedding model | Turns text into 768 numbers so similar meanings can be found by distance | About 274 MB |

They are different kinds of model and cannot replace each other:

- The _chat model_ generates text.   
- The _embedding model_ only produces vectors for searching.

### 5.3 How the app talks to Ollama

Ollama runs a local server on `http://localhost:11434`. The Python client calls it:

- `ollama.embed(model=..., input=...)` returns the embedding vector.
- `ollama.chat(model=..., messages=[...])` returns the reply.
- `ollama.chat(..., format=<JSON schema>)` forces structured JSON output, which `extract.py` relies on.

Your machine's native Ollama uses Apple's GPU (Metal), which is why it is fast.  

### 5.4 Everyday commands

```bash
ollama list                    # models downloaded on disk
ollama ps                      # models currently loaded in memory (and CPU/GPU use)
ollama show llama3.1:8b        # details: parameters, context length, quantization
ollama pull <model>            # download another model
ollama rm <model>              # delete a model to free disk space
brew services list             # is ollama started?
brew services restart ollama   # restart the server
```

Models are stored under `~/.ollama/models`.

### 5.5 Memory behaviour

- A model is loaded into RAM the first time it is used, so the first request is slower.
- Ollama unloads an idle model after a few minutes by default.
- On Apple Silicon the model shares memory with macOS and your other apps. The 8B model needs roughly 5 to 6 GB while loaded.
- `ollama ps` shows whether a model is running on the GPU. It should report the GPU, not the CPU.

---

## 6. Daily start and stop

After a reboot, both services start automatically at login because they were started with `brew services`.

To stop them (for example to free RAM):

```bash
brew services stop ollama
brew services stop postgresql@17
```

To start them again:

```bash
brew services start postgresql@17
brew services start ollama
```

Then, from `~/llm/memory-system`, run any script with `poetry run python scripts/<name>.py`.
