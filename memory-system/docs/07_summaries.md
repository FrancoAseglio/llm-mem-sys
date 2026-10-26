# 7. Summaries (episode notes)

The part of memory that holds what typed facts cannot: things that happened, plans, purchases, a story told over several messages. It is written after the write path and read after the facts.

## 1. Why it exists

Facts hold 13 kinds of information ([03_storage.md](03_storage.md)). Set G ([08_evaluation.md](08_evaluation.md)) asked questions outside them (a trip, a plan, a purchase, a story told over several messages). Without this layer smart memory had the needed information for 8 of 17 questions, the baseline for all 17, because the baseline searches the raw messages. Raw messages bring noise and outdated values with them; a note keeps the information as one clean sentence.

A note is a short, self-contained sentence about the user, written from one or more of their messages. Real examples from the chat test ([section 7](#7-using-it)):

| Message | Note |
|---|---|
| "Last month I built a bookshelf with my dad, it took the whole weekend." | The user built a bookshelf with their dad last month and it took the whole weekend. |
| "My neighbour Greta is opening a bakery in Gothenburg next spring." | The user's neighbour Greta is opening a bakery in Gothenburg next spring. |
| "Today I finally painted the garage door green." | The user painted the garage door green today. |

## 2. Where it lives in the code

| File | Job |
|---|---|
| `src/memory_system/summarize.py` | Write side: finds new messages, asks the model for notes, stores the ones that pass |
| `src/memory_system/summary_rules.py` | Pure rules, no database or model: the chatter filter, the faithfulness check, the gate for notes |
| `src/memory_system/summary_retrieve.py` | Read side: the note lines that pass the gate for a question |
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

`summarize_pending(user_id)` takes the user's messages that came after the last run. Where the last run ended is stored in the `summarize` event (`details.up_to`, the last message id seen), so no schema change was needed. It works through them `SUMMARY_BATCH` (12) at a time, oldest first.

Before the model sees a batch, `is_chatter` removes messages that hold nothing to remember: a message that starts with a question word and ends with "?", one that starts with a request ("give me", "explain", "suggest", "tell me", "show me", "help me", "recommend") or with "thanks" or "thank you". A statement followed by a question ("I moved to Rome, can you suggest places?") is kept. Removed messages still count as seen. The prompt also asks the model to skip them, but in the first run it did not always, so the rule runs in code.

### 4.2 The model call

`chat_structured` with temperature 0 returns a list of episodes, each a sentence and the numbers of the messages it used. The prompt (`SYSTEM_PROMPT` in `summarize.py`) asks for:

- only what the messages say, with names, places, numbers and times kept exactly;
- sentences that start with "The user" or "The user's", in the third person;
- related messages combined into one sentence, and the final state if a later message changes or cancels an earlier one;
- a note about another person to stay about that person, not about the user;
- no notes about questions, thanks, or plain personal facts stored elsewhere (name, home city, job, allergies, languages, likes, dislikes);
- two worked examples (one combines two messages about a pottery class into one sentence).

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

`retrieve_summaries(user_id, query, lines, k, touch)` runs after the facts have been chosen (`lines` are their prompt lines).

1. **Room.** At most `SUMMARY_MAX_LINES` (2) notes, and only as many as fit among `k` lines after the facts. Facts keep priority; four fact lines leave no room.
2. **Gate.** Notes whose similarity to the question is at least `MIN_RELEVANCE` (0.42) and within `RELATIVE_WINDOW` (0.08) of the best note. There is no routing step for notes, and no new threshold.
3. **Stale-source rule.** A note is skipped if any of its source messages produced a fact that is no longer `active` (superseded, archived or conflicted). Without this rule a note written from "I live in Turin" would bring back a value the facts have replaced.
4. **No repetition.** A note is skipped if every content word in it is already in the chosen lines (`adds_information`), so "The user lives in Milan." does not follow `Lives in: Milan`.
5. **Format.** `Note from 2026-10-26: The user's neighbour Greta is opening a bakery in Gothenburg next spring.` The date is the date of the newest source message, which keeps words like "last month" or "today" interpretable.
6. A `retrieve` event with the note ids is logged unless the call is a measurement (`touch=False`).

## 6. Settings

In `config.py`:

| Setting | Value | Meaning |
|---|---|---|
| `SUMMARIES` | on (`SUMMARIES=0` switches it off) | Off means nothing is written or shown; the system behaves as before the layer existed |
| `SUMMARY_MAX_LINES` | 2 | Most note lines per question |
| `SUMMARY_BATCH` | 12 | Messages per model call |
| `SUMMARY_EVERY` | 6 | New messages that trigger a summary run in the chat |
| `SUMMARY_FAITHFUL_MIN` | 0.75 | Share of a sentence's content words that must be in its sources |

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

Details and caveats in [08_evaluation.md](08_evaluation.md); the full record of runs, failures and changes in `results/summaries_dev_log.md`.

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

The four outdated mentions are true past-tense statements ("The user used to live in Turin ...") that the keyword test counts as stale; no answer used them wrongly.

## 9. Known gaps

| Gap | Impact |
|---|---|
| It is not compression | Kept information is not shorter: the notes of the evaluation users are 3,061 characters against 2,971 characters of the messages they came from (ratio 1.03), because each note restates one sentence in the third person. Against all stored messages the notes are 28% (10,905 to 3,061), but that saving is the questions and filler that are left out |
| No consolidation | Old notes are never merged into shorter digests |
| No routing for notes | A note about plans can match any question about plans. Seen in sets A to F: goal notes (marathon, house) came back for "Which language am I trying to learn?" |
| Truthful mentions of old values | "Used to live in Turin" can reach a prompt next to `Lives in: Milan` |
| The stale-source rule needs a fact | It covers only notes whose source messages produced facts |
| One summary per message | A message shared by two sentences is linked to the first, so the rule above sees only part of the sources of the second |
| Incomplete citations lose sentences | A sentence that combines two messages but cites one is dropped if a name comes from the other (the billing-project sentence of set G) |
| Details are dropped | The wedding speech, a rejection in a job search. A story may become several sentences, or none |
| Faithfulness is only word-level | Misattribution and wrong inferences made of source words pass |
| The last messages are not summarised | The chat summarises every 6 new messages, so up to 5 recent messages have no note until the next run; the 6-turn chat history covers them |
| Relative times | "Last month" and "today" stay in the text; the note date helps but does not rewrite them |
| English only | The chatter rules and the stopword lists are in English |
| Questions about the past | "Where did I live before?" is not addressed: the stale-source rule hides notes built on replaced facts, by design, and set G's question about the past still fails |
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
| [05 Write path](05_write_path.md) | The stale-source rule reads `facts.source_message_id` and fact status; `is_faithful` reuses `same_word` and the stopwords of `actions.py` |
| [06 Read path](06_read_path.md) | Notes are added after the facts chosen by the gate |
| [08 Evaluation](08_evaluation.md) | Sets G and H measure this layer |
| [10 Limits and roadmap](10_limits_and_roadmap.md) | Consolidation, the past-question mechanism and the other open items |
