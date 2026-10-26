# 9. Findings and decisions

The experiments, mistakes and decisions that shaped the current design. Retrieval numbers are exploratory: sets A to C had been seen when they were measured. The one-off scripts used for the retrieval experiments were removed; the settings they produced live in `config.py` and `relation_types.routing_hint`.

## 1. Retrieval experiments

### 1.1 Embedding format does not help

Seven ways of embedding a fact against the question were compared: the stored `relation: value` text, a natural sentence ("The user lives in Milan."), nomic's `search_query:` and `search_document:` prefixes, both combined, the raw source message, and the better of sentence and message. None separated relevant from irrelevant facts clearly better than the stored format, so facts are still embedded as `relation: value`. Relevance had to come from the gate instead.

### 1.2 Floor and relative window

An absolute similarity threshold alone cannot work: a topical neighbour (`lives_in = Rome`, 0.50) can outscore a needed fact for another question (`allergic_to = peanuts` for "a quick snack", 0.44). Fitted on set A, checked on B, then C:

- `MIN_RELEVANCE = 0.42`: the middle of the 0.40 (must reject) to 0.44 (must accept) window. It rests on one example per side, so it is fragile.
- `RELATIVE_WINDOW = 0.08`: the feasible range was about 0.05 to just under 0.11. It removes neighbours far below the best match for the same question.

### 1.3 Relation routing: top 2 with hints

The question is compared with each relation type's text (`name: description` plus an optional `routing_hint`), and only facts of the `ROUTING_TOP_N` best types pass. It reuses the question embedding, so no extra model call. On 30 questions from sets A to C:

| | Irrelevant lines per question | Needed facts present |
|---|---|---|
| floor + window | 0.70 | 26/26 |
| + routing top 2, no hints | 0.13 | 24/26 |
| + routing top 2, with hints | 0.13 | 26/26 |

Without hints, food questions routed to `likes` instead of `allergic_to`. The two hints (`allergic_to`, `dislikes`) were written after seeing those misses, so they are a design choice, not evidence. Set D was written before routing existed and was run once.

### 1.4 Limits found on set E (not fixed)

- **Top-2 routing vetoes a strong match.** "Which language am I trying to learn?" against `goal = learn Japanese`: raw similarity 0.70, far above the floor, but `goal` ranked 4th among relation types and was dropped.
- **An allergy just outside the bypass.** `allergic_to = sesame` (raw 0.42) for a food question: `allergic_to` ranked 3rd, so the bypass (top 2 only) did not apply and the floor removed it.
- **Proposed fix, not implemented:** a strong-match override (raw similarity of about 0.60 or more skips routing) and an allergy bypass for relation rank up to 3. Reserved as a pre-registered ablation for a fresh set.

## 2. Write-path findings

### 2.1 The 8B model slips on corrections

On about 30 messages with "not X, but Y" or "no longer" wording, the model made three kinds of error: it listed the same value as retract and assert; it labelled every item a retract, losing the replacement; and for a single-valued relation it asserted both the old and the new value. `normalize_actions` fixes each of them ([05_write_path.md](05_write_path.md), section 4.2). The first retraction support made the second half of "not peanuts, walnuts" disappear; this was found on a full re-ingest, not by a unit test, and is now covered by tests built from the observed outputs.

### 2.2 Grounding needed care

The first grounding rule (a value must share a word of four or more letters with the message) rejected real facts: short names (`Ana`, `Li`, `Rio`) and short allergens (`egg`, `soy`). The rule now accepts three-letter words, accepts name-like relations whose words all appear verbatim, and treats generic words such as `new`, `job` and `work` as stopwords. It still lets junk made of message words pass ("new position"), and it rejects paraphrases ("dev" for "developer").

### 2.3 The `conflicted` status earns its place

An employer change used to leave the old job title active, so a stale title could reach a prompt. Marking the title `conflicted` removes it from retrieval without claiming it is false. The cost is that "What is my job title?" now abstains after a change unless the title is restated, which is the intended trade.

### 2.4 Likes and dislikes

A new like that matches an active dislike (or the reverse) now supersedes it with a `contradiction` event. Matching uses the same exact or trigram check, so near misses ("jazz" against "jazz music") are not caught.

## 3. Mistakes made and what they changed

| Mistake | How it was found | Change |
|---|---|---|
| Ranking by recency and importance made old facts disappear and let irrelevant ones in | Early evaluation sets | Relevance became a gate; ranking only orders what passed |
| Pinning the most important facts put an allergy into every unrelated question | Evaluation noise | Pinning is off; the routed safety bypass replaced it |
| An absolute threshold alone could not separate needed facts from topical neighbours | Sets A to C (section 1.2) | A floor of 0.42 plus a window of 0.08 below the best match |
| `normalize_actions` flipped a real retraction without a negation word ("I moved out of Berlin") into an assert | A regression test written from the observed output | A lone retract is never changed; two or more are needed, plus a negation clause and an independent clause |
| The grounding rule rejected short names and allergens | Re-ingest of sets A to E | Three-letter words, verbatim rule for names |
| `--no-ingest` on stale evaluation data produced a false regression (6/7 instead of 7/7 on set B) | A user's run after a refactor | The scenario's stored data held 2 of 8 messages; re-ingest restored the numbers. Protocol rule 7 in [08_evaluation.md](08_evaluation.md) |
| `pytest` collected `scripts/smoke_test.py` because of its name and ran it at import | A failure after a refactor | `testpaths = ["tests"]` in `pyproject.toml` |

### Summaries layer

Full record in [results/summaries_dev_log.md](results/summaries_dev_log.md); the design in [07_summaries.md](07_summaries.md).

| Finding | Evidence | Change |
|---|---|---|
| Facts alone cannot answer episodic questions | Set G first run: 8/17 needed present against the baseline's 17/17 | Episode notes stored in `summaries`, read after the facts |
| The model wrote notes about questions and thanks although told not to (about a dozen) | The 48 notes of the first A to F run | `is_chatter` filters them in code before the model |
| That fix did not remove the extra noise: it stayed at 17/46 | Run 2; the first diagnosis (question notes cause the noise) was incomplete | Read the nine prompts: seven true mentions that the keyword lists score as bad, two real noise (goal notes for a language question, a distractor). Recorded as not met; no threshold changed |
| The faithfulness check rejected true sentences ("works" against "work") | The dropped-sentence list of the `summarize` event, set G | Match against all source words, stopwords included; three notes recovered; set E also gained a note |
| A note of a replaced fact would bring the old value back | Design review before building | The stale-source rule: skip a note whose source message produced a non-active fact |
| Notes did not compress | Compression query: notes 3,061 characters, linked source messages 2,971 | Not fixed; consolidation is on the roadmap |

Two things were disclosed in the record: set G was run before its code was committed, and G was re-run once with summaries, so its second result is labelled a re-run and not blind. Set H was run once.

### Questions about the past

Full record in [results/past_step_log.md](results/past_step_log.md); the mechanism in [06_read_path.md](06_read_path.md), section 10.

| Finding | Evidence | Change |
|---|---|---|
| Replaced facts were invisible, so "where did I live before?" failed | Set G, `g_past_home` | Replaced (superseded) facts are read when the question matches a keyword list, as `Earlier:` lines |
| The trigger missed "did I use to dislike" (no d) | A unit test written for the rule, before any run of set I | "did I use to" added to the list; recorded in the predictions file |
| The rule recovers replaced values but not archived ones | Set I: `i_job` (Halvorsen archived) and `i_partner` (Dario archived) | Not changed: set I is spent. A fresh set must test reading retraction-archived facts for past questions |
| "I left X, I now work at Y" is stored as a retraction | The stored facts of `i_job` | Recorded as a write-path behaviour; whether the status should be `superseded` in such a case is open |
| Lines ordered by similarity can bury the oldest value | `i_two_moves`, "originally": Valencia first, Ghent second, answer "I don't know" | Not changed; proposed for the fresh set |
| A note can answer a past question the rule cannot | `i_partner` passed with the rule off, through the note about Dario | Reported: that criterion was met by the notes layer |
| Nothing else moved | Sets A to F, H identical; G changed only on its past question | The rule fires on one question in sets A to H |

## 4. Refactor results

The code was split into smaller modules without changing behaviour: the scenarios into a package, `conflicts.py` into `actions.py`, `events.py` and `conflicts.py`, and `evaluate.py` into three files, with the gate's logic shared by `select_memories` and `inspect_scores.py`. Each step was checked by identical snapshots or outputs: the scenarios by a diff of their data, the gate by a randomised comparison with the old implementation, the evaluation by an identical `eval_results.json`, and the full set A to F by identical tables from an empty database.

## 5. Decision log

| Decision | Alternative considered | Why |
|---|---|---|
| Postgres with `pgvector` and `pg_trgm` | MongoDB, a separate vector store | The data is structured and rule-checked; Postgres already provides vector search, fuzzy matching, unique indexes, foreign keys and transactions |
| Supersede, never overwrite | Overwrite in place | History, audit trail, undoable mistakes |
| Facts as the memory, messages as raw material | Searching messages only | Lets retrieval return nothing, exclude outdated information and stay short |
| Relevance as a gate, ranking only orders | One blended score | A blended score let weak matches in on importance or recency |
| Relation routing with two hints | No routing | Removed most irrelevant lines (0.70 to 0.13 per question) |
| Allergies skip floor and window when routed | Always pin allergies | Pinning flooded unrelated questions |
| Importance set by relation in `config.py` | Ask the model to rate | The 8B model rated nearly everything 1.0 |
| Pure rules separate from database code | Everything in `apply_fact` | Rules testable without services; each past mistake became a test |
| Retraction archives, `conflicted` for dependents | Delete, or trust newest-wins | Keeps history; avoids asserting that an unknown is false |
| Keep the message when extraction fails | Roll back everything | Nothing the user said is lost |
| Temperature 0 for extraction and evaluation | Default sampling | Repeatable experiments |
| All test sets labelled tuning, spent or blind | Re-using sets freely | Keeps the evidence honest |
| Strong-match override and rank-3 allergy bypass not implemented | Implement now | Held for a pre-registered test on a fresh set |
| Episode notes separate from facts | Add relation types for episodes | Episodes have no fixed type; facts stay clean and versioned |
| Notes use the fact floor and window, with no routing | Tune a separate threshold | All earlier sets were spent, so a threshold could only be fitted on data already seen |
| Notes are verified sentence by sentence in code | Trust the model | A small model invents details; a failing sentence is dropped and logged |
| Past-question mechanism and "say you don't know" prompt held out of the summaries step | Add them to the same step | Each is a separate change that needs its own measurement |
| Past lines read only from `superseded` facts | Also read `archived` | Archived also holds facts the user said were never true; a reading of retractions needs its own measurement on a fresh set |
| A keyword trigger for past questions | A model call to classify each question | No extra model call per question; the trigger is testable and its misses are known |

## 6. Manual chat tests (2026-10-25)

Hand-run chats with `scripts/chat.py`, on fresh users, after the evaluation was finished. They were not part of any test set. The "expected" column is what was predicted before typing the message.

| User | Message | Stored or recalled | Expected | Verdict |
|---|---|---|---|---|
| demo1 | "Actually I moved to Milan." (after "I live in Turin") | `UPDATE lives_in = Milan`; Turin `superseded` | update | as expected |
| demo1 | "Can you suggest a quick snack?" | recalled only `allergic_to = peanuts` | allergy only | as expected |
| demo1 | after a restart: name, city | recalled `Name: Franco`, `Lives in: Milan`, one line each | recall from memory alone | as expected |
| demo1 | "where do i used to live?" | recalled `Lives in: Milan`; answer "I don't know" | cannot answer | known limit: superseded facts are never read |
| t3 | "My brother lives in Rome." | `ADD family_member = brother`, no `lives_in` | no city for the user | as expected |
| t3 | "I used to live in Berlin." | `RETRACT_MISS lives_in = Berlin`, nothing stored | nothing stored | as expected (outcome); the past tense was read as a retraction of a fact that did not exist |
| t3 | "Thanks, that was helpful!" | nothing | nothing | as expected |
| t3 | "What's my blood type?" | smart: nothing recalled, "I don't know"; baseline: four unrelated messages recalled | abstain | as expected |
| t5 | "I'm vegetarian." | `ADD hobby = vegetarianism` | no fact | **wrong**: a diet was filed as a hobby (outside the 13 types) |
| t5 | "I got the promotion." | nothing | nothing | as expected |
| t5 | "I don't like jazz." | `ADD dislikes = jazz` | possibly read as a retraction | prediction wrong; the result is correct |

What these showed:

- The misfiling of "I'm vegetarian" is a real gap. The extraction prompt has no way to say "this is not one of the types", so the model picks the nearest one, and grounding lets it through because the word appears in the message. Candidates for a fix: a free-form note type, or an explicit "none of these" outcome. To be decided with set G.
- The question about the past ("where did I used to live?") is a concrete case for set G.
- The 8B model sometimes claims knowledge it does not have ("nice to chat with you again", "I remember you mentioning ...", "we haven't discussed your personal information before"). These come from the model and from the 6-turn chat history, not from the memory, which had recalled nothing or something different.
- The chat sends the last 6 turns in every mode, so a short chat does not test long-term memory. Quit and restart with the same user to test it.
- Pasting several lines at once into the chat feeds them one after another and can glue a command to the next message. Send one line at a time.

A further manual test on 2026-10-26 (user `sumtest`) checked the summaries layer: after six messages three notes were written (bookshelf with the dad, the neighbour's bakery, the garage door); "Thanks!", a goldfish-name question and a message already stored as a fact produced none. "What did I build with my dad?" and "Who is opening a bakery?" were answered from the notes, and "Am I opening a bakery?" was answered "No." The full session is in [07_summaries.md](07_summaries.md), section 7.
