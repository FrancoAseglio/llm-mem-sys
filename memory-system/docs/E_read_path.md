# E. Read path (using memory when answering)

Everything that happens between "the user asks something" and "the model answers with memory in its prompt". The write path (category D) builds the memory. The read path decides which small part of it the model gets to see.

| File | Job |
|---|---|
| `src/memory_system/retrieve.py` | Smart retrieval over facts (gate, then rank), plus the plain vector baseline over messages |
| `src/memory_system/assistant.py` | Formats the chosen memories as text and builds the final prompt |

Used by `scripts/chat.py` (interactive), `scripts/evaluate.py` (measurement) and `scripts/inspect_scores.py` (per-fact breakdown).

---

## 1. The flow at a glance

```
 user question: "Any ideas for a quick snack?"
        │
        ▼
 assistant.recall(mode, user, question)
        │
        ├─ mode = smart ───▶ retrieve.retrieve()          reads: facts (active only)
        ├─ mode = baseline ─▶ retrieve.retrieve_baseline() reads: messages (user role)
        └─ mode = none ────▶ nothing
        │
        ▼
 list of memory lines  ["Allergic to: peanuts (since 2026-03-02)"]
        │
        ▼
 assistant.build_messages(mode, lines, history, question)
        │
        ▼
 [system prompt with memory] + [recent chat history] + [question]
        │
        ▼
 chat model (Ollama)  ──▶  answer
```

Retrieval happens **before** the model answers. Learning from the same message (write path) happens **after**, so the question never retrieves itself.

---

## 2. The three modes

| Mode | Memory source | What reaches the prompt |
|---|---|---|
| `smart` | `facts` table, only `status = 'active'` | Only facts that pass the relevance gate, at most `k`, as short lines. Often zero or one. |
| `baseline` | `messages` table, role `user` | The top `k` most similar past messages, whatever they are |
| `none` | nothing | No memory block at all |

`baseline` imitates the common "vector memory" approach, so it is the control group. `none` shows what the model does with no help.

---

## 3. `retrieve.py`: smart retrieval

Smart retrieval has two separate jobs:

1. **Gate**: decide *whether* a fact is relevant at all. Uses raw similarity and relation routing only.
2. **Rank**: among facts that passed, decide the *order* and which `k` survive. Uses a blended score.

Importance, recency and usage never let an irrelevant fact in. They only order the relevant ones.

### 3.1 Functions

| Function | Purpose |
|---|---|
| `score_facts(user_id, query)` | Embed the query, load every active fact with its raw similarity, compute the ranking score and the relation rank. Read-only. |
| `relation_ranks(q)` | Rank all relation types by similarity between the question and the relation's routing text. |
| `select_memories(scored, k)` | Apply the gate, return `(pinned, relevant)`. |
| `retrieve(user_id, query, k=4, touch=True)` | `score_facts` + `select_memories`, then reinforcement (3.6). |
| `retrieve_baseline(user_id, query, k=4)` | The control group (section 4). |

### 3.2 The result type

```python
@dataclass
class Memory:
    id: int               # facts.id
    relation: str         # "lives_in"
    value: str            # "Milan"
    since: datetime       # facts.valid_from
    score: float          # ranking score (3.4)
    pinned: bool          # always False: pinning is off (3.5)
    parts: dict           # the five ranking components
    raw_similarity: float # cosine similarity, what the gate uses
    age_days: float       # days since created, repeated or used
    relation_rank: int    # 1 = the relation type that best matches the question
    relation_sim: float   # similarity of the question to that relation type
```

### 3.3 The gate

A fact reaches the prompt only if it passes **all three** parts, applied in this order:

| # | Part | Rule | Setting | Why |
|---|---|---|---|---|
| 1 | Floor | `raw_similarity >= MIN_RELEVANCE` | 0.42 | Lets the system return nothing when nothing is relevant |
| 2 | Window | `raw_similarity >= best - RELATIVE_WINDOW`, where `best` is the top raw similarity among facts that passed the floor | 0.08 | Drops topical neighbours: for a languages question, speaks=Spanish at 0.73 removes lives_in=Rome at 0.50 |
| 3 | Routing | the fact's `relation_rank <= ROUTING_TOP_N` | 2 (env `ROUTING_TOP_N`, 0 = off) | Only facts of the kinds of information the question is about |

Then the survivors are sorted by score and cut to `k`.

Note on the order: the window's `best` is taken *before* routing, so a fact that is later routed out can still set the window for the others.

**Routing text.** Each relation type is embedded once per process as

```
"<name with spaces>: <description>[ <routing_hint>]"     e.g. "allergic to: Allergies Relevant to food, snacks, ..."
```

The question embedding is compared with these 13 vectors (no extra model call: the question is already embedded). Only `allergic_to` and `dislikes` have a `routing_hint`; without them, food questions routed to `likes` and missed allergies. Edit `relation_types` and restart the process to change routing.

Evidence for the three settings: `docs/findings.md`.

### 3.4 Ranking

Each component is between 0 and 1:

| Component | How it is computed |
|---|---|
| `similarity` | raw similarity rescaled: `clamp((raw - SIM_FLOOR) / (SIM_CEIL - SIM_FLOOR))`, with 0.35 and 0.75 |
| `importance` | the fact's stored importance (from `DEFAULT_IMPORTANCE`: allergy 0.95 down to hobby 0.40) |
| `usage` | `min(1, ln(1 + access_count) / ln(11))` |
| `confidence` | the fact's stored confidence (rises with repetition) |
| `recency` | `0.5 ** (age_days / 90)`, age measured from the later of `updated_at` and `last_accessed_at` |

```
score = 0.50 × similarity + 0.25 × importance + 0.10 × usage + 0.10 × confidence + 0.05 × recency
```

Weights come from `WEIGHTS` in `config.py`. Because the gate already decided relevance, recency no longer makes old facts disappear; it only nudges order.

### 3.5 Pinning (off)

`select_memories` still supports pinning (always include facts with importance >= `PIN_IMPORTANCE`), but `PIN_IMPORTANCE = 1.01` is above any possible importance, so `pinned` is always empty. It was switched off because a pinned allergy was injected into every unrelated question. Whether `allergic_to` should instead skip only the floor is an open question (TODO in `retrieve.py`).

### 3.6 Reinforcement ("touch")

When `touch=True` (the default, used by `chat.py`), the returned facts get `access_count + 1` and a fresh `last_accessed_at`, and one `retrieve` row is written to `memory_events` with the query and the returned ids. `evaluate.py` and `inspect_scores.py` never touch, so measuring does not change what is measured.

---

## 4. `retrieve_baseline`: the control group

```sql
SELECT content, created_at, 1 - (embedding <=> query) AS similarity
FROM messages
WHERE user_id = ... AND role = 'user'
ORDER BY embedding <=> query
LIMIT k
```

| Property | Behaviour |
|---|---|
| Source | Raw user messages |
| Filtering | None. It always returns `k` rows if that many messages exist. |
| Staleness | No concept of it. Old and new statements compete equally. |
| Side effects | None |

Because it cannot say "nothing is relevant", chit-chat and outdated statements reach the prompt.

---

## 5. `assistant.py`: building the prompt

| Function | Purpose |
|---|---|
| `format_memory(m)` | `Lives in: Milan (since 2026-10-24)`, using the `LABELS` table (unknown relations fall back to their raw name) |
| `recall(mode, user_id, query, k=4, touch=True)` | Memory lines for the chosen mode |
| `build_messages(mode, memory_lines, history, user_text)` | Full message list for the chat model |

```
[system]    persona + today's date + "no real-time data" + "say you don't know instead of guessing"
            + (if there are memories) header + bullet list + "use only when relevant, don't mention memory"
[history]   previous chat turns (chat.py passes the last six entries)
[user]      the current question
```

Headers: smart mode says "What you currently know about the user:", baseline says "Past messages from the user that may be relevant:" and prefixes each message with its date. If the list is empty, there is no memory block at all.

---

## 6. Inspecting and measuring

| Script | Use |
|---|---|
| `evaluate.py --set A B C --retrieval-only --no-ingest` | Needed facts present, noise present, stale values and lines per question for baseline vs smart, without the LLM |
| `inspect_scores.py --scenario <id>` or `--user U --question Q` | Every fact's raw similarity, score, components and relation rank, and *why* a needed fact was missed (floor, window, routing or `k`) |
| `chat.py` | Talk to it; `/mode smart|baseline|none` switches retrieval, `/facts` lists stored facts |

### Tuning guide

| Symptom (check with `inspect_scores.py`) | Knob |
|---|---|
| Needed fact below the floor | `MIN_RELEVANCE` |
| Needed fact more than the window below the best | `RELATIVE_WINDOW` |
| Needed fact "routed out" | `ROUTING_TOP_N`, or a `routing_hint` on that relation |
| Passed the gate but cut by `k` | `--k` |
| Irrelevant fact in the prompt | the gate part that let it through, never the ranking weights |

Sets A to D are all spent. Any retuning needs a new blind set.

---

## 7. Smart versus baseline

| Aspect | Smart memory | Baseline vector memory |
|---|---|---|
| Source | `facts` (clean statements) | `messages` (raw text) |
| Handles outdated info | Yes, superseded facts are excluded | No |
| Can return "nothing relevant" | Yes (the gate) | No, always returns `k` |
| Depends on extraction quality | Yes, a missed fact is invisible | No, every message is searchable |
| Can answer questions about the past | No (superseded facts hidden) | Partly |
| Model calls per retrieval | 1 embedding (+13 relation embeddings once per process) | 1 embedding |
| Database work | Loads all active facts, scores in Python | One indexed nearest-neighbour query |

---

## 8. Known gaps

| Gap | Impact |
|---|---|
| Floor rests on one example per side | `MIN_RELEVANCE` may not transfer to new phrasings. |
| Routing hints were written after seeing failures | They are a design choice, not validated evidence. |
| Safety facts can be gated out | A loosely worded food question may miss an allergy (open TODO). |
| Superseded facts are invisible | "Where did I live before?" cannot be answered. |
| Summaries are not retrieved | Compression is not built yet. |
| Scoring loads all active facts | Fine for a prototype; the facts HNSW index is unused. |
| Memory text is trusted | A stored value is pasted into the prompt as is. |
| Relation vectors are cached per process | Editing `relation_types` needs a restart. |

---

## 9. Where the read path connects to the rest

| Connects to | How |
|---|---|
| **B. Storage design** | Reads active `facts`, `messages` and `relation_types` (incl. `routing_hint`); writes `access_count`, `last_accessed_at` and `retrieve` events. |
| **C. Model access** | Uses `embed` for queries and relation texts, `chat` or `chat_stream` for answers. Settings live in `config.py`. |
| **D. Write path** | Retrieval can only return what extraction stored and the conflict logic kept current. |
