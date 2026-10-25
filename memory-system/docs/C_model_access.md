# C. Model access (talking to Ollama)

How the project code reaches the AI models and the database: three small files that every other module depends on. Nothing here decides *what* memory does. It only provides the plumbing and the tuning knobs.

| File | Job |
|---|---|
| `src/memory_system/llm.py` | The only place that talks to Ollama: embeddings, chat, streaming chat, structured JSON output |
| `src/memory_system/config.py` | Loads settings from `.env` and holds every tunable number |
| `src/memory_system/db.py` | One shared, pooled connection to Postgres with the vector type enabled |

---

## 1. Big picture

```
 extract.py ──────────────▶ chat_structured() ─┐
 manager.py, conflicts.py ─▶ embed() ──────────┤
 retrieve.py ─────────────▶ embed() ───────────┼──▶ llm.py ──▶ Ollama (localhost:11434)
 scripts/chat.py ─────────▶ chat_stream() ─────┤                 ├─ llama3.1:8b
 scripts/evaluate.py ─────▶ chat() ────────────┘                 └─ nomic-embed-text

 manager.py, conflicts.py, retrieve.py ──▶ get_pool() ──▶ db.py ──▶ Postgres (memory_db)

 every module ──▶ config.py ──▶ .env
```

Design rule: **no other file imports `ollama` directly.**  
Everything goes through `llm.py`, so swapping Ollama for another provider later means editing one file.

---

## 2. `llm.py`: function reference

| Function | Signature | Returns | Used by |
|---|---|---|---|
| `embed` | `embed(text: str)` | numpy array, 768 floats (float32) | `manager.py` (message), `conflicts.py` (new fact), `retrieve.py` (query) |
| `chat` | `chat(messages, temperature=0.3)` | the full reply as a string | `scripts/evaluate.py` |
| `chat_stream` | `chat_stream(messages, temperature=0.3)` | an iterator that yields the reply piece by piece | `scripts/chat.py` |
| `chat_structured` | `chat_structured(system, user, schema)` | an instance of the pydantic class you pass in | `extract.py` |

### 2.1 `embed`

Turns text into a list of 768 numbers that represent its meaning. Two texts with similar meaning get vectors that point in similar directions. It calls the embedding model (`EMBED_MODEL`) and converts the result to a float32 numpy array, which is the format the pgvector Python adapter accepts for database parameters.

### 2.2 `chat`

Sends a list of messages to the chat model and waits for the complete answer. Messages follow the standard format:

```python
[
  {"role": "system",    "content": "You are a helpful assistant."},
  {"role": "user",      "content": "Hi"},
  {"role": "assistant", "content": "Hello!"},
  {"role": "user",      "content": "What's 2+2?"},
]
```

### 2.3 `chat_stream`

Same as `chat`, but yields text as the model generates it, so the terminal shows words appearing live instead of a long pause. It is a generator: the caller loops over it and prints each piece.

### 2.4 `chat_structured`

Forces the model to answer in a fixed JSON shape and returns it as a validated Python object.  
This is what makes small local models usable for extraction. It is explained in detail in section 5.

The function is declared with the Python 3.12 generic syntax `chat_structured[T: BaseModel]`, meaning "give me a pydantic class `T`, I return an instance of `T`". This syntax is the reason the project needs Python 3.12 or newer.

---

## 3. How Ollama is called

| Item | Value |
|---|---|
| Server address | `http://localhost:11434` (the Python client's default; override with the `OLLAMA_HOST` environment variable) |
| Embedding call | `ollama.embed(model=..., input=...)` |
| Chat call | `ollama.chat(model=..., messages=[...], options={...})` |
| Streaming | the same chat call with `stream=True` |
| Structured output | the same chat call with `format=<JSON schema>` |

Parameters that matter:

| Parameter | What it does |
|---|---|
| `model` | Which downloaded model to use (`CHAT_MODEL` or `EMBED_MODEL` from `.env`). |
| `messages` | The conversation, as above. |
| `options["temperature"]` | Randomness. 0 gives the most predictable output, higher gives more varied output. |
| `stream` | `True` returns pieces as they are generated. |
| `format` | A JSON schema the output must follow. |

First-call behaviour: Ollama loads a model into memory on first use, so the first request after a pause is slower.  
It unloads idle models after a few minutes by default.

Context length: Ollama applies its own default context window, which may be smaller than the model's maximum.  
Prompts longer than the window can be cut off. Check with `ollama show llama3.1:8b`, and if you ever need more, pass `options={"num_ctx": ...}`.

---

## 4. Embeddings in depth

### 4.1 What they are used for

| Where | What is embedded | Why |
|---|---|---|
| `manager.py` | Every user message | Stored in `messages.embedding`, used by baseline retrieval |
| `conflicts.py` | Each new fact, as text like `lives in: Milan` | Stored in `facts.embedding`, used by smart retrieval |
| `retrieve.py` | The user's current question | Compared with stored vectors to find related memories |

### 4.2 Distance and similarity

pgvector's `<=>` operator returns **cosine distance** (0 means identical direction, larger means less related).  
The code converts it to similarity with `similarity = 1 - distance`.

With `nomic-embed-text`, similarities are compressed into a narrow band.  
In your tests, related text scored around 0.5 to 0.6 and unrelated text around 0.4.  
That is why `retrieve.py` rescales raw similarity using `SIM_FLOOR` and `SIM_CEIL` from `config.py`.

### 4.3 The type bridge between Python and Postgres

1. `embed()` returns a numpy float32 array.
2. `db.py` registers the `vector` type on every connection (`register_vector`).
3. psycopg then sends the numpy array to Postgres as a `vector` value, and reads `vector` columns back as numpy arrays.

If you pass a plain Python list instead of a numpy array, psycopg treats it as a normal array and the query fails.  
That is why `embed()` always returns numpy.

### 4.4 Rules to remember

- **One embedding model per database.** Vectors from different models live in different spaces, so mixing them makes distances meaningless. Changing `EMBED_MODEL` means re-embedding everything.
- **Dimension must match the schema.** `nomic-embed-text` gives 768, and the tables declare `vector(768)`.
- **Task prefixes (untested idea).** The `nomic-embed-text` documentation recommends prefixes such as `search_query:` for questions and `search_document:` for stored text. This project does not use them. Testing them is a cheap way to improve retrieval similarity.

---

## 5. Structured output in depth

Small models often ignore "reply in JSON" instructions or wrap the JSON in chatter.

`chat_structured` avoids this in three steps:

```
1. A pydantic class describes the shape you want:
       class ExtractionResult(BaseModel):
           facts: list[ExtractedFact]

2. Its JSON schema is sent to Ollama in the `format` parameter.
   Ollama constrains generation so the output must match the schema.

3. The reply is parsed with model_validate_json().
   You get a real Python object, or a clear error if it is invalid.
```

Why this matters here:

- **Reliability.** The extractor always returns parseable JSON, even with an 8B model.
- **Validation.** pydantic checks types, so a missing or mistyped field fails loudly instead of corrupting memory.
- **Temperature 0.** Extraction should be repeatable, so this function always uses temperature 0.

What the schema does **not** guarantee: that the *content* is right. It guarantees the shape.  
The model can still choose the wrong relation or miss a fact.   
That is why `extract.py` additionally drops any relation that is not in `relation_types`.

Minimal example:

```python
from pydantic import BaseModel
from memory_system.llm import chat_structured

class Color(BaseModel):
    name: str

print(chat_structured("Return the colour mentioned.", "The sky is blue.", Color))
# Color(name='blue')
```

---

## 6. Temperature settings used in the project

| Where | Temperature | Reason |
|---|---|---|
| Fact extraction (`chat_structured`) | 0 (fixed) | Repeatable, no creativity wanted |
| Evaluation answers (`evaluate.py`) | 0 | So differences between modes come from memory, not randomness |
| Interactive chat (`chat`, `chat_stream` default) | 0.3 | Slightly natural-sounding but still fairly steady |

---

## 7. `config.py` reference

`config.py` calls `load_dotenv()`, which reads `.env` (`DATABASE_URL` required; `CHAT_MODEL`, `EMBED_MODEL` and `ROUTING_TOP_N` optional), then exposes constants for the rest of the code. Each setting has a one-line explanation in the file itself. Write-path settings (`DEFAULT_IMPORTANCE`, `DUPLICATE_SIMILARITY`) are used in D; retrieval settings in E, section 3.

---

## 8. `db.py`: the connection pool

```python
_pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=5, configure=register_vector, open=True)
```

| Part | Meaning |
|---|---|
| Connection pool | A small set of ready-made database connections reused across calls, instead of opening a new one each time. |
| `min_size=1`, `max_size=5` | Keep at least 1 open, never more than 5. Plenty for a single-user prototype. |
| `configure=register_vector` | Runs on every new connection so Postgres vectors map to numpy arrays. |
| Lazy creation | `get_pool()` builds the pool on first use and returns the same one afterwards. Importing the module costs nothing. |

Typical use:

```python
with get_pool().connection() as conn:
    conn.execute("...")
# leaving the block commits; an exception inside rolls everything back
```

That commit-or-rollback behaviour is important for the write path: a message, its facts, and their events either all get saved, or none do.

---

## 9. Cost per interaction

How many model calls one chat turn triggers in smart mode:

| Step | Calls |
|---|---|
| Before answering: embed the question for retrieval | 1 embedding |
| Answer | 1 chat (streamed) |
| After answering: embed the message for storage | 1 embedding |
| After answering: extract facts | 1 structured chat |
| After answering: each new (non-duplicate) fact | 1 embedding each |

So a typical turn is 3 embeddings or fewer, plus 2 chat calls. The chat calls dominate the time. Extraction uses the same 8B model as the answer, so each message costs roughly two model generations.

---

## 10. Testing each piece from the shell

Run these from `memory-system/` to check one layer at a time.

```bash
# Embeddings: expect (768,) float32
poetry run python -c "from memory_system.llm import embed; v = embed('hello'); print(v.shape, v.dtype)"

# Chat
poetry run python -c "from memory_system.llm import chat; print(chat([{'role':'user','content':'Say hi in 3 words'}]))"

# Database connection with the vector type registered
poetry run python -c "from memory_system.db import get_pool; c = get_pool().connection().__enter__(); print(c.execute('SELECT 1').fetchone())"

# Settings loaded from .env
poetry run python -c "from memory_system import config; print(config.CHAT_MODEL, config.EMBED_MODEL, config.DATABASE_URL)"
```

---

## 11. Swapping models

### Chat model (easy)

1. `ollama pull <new-model>`
2. Edit `CHAT_MODEL` in `.env`.
3. Re-run `scripts/demo_ingest.py` and check the extraction output is still correct: valid facts, right relations, no invented ones.

Existing data is unaffected, because no stored vector depends on the chat model.

### Embedding model (disruptive)

1. `ollama pull <new-embedding-model>`
2. Find its dimension (`len(embed("x"))` after changing `.env`).
3. If it differs from 768, change every `vector(768)` in `schema.sql`.
4. Rebuild the database and re-embed all stored messages and facts. No re-embedding script exists yet, so the simplest route for a prototype is to wipe the data and re-ingest.
5. Re-tune `MIN_RELEVANCE`, `RELATIVE_WINDOW`, `SIM_FLOOR` and `SIM_CEIL`, since each model has its own similarity range.

---

## 12. Errors and troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Connection error to `localhost:11434` | Ollama is not running | `brew services start ollama` |
| `ResponseError` saying a model is not found | Model name in `.env` is not pulled | `ollama pull <name>`, check `ollama list` |
| `KeyError: 'DATABASE_URL'` | `.env` missing or in the wrong folder | Put `.env` inside `memory-system/` |
| `ModuleNotFoundError: memory_system` | Package not registered | `poetry install`, run through `poetry run` |
| pydantic `ValidationError` in extraction | Model returned JSON that does not fit the schema | Re-run; if frequent, simplify the prompt or try a bigger model |
| Database error mentioning `vector` or wrong dimensions | Embedding size does not match the schema | Match `vector(N)` to the model's output size |
| Very slow first answer | Model loading | Normal; `ollama ps` shows what is loaded |
| Slow every time | Model too big for the RAM, or running on CPU | `ollama ps`; try a smaller model |

---

## 13. Design decisions

| Decision | Reason |
|---|---|
| **One wrapper file for all model calls** | A single place to change provider, add logging, retries or caching later. |
| **Settings in `.env` plus `config.py`** | Switch models without editing code, and keep tunable numbers together. |
| **Lazy connection pool** | Importing modules never opens a database connection, which keeps scripts and tests simple. |
| **Structured output validated with pydantic** | The only dependable way to get usable facts from a small local model. |
| **Temperature 0 for extraction and comparisons** | Repeatability, so experiments are fair. |
| **numpy float32 vectors** | The format pgvector's Python adapter expects. |
| **Importance and weights in config, not in the database** | Easy to tune and re-run experiments without migrations. |

---

## 14. Known gaps

| Gap | Impact |
|---|---|
| No error handling, retries or timeouts | If Ollama is down or returns bad JSON, the script stops with a traceback. |
| Embedding size is never checked | A model or schema mismatch only shows up as a database error later. |
| No caching or batching of embeddings | In `chat.py` the same message is embedded twice per turn (once for recall, once for storage). `ollama.embed` accepts a list, so batching is possible. |
| Database transaction stays open during extraction | `ingest_user_message` holds the transaction while the LLM runs. It keeps the write atomic, but if extraction fails the message is not saved either. |
| Extraction sees only one message | No surrounding context, so replies like "yes, that's right" yield nothing. |
| No token or context budgeting | Fine for today's short prompts, but needed once summaries and long histories exist. |
| Synchronous only | One call at a time, which is fine for a single user. |
| Prompts live elsewhere | Extraction prompt is in `extract.py`, answer prompt in `assistant.py`, not in `llm.py`. |
| Embedding prefixes | Tested, no clear gain (`docs/findings.md`). |
