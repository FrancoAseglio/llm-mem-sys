# 4. Models, database access and settings

How the code reaches the local models and the database.
Three small files that every other module depends on.
They decide nothing about memory; they provide the plumbing and the tuning knobs.

| File | Job |
|---|---|
| `src/memory_system/core/llm.py` | The only place that talks to Ollama: embeddings, chat, streaming chat, structured JSON output |
| `src/memory_system/core/config.py` | Loads `.env` and holds every tunable number |
| `src/memory_system/core/db.py` | One shared, pooled connection to Postgres with the vector type enabled |

## 1. Big picture

```
 write/extract.py ───────────────▶ chat_structured() ─┐
 write/manager.py, write/conflicts.py ─▶ embed() ─────┤
 read/retrieve.py ──────────────▶ embed() ────────────┼──▶ core/llm.py ──▶ Ollama (localhost:11434)
 scripts/chat.py ──────────▶ chat_stream() ───────────┤                     ├─ llama3.1:8b
 scripts/evaluate.py ──────▶ chat() ──────────────────┘                     └─ nomic-embed-text

 write/manager.py, write/conflicts.py, core/events.py, read/retrieve.py ─▶ get_pool() ─▶ core/db.py ─▶ Postgres (memory_db)

 every module ──▶ core/config.py ──▶ .env
```

Design rule: no other file imports `ollama` directly. Swapping the provider means editing `core/llm.py` only.

## 2. `core/llm.py`

| Function | Signature | Returns | Used by |
|---|---|---|---|
| `embed` | `embed(text)` | numpy array, 768 floats (float32) | `write/manager.py` (message), `write/conflicts.py` (new fact), `read/retrieve.py` (question, relation texts), `summaries/summarize.py` (note), `summaries/retrieve.py` (question) |
| `chat` | `chat(messages, temperature=0.3)` | the full reply as a string | `scripts/evaluate.py` |
| `enable_cache`, `cache_stats` | `enable_cache(path)`, `cache_stats()` | the disk cache; its (hits, misses) | `scripts/evaluate.py` only |
| `chat_stream` | `chat_stream(messages, temperature=0.3)` | an iterator yielding the reply piece by piece | `scripts/chat.py` |
| `chat_structured` | `chat_structured(system, user, schema)` | an instance of the pydantic class passed in | `write/extract.py`, `summaries/summarize.py` |

- **`embed`** turns text into 768 numbers that represent its meaning; similar meanings point in similar directions.
It returns numpy because the pgvector adapter sends numpy arrays as `vector` values (a list would be treated as an ordinary array and the query would fail).
- **`chat`** takes the standard message list (`system`, `user`, `assistant` roles) and waits for the whole answer.
- **`chat_stream`** is the same but yields text as it is generated, so the terminal shows words appearing live.
- **`chat_structured`** forces the model to answer in a fixed JSON shape and returns a validated Python obj (section 4).
- **Caching.** `embed` remembers its last 512 texts in memory, so a question embedded by the fact, past and note retrievals is sent to the model once. After `enable_cache()` (the evaluation does this; the chat never does), embeddings, temperature-0 `chat` replies and `chat_structured` replies are also stored in `.cache/llm.sqlite`, keyed by the model name and the whole input (`core/cache.py`). Replies at temperature above 0 and streamed replies are never cached.

Ollama calls: `ollama.embed(model, input)`, `ollama.chat(model, messages, options)`, with `stream=True` for streaming and `format=<JSON schema>` for structured output. The server address is `http://localhost:11434` (override with `OLLAMA_HOST`). Ollama applies its own default context window, which may be smaller than the model's maximum; check with `ollama show llama3.1:8b` and pass `options={"num_ctx": ...}` if prompts ever get cut.

## 3. Embeddings

| Where | What is embedded | Why |
|---|---|---|
| `write/manager.py` | Every user message | Stored in `messages.embedding`; baseline retrieval |
| `write/conflicts.py` | Each new fact, as text like `lives in: Milan` | Stored in `facts.embedding`; smart retrieval |
| `read/retrieve.py` | The question; and once per process, the 13 relation texts | Compared with stored vectors and used for routing |

pgvector's `<=>` returns cosine distance (0 means identical direction); the code uses `similarity = 1 - distance`. With `nomic-embed-text`, similarities sit in a narrow band: related text scores around 0.5 to 0.7 and unrelated text around 0.35 to 0.45. That is why the gate works on raw similarity with a floor and a window ([06_read_path.md](06_read_path.md)), and why ranking rescales similarity between `SIM_FLOOR` and `SIM_CEIL`.

Rules to remember:

- **One embedding model per database.** Vectors from different models live in different spaces; mixing them makes distances meaningless.
- **The dimension must match the schema** (768).
- **Task prefixes** (`search_query:` and `search_document:`, recommended by the model's authors) were tested and gave no clear gain ([09_findings.md](09_findings.md)), so they are not used.

## 4. Structured output

Small models often ignore "reply in JSON" or wrap the JSON in chatter. `chat_structured` avoids that:

```
1. A pydantic class describes the shape:
       class ExtractionResult(BaseModel):
           facts: list[ExtractedFact]
2. Its JSON schema goes to Ollama in the `format` parameter, which constrains generation.
3. The reply is parsed with model_validate_json(): a real Python object, or an error.
```

This gives reliable shape and type checking, and always runs at temperature 0 so extraction is repeatable.
It does not guarantee the content is right: the model can still pick the wrong relation or miss a fact.
That is why the write path checks the extraction afterwards ([05_write_path.md](05_write_path.md)).

## 5. `core/db.py`: the connection pool

```python
ConnectionPool(DATABASE_URL, min_size=1, max_size=5, configure=register_vector, open=True)
```

| Part | Meaning |
|---|---|
| Connection pool | A few ready-made connections reused across calls |
| `min_size=1`, `max_size=5` | Plenty for a single-user prototype |
| `configure=register_vector` | Maps Postgres `vector` values to numpy arrays on every connection |
| Lazy creation | `get_pool()` builds the pool on first use; importing the module costs nothing |

```python
with get_pool().connection() as conn:
    conn.execute("...")
# leaving the block commits; an exception inside rolls everything back
```

That behaviour matters for the write path: a message, its facts and their events are saved together or not at all.

## 6. Settings (`core/config.py`)

`core/config.py` calls `load_dotenv()`. `DATABASE_URL` is required; `CHAT_MODEL`, `EMBED_MODEL`, `ROUTING_TOP_N` and `SAFETY_BYPASS` are optional.

| Setting | Value | Used by | Meaning |
|---|---|---|---|
| `DATABASE_URL` | from `.env` | `core/db.py` | Postgres connection string |
| `CHAT_MODEL` | `llama3.1:8b` | `core/llm.py` | Chat and extraction model |
| `EMBED_MODEL` | `nomic-embed-text` | `core/llm.py` | Embedding model (768 dimensions, matches `schema.sql`) |
| `DEFAULT_IMPORTANCE` | allergy 0.95 down to hobby 0.40; others in the file | `write/conflicts.py` | Importance by relation; fallback 0.5 |
| `DUPLICATE_SIMILARITY` | 0.8 | `write/conflicts.py` | Trigram similarity at or above which a value counts as the same fact |
| `MIN_RELEVANCE` | 0.42 | `read/retrieve.py` | Gate: floor on raw similarity |
| `RELATIVE_WINDOW` | 0.08 | `read/retrieve.py` | Gate: distance below the best match still allowed |
| `ROUTING_TOP_N` | 2 (env; 0 = off) | `read/retrieve.py` | Gate: how many best-matching relation types are allowed |
| `SAFETY_RELATIONS` | `{"allergic_to"}` | `read/retrieve.py` | Relations that skip floor and window when routed in |
| `SAFETY_BYPASS` | on (env `SAFETY_BYPASS=0` turns it off) | `read/retrieve.py` | Switch for the allergy pass |
| `WEIGHTS` | similarity 0.50, importance 0.25, usage 0.10, confidence 0.10, recency 0.05 | `read/retrieve.py` | Ranking blend |
| `SIM_FLOOR`, `SIM_CEIL` | 0.35, 0.75 | `read/retrieve.py` | Rescaling range for the similarity component of the ranking |
| `RECENCY_HALF_LIFE_DAYS` | 90 | `read/retrieve.py` | A fact untouched this long counts as half as fresh |
| `PIN_IMPORTANCE` | 1.01 | `read/retrieve.py` | Pinning threshold; above any importance, so pinning is off |
| `LLM_CACHE_PATH` | `.cache/llm.sqlite` | `core/cache.py` | Where the evaluation caches embeddings and temperature-0 replies; the chat never caches |
| `PAST_FACTS` | on (env `PAST_FACTS=0` turns it off) | `read/past_retrieve.py` | Switch for reading replaced facts on past questions |
| `ABOUT_USER` | on (env `ABOUT_USER=0` turns it off) | `write/conflicts.py`, `write/manager.py` | Switch for the check that drops facts the message gives to someone else ([05](05_write_path.md), section 4.3) |
| `PAST_MAX_LINES` | 2 | `read/past_retrieve.py` | Most `Earlier:` lines per question |
| `SUMMARIES` | on (env `SUMMARIES=0` turns it off) | `summaries/summarize.py`, `summaries/retrieve.py` | Switch for the whole summaries layer |
| `NOTE_TAGS` | on (env `NOTE_TAGS=0` turns it off) | `summaries/summarize.py` | Show the notes model the facts stored from each message ([07](07_summaries.md), section 4.2) |
| `NOTE_FACT_WINDOW` | on (env `NOTE_FACT_WINDOW=0` turns it off) | `assistant.py`, `summaries/retrieve.py` | Measure the note window from the best line, facts included ([07](07_summaries.md), section 5) |
| `SUMMARY_MAX_LINES` | 2 | `summaries/retrieve.py` | Most note lines per question |
| `SUMMARY_BATCH` | 12 | `summaries/summarize.py` | Messages per summarising call |
| `SUMMARY_EVERY` | 6 | `scripts/chat.py` | New messages before the chat runs a summary |
| `SUMMARY_FAITHFUL_MIN` | 0.75 | `summaries/rules.py`, `summaries/consolidate.py` | Share of a note's (or a digest's) content words that must appear in its source messages |
| `CONSOLIDATE` | on (env `CONSOLIDATE=0` turns it off) | `summaries/consolidate.py`, `summaries/retrieve.py` | Switch for merging old notes into digests; off also makes retrieval read all notes |
| `CONSOLIDATE_MIN` | 6 | `summaries/consolidate.py` | Old notes a user needs before a consolidation run |
| `CONSOLIDATE_AGE_DAYS` | 30 | `summaries/consolidate.py` | A note is old when its newest source message is older than this |
| `CONSOLIDATE_BATCH` | 40 | `summaries/consolidate.py` | Most old notes sent to the model in one call |

Importance, recency and the other ranking weights live in code, not in the database, so experiments can be tuned and re-run without schema changes.

## 7. Temperatures

| Where | Temperature | Reason |
|---|---|---|
| Fact extraction and summarising (`chat_structured`) | 0, fixed | Repeatable; no creativity wanted |
| Evaluation answers (`evaluate.py`) | 0 | Differences between modes come from memory, not randomness |
| Interactive chat | 0.3 | Natural but steady |

## 8. Cost of one chat turn (smart mode)

| Step | Model calls |
|---|---|
| Recall: embed the question | 1 embedding, shared by the facts, past and note retrievals (plus 13 relation embeddings once per process) |
| Answer | 1 chat, streamed |
| Remember: embed the message | 1 embedding |
| Remember: extract facts | 1 structured chat |
| Remember: each new, non-duplicate fact | 1 embedding each |
| Every 6th new message (chat only): episode notes | 1 structured chat for the batch, plus 1 embedding per note kept |

A typical turn is three embeddings or fewer plus two chat calls, and one more chat call every sixth message. The chat calls dominate the time; extraction uses the same 8B model as the answer.

## 9. Failure behaviour

| Failure | What happens |
|---|---|
| Ollama down or invalid JSON during extraction | `ingest_user_message` keeps the message, logs a `reject` event with the error, and returns `[("extraction_failed", "", "")]`. `chat.py` prints `[memory] EXTRACTION_FAILED`. No facts are written for that message. |
| Ollama down during an embedding or an answer | The call raises; there are no retries or timeouts |
| Database error | The transaction rolls back and the call raises |

## 10. Checking each piece from the shell

```bash
# Embeddings: expect (768,) float32
poetry run python -c "from memory_system.llm import embed; v = embed('hello'); print(v.shape, v.dtype)"
```

```bash
# Chat
poetry run python -c "from memory_system.llm import chat; print(chat([{'role':'user','content':'Say hi in 3 words'}]))"
```

```bash
# Settings loaded from .env
poetry run python -c "from memory_system import config; print(config.CHAT_MODEL, config.EMBED_MODEL, config.DATABASE_URL)"
```

```bash
# Everything at once
poetry run python scripts/smoke_test.py
```

## 11. Swapping models

**Chat model (easy).** `ollama pull <model>`, change `CHAT_MODEL` in `.env`, then re-run the write-path tests and sets D and F of the evaluation (`evaluate.py --set D F --retrieval-only`) to check extraction is still correct: valid facts, right relations, nothing invented. Stored data is unaffected, because no stored vector depends on the chat model. The extraction rules ([05_write_path.md](05_write_path.md)) were built around the slips of an 8B model and may need review.

**Embedding model (disruptive).**

1. `ollama pull <model>` and find its dimension (`len(embed("x"))` after changing `.env`).
2. If it differs from 768, change every `vector(768)` in `schema.sql`.
3. Recreate the database and re-ingest; there is no re-embedding script.
4. Re-tune `MIN_RELEVANCE`, `RELATIVE_WINDOW`, `SIM_FLOOR` and `SIM_CEIL`, since each model has its own similarity range. The test sets are spent, so this needs a new set ([08_evaluation.md](08_evaluation.md)).

## 12. Design decisions

| Decision | Reason |
|---|---|
| One wrapper file for all model calls | One place to change provider or add logging, retries or caching |
| Settings in `.env` plus `core/config.py` | Switch models without editing code; tunable numbers together |
| Lazy connection pool | Importing modules never opens a connection, which keeps tests simple |
| Structured output validated with pydantic | The dependable way to get usable facts from a small local model |
| Temperature 0 for extraction and comparisons | Repeatability, so experiments are fair |
| numpy float32 vectors | The format pgvector's Python adapter expects |

## 13. Known gaps

| Gap | Impact |
|---|---|
| No retries or timeouts on model calls | A stalled Ollama stalls the script |
| Embedding size is never checked | A model or schema mismatch shows up as a database error later |
| No caching or batching of embeddings | `chat.py` embeds the same message twice per turn (recall and storage) |
| The transaction stays open during extraction | Safe for one user; would not scale to many simultaneous users |
| Extraction sees one message only | "Yes, that's right" yields nothing |
| No token or context budget | Fine for short prompts; needed once summaries and long histories exist |
| Synchronous only | One call at a time |
| Prompts live outside `core/llm.py` | The extraction prompt is in `write/extract.py`, the answer prompt in `assistant.py` |
