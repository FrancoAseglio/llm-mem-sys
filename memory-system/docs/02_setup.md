# 2. Setup

Everything that must be installed and running before the project works.  
The project runs entirely on one Mac, with no cloud service.

## 1. Overview

```
┌──────────────────────┐        ┌───────────────────────────┐
│  Python app (Poetry) │ ─SQL──▶│ Postgres 17 + pgvector    │
│  src/memory_system   │        │ database: memory_db       │
│  scripts/            │        │ messages, facts, events   │
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

| Piece | Role | Runs as |
|---|---|---|
| Postgres 17 | Storage for messages, facts, summaries and the event log | Background service (Homebrew) |
| `pgvector` | Extension: stores embeddings and searches by meaning | Inside `memory_db` |
| `pg_trgm` | Extension: fuzzy text matching, used to spot duplicate values | Inside `memory_db` |
| Ollama | Runs the language and embedding models locally | Background service (Homebrew) |
| Python 3.12 and Poetry | The application and its dependencies | Virtual environment |

## 2. Install

```bash
# Python (pyenv keeps the macOS system Python untouched; Poetry isolates the project)
brew install pyenv
pyenv install 3.12 && pyenv local 3.12
# install Poetry (https://python-poetry.org/docs/#installation), then:
poetry install

# Postgres
brew install postgresql@17 pgvector
brew services start postgresql@17
createdb memory_db
psql memory_db -f schema.sql        # creates the extensions and all tables

# Ollama
brew install ollama
brew services start ollama
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

Create `.env` in `memory-system/`:

```
DATABASE_URL=postgresql://<user>@localhost:5432/memory_db
CHAT_MODEL=llama3.1:8b
EMBED_MODEL=nomic-embed-text
```

Check that everything is wired up:

```bash
poetry run python scripts/smoke_test.py     # ends with "All good."
poetry run pytest -q                        # 150 passed
```

## 3. Versions used during development

| Tool | Version |
|---|---|
| Postgres | 17.x (Homebrew `postgresql@17`) |
| pgvector extension | 0.8.7 |
| Python | 3.12.15 via pyenv |
| Ollama | 0.40.10 |
| Chat model | `llama3.1:8b`, about 4.9 GB |
| Embedding model | `nomic-embed-text`, about 274 MB, 768 dimensions |

Python libraries are pinned in `poetry.lock`.  
Runtime dependencies: `psycopg` (with binary and pool), `pgvector`, `numpy`, `pydantic`, `ollama`, `python-dotenv`.  
Development: `pytest`, `ruff`.  
Python 3.12 or newer is required because `core/llm.py` uses the generic function syntax `chat_structured[T: BaseModel]`.

## 4. The database

### Starting from a clean database

```bash
dropdb memory_db
createdb memory_db
psql memory_db -f schema.sql
```

There are no migrations.  
After any schema change, recreate the database from `schema.sql` and re-ingest. Deleting a user also deletes their messages, facts, summaries and events (`ON DELETE CASCADE`).

### The embedding dimension is fixed

Embedding columns are `vector(768)` because `nomic-embed-text` produces 768 numbers. A different embedding model with another dimension means changing every `vector(768)` in `schema.sql`, recreating the database, and re-embedding all stored text.

## 5. Ollama

| Model | Type | Job |
|---|---|---|
| `llama3.1:8b` | Chat (language) model | Answers questions and extracts facts as JSON |
| `nomic-embed-text` | Embedding model | Turns text into 768 numbers so similar meanings can be found by distance |

The two cannot replace each other: the chat model generates text, the embedding model only produces vectors.

Ollama serves on `http://localhost:11434`. On Apple Silicon it uses the GPU (Metal). A model loads into memory on first use, so the first request after a pause is slower, and idle models unload after a few minutes. The 8B model needs about 5 to 6 GB of RAM while loaded.

```bash
ollama list                    # models on disk
ollama ps                      # models loaded now, and whether on GPU or CPU
ollama show llama3.1:8b        # parameters, context length, quantization
ollama pull <model>            # download a model
ollama rm <model>              # delete a model
brew services restart ollama   # restart the server
```

## 6. Daily use

Both services start at login because they were started with `brew services`. To free memory:

```bash
brew services stop ollama
brew services stop postgresql@17
```

and to start them again, replace `stop` with `start`. Then run scripts with `poetry run python scripts/<name>.py`.

## 7. Try it: a first chat

A worked example of the chat with long-term memory, run on a fresh user (`demo1`). Start it with:

```bash
poetry run python scripts/chat.py --user demo1
```

After each message the chat prints `[recalled]` (the memory lines put into the prompt, if any), the streamed `assistant>` reply, and `[memory]` (what was stored from your message).

### Session 1: storing and updating

```
you> Hi, I'm Franco and I live in Turin.
assistant> Nice to chat with you again, Franco! I remember you're from Turin. ...
  [memory] ADD name = Franco
  [memory] ADD lives_in = Turin

you> I'm allergic to peanuts.
  [memory] ADD allergic_to = peanuts

you> Actually I moved to Milan.
  [recalled]
    - Lives in: Turin (since 2026-10-25)
assistant> I didn't know you'd moved. You now live in Milan. ...
  [memory] UPDATE lives_in = Milan

you> /facts
  allergic_to   peanuts             active      imp=0.95 conf=0.80
  lives_in      Milan               active      imp=0.70 conf=0.80
  lives_in      Turin               superseded  imp=0.70 conf=0.80
  name          Franco              active      imp=0.80 conf=0.80

you> Which city do I live in?
  [recalled]
    - Lives in: Milan (since 2026-10-25)
assistant> You live in Milan.

you> Can you suggest a quick snack?
  [recalled]
    - Allergic to: peanuts (since 2026-10-25)
assistant> Considering your peanut allergy, I'd suggest a fruit salad or some fresh fruit ...

you> /mode baseline
you> Which city do I live in?
  [recalled]
    - [2026-10-25] "Which city do I live in?"
    - [2026-10-25] "Hi, I'm Franco and I live in Turin."
    - [2026-10-25] "Actually I moved to Milan."
    - [2026-10-25] "I'm allergic to peanuts."
assistant> You live in Milan.
```

What to notice:

| Observation | Why |
|---|---|
| `UPDATE lives_in = Milan`, and Turin is `superseded` in `/facts` | A single-valued relation is replaced, never overwritten; the old row stays as history ([03_storage.md](03_storage.md)) |
| The city question recalls only `Lives in: Milan` | Superseded facts are never read ([06_read_path.md](06_read_path.md)) |
| The snack question recalls only the allergy, not the city or the name | The relevance gate and the allergy safety bypass |
| In `baseline` mode, four raw messages come back, including the stale "live in Turin" and the question itself | This is the noise the evaluation measures. The answer was still right here because the model found "moved to Milan" among them |
| The recall for "Actually I moved to Milan." still shows Turin | Recall runs before the new message is stored, so the assistant answers with what it knew before |
| "Nice to chat with you again ... I remember" in the first reply | A habit of the 8B model, not memory: nothing was recalled yet, and it only repeated your own message |

### Session 2: memory across a restart

In the first session the chat also sends the last 6 turns to the model in every mode, so the model could see "Turin" and "Milan" in the conversation itself.  
To test long-term memory, quit and start again with the same user.  
The history is then empty, and the recalled lines are the only source of knowledge:

```
you> what is my name?
  [recalled]
    - Name: Franco (since 2026-10-25)
assistant> Your name is Franco.

you> where do i used to live?
  [recalled]
    - Lives in: Milan (since 2026-10-25)
assistant> I don't know.

you> where do i live ?
  [recalled]
    - Lives in: Milan (since 2026-10-25)
assistant> You live in Milan.
```

Name and city are answered from memory alone, one recalled line each, after a restart.

The middle question shows a known limit. The fact `lives_in = Turin` is in the database, but it is `superseded`, and retrieval never reads superseded facts. So the system can say where you live now but not where you lived before. This was a design choice (reading old facts for every question would bring back the stale-fact problem) and it is listed in [10_limits_and_roadmap.md](10_limits_and_roadmap.md). A possible fix is to include superseded facts, labelled with their dates, only when the question is about the past ("used to", "before").

To compare with no memory at all, start a new user (`--user demo2`) and ask the same questions: the assistant knows nothing. Use `/mode baseline` to see raw-message recall for the same user.

### Episode notes in the chat

Facts only cover the 13 relation types. Anything else you say (a plan, a purchase, what happened at the weekend) is turned into a one-sentence episode note. After every sixth new message the chat runs the summariser and prints what it kept:

```
  [summary] The user's neighbour Greta is opening a bakery in Gothenburg next spring.
```

Questions and thanks produce no note. Later questions can bring a note into the prompt as `Note from 2026-10-26: ...`. The full session, the checks and the settings are in [07_summaries.md](07_summaries.md). `SUMMARIES=0 poetry run python scripts/chat.py --user me` switches the layer off.

## 8. Look inside the database

The same `demo1` session, seen from the database. Run each line with `psql memory_db -c "..."`.

### The three layers side by side

```bash
psql memory_db -c "select count(*) from messages where user_id='demo1'"
psql memory_db -c "select relation, value, status from facts where user_id='demo1' order by id"
psql memory_db -c "select left(content, 50), created_at from messages where user_id='demo1' order by id"
```

The session produced 9 messages and 4 facts. The 5 extra messages are questions and chit-chat: they stay in `messages` (the raw layer the baseline reads) but produce no fact.

```
  relation   |  value  |   status
-------------+---------+------------
 name        | Franco  | active
 lives_in    | Turin   | superseded
 allergic_to | peanuts | active
 lives_in    | Milan   | active
```

### Episode notes and the unused table

```bash
psql memory_db -c "select content from summaries where user_id='demo1' order by id"
psql memory_db -c "select details from memory_events where user_id='demo1' and event_type='summarize'"
psql memory_db -c "select count(*) from relations"
```

The first two show the notes written for the user and what each summary run kept and dropped; they are empty until the chat has summarised (after six new messages, see section 7 and [07_summaries.md](07_summaries.md)). `relations` returns 0: nothing writes to it yet ([10_limits_and_roadmap.md](10_limits_and_roadmap.md)).

### The structure

```bash
psql memory_db -c "\d facts"
psql memory_db -c "\d relation_types"
```

`\d` is a psql command, so it goes inside the quotes after `-c`. Worth noticing in `\d facts`:

| Part | What it does |
|---|---|
| `status` check | Only `active`, `superseded`, `conflicted` and `archived` can be stored |
| `superseded_by` | Points from an old fact to the one that replaced it |
| `facts_unique_active` | A unique index on active rows: no two active facts with the same user, relation and value (case-insensitive) |
| `facts_relation_fkey` | Every fact's relation must exist in `relation_types` |
| `embedding vector(768)` with an `hnsw` index | Vector search (pgvector) |
| `facts_value_trgm_idx` | Fuzzy text match, used to catch near-duplicates |

### Follow a change

```bash
psql memory_db -c "select id, value, status, superseded_by from facts where user_id='demo1' and relation='lives_in' order by id"
```

```
  id  | value |   status   | superseded_by
------+-------+------------+---------------
 1286 | Turin | superseded |          1288
 1288 | Milan | active     |
```

### The fact types

```bash
psql memory_db -c "select name, cardinality, routing_hint from relation_types order by cardinality, name"
```

`cardinality` is `single` (6 types: a new value replaces the old one) or `multi` (7 types: values accumulate). Only `allergic_to` and `dislikes` have a `routing_hint`.

### The audit log

```bash
psql memory_db -c "select event_type, count(*) from memory_events where user_id='demo1' group by event_type order by 2 desc"
psql memory_db -c "select event_type, fact_id, details from memory_events where user_id='demo1' and event_type <> 'retrieve' order by id"
psql memory_db -c "select details from memory_events where user_id='demo1' and event_type='retrieve' order by id desc limit 1"
```

```
 event_type | fact_id |                          details
------------+---------+------------------------------------------------------------
 add        |    1285 | {"value": "Franco", "relation": "name"}
 add        |    1286 | {"value": "Turin", "relation": "lives_in"}
 add        |    1287 | {"value": "peanuts", "relation": "allergic_to"}
 update     |    1288 | {"new": "Milan", "old": ["Turin"], "relation": "lives_in"}

 {"query": "where do i live ?", "returned": [1288]}
```

Every write decision is recorded with the fact it created, and every question records which fact ids went into the prompt. 

If an answer looks wrong, this is where to trace it. The ids in your own database will differ.

## 9. Everyday commands

| Task | Command |
|---|---|
| Create the database and its tables | `make db` (creates `memory_db` and runs `schema.sql`; safe to re-run) |
| Chat with memory | `make chat` (or `make chat U=franco`; the same as `poetry run python scripts/chat.py --user me`; `/mode smart|baseline|none`, `/facts`, `/quit`) |
| Run the tests | `poetry run pytest -q` |
| Run the evaluation without model answers | `poetry run python scripts/evaluate.py --set A B C D E F --retrieval-only` |
| Re-run on stored data | add `--no-ingest` |
| See all shortcuts | `make help` (see the next section) |
| Fix and check everything before a commit | `make format` (fixes lint, formats, then runs `make check`: ruff check, ruff format check, tests). `make check` alone changes nothing; it is what CI runs on every push |
| List the scenarios and their ids | `make scenarios` (one set: `make scenarios SET=J`) |
| See why each fact was kept or dropped | `make inspect SCENARIO=b_stale_flood` (or `poetry run python scripts/inspect_scores.py --scenario b_stale_flood`) |
| Reset one user | `psql memory_db -c "delete from users where id = 'me'"` |

### Colours

`chat.py` and `evaluate.py` colour their output when printing to a terminal: green for added or active, yellow for updates and conflicts, red for retractions, rejections and wrong answers, magenta for `Earlier:` lines, blue for notes and digests, dim for progress. Colour is off when the output is piped or saved (`| tee file`), when `NO_COLOR=1` is set, or with `--no-color`. The text itself is the same either way. The code is `src/memory_system/core/style.py`.

### Keeping the Mac cool

The heavy part is the 8B chat model. A full run of sets A to I would make about 735 calls to it (extraction, summaries, answers), and most calls repeat the previous run exactly. Three things keep this small:

- **The cache.** `evaluate.py` stores embeddings and temperature-0 replies in `.cache/llm.sqlite` (git-ignored). A second run of an unchanged set reads them from disk and finishes in seconds; the last line says `cache: N hits, M misses`. The chat never uses the cache. Add `--no-cache` for a fresh run, and delete `.cache/` after an `ollama pull` of a new version of a model.
- **Fewer answers.** By default only the baseline and smart answers are generated; `--answers none baseline smart` adds the no-memory ones.
- **The right command for the change.**

| What changed | Run | Cost |
|---|---|---|
| A rule, the gate, ranking or the read path | `make quick` (retrieval only on stored data, all sets) | seconds, no chat model |
| The write path or a prompt | `make set SET=B` (ingest and score one set, retrieval only), then the other sets one at a time | one extraction call per message |
| Something that changes answers | `make answers SET=I` for the set you test, once, at the end of a step | one chat call per question and mode |
| Nothing; a final run from scratch is needed | `make eval SET=I RUN=I_rerun PHASE=development` (ingest, no cache, verbose; adds the run to `results/*.csv` and keeps the printed output in `runs/I_rerun.txt`). `ARGS=--no-ingest` reuses the stored data; switches such as `SUMMARIES=0` go before `make` | everything, no cache |
| Set K, the session set | `make sessions RUN=K_rerun PHASE=regression` | every turn, every mode, no cache |

Also: `make` runs the model at low priority (`nice`), `ollama ps` shows whether it runs fully on the GPU, and the tests (`make test`, about a second) never call a model. Close other heavy apps during a full run, and avoid running two evaluations at once.

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Connection error to `localhost:11434` | Ollama is not running | `brew services start ollama` |
| `ResponseError`: model not found | The model in `.env` is not pulled | `ollama pull <name>`, check `ollama list` |
| `KeyError: 'DATABASE_URL'` | `.env` is missing or in the wrong folder | Put `.env` inside `memory-system/` |
| `ModuleNotFoundError: memory_system` | Package not installed | `poetry install`, and run through `poetry run` |
| `ModuleNotFoundError: dotenv` | Dependency removed by mistake | `poetry add "python-dotenv>=1.2.4,<2.0.0"` |
| Database error mentioning `vector` or dimensions | Embedding size does not match the schema | Match `vector(N)` to the model's output size |
| Chat shows `EXTRACTION_FAILED` | The model returned invalid JSON, or Ollama is down | The message is still saved; check `ollama ps` and send it again |
| Very slow first answer | The model is loading | Normal |
| Slow every time | Model too large for the RAM, or running on CPU | `ollama ps`; try a smaller model |
| A set shows fewer or older facts than expected with `--no-ingest` | The stored evaluation data is stale or incomplete | Re-run without `--no-ingest` to re-ingest |
| `pytest` runs unexpected scripts | `testpaths` is missing | `pyproject.toml` must contain `testpaths = ["tests"]` |
