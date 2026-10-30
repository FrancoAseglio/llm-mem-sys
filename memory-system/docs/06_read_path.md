# 6. Read path (using memory when answering)

Everything between "the user asks something" and "the model answers with memory in its prompt".  
The write path ([05](05_write_path.md)) builds the memory.  
The read path decides which small part of it the model gets to see.

| File | Job |
|---|---|
| `src/memory_system/read/retrieve.py` | Smart retrieval over facts (gate, then rank) and the plain vector baseline over messages |
| `src/memory_system/read/hybrid.py`, `read/hybrid_rules.py` | The hybrid mode (baseline messages, marked, plus a few facts) and the full reference mode (section 11) |
| `src/memory_system/read/labels.py` | The prompt label of each relation type (`lives_in` → "Lives in") |
| `src/memory_system/assistant.py` | Formats the chosen memories as text and builds the final prompt |

Used by `scripts/chat.py` (interactive), `scripts/evaluate.py` (measurement) and `scripts/inspect_scores.py` (per-fact breakdown).

## 1. The flow at a glance

```
 user question: "Any ideas for a quick snack?"
    │
    ▼
 assistant.recall(mode, user, question)
    │
    ├─ mode = smart ────▶ read/retrieve.retrieve()      reads: facts (active only)
    │                     + read/past_retrieve          reads: replaced facts, past questions only
    │                     + summaries/retrieve          reads: episode notes, in the room left
    ├─ mode = hybrid ───▶ read/hybrid.hybrid_lines()    reads: facts (2 lines at most), messages,
    │                                                          replaced facts (markers, timeline)
    ├─ mode = full ─────▶ read/hybrid.all_messages()    reads: every user message
    ├─ mode = baseline ─▶ retrieve.retrieve_baseline()  reads: messages (user role)
    └─ mode = none ─────▶ nothing
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

For a question about the past, `assistant.recall` first adds replaced facts (section 10). In smart mode it also adds up to two episode-note lines after the fact lines when there is room among the `k` lines ([07_summaries.md](07_summaries.md), section 5).  
The rest of this document describes the facts.

Retrieval happens before the model answers.  
Learning from the same message (write path) happens after, so a question never retrieves itself.

## 2. The three modes

| Mode | Memory source | What reaches the prompt |
|---|---|---|
| `smart` | `facts`, only `status = 'active'` | Only facts that pass the relevance gate, at most `k` (default 4), as short lines. Often zero or one. |
| `baseline` | `messages`, role `user` | The top `k` most similar past messages, whatever they are |
| `hybrid` | `messages` and `facts` | Up to 2 current facts (smart's gate), one timeline line for a past question, then the baseline's `k` messages, each marked when a fact it gave has changed (section 11) |
| `full` | `messages`, role `user` | Every past message, oldest first: a reference ceiling, not a design (section 11) |
| `none` | nothing | No memory block at all |

`baseline` imitates the common "vector memory" approach and is the control group.  
`none` shows what the model does without help.

## 3. Smart retrieval

Two separate jobs:

1. **Gate**: decide whether a fact is relevant at all, using raw similarity and relation routing.
2. **Rank**: among the facts that passed, decide the order and which `k` survive, using a blended score.

Importance, recency and usage never let an irrelevant fact in. They only order the relevant ones.

### 3.1 Functions

| Function | Purpose |
|---|---|
| `score_facts(user_id, query)` | Embed the query, load every active fact with its raw similarity, compute the ranking score and the relation rank. Read-only. |
| `relation_ranks(q)` | Rank all relation types by similarity between the question and each relation's routing text |
| `best_raw(scored)` | Best raw similarity among unpinned facts that pass the floor; the window is measured from it |
| `gate_failure(m, best)` | Why the gate drops a fact: `("floor", gap)`, `("window", gap)`, `("routing", rank)`, or `None` if it passes |
| `select_memories(scored, k)` | Apply the gate, return `(pinned, relevant)` with at most `k` relevant |
| `retrieve(user_id, query, k=4, touch=True)` | `score_facts`, then `select_memories`, then reinforcement (3.6) |
| `retrieve_baseline(user_id, query, k=4)` | The control group (section 4) |

`gate_failure` is the single definition of the gate.  
`select_memories` uses it to choose, and `inspect_scores.py` uses it to explain a miss, so the two cannot drift apart.  
`tests/read/test_gate.py` covers it.

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

A fact reaches the prompt only if it passes all three parts, checked in this order:

| # | Part | Rule | Setting | Why |
|---|---|---|---|---|
| 1 | Floor | `raw_similarity >= MIN_RELEVANCE` | 0.42 | Lets the system return nothing when nothing is relevant |
| 2 | Window | `raw_similarity >= best - RELATIVE_WINDOW`, where `best` is the top raw similarity among facts that passed the floor | 0.08 | Drops topical neighbours: for a languages question, `speaks = Spanish` at 0.73 removes `lives_in = Rome` at 0.50 |
| 3 | Routing | the fact's `relation_rank <= ROUTING_TOP_N` | 2 (env `ROUTING_TOP_N`; 0 = off) | Only facts of the kind of information the question is about |

**Safety bypass.** A fact whose relation is in `SAFETY_RELATIONS` (`allergic_to`) skips the floor and the window when routing ranks its relation in the top `ROUTING_TOP_N`, so an allergy reaches a loosely worded food question. It only applies with routing on, and `SAFETY_BYPASS=0` switches it off. The cost is that an allergy also reaches any question where `allergic_to` routes into the top two, such as a drug allergy on a dinner question.

The survivors are sorted by score and cut to `k`. The window's `best` is taken before routing, so a fact that is later routed out can still set the window for the others.

**Routing text.** Each relation type is embedded once per process as

```
"<name with spaces>: <description>[ <routing_hint>]"    e.g. "allergic to: Allergies Relevant to food, snacks, ..."
```

The question embedding is compared with these 13 vectors (no extra model call).  
Only `allergic_to` and `dislikes` have a `routing_hint`; without, food questions routed to `likes` and missed allergies.  
Editing `relation_types` needs a process restart.  
The evidence for the three settings is in [09_findings.md](09_findings.md).

### 3.4 Ranking

Each component is between 0 and 1:

| Component | How it is computed |
|---|---|
| `similarity` | raw similarity rescaled: `clamp((raw - SIM_FLOOR) / (SIM_CEIL - SIM_FLOOR))`, with 0.35 and 0.75 |
| `importance` | the fact's stored importance (allergy 0.95 down to hobby 0.40) |
| `usage` | `min(1, ln(1 + access_count) / ln(11))` |
| `confidence` | the fact's stored confidence (rises with repetition) |
| `recency` | `0.5 ** (age_days / 90)`, age measured from the later of `updated_at` and `last_accessed_at` |

```
score = 0.50 × similarity + 0.25 × importance + 0.10 × usage + 0.10 × confidence + 0.05 × recency
```

Weights are `WEIGHTS` in `core/config.py`.  
Because the gate already decided relevance, recency no longer makes old facts disappear; it only nudges the order.

### 3.5 Pinning (off)

`select_memories` still supports pinning (always include facts with importance at or above `PIN_IMPORTANCE`), but `PIN_IMPORTANCE = 1.01` is above any importance, so `pinned` is always empty. Pinning was switched off because a pinned allergy was injected into every unrelated question; the routing-gated safety bypass replaced it.

### 3.6 Reinforcement ("touch")

With `touch=True` (the default, used by `chat.py`), the returned facts get `access_count + 1` and a fresh `last_accessed_at`, and one `retrieve` row is written to `memory_events` with the query and the returned ids. `evaluate.py` and `inspect_scores.py` never touch, so measuring does not change what is measured.

## 4. `retrieve_baseline`: the control group

```sql
SELECT content, created_at, 1 - (embedding <=> query) AS similarity
FROM messages  
WHERE user_id = ... AND role = 'user'
ORDER BY embedding <=> query LIMIT k
```

| Property | Behaviour |
|---|---|
| Source | Raw user messages |
| Filtering | None: it always returns `k` rows if that many messages exist |
| Staleness | No concept of it; old and new statements compete equally |
| Side effects | None |

Because it cannot say "nothing is relevant", chit-chat and outdated statements reach the prompt.

## 5. `assistant.py`: building the prompt

| Function | Purpose |
|---|---|
| `format_memory(m)` | `Lives in: Milan (since 2026-10-24)`, using the `LABELS` table (unknown relations fall back to their raw name) |
| `recall(mode, user_id, query, k=4, touch=True)` | Memory lines for the chosen mode; baseline lines are `[date] "message"` |
| `build_messages(mode, memory_lines, history, user_text)` | The full message list for the chat model |

```
[system]    persona + today's date + "no real-time data" + "say you don't know instead of guessing"
            + (if there are memories) header + bullet list + "use only when relevant, don't mention memory"
[history]   previous chat turns (chat.py passes the last six entries)
[user]      the current question
```

Smart mode's header is "What you currently know about the user:";  
baseline's is "Past messages from the user that may be relevant:".  
Hybrid's says that current facts come first, then past messages, and what the two markers mean; full's is "Everything the user has told you, oldest first:".  
With no memory lines there is no memory block at all.

The modes, in the order the evaluation prints them, are `assistant.MODES`.

## 6. Inspecting and tuning

| Script | Use |
|---|---|
| `evaluate.py --set A B C D E F --retrieval-only --no-ingest` | Needed facts present, noise, stale values and lines per question for baseline and smart, without model answers |
| `inspect_scores.py --scenario <id>` or `--user U --question Q` | Every fact's raw similarity, score, components and relation rank, and why a needed fact was missed (floor, window, routing or `k`) |
| `chat.py` | Talk to it; `/mode smart|baseline|none`, `/facts` |

| Symptom (check with `inspect_scores.py`) | Knob |
|---|---|
| Needed fact below the floor | `MIN_RELEVANCE` |
| Needed fact more than the window below the best | `RELATIVE_WINDOW` |
| Needed fact "routed out" | `ROUTING_TOP_N`, or a `routing_hint` on that relation |
| Allergy on an unrelated question | `SAFETY_BYPASS`, `SAFETY_RELATIONS` |
| Passed the gate but cut by `k` | `--k` |
| Irrelevant fact in the prompt | the gate part that let it through, never the ranking weights |

All test sets are spent, so any retuning needs a new blind set ([08_evaluation.md](08_evaluation.md)).

## 7. Smart versus baseline

| Aspect | Smart | Baseline |
|---|---|---|
| Source | `facts` (clean statements) | `messages` (raw text) |
| Handles outdated information | Yes: superseded facts are excluded | No |
| Can return "nothing relevant" | Yes (the gate) | No: always `k` rows |
| Depends on extraction quality | Yes: a missed fact is invisible | No: every message is searchable |
| Can answer about things outside the 13 fact types | Partly: through episode notes ([07](07_summaries.md)), when one was written and passes the gate | Partly |
| Can answer about the past ("where did I live before") | Partly: replaced values, only for questions that ask about the past (section 10) | Partly |
| Model calls per retrieval | 1 embedding (plus 13 relation embeddings once per process) | 1 embedding |
| Database work | Loads all active facts, scores in Python | One indexed nearest-neighbour query |

## 8. Known gaps

| Gap | Impact |
|---|---|
| Routing can veto a strong match | "Which language am I trying to learn?" against `goal = Japanese`: raw similarity 0.70, but `goal` ranks 4th among relation types and is dropped. Found on set E, not fixed |
| An allergy just outside the bypass | `allergic_to = sesame` (raw 0.42) for a food question: `allergic_to` ranked 3rd, so the bypass did not apply and the floor removed it |
| The floor rests on one example per side | `MIN_RELEVANCE` may not transfer to new phrasings |
| Routing hints were written after seeing failures | A design choice, not validated evidence |
| The safety bypass trades noise for recall | Allergies reach any question that routes to `allergic_to`, relevant or not |
| Abstain questions still get lines | A question with no answer in memory can still pull weakly related facts through |
| Superseded facts are read only for past questions | Values archived by a retraction are still invisible (section 10) |
| Episode notes have no routing | They use the floor and window only; a note about plans can match any question about plans ([07](07_summaries.md), section 9); their window is measured from the best line, facts included ([07](07_summaries.md), section 5) |
| Scoring loads all active facts | Fine for a prototype; the facts HNSW index is unused |
| Memory text is trusted | A stored value is pasted into the prompt as is |
| Relation vectors are cached per process | Editing `relation_types` needs a restart |

Proposed but not implemented: a strong-match override (a fact with raw similarity of about 0.60 or more skips routing) and an allergy bypass for relation rank up to 3. Both are held back as a pre-registered ablation for a fresh test set, so that set can measure them blind ([10_limits_and_roadmap.md](10_limits_and_roadmap.md)).

## 9. Connections

| Connects to | How |
|---|---|
| [03 Storage](03_storage.md) | Reads active `facts`, `messages` and `relation_types` (including `routing_hint`); writes `access_count`, `last_accessed_at` and `retrieve` events |
| [04 Models](04_models.md) | Uses `embed` for questions and relation texts, `chat` or `chat_stream` for answers; settings in `core/config.py` |
| [07 Summaries](07_summaries.md) | Adds up to two note lines after the facts, using the same floor and window |
| [05 Write path](05_write_path.md) | Retrieval can only return what extraction stored and the conflict logic kept current |
| [08 Evaluation](08_evaluation.md) | Measures what this document describes |

## 10. Questions about the past

Active facts answer "now". For a question about what used to be true, the system also reads facts that were replaced. Code: `read/past_rules.py` (pure) and `read/past_retrieve.py`; the prompt line is built in `assistant.py`.

1. **Trigger.** `is_past_question(query)`: the question contains one of "used to", "did I use to", "before", "previously", "formerly", "originally", "in the past", "back then", "prior to" as whole words. English only. Everything else behaves as before. It is a keyword list: "Where was home when I was a student?" does not fire, and "How long was I at my job before it closed?" does.
2. **What is read.** Only facts with status `superseded` (a newer value replaced them, or a like and a dislike flipped). Not `archived` and not `conflicted`.
3. **Gate.** The same as for active facts (floor 0.42, window 0.08 among the superseded facts, routing top 2), without the allergy bypass. At most `PAST_MAX_LINES` (2) lines, best raw similarity first. A past value that is also active now (a user who moved back) is skipped.
4. **Prompt.** Past lines come first, then the active facts in the room left of `k`, then notes. Line format: `Earlier: Lives in: Bergen (until 2026-09-01)`. The date is when the value was replaced.
5. **Switch.** `PAST_FACTS=0`.

Example from set I (`i_two_moves`, question "Where did I live before Gdansk?"):

```
Earlier: Lives in: Ghent (until 2026-04-29)
Earlier: Lives in: Valencia (until 2026-09-06)
Lives in: Gdansk (since 2026-09-06)
```

Known gaps (measured on set I, [08_evaluation.md](08_evaluation.md)):

| Gap | Impact |
|---|---|
| Values archived by a retraction are not read | "I left Halvorsen Marine, I now work at Pelican" and "we split up, I'm with Elena now" archive the old value; "Where did I work previously?" gets no line |
| Past lines are ordered by similarity, not by date | For "Where did I live originally?" the oldest value came second and the model answered "I don't know" |
| Keyword trigger | Missed paraphrases and false positives are possible |
| Notes built on replaced facts stay hidden | The stale-source rule of the notes layer is unchanged ([07_summaries.md](07_summaries.md)) |

## 11. Hybrid and full modes

Set M showed that on long histories the baseline's four raw messages answer more than smart's facts and notes ([results/set_M/log.md](results/set_M/log.md)). The hybrid mode keeps the baseline's recall and adds what facts do well: current values, outdated values, allergies, and the order of past values. Code: `read/hybrid.py` (database), `read/hybrid_rules.py` (pure); `assistant.recall` puts the lines together. It is development on spent sets until a fresh set measures it ([results/logs/hybrid_dev.md](results/logs/hybrid_dev.md)).

### 11.1 What the prompt holds, in order

| # | Lines | Rule | Setting |
|---|---|---|---|
| 1 | Current facts | Smart's gate and ranking (`retrieve`), allergy pass included, at most 2. Same format as smart: `Lives in: Kristiansand (since 2026-03-01)` | `HYBRID_FACT_LINES` (2) |
| 2 | One timeline | Only for a past question (the keyword trigger of section 10, and `PAST_FACTS` on). The relation of the best replaced or retracted fact that passes the gate (floor, window, routing; no allergy pass); then every value that relation ever had, oldest first | `HYBRID_TIMELINE` (env, on) |
| 3 | The baseline's `k` messages | Exactly the baseline's choice (`baseline_messages`, the same query), word for word, with markers | `HYBRID_MARKERS` (env, on) |

No episode notes: the raw messages carry the details that notes lost on set M.  
At most `2 + 1 + k` lines (7 with `k = 4`), against the baseline's 4. Hybrid gives up smart's short prompt.

### 11.2 Markers on messages

For each message, every user fact it produced (`facts.source_message_id`) that is no longer active gives one marker after the message:

| The fact | Marker | Example |
|---|---|---|
| Superseded; its `superseded_by` chain ends on an active fact | `[outdated: now <current value>]` | `"I've moved to Oslo" [outdated: now Kristiansand]` |
| The chain ends on another relation (a like that became a dislike) | `[outdated: now <Label>: <value>]` | `[outdated: now Dislikes: coffee]` |
| Archived by a retraction, or the chain does not end on an active fact | `[no longer true: <value>]` | `"I play bass in a covers band" [no longer true: bass]` |
| The chain ends on the same value again (a user who moved back) | none | the old message is true again |
| Conflicted (a dependent fact we cannot judge) | none | |

The header tells the model what the markers mean.

### 11.3 Timeline

`Lives in, oldest first: Stavanger -> Oslo -> Kristiansand (now)`. Values are in the order of `valid_from`; repeats in a row are merged; the current value gets `(now)`, a retracted one `(ended)`, a conflicted one `(unsure)`. No dates, because the `(since date)` labels have been read as event dates before (set M, "When is my wedding?"). Fixes the gap of section 10 where past lines were ordered by similarity, and reads retracted values, which section 10 does not.

### 11.4 Full mode

Every user message, oldest first, in the baseline's line format. On set M a user's history is about 1,100 tokens. The chat call for this mode asks for a context window of `FULL_NUM_CTX` tokens (8192), so the history is never cut silently; every other mode's call is unchanged. It answers "how much could the model do with everything in front of it?" and is not meant to scale. It is used by the evaluation only (`scripts/chat.py` offers `hybrid`, not `full`).

### 11.5 Known gaps

| Gap | Impact |
|---|---|
| Only the message that first gave a fact is marked | A later message that repeats the old value ("Oslo is lovely in spring") is not marked |
| Other people's changes are not marked | A brother's old city in a message has no user fact behind it |
| A marker is only as right as the facts | A wrong supersession marks a true message as outdated |
| One timeline per question | A past question about two relations gets one |
| Keyword trigger | The same as section 10 |
| Longer prompt | Up to 7 lines against 4 |
| A marker covers the whole message | Set M: "Hi, I'm Ruben. I'm a software engineer at Kiwibyte ..." got three markers, and the bio left out the still-true name |
| Fact lines can be incomplete | Set M: `Speaks: English`, `Speaks: Spanish` without Dutch; the model trusted the facts over the message below them |
| The 2-line cap cuts multi-valued answers | Set N: three languages stored, two shown, two answered |
| A wrong fact gives a wrong marker | Set N: a `name` fact corrupted by other people's names marked "Malte moved to Vienna" as `[outdated: now Jonte]`; the model then said it did not know |
| A stale active fact is trusted over the messages | Set N: `Works at: Clinica Albereda` (a new employer was never stored) beat "I'm starting at Alpenmed" in the line below |
