# 7. Summaries (episode notes)

The part of memory that holds what typed facts cannot: things that happened, plans, purchases, a story told over several messages.

It is written after the write path and read after the facts.

## 1. Why it exists

Facts hold 13 kinds of information ([03_storage.md](03_storage.md)).
Set G ([08_evaluation.md](08_evaluation.md)) asked questions outside them (a trip, a plan, a purchase, a story told over several messages).
Without this layer smart memory had the needed information for 8 of 17 questions, the baseline for all 17, because the baseline searches the raw messages.
Raw messages bring noise and outdated values with them; a note keeps the information as one clean sentence.

A note is a short, self-contained sentence about the user, written from one or more of their messages.
Real examples from the chat test ([section 7](#7-using-it)):

| Message | Note |
|---|---|
| "Last month I built a bookshelf with my dad, it took the whole weekend." | The user built a bookshelf with their dad last month and it took the whole weekend. |
| "My neighbour Greta is opening a bakery in Gothenburg next spring." | The user's neighbour Greta is opening a bakery in Gothenburg next spring. |
| "Today I finally painted the garage door green." | The user painted the garage door green today. |

## 2. Where it lives in the code

| File | Job |
|---|---|
| `src/memory_system/summaries/summarize.py` | Write side: finds new messages, asks the model for notes, stores the ones that pass |
| `src/memory_system/summaries/consolidate.py` | Merges notes older than 30 days into digests ([section 12](#12-consolidation-digests)) |
| `src/memory_system/summaries/rules.py` | Pure rules, no database or model: the chatter filter, the faithfulness check, the retention check for digests, the gate for notes |
| `src/memory_system/summaries/retrieve.py` | Read side: the note lines that pass the gate for a question |
| `src/memory_system/assistant.py` | In smart mode, adds the note lines after the fact lines |
| `scripts/chat.py`, `scripts/evaluate.py` | Call `summarize_pending` (the chat after every 6 new messages, the evaluation after each ingest) |

## 3. The flow

```
 WRITE (after enough new messages)                  READ (smart mode, after the facts)

 messages not yet looked at                         question
    │ drop questions, requests, thanks                 │ embed
    ▼   (summary_rules.is_chatter)                     ▼
 local model: one sentence per episode,             notes of this user, with similarity
  citing the numbers of the messages it used           │
    │                                                  ▼
    ▼                                               floor 0.42, window 0.08 (same as facts)
 faithfulness check per sentence                       │
  (summary_rules.is_faithful)                          ▼
    │ keep or drop (dropped ones are logged)        skip notes whose source fact is no longer
    ▼                                                active, and notes that add nothing
 summaries row + messages.summary_id                   │
 + one `summarize` event                               ▼
                                                    at most 2 lines, only in the room left
                                                    among k = 4 after the facts
```

## 4. Write side

### 4.1 Which messages

`summarize_pending(user_id)` takes the user's messages that came after the last run.
Where the last run ended is stored in the `summarize` event (`details.up_to`, the last message id seen), so no schema change was needed.
It works through them `SUMMARY_BATCH` (12) at a time, oldest first.

Before the model sees a batch, `is_chatter` removes messages that hold nothing to remember: a message that starts with a question word and ends with "?", one that starts with a request ("give me", "explain", "suggest", "tell me", "show me", "help me", "recommend") or with "thanks" or "thank you". A statement followed by a question ("I moved to Rome, can you suggest places?") is kept. Removed messages still count as seen. The prompt also asks the model to skip them, but in the first run it did not always, so the rule runs in code.

### 4.2 The model call

`chat_structured` with temperature 0 returns a list of episodes, each a sentence and the numbers of the messages it used. The prompt (`SYSTEM_PROMPT` in `summaries/summarize.py`) asks for:

- only what the messages say, with names, places, numbers and times kept exactly;
- sentences that start with "The user" or "The user's", in the third person;
- related messages combined into one sentence, and the final state if a later message changes or cancels an earlier one;
- a note about another person to stay about that person, not about the user;
- no notes about questions or thanks;
- **no notes about what the facts of a message already hold, and nothing else skipped.** Each message is shown with the facts first stored from it (`tag_message` in `summaries/rules.py`): `1. "I live in Rome." [stored: lives_in = Rome]`, or `[stored: nothing]`. A message with `[stored: nothing]` that tells something about the user or their people gets a note (a hobby, lessons, a pet, a family event, where something ended up);
- three worked examples: an episode and another person's news; a message whose fact is stored but whose lessons are not; a plan whose companion changes, written in its final state.

Before the tags (set L, 2026-10-28) the prompt said "skip plain personal facts stored elsewhere (name, home city, job, allergies, languages, likes, dislikes)". The model cannot know what was stored, and it skipped cello lessons, learning Finnish and a brother's wedding that extraction had not stored either, so nothing kept them. `NOTE_TAGS=0` restores that prompt (`SYSTEM_PROMPT_UNTAGGED`) for comparison.

With the tags the model also wrote profile notes that only restate stored facts ("The user lives in Bologna and works as an architect at Studio Verdi"); they matched many questions and raised noise. So, with tags on, a note is dropped (reason "only stored facts") when every message it cites is held by its stored facts: `only_stored` in `summaries/rules.py` requires every name of the message to be in a stored value and `NOTE_STORED_MIN` (0.75) of its content words to match a stored value or a word that states that kind of fact (`RELATION_WORDS`: "wife", "called" for `partner`). Development record: [history](history.md#note-tags).

### 4.3 The faithfulness check

`is_faithful(statement, sources)` decides, per sentence, using only the messages the model cited:

1. Every number in the sentence must appear in the sources.
2. Every capitalised word that does not start the sentence (a name or a place) must appear in the sources.
3. At least 75% of the remaining content words (`SUMMARY_FAITHFUL_MIN`) must match a word of the sources. Matching is by `same_word`: equal, or one is the other plus a short ending (egg/eggs, ski/skiing, work/works). Stopwords in the sources count as matches ("works" matches "work").

It catches invented names, places and numbers. It does not catch a wrong statement made only of source words (a misattribution or a wrong inference). A sentence that fails is dropped and listed in the event as `"reason": "not faithful"`.

### 4.4 Storing

Each kept sentence becomes a row in `summaries` (`content`, `embedding`, `period_start` and `period_end` from the cited messages' dates). Its source messages get `messages.summary_id`. A message can point to only one summary, so if two sentences cite the same message, only the first is linked. A sentence already stored for the user is skipped.

One `summarize` event per batch records `up_to`, how many messages, how many were skipped as chatter, the ids kept and the sentences dropped with their reasons.

### 4.5 When the model fails

If the call raises (Ollama down, invalid JSON), nothing is stored, a `reject` event with `"reason": "summarization failed"` is logged, and `up_to` does not move, so the same messages are tried again next time.

## 5. Read side

`retrieve_summaries(user_id, query, lines, k, touch, fact_best)` runs after the facts have been chosen (`lines` are their prompt lines, `fact_best` the raw similarity of the best of them).

1. **Room.** At most `SUMMARY_MAX_LINES` (2) notes, and only as many as fit among `k` lines after the facts. Facts keep priority; four fact lines leave no room.
2. **Gate.** Notes whose similarity to the question is at least `MIN_RELEVANCE` (0.42) and within `RELATIVE_WINDOW` (0.08) of the best line: the best note or, when a fact was chosen, the best fact if it is higher (`NOTE_FACT_WINDOW`, on). So "The user plays the guitar in the evenings" (0.48) does not join `Partner: Ines` (0.70) for "What's my wife's name?". Before 2026-10-28 the window was measured among notes only. There is no routing step for notes, and no new threshold.
3. **Stale-source rule.** A note is skipped if any of its source messages produced a fact that is no longer `active` (superseded, archived or conflicted). Without this rule a note written from "I live in Turin" would bring back a value the facts have replaced.
4. **No repetition.** A note is skipped if every content word in it is already in the chosen lines (`adds_information`), so "The user lives in Milan." does not follow `Lives in: Milan`.
5. **Format.** `Note from 2026-10-26: The user's neighbour Greta is opening a bakery in Gothenburg next spring.` The date is the date of the newest source message, which keeps words like "last month" or "today" interpretable.
6. A `retrieve` event with the note ids is logged unless the call is a measurement (`touch=False`).

## 6. Settings

In `core/config.py`:

| Setting | Value | Meaning |
|---|---|---|
| `SUMMARIES` | on (`SUMMARIES=0` switches it off) | Off means nothing is written or shown; the system behaves as before the layer existed |
| `SUMMARY_MAX_LINES` | 2 | Most note lines per question |
| `SUMMARY_BATCH` | 12 | Messages per model call |
| `SUMMARY_EVERY` | 6 | New messages that trigger a summary run in the chat |
| `SUMMARY_FAITHFUL_MIN` | 0.75 | Share of a sentence's content words that must be in its sources |
| `NOTE_TAGS` | on (`NOTE_TAGS=0` switches it off) | Show the notes model the facts stored from each message, and drop notes that only restate them (section 4.2) |
| `NOTE_FACT_WINDOW` | on (`NOTE_FACT_WINDOW=0` switches it off) | The note window is measured from the best line, facts included (section 5) |
| `NOTE_STORED_MIN` | 0.75 | Share of a message's content words its stored facts must cover for the message to count as only stored |
| `CONSOLIDATE` | on (`CONSOLIDATE=0` switches it off) | Merging old notes into digests; off means retrieval reads every note, as before |
| `CONSOLIDATE_MIN` | 6 | Old notes needed before a consolidation run |
| `CONSOLIDATE_AGE_DAYS` | 30 | Age of a note (its newest source message) before it can be merged |
| `CONSOLIDATE_BATCH` | 40 | Old notes per consolidation call |

The floor and window are the fact settings (`MIN_RELEVANCE`, `RELATIVE_WINDOW`); notes were not tuned separately.

## 7. Using it

In the chat, after the sixth new message, the notes written are printed:

Session with a new user (`--user sumtest`); the assistant's replies are shortened to what matters:

```
you> Last month I built a bookshelf with my dad, it took the whole weekend.
you> Thanks!
you> My neighbour Greta is opening a bakery in Gothenburg next spring.
you> I'm learning to juggle and can almost do three balls.
  [memory] ADD hobby = juggling
you> What's a good name for a goldfish?
you> Today I finally painted the garage door green.
  [recalled]
    - Hobby: juggling (since 2026-10-26)
  [summary] The user built a bookshelf with their dad last month and it took the whole weekend.
  [summary] The user's neighbour Greta is opening a bakery in Gothenburg next spring.
  [summary] The user painted the garage door green today.

you> What did I build with my dad?
  [recalled]
    - Hobby: juggling (since 2026-10-26)
    - Note from 2026-10-26: The user built a bookshelf with their dad last month and it took the whole weekend.
assistant> I remember that you mentioned building a bookshelf with your dad last month. ...

you> Who is opening a bakery?
  [recalled]
    - Note from 2026-10-26: The user's neighbour Greta is opening a bakery in Gothenburg next spring.
assistant> Greta, your neighbour, is opening a bakery in Gothenburg next spring.

you> Am I opening a bakery?
  [recalled]
    - Note from 2026-10-26: The user's neighbour Greta is opening a bakery in Gothenburg next spring.
assistant> No.
```

The sixth message triggered the summary run: six messages, three notes. "Thanks!", the goldfish question and the juggling message (already stored as a fact) produced no note. The note about Greta stayed about Greta, so "Am I opening a bakery?" was answered "No." The `Hobby: juggling` line is a fact that passed the fact gate for the first and the second question even though it is not related; the gate does not always return nothing. The `summarize` event of this run: `{"kept": [5, 6, 7], "up_to": 1659, "dropped": [], "messages": 6}`.

In the evaluation, `evaluate.py` runs `summarize_pending` for each scenario's user before asking the questions; with `--no-ingest` only messages not yet seen are summarised. `--verbose` prints the notes stored for each scenario. To switch the layer off for a comparison:

```bash
SUMMARIES=0 poetry run python scripts/evaluate.py --set A B C D E F --retrieval-only --no-ingest
```

Looking at the data:

```bash
psql memory_db -c "select content from summaries where user_id='demo1' order by id"
psql memory_db -c "select details from memory_events where user_id='demo1' and event_type='summarize'"
```

The second query shows `up_to`, the kept ids and every dropped sentence with its reason.

## 8. Results in brief

Details and caveats in [08_evaluation.md](08_evaluation.md); the full record of runs, failures and changes in [history, summaries](history.md#summaries).

| Measure (smart) | Layer off | Layer on |
|---|---|---|
| Set G, needed fact present (17 questions) | 8 | 13 (baseline 17) |
| Set G, answers correct (18) | 8 | 12 (baseline 16) |
| Set H, needed fact present (13), run once | not run | 12 (baseline 13) |
| Set H, answers correct (14) | not run | 13 (baseline 13) |
| Sets A to F, answers correct (61) | 57 | 58 |
| Sets A to F, irrelevant text in the prompt (46 questions) | 14 | 16 |
| Sets A to F, outdated value in the prompt | 0 | 4 |
| Outdated value in an answer, all sets | 0 | 0 |

Consolidation was measured on set J ([section 12](#12-consolidation-digests)): no loss of answers, little compression.

The four outdated mentions are true past-tense statements ("The user used to live in Turin ...") that the keyword test counts as stale; no answer used them wrongly.

## 9. Known gaps

| Gap | Impact |
|---|---|
| Little compression | Notes restate one sentence each in the third person, so they are as long as their sources (1.03 over the evaluation users, 1.10 on set J). Digests cut the notes they replace to 0.79 of their length, and on set J summary text in use is still 1.01 of its source messages. The saving against all stored messages comes from the questions and filler that are left out |
| Most notes are never merged | On set J the model proposed 24 digests, 14 of them a single note (dropped by the rules); 19 of the 36 old notes sent were merged |
| No routing for notes | A note about plans can match any question about plans. Seen in sets A to F: goal notes (marathon, house) came back for "Which language am I trying to learn?". Since the window counts the best fact (section 5), a weak note no longer joins a strong fact; a note can still reach a question for which no fact passes |
| Truthful mentions of old values | "Used to live in Turin" can reach a prompt next to `Lives in: Milan` |
| The stale-source rule needs a fact | It covers only notes whose source messages produced facts |
| A repeated fact is tagged on its first message only | A message that repeats a stored fact is tagged `[stored: nothing]` (a duplicate stores no row), so the model may write a note that restates the fact |
| One summary per message | A message shared by two sentences is linked to the first, so the rule above sees only part of the sources of the second |
| Incomplete citations lose sentences | A sentence that combines two messages but cites one is dropped if a name comes from the other (the billing-project sentence of set G) |
| Details are dropped | The wedding speech, a rejection in a job search. A story may become several sentences, or none |
| Faithfulness is only word-level | Misattribution and wrong inferences made of source words pass |
| The last messages are not summarised | The chat summarises every 6 new messages, so up to 5 recent messages have no note until the next run; the 6-turn chat history covers them |
| Relative times | "Last month" and "today" stay in the text; the note date helps but does not rewrite them |
| English only | The chatter rules and the stopword lists are in English |
| Questions about the past | Facts that were replaced are read for such questions ([06_read_path.md](06_read_path.md), section 10). Notes built on replaced facts stay hidden by the stale-source rule |
| No answer-time guard | When nothing is recalled the model answers from its own wording; the "say you don't know" prompt change was held out |

## 10. Design decisions

| Decision | Alternative | Why |
|---|---|---|
| Notes are separate from facts | Extend the 13 relation types | Episodes have no fixed type; facts stay clean and versioned |
| Same floor and window as facts, no new thresholds | Tune a floor for notes | The sets that exist were spent; a threshold could only be fitted on data already seen |
| Facts first, notes fill the remaining room (at most 2) | Mix by score | Keeps the prompt short and the fact behaviour unchanged (sets A to F: needed present did not drop) |
| Skip notes whose source fact is no longer active | Show them | Keeps old values from coming back as notes |
| Questions and thanks filtered in code | Trust the prompt | The model wrote about a dozen notes about questions and thanks ("The user wants to remove a coffee stain.") although told not to |
| Faithfulness check on every sentence | Trust the model | Catches invented names, places and numbers, which a small model produces |
| Where the last run ended stored in the `summarize` event | A new column or table | No schema change, and a failed call leaves the position untouched |
| One summary per message | A link table | Uses the existing `messages.summary_id`; costs some precision in the stale-source rule |
| Stopwords match as source words | Content words only | Fixed a bug found on set G: "works" was rejected against "work" |
| `SUMMARIES=0` switch | Always on | Lets any result be compared with and without the layer |

## 11. Connections

| Connects to | How |
|---|---|
| [03 Storage](03_storage.md) | Uses `summaries`, `messages.summary_id`, and the `summarize` and `reject` events |
| [05 Write path](05_write_path.md) | The stale-source rule reads `facts.source_message_id` and fact status; `is_faithful` reuses `same_word` and the stopwords of `write/actions.py` |
| [06 Read path](06_read_path.md) | Notes are added after the facts chosen by the gate |
| [08 Evaluation](08_evaluation.md) | Sets G and H measure this layer |
| [10 Limits and roadmap](10_limits_and_roadmap.md) | Consolidation and the other open items |

## 12. Consolidation (digests)

Old notes of one user are merged into shorter digests. The design was frozen before any code ([predictions/set_J.md](predictions/set_J.md)) and measured on set J.

### 12.1 Write side

`consolidate(user_id)` runs right after `summarize_pending` (in the evaluation after each scenario, in the chat after each summary run).

1. **Trigger.** At least `CONSOLIDATE_MIN` (6) live notes whose newest source message is older than `CONSOLIDATE_AGE_DAYS` (30). Newer notes are never sent. A run that would send exactly the notes of the last run is skipped.
2. **Model call.** The old notes, numbered oldest first, go to the model (temperature 0), which returns digests of one or two sentences, each citing the notes it merges. The prompt (`SYSTEM_PROMPT` in `summaries/consolidate.py`) asks for every name, place, number and time kept, the final state when something changed, other people's actions kept as theirs, and at least two notes per digest.
3. **Checks**, in this order. A digest that fails one is dropped and logged; its notes stay live.

| Check | Rule | Drop reason |
|---|---|---|
| Two notes | It cites at least 2 of the notes sent | `fewer than 2 notes` |
| No overlap | None of its notes was merged by an earlier digest of the same run | `note already merged` |
| Faithful | `is_faithful` against the source messages of its notes (the notes' own rule) | `not faithful` |
| Retention | `missing_details`: every number and every capitalised name of its notes is in the digest; month and weekday names may change. Numbers match without separators (21,500 = 21500) | `dropped details` (with what is missing) |
| Shorter | Shorter than its notes together | `not shorter` |

4. **Storing.** A digest is a `summaries` row with `kind = 'digest'`; its notes get `digest_id`. Nothing is deleted, and messages are not touched. One `consolidate` event per run ([03_storage.md](03_storage.md)).

### 12.2 Read side

With consolidation on, retrieval reads digests and the notes no digest replaced, through the same gate and the same room as notes (section 5). The stale-source rule checks a digest through the source messages of all its notes. With `CONSOLIDATE=0` retrieval reads every note and ignores digests, so the same data can be measured both ways.

### 12.3 Results (set J and the regression)

| Measure | Off | On |
|---|---|---|
| Set J, needed present, smart (25) | 23 | 24 (baseline 25) |
| Set J, answers correct, smart (26) | 24 | 25 (baseline 26) |
| Set J, average lines, smart | 1.9 | 1.7 |
| Digests / notes they replaced (characters) | | 0.79 (1,092 / 1,388) |
| Summary text in use / its source messages, set J | 1.10 | 1.01 |
| Sets A to I | | Identical to the last regression, except B: stale in prompt 1 to 0 |

Of the seven pre-registered criteria, compression failed (targets 0.70 and 0.85); retention, final state, the age rule and the regression passed; attribution passed but was weakly tested. Checked by hand, no digest invents a detail, but one turns "the removal company paid for a technician to repair the piano" into "it was repaired by the removal company", and one keeps a "partner" that its notes had invented. Details in [08_evaluation.md](08_evaluation.md) and [history, set j](history.md#set-j).

### 12.4 What was learned

- **The model rarely groups.** 14 of its 24 proposed digests cited a single note. The rule drops them, so those notes are never merged.
- **Better grouping would not be enough.** Grouping by code (shared names, similar meaning) was explored on J afterwards and grouped only 21 of 36 old notes, with some wrong groups (two trips joined by one person's name). Even if every old note were merged at 0.79, summary text in use would be 0.92 of its sources; the target needs 0.70 on every note. Keeping every detail is what limits compression ([history](history.md#consolidation-v2)).
- **Retention works as intended and costs merges.** The only group in the band story was dropped because it lost the name "Margit".
- **One line instead of two helps.** The Hanoi question was answered correctly only with consolidation: a digest of the two December notes left room for the newer February note. This is a side effect of the line budget, not of the final-state rule; the February note was too recent to merge.
- **The stale-source rule hides a whole digest.** In set B a digest merged "The user lives in Turin" (a note that should not exist) with five harmless notes about Turin. The superseded city hides all six. That removed a stale line from the B prompts, but also five pieces of information.
- **Day numbers block a final state.** The retention rule exempts month names but not day numbers, so a digest that replaces "December 12" with "February" would be dropped. On J the model kept the old date instead.
- **Consolidation cannot recover what notes lost.** The asbestos answer of set J was lost at note time: the faithfulness check dropped a true sentence that paraphrased its message.

