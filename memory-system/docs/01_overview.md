# 1. Overview

## The problem

A language model forgets everything between conversations, and the usual fix, storing old messages and searching them by similarity, has three weaknesses:

- **It retrieves irrelevant things.** Similarity search always returns something, so chit-chat and unrelated messages reach the prompt.
- **It keeps outdated facts.** "I live in Turin" and "I moved to Milan" are both stored, and either may come back.
- **It cannot tell what matters.** An allergy and a passing remark are just two messages.

## The goal

A memory architecture that stores what users say over long periods, returns only what is relevant, detects contradictions, replaces outdated information, compresses old history into summaries, and keeps the assistant consistent.  
_The expected outcome is a prototype that gives better answers than traditional vector storage._

## The design

Memory has three layers in one Postgres database:

| Layer | Holds | Status |
|---|---|---|
| **Messages** | Everything the user said, untouched | In use |
| **Facts** | Short structured statements extracted from messages, such as `lives_in = Milan`, each with a status and dates | In use |
| **Summaries** | One-sentence notes about episodes, plans and stories, written from messages ("episode notes") | In use, see [07](07_summaries.md); not yet a compression of old history |

Two paths move information through it:

```
 WRITE PATH (after the user speaks)               READ PATH (before the model answers)

 message                                           question
    │ store (messages)                                │ embed
    ▼                                                 ▼
 local model extracts facts                        score every active fact
    │                                                 │
    ▼                                                 ▼
 pure rules check the extraction                   relevance gate:
  (grounded? assert or retract?)                    floor, window, routing, allergy pass
    │                                                 │
    ▼                                                 ▼
 apply each fact to the database:                  rank what passed, keep at most k
  add, duplicate, replace, contradict, retract        │
    │                                                 ▼
    ▼                                              memory lines in the prompt
 facts table (versioned) + audit log                  │
                                                      ▼
                                                   model answers
```

A second, smaller write path runs after the first: every few messages, the messages not yet looked at are turned into one-sentence episode notes, which are checked and stored. The read path adds those notes after the fact lines when there is room. See [07_summaries.md](07_summaries.md).

The key ideas:

1. **Facts, not messages, are the memory.** A small model turns messages into structured facts. Retrieval searches facts.
2. **Nothing is overwritten.** A new city makes the old one `superseded`; "I'm not a teacher anymore" makes the fact `archived`. History stays, and only `active` facts are read.
3. **Relevance is a gate, not a ranking.** A fact must pass a similarity floor, stay close to the best match, and belong to the kind of information the question is about. Ranking only orders what already passed. Often one line passes, or none.
4. **Allergies get a special pass,** so a loosely worded food question does not lose them.
5. **Every decision is logged** in an audit table, so behaviour can be explained and measured.

## Vocabulary

| Term | Meaning |
|---|---|
| **Fact** | A row with a `relation` (kind), a `value`, a `status`, and validity dates. Example: `allergic_to = peanuts`. |
| **Relation type** | One of 13 allowed kinds of fact, such as `lives_in` or `hobby`. Each is `single` (one value at a time) or `multi`. |
| **Active / superseded / conflicted / archived** | The four fact statuses. Only active facts are retrieved. See [03_storage.md](03_storage.md). |
| **Assert / retract** | What a message does to a fact: state it, or say it is not true. |
| **Grounded** | A value is grounded if it can be traced to words in the message it came from. Used to reject invented values. |
| **Gate** | The relevance test a fact must pass to reach the prompt. |
| **Routing** | The part of the gate that checks the fact's relation type fits the question. |
| **Smart / baseline / none** | The three memory modes compared: this system, plain vector search over messages, and no memory. |
| **Scenario / set** | A scripted life history with questions, and a group of scenarios (sets A to H). |
| **Episode note** | A one-sentence summary of what the user said about something that happened or is planned, linked to its source messages. See [07](07_summaries.md). |
| **Blind / spent** | A blind set was written before the change it tests and run once. After that it is spent: it cannot validate further tuning. |

## Status against the project goals

| Goal | Status | Where |
|---|---|---|
| Store memories over long periods | Done | [03](03_storage.md), [05](05_write_path.md) |
| Prioritise relevant information | Done | [06](06_read_path.md) |
| Detect contradictory facts | Done: likes against dislikes, retractions, employer change | [05](05_write_path.md) |
| Update outdated information | Done: supersede, never overwrite | [05](05_write_path.md) |
| Compress history into summaries | **Partly**: episode notes are written, checked and retrieved, but they do not shorten anything yet (notes are 1.03 times the size of the messages they came from) | [07](07_summaries.md), [10](10_limits_and_roadmap.md) |
| Improve conversational consistency | **Partly**: single questions are measured; consistency across turns is not | [08](08_evaluation.md), [10](10_limits_and_roadmap.md) |

## Results in brief

Measured on 49 scripted life stories with 105 questions (sets A to H), comparing smart memory with baseline (the 4 most similar past messages). Details and caveats in [08_evaluation.md](08_evaluation.md).

Sets A to F (33 stories, 71 questions) were built around the 13 fact types and are all spent:

| Measure | Baseline | Smart, no summaries | Smart, with summaries |
|---|---|---|---|
| Needed fact reached the prompt | 54/58 | 55/58 | 56/58 |
| Questions where irrelevant text reached the prompt (lower is better) | 42/46 | 14/46 | 16/46 |
| Outdated value reached the prompt (lower is better) | 15 | 0 | 4 (true past-tense mentions) |
| Average memory lines per question | 2.4 to 4.0 | 0.9 to 1.7 | 1.3 to 1.8 |
| Answers correct (scored by keywords) | 52/61 | 57/61 | 58/61 |

Sets G and H ask about episodes, plans and purchases that no fact type holds. There the baseline is strong, because it searches the raw messages:

| Set | Baseline | Smart, no summaries | Smart, with summaries |
|---|---|---|---|
| G, needed present (17 questions) | 17 | 8 | 13 |
| G, answers correct (18) | 16 | 8 | 12 |
| H, needed present (13), run once | 13 | not run | 12 |
| H, answers correct (14) | 13 | not run | 13 |

The clearest result is that no outdated value reached an answer with smart memory. On the new question types, smart memory with summaries matches the baseline on the answers of set H and stays behind it on set G (G had been seen once without summaries, so its second run is labelled a re-run). The gaps are a few questions on small sets, so they are encouraging, not conclusive.

## The stack

Python 3.12 with Poetry; Postgres 17 with `pgvector` and `pg_trgm`; Ollama running `llama3.1:8b` (chat and fact extraction) and `nomic-embed-text` (768-dimension embeddings). Everything runs locally. See [02_setup.md](02_setup.md).

## Code map

| Path | Role |
|---|---|
| `src/memory_system/extract.py` | Asks the local model for facts (write path) |
| `src/memory_system/actions.py` | Pure rules that check the extraction (write path) |
| `src/memory_system/conflicts.py` | Decides what each fact does to the database (write path) |
| `src/memory_system/summarize.py`, `summary_rules.py` | Write side of the summaries layer: episode notes and the checks on them |
| `src/memory_system/events.py` | Audit log helper |
| `src/memory_system/manager.py` | Runs the whole write path for one message |
| `src/memory_system/retrieve.py` | The gate, ranking and the baseline (read path) |
| `src/memory_system/summary_retrieve.py` | Reads the episode notes that pass the gate (read path) |
| `src/memory_system/assistant.py` | Builds the prompt from the memory lines (read path) |
| `src/memory_system/llm.py`, `db.py`, `config.py` | Model calls, database pool, settings |
| `scripts/` | `evaluate.py`, `inspect_scores.py`, `chat.py`, `smoke_test.py`, and `scenarios/` with the test sets |
| `tests/` | 116 automated tests: pure rules and the gate need no services, the rest need Postgres |
