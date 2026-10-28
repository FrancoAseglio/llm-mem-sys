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
| **Summaries** | One-sentence notes about episodes, plans and stories, written from messages ("episode notes"); old notes merged into digests | In use, see [07](07_summaries.md); digests shorten the notes they replace by about a fifth, not enough to call it compression |

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

A second, smaller write path runs after the first: every few messages, the messages not yet looked at are turned into one-sentence episode notes, which are checked and stored. Notes older than 30 days are then merged by topic into digests, which are checked again and replace them. The read path adds notes and digests after the fact lines when there is room. See [07_summaries.md](07_summaries.md).

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
| **Scenario / set** | A scripted life history with questions, and a group of scenarios (sets A to J). |
| **Episode note** | A one-sentence summary of what the user said about something that happened or is planned, linked to its source messages. See [07](07_summaries.md). |
| **Digest** | One or two sentences that replace several old notes on one topic; the notes are kept but no longer read. See [07](07_summaries.md), section 12. |
| **Blind / spent** | A blind set was written before the change it tests and run once. After that it is spent: it cannot validate further tuning. |

## Status against the project goals

| Goal | Status | Where |
|---|---|---|
| Store memories over long periods | Done | [03](03_storage.md), [05](05_write_path.md) |
| Prioritise relevant information | Done | [06](06_read_path.md) |
| Detect contradictory facts | Done: likes against dislikes, retractions, employer change | [05](05_write_path.md) |
| Update outdated information | Done: supersede, never overwrite | [05](05_write_path.md) |
| Compress history into summaries | **Partly**: old notes are merged into digests (set J), but the saving is small: digests are 0.79 of the notes they replace, and summary text in use is still about the size of its source messages (1.01). The pre-registered target failed | [07](07_summaries.md), [10](10_limits_and_roadmap.md) |
| Improve conversational consistency | **Partly**: measured across sessions (set K); smart and baseline about even, smart with no contradiction; stability not better | [08](08_evaluation.md), [10](10_limits_and_roadmap.md) |

## Results in brief

Measured on 71 scripted life stories with 173 questions (sets A to J, and L on unseen data) and 6 multi-session stories with 23 probes (set K), comparing smart memory with baseline (the 4 most similar past messages). Details and caveats in [08_evaluation.md](08_evaluation.md).

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

Set I (12 questions) tests questions about the past. Smart memory with the past rule had the needed value for 5 of 6 past questions (1 of 6 with the rule off), kept every present-tense control and "before" trap free of old values, and answered 3 of 6 past questions correctly (criterion 4). Values that the write path archives, such as a left employer, are not reachable yet ([06](06_read_path.md), section 10).

Set J (26 questions) tests merging old notes into digests on users with 10 to 16 episode messages. Consolidation did not cost answers (smart 24/26 without it, 25/26 with it; baseline 26/26), but it saved little text: the digests are 0.79 of the length of the notes they replaced, against a target of 0.70 ([07](07_summaries.md), section 12).

Set K (23 probes) tests consistency across sessions, where each session starts with no chat history and only memory carries facts. Smart answered 17, baseline 16; smart never used an outdated value, baseline once; each kept 2 of 7 facts stable. Most of smart's misses were indirect questions ("sign this with my name") whose fact did not pass the gate ([08](08_evaluation.md)).

Set L (30 questions) is the first measure on unseen data: written after every other set was spent, every question type mixed, run once. **The baseline answered 28, smart 20** (16 with facts only). Half of smart's misses were facts stored wrongly: a sister's city and job saved as the user's, a place where lost luggage turned up saved as the user's home, a friend saved as a partner. Smart answers from facts, so those errors became wrong answers, including its first outdated one; the baseline reads raw messages and cannot make them. The rest were the known gate weakness on indirect questions ([08](08_evaluation.md), `results/set_L/log.md`).

On the sets written with the system, no outdated value reached an answer with smart memory; on set L one did, through a wrongly stored fact. On the new question types, smart memory with summaries matches the baseline on the answers of set H and stays behind it on set G (G had been seen once without summaries, so its second run is labelled a re-run). The gaps are a few questions on small sets, so they are encouraging, not conclusive; set L, the one fresh set, favours the baseline.

## The stack

Python 3.12 with Poetry; Postgres 17 with `pgvector` and `pg_trgm`; Ollama running `llama3.1:8b` (chat and fact extraction) and `nomic-embed-text` (768-dimension embeddings). Everything runs locally. See [02_setup.md](02_setup.md).

## Code map

The package `src/memory_system/` is split by what happens to information:

| Package | Holds | Modules |
|---|---|---|
| `core/` | Shared plumbing | `config` (settings), `db` (connection pool), `llm` (model calls), `cache` (disk cache for the evaluation), `events` (audit log) |
| `write/` | What happens when the user speaks | `extract` (asks the model for facts), `actions` (pure rules that check the extraction), `conflicts` (what each fact does to the database), `manager` (runs the whole write path for one message) |
| `read/` | What happens when the user asks | `retrieve` (the gate, ranking and the baseline), `past_rules` (pure: is it a question about the past), `past_retrieve` (replaced facts for such questions) |
| `summaries/` | Episode notes and digests | `summarize` (write side), `consolidate` (merges old notes into digests), `rules` (pure checks: chatter filter, faithfulness, retention, gate for notes), `retrieve` (read side) |
| `assistant.py` | Builds the prompt from the fact lines, past lines and note lines | |

Outside the package:

| Path | Role |
|---|---|
| `scripts/` | The commands you run: `chat.py`, `evaluate.py`, `inspect_scores.py`, `list_scenarios.py`, `smoke_test.py` |
| `scripts/evaluation/` | Support for the evaluation: `metrics.py` (scoring), `report.py` (printing) and `scenarios/` (the test sets, one JSON file each) |
| `tests/` | Mirrors the package: `tests/write/`, `tests/read/`, `tests/summaries/`, plus `tests/evaluation/` for the scenario files |

205 automated tests: pure rules and the gate need no services, the rest need Postgres.
