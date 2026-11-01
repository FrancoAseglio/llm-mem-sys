# Design

How the memory works: what is stored, what happens when the user speaks (write path), and what
happens before the model answers (read path). Settings live in `src/memory_system/core/config.py`;
most can be switched off from `.env` for an ablation.

## Three layers in one database

| Layer | Table | Holds |
|---|---|---|
| Messages | `messages` | Everything the user said, untouched, with an embedding |
| Facts | `facts` | Short structured statements extracted from messages (`lives_in = Milan`), each with a status and validity dates |
| Episode notes | `summaries` | One-sentence notes about episodes and plans, written from messages; old notes merged into digests |

A fact has one of 13 relation types (`relation_types`), each `single` (one value at a time:
city, employer, partner) or `multi` (hobbies, allergies, languages). It also has a status:

| Status | Meaning | Read? |
|---|---|---|
| `active` | Currently true | yes |
| `superseded` | Replaced by a newer value (`superseded_by` points to it) | only for questions about the past |
| `archived` | Retracted ("I don't play bass any more") | only in hybrid's markers and timelines |
| `conflicted` | Cannot be judged (a job title after an employer change) | no |

Nothing is overwritten or deleted: history stays, and every decision is logged in `memory_events`.
The schema is `db/schema.sql`.

```
 WRITE PATH (after the user speaks)            READ PATH (before the model answers)

 message ── store ──▶ messages                 question ── embed
    │                                              │
 local model extracts facts                    score the facts (and messages)
    │                                              │
 pure rules check them                         relevance gate, then ranking
  (grounded? about the user? a real change?)       │
    │                                          memory lines, by mode
 apply: add, duplicate, replace,                   │
  contradict, retract ──▶ facts + audit log    the model answers
```

## Write path

Code: `src/memory_system/write/` (`manager.py` runs it for one message).

1. **Store** the message with its embedding.
2. **Extract** facts with the local model (`extract.py`), as JSON matching a schema, at
   temperature 0. Each fact is an `assert` or a `retract`.
3. **Check** them with pure rules (`actions.py`): the value must appear in the message
   (*grounded*); it must be about the user, not a sister or a friend (*about user*); and a new
   city, employer, job title or partner must come with words that signal a change ("I moved",
   "I started at"), so an incidental mention ("prices in Utrecht are crazy") does not replace the
   current value (*change rule*).
4. **Apply** each fact (`conflicts.py`), stopping at the first case that fits:

| Case | Result |
|---|---|
| Rejected by a check | nothing stored, a `reject` event |
| Retraction | the matching active fact becomes `archived` |
| Duplicate (same or near-same value) | confidence +0.05, no new row |
| Opposite (`likes` against `dislikes`) | the old side becomes `superseded` |
| Single-valued relation with an older value | the old value becomes `superseded` |
| Otherwise | a new `active` fact |

When the employer changes, the job title becomes `conflicted` unless the same message restates it.

## Read path

Code: `src/memory_system/read/` and `assistant.py` (`recall` builds the memory lines, then
`build_messages` puts them in the system prompt). Five modes are compared:

| Mode | Memory in the prompt |
|---|---|
| `none` | nothing |
| `baseline` | the 4 past messages most similar to the question: traditional vector memory, the control |
| `smart` | the facts that pass the relevance gate, then episode notes in the room left (at most 4 lines) |
| `hybrid` | **the final design**: the best current facts, a timeline for a past question, then the baseline's 4 messages, each marked when a fact it gave has changed |
| `full` | the whole history: a reference ceiling, not a design |

### The relevance gate (smart, and hybrid's facts)

A fact reaches the prompt only if it passes all three tests, so the prompt can stay empty when
nothing is relevant:

| Test | Rule | Value |
|---|---|---|
| Floor | cosine similarity to the question at least | 0.42 |
| Window | within this of the best fact that passed the floor | 0.08 |
| Routing | its relation type among the 2 that best match the question | top 2 |

Allergies skip the floor and the window when routing picks them, so a loosely worded food question
still sees them. What passes is ranked by
`0.50 similarity + 0.25 importance + 0.10 usage + 0.10 confidence + 0.05 recency` and cut to 4.

**Questions about the past** ("Where did I live before Oslo?", found by keywords such as *before*,
*used to*) also read superseded facts: `Earlier: Lives in: Bergen (until 2026-09-01)`.

### Hybrid, the final design

Set M showed that on long histories the baseline's raw messages answer more than facts alone
(facts lose details and pick up extraction errors). Hybrid keeps the raw messages and adds facts
only where they are strong:

1. **Current facts** of the two best relation types (at most 4 lines; every value for lists such
   as languages): `Lives in: Kristiansand (since 2026-03-01)`.
2. **One timeline** for a past question: `Lives in, oldest first: Stavanger -> Oslo -> Kristiansand (now)`.
3. **The baseline's 4 messages, with markers** on those whose facts changed:
   `"I've moved to Oslo" [outdated: Lives in: Oslo -> now Kristiansand]`, or
   `[no longer true: Hobby: bass]` after a retraction.

The model still reads the original sentences, and outdated ones are labelled instead of hidden.

## Episode notes and digests

Code: `src/memory_system/summaries/`. Every few messages, the ones not yet seen are sent to the
model, which writes one-sentence notes about episodes and plans ("The user baked a sourdough loaf
named Bruno"). A faithfulness check drops a note whose names, numbers or most of its words are not
in the messages it cites. Once at least 6 notes are older than 30 days, they are merged by topic
into digests, checked again (faithful, no name or number lost, shorter), which replace them in
retrieval; the notes themselves are kept. Smart
mode reads notes after the facts; hybrid does not need them, since it reads the raw messages.

Notes recovered most questions about episodes that no fact type holds (set G: 8 to 13 of 17).
Digests saved little text (0.79 of the notes they replace), so compression stays a weak point.

## Model calls

Ollama runs `llama3.1:8b` (extraction, notes, answers) and `nomic-embed-text` (768-dimension
embeddings). Every call has a timeout and a cap on reply length (`LLM_TIMEOUT`, `MAX_TOKENS_*`).
The evaluation caches deterministic calls in `.cache/llm.sqlite`, so a repeated run takes seconds.

## Code map

| Path | Holds |
|---|---|
| `src/memory_system/core/` | settings, database pool, model calls, cache, audit log |
| `src/memory_system/write/` | extraction, the pure checks, the decisions, the write path for one message |
| `src/memory_system/read/` | the gate and ranking, the baseline, past questions, hybrid and full |
| `src/memory_system/summaries/` | episode notes, digests, their checks and retrieval |
| `src/memory_system/assistant.py` | the memory lines per mode and the prompt |
