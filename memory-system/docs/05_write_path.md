# 5. Write path (learning from what the user says)

Everything between "the user sends a message" and "memory is updated". This is the part that turns conversation into clean, current, versioned knowledge.

| File | Job | Needs a database or model? |
|---|---|---|
| `src/memory_system/write/extract.py` | Asks the local model for facts in a fixed JSON shape | Model |
| `src/memory_system/write/actions.py` | Pure rules that check what the model returned | No |
| `src/memory_system/write/conflicts.py` | Decides what each fact does to the stored facts, and writes it | Database |
| `src/memory_system/core/events.py` | Writes one row to the audit log | Database |
| `src/memory_system/write/manager.py` | Runs the whole flow for one message; reads facts back for display | Both |

## 1. The flow at a glance

```
                user message: "Big news: I just moved to Milan!"
                                       │
                                       ▼
 ┌───────────────────────── manager.ingest_user_message ────────────────────────┐
 │  1. create the user row if missing                          (users)          │
 │  2. embed the text and save it                              (messages)       │
 │  3. load the allowed relations                              (relation_types) │
 │  4. extract.extract_facts  ──▶  [ lives_in = Milan ]        (model call)     │
 │         if the model fails: keep the message, log it, stop                   │
 │  5. actions.normalize_actions: fix clear assert/retract slips                │
 │  6. for each fact: conflicts.apply_fact                                      │
 │         ├─ not grounded in the message?  ─▶ reject                           │
 │         ├─ retraction?                   ─▶ archive the matching fact        │
 │         ├─ already known?                ─▶ raise confidence                 │
 │         ├─ new?                          ─▶ insert fact + embedding          │
 │         ├─ opposite like/dislike?        ─▶ supersede the opposite           │
 │         └─ replaces a single value?      ─▶ supersede the old one            │
 │  7. return [("update", "lives_in", "Milan")]                                 │
 └──────────────────────────────────────────────────────────────────────────────┘

  steps 1 to 6 happen in ONE database transaction
```

Two kinds of knowledge result from one message:

- The **raw message** is always saved, including chit-chat, for the baseline comparison and for the summaries layer.
- **Facts** are saved only when the message holds something durable.

## 2. Step by step

| # | Step | Where | Writes to | Model calls |
|---|---|---|---|---|
| 1 | Ensure the user exists | `write/manager.py` | `users` | none |
| 2 | Embed and store the message | `write/manager.py` | `messages` | 1 embedding |
| 3 | Read the allowed relations | `write/extract.py` | nothing | none |
| 4 | Extract facts as validated JSON | `write/extract.py` | nothing | 1 structured chat |
| 5 | Clean the list, then check the labels | `write/extract.py`, `write/actions.py` | nothing | none |
| 6 | Apply each fact | `write/conflicts.py` | `facts`, `memory_events` | 1 embedding per new fact |
| 7 | Commit | `write/manager.py` | all of the above, together | none |

If a step fails with a database error, the transaction rolls back and nothing is saved. If only the model fails at step 4, the message is kept (section 6).

## 3. `write/extract.py`: from text to facts

### 3.1 Data shapes

```python
class ExtractedFact(BaseModel):
    relation: str                              # e.g. "lives_in"
    value: str                                 # e.g. "Milan"
    action: Literal["assert", "retract"] = "assert"

class ExtractionResult(BaseModel):
    facts: list[ExtractedFact]
```

`assert` means the user states the fact; `retract` means the user says it is not (or no longer) true.

### 3.2 Functions

| Function | What it does |
|---|---|
| `load_relation_types(conn)` | Reads `relation_types` as `{name: (cardinality, description)}` |
| `build_prompt(relations)` | Builds the system prompt listing every allowed relation |
| `extract_facts(text, relations)` | Calls the model, then cleans the result |

### 3.3 The prompt

| Part | Content |
|---|---|
| Role | "You extract long-term facts about the USER from one message." |
| Allowed relations | One line per relation, built from the database, so a new row in `relation_types` changes what can be extracted without a code change |
| Rules | Only facts the user states about themselves; ignore questions, greetings, thanks, chit-chat and temporary things; keep values short and normalised; "I moved to X" is `lives_in = X`; plans, hopes and things the user is saving for are `goal`; if something is not or no longer true, give it with action `retract`, where "not X, but Y" is a retract for X and a fact for Y; disliking or hating X is not a retract but `dislikes = X`; one item per fact; an empty list when nothing is durable |
| Examples | Four: a message with two facts; "I don't speak French, I speak Spanish" (a retract and an assert); a thanks message; a question |

The user message is sent separately as `Message: "<text>"`.

### 3.4 Cleaning after the model answers

`extract_facts` does not trust the answer. It trims whitespace, drops any relation not in `relation_types`, drops empty values, and removes repeats (same relation, value and action, ignoring case).

## 4. `write/actions.py`: checking the extraction

Pure functions with no database and no model, covered by `tests/write/test_actions.py`.
They exist because the 8B model makes a few predictable slips.

### 4.1 `is_grounded(value, text, relation=None)`

True if the value can be traced to the message it came from.
It stops values the model invented out of nothing.

- A **content word** has three or more letters and is not a stopword. So `egg`, `soy` and `ski` count, but "new job" has nothing to check and is rejected. Words match when they are equal, when one is the other plus a short ending (`egg`/`eggs`, `sail`/`sailing`), or when two long words share their first five letters (`anchovy`/`anchovies`).
- The value is grounded if it shares at least one content word with the message.
- For names, places and dates (`name`, `family_member`, `partner`, `lives_in`, `works_at`, `birthday`) it is also enough that every word of the value appears in the message, so `Ana`, `Li`, `Rio` and `5 May` are accepted.

What it cannot catch: junk made of message words ("new position" from "a new position at Delta Labs") passes, and legitimate paraphrases ("dev" for "developer") are rejected.

### 4.2 `normalize_actions(facts, text, single_relations)`

Checks the model's assert/retract labels against the message and fixes clear errors. Observed on about 30 messages, the model slips on "not X, but Y" sentences in three ways:

| # | Slip | Example | Fix |
|---|---|---|---|
| 1 | The same value is both retracted and asserted | "It's not Turin, I live in Genoa" gives retract Genoa and assert Genoa | The retract is dropped |
| 2 | Every item of a relation is labelled retract, so the replacement is lost | "I'm not a teacher anymore, I became a pilot" gives retract teacher and retract pilot | If a relation has two or more retracts and no assert, one sitting in a clause with a negation word and another in a different clause that is a statement of its own without one ("I became a pilot"), the second becomes an assert. A lone retract is never touched. |
| 3 | A single-valued relation gets two asserts | "I quit my job at Initech, I work at Hooli now" gives assert Initech and assert Hooli | The value whose clause has a negation or ending word (`n't`, `not`, `no longer`, `anymore`, `never`, `used to`, `stopped`, `quit`, `left`, `moved out of`, `switched from`, and similar) becomes the retract |

Repeats are then removed and retractions are put first, so a retraction can never archive a fact asserted by the same message.

The "lone retract is never touched" rule exists because an earlier version flipped a real retraction without a negation word ("I moved out of Berlin") into an assert. That mistake is recorded in [09_findings.md](09_findings.md), and it has a regression test.

### 4.3 `about_user(value, relation, text)`

True unless the message gives the value to someone or something other than the user. Added after set L, where the model stored "My sister Agathe lives in Montreal and works as an airline pilot" as the user's city and job (Montreal replaced the user's real city), "it had ended up in Frankfurt" (a suitcase) as the user's city, and "my friend Pieter" as the user's partner.

| Relations | Rule |
|---|---|
| `lives_in`, `works_at`, `job_title`, `birthday` | In each clause that mentions the value, the last subject word before it decides: `I`, `I'm`, `we` ... mean the user; `he`, `she`, `it`, `who`, `their` or a word for another person (`sister`, `friend`, `colleague` ...) mean someone else; no subject word ("My birthday is 5 May") means the user. The value is kept if any clause gives it to the user |
| `partner` | The message must contain a partner word: `boyfriend`, `girlfriend`, `partner`, `wife`, `husband`, `seeing`, `dating`, `married`, `I'm with`, `split up` ... |
| all others | Not checked: `family_member`, `hobby` and the rest can describe anyone |

Only asserted facts are checked, and the manager uses the same check when it lists the relations a message really sets (so a rejected `works_at` does not mark `job_title` as conflicted). `ABOUT_USER=0` switches it off. It is a word list, English only: "I live with my sister in Lyon" is kept only because "I" comes first, and "I work with my friend at Acme" would lose Acme.

## 5. `write/conflicts.py`: from fact to decision

### 5.1 The decision order

`apply_fact(conn, user_id, relation, value, source_message_id, at, action, source_text, message_relations)` runs these stages in order and stops at the first that applies:

| # | Stage | Condition | Result | Event |
|---|---|---|---|---|
| 0 | Grounding | `source_text` is given and the value is not grounded in it | `rejected`; nothing stored | `reject` |
| 0b | About someone else | `action` is `assert`, `source_text` is given, `ABOUT_USER` is on and `about_user` (section 4.3) says the message gives the value to someone else | `rejected`; nothing stored | `reject`, reason "about someone else" |
| 1 | Retraction | `action` is `retract` | An active fact with the same value (equal, or trigram similarity of 0.8 or more) becomes `archived`, `valid_to` set. Returns `retract`; or `retract_miss` when nothing matches | `retract` |
| 2 | Duplicate | An active fact with the same relation and a matching value exists | Confidence +0.05, `updated_at` set. Returns `duplicate`; no new row, no embedding call | `duplicate` |
| 3 | Insert | otherwise | A new active row with its embedding | held until the outcome is known |
| 4 | Opposite | The relation is `likes`, `hobby` or `dislikes`, and an active fact of the opposite side matches the value | The opposite is `superseded` by the new row. Returns `contradiction` | `contradiction` |
| 5 | Replacement | The relation is `single` and older active or conflicted values exist | They become `superseded` by the new row. Returns `update` | `update` |
| 6 | Add | otherwise | Returns `add` | `add` |

Opposites: a new `likes` or `hobby` contradicts an active `dislikes`; a new `dislikes` contradicts an active `likes` or `hobby`.

### 5.2 Dependent facts: the `conflicted` status

When the employer changes (`works_at` replaced at stage 5, or retracted at stage 1), the job title may no longer hold. Unless the same message also states a job title, the active `job_title` becomes `conflicted` and a `conflict` event is logged. It is not superseded, because the system cannot know whether it is still true. Retrieval skips conflicted facts, so a possibly stale title never reaches a prompt. Restating the title later supersedes the conflicted row through stage 5.

The dependency table is `DEPENDENTS = {"works_at": "job_title"}` in `write/conflicts.py`. Only that pair is defined.

### 5.3 Values written on a new fact

| Column | Value |
|---|---|
| `importance` | `DEFAULT_IMPORTANCE[relation]`, or 0.5 if the relation has no entry |
| `confidence` | 0.8 (the column default) |
| `status` | `active` |
| `valid_from` | `at` if given (evaluation replays old dates), otherwise now |
| `source_message_id` | the message that produced it |
| `embedding` | embedding of `relation with spaces: value`, for example `lives in: Milan` |

### 5.4 Duplicate matching

Uses `pg_trgm` `similarity()` on lower-case text. Trigram similarity compares overlapping three-letter chunks, so it catches small spelling differences. The threshold is `DUPLICATE_SIMILARITY` (0.8). Singular and plural can fall below it (`peanut` against `peanuts` is about 0.67), so a retraction of `peanut` can miss a stored `peanuts`; the miss is logged.

### 5.5 Subtle behaviours

| Behaviour | Consequence |
|---|---|
| A duplicate keeps the old wording and the old source message | Only confidence and `updated_at` change |
| "Newest statement wins" for single-valued relations | No judgement about which statement is more likely true |
| Spelling variants of a single-valued fact may not count as duplicates | "Milan" then "Milano" may replace instead of repeat |
| Similar but different values of a `multi` relation are added separately | "cycling" and "road cycling" can both exist |
| Superseded rows are never reactivated | Moving back to Turin inserts a new Turin row; the unique index allows it because the old row is not active |
| A retraction only sees active facts | A `conflicted` fact cannot be retracted |

## 6. `write/manager.py`: orchestration

| Function | Purpose |
|---|---|
| `ingest_user_message(user_id, text, at=None)` | The whole flow in section 1. Returns `(outcome, relation, value)` tuples, for example `[("update", "lives_in", "Milan")]`. An empty list means nothing durable was found. `at` backdates the message, which the evaluation uses to replay old conversations. |
| `list_facts(user_id, include_history=True)` | Facts for display: relation, value, status, importance, confidence and `valid_from` as text. With `include_history=False`, only active facts. |

Notes:

- Outcomes are `add`, `duplicate`, `update`, `contradiction`, `retract`, `retract_miss`, `rejected`, or `extraction_failed`.
- **When the model fails** (Ollama down, malformed JSON), the message stays stored and searchable, a `reject` event records the error, and the function returns `[("extraction_failed", "", "")]`. No facts are written for that message.
- Only user messages are ingested. Assistant replies are deliberately not stored, so the system does not learn from its own guesses.
- `list_facts` sorts by relation and then by `valid_from` as text with minute resolution, so facts from the same minute have no defined order.

## 7. Worked examples

| Message | What the model returns (typical) | Stored result |
|---|---|---|
| "I live in Turin and I work at Acme as a software engineer." | assert `lives_in` Turin, `works_at` Acme, `job_title` software engineer | three `add` |
| "Big news: I just moved to Milan!" | assert `lives_in` Milan | `update`: Turin `superseded`, Milan `active` |
| "I'm not allergic to peanuts, I'm allergic to walnuts." | retract `allergic_to` peanuts; retract walnuts (slip 2) | after `normalize_actions`: peanuts `archived`, walnuts `add` |
| "I quit my job at Initech, I work at Hooli now." | assert `works_at` Initech and Hooli (slip 3) | after `normalize_actions`: Initech `archived`, Hooli `add`, `job_title` `conflicted` |
| "I've gone right off spicy food, I can't stand it." (after "I love spicy food") | assert `dislikes` spicy food | `contradiction`: likes `superseded`, dislikes `active` |
| "Exciting news, I just started a new position at Delta Labs!" | assert `works_at` Delta Labs, maybe `job_title` "new job" | `works_at` replaced; "new job" `rejected` (no content word), old title `conflicted` |
| "Thanks, that was helpful!" | nothing | the message only |

## 8. Known weaknesses of the write path

| Weakness | Effect |
|---|---|
| Junk made of message words passes grounding | "new position" can be stored as a job title; a generic phrase after a promotion can overwrite the real title |
| An achieved goal stays a `goal` | "I finally got the promotion" can leave the old goal stored |
| An abandoned hobby can be filed as a dislike | "I'm done with chess" |
| A negated like may be read as a retraction | "I don't like jazz" can be labelled retract, so the dislike is not stored. The prompt tells the model that disliking is not a retraction, but it does not always follow it |
| The rules know English phrasing only | Negation words and fillers are English; other languages are untested |
| Past and hypothetical statements rely on the model | "I used to live in..." is handled by the prompt, not by a rule. Third-person statements are checked by `about_user` (4.3) only for `lives_in`, `works_at`, `job_title`, `birthday` and `partner` |
| Single-message extraction | "No, I meant Rome" is not recognised as a correction of the previous message |
| Confidence is a counter | Repetition adds 0.05; it says nothing about how certain the statement was |
| User text goes into the prompt unescaped | A crafted message could try to steer the extractor; relation validation limits the damage |
| Only `works_at` to `job_title` is a dependency | Moving city does not affect `works_at` |

## 9. Common changes

**Teach memory a new kind of fact** ("I'm vegetarian"):

```sql
INSERT INTO relation_types (name, cardinality, description)
VALUES ('diet', 'single', 'Dietary pattern, e.g. vegetarian, vegan');
```

Optionally add an importance entry (`"diet": 0.75`) to `DEFAULT_IMPORTANCE` in `core/config.py`; without it the fallback is 0.5. The extraction prompt picks up the new relation automatically. For retrieval, the description is also used for routing, so restart the process.

**Make duplicates stricter or looser:** change `DUPLICATE_SIMILARITY` in `core/config.py`. Lower merges more near-matches.

**Improve extraction:** add a short example to `build_prompt` in `write/extract.py` for a case it gets wrong. Add the failing sentence as a case in `tests/write/test_actions.py` if a rule can fix it instead.

**See what was decided:**

```sql
SELECT created_at, event_type, details
FROM memory_events
WHERE user_id = 'demo1'
ORDER BY id;
```

**Reset a user:** `DELETE FROM users WHERE id = 'demo';`

## 10. Design decisions

| Decision | Reason |
|---|---|
| Extract only from the user's messages | Stops the system from storing the assistant's own statements |
| Allowed relations come from the database | Extending what memory can learn is one SQL `INSERT` |
| The model supplies only relation, value and action | Small models are unreliable at scoring; importance and confidence come from deterministic rules |
| Validate and fix after the model answers | The model's output is untrusted input |
| Pure rules separated from database code | They can be tested without services, and each past mistake became a test |
| Retraction archives, never deletes | The record of what was believed stays |
| Duplicate check before the embedding call | Saves a model call |
| Supersede instead of overwrite | History for later questions and for the audit trail |
| Whole write in one transaction | A message, its facts and its events are saved together or not at all |
| Keep the message when extraction fails | It stays searchable and nothing the user said is lost |
| Log every decision | Behaviour is explainable and measurable |
| Store chit-chat messages too | Raw material for the baseline and for summaries |

## 11. Connections

| Connects to | How |
|---|---|
| [03 Storage](03_storage.md) | Writes `users`, `messages`, `facts`, `memory_events`; reads `relation_types` |
| [04 Models](04_models.md) | Uses `embed`, `chat_structured`, `get_pool` and the importance and duplicate settings |
| [06 Read path](06_read_path.md) | Produces the active facts that retrieval ranks; retrieval reads only `status = 'active'` |
| Tests | `tests/write/test_actions.py` (pure rules), `tests/write/test_write_path.py` (`apply_fact` against the database), `tests/write/test_manager.py` (extraction failure) |
| Scripts | `chat.py` calls `ingest_user_message` after each answer |
