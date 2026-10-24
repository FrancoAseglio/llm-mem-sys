# D. Write path (learning from what the user says)

Everything that happens between "the user sends a message" and "memory is updated". This is the part of the project that turns raw conversation into clean, current, versioned knowledge.

| File | Job |
|---|---|
| `src/memory_system/extract.py` | Pulls facts out of a message using the LLM |
| `src/memory_system/conflicts.py` | Decides whether each fact is new, a duplicate, or a replacement, and writes it |
| `src/memory_system/manager.py` | Runs the whole flow in one transaction; also reads facts back for display |
| `scripts/demo_ingest.py` | A scripted demo of the flow with seven messages |

---

## 1. The flow at a glance

```
 user message: "Big news: I just moved to Milan!"
        │
        ▼
 ┌─────────────────────────── manager.ingest_user_message ───────────────────────────┐
 │  1. create the user row if missing                          (users)               │
 │  2. embed the text and save it                              (messages)            │
 │  3. load the allowed relations                              (relation_types)      │
 │  4. extract.extract_facts  ──▶  [ lives_in = Milan ]        (LLM call)            │
 │  5. for each fact: conflicts.apply_fact                                           │
 │         ├─ duplicate? ─▶ raise confidence                   (facts, events)       │
 │         ├─ new?       ─▶ insert fact + embedding            (facts, events)       │
 │         └─ replaces?  ─▶ insert, mark old as superseded     (facts, events)       │
 │  6. return [("update", "lives_in", "Milan")]                                      │
 └───────────────────────────────────────────────────────────────────────────────────┘
        all of steps 1 to 5 happen in ONE database transaction
```

Two kinds of knowledge result from one message:

- The **raw message** is always saved (including chit-chat), for the baseline comparison and future summarisation.
- **Facts** are saved only when the message contains something durable.

---

## 2. Step by step

| # | Step | Where | Writes to | Model calls |
|---|---|---|---|---|
| 1 | Ensure the user exists | `manager.py` | `users` | none |
| 2 | Embed and store the message | `manager.py` | `messages` | 1 embedding |
| 3 | Read the allowed relations | `extract.py` | nothing (read only) | none |
| 4 | Extract facts as validated JSON | `extract.py` | nothing | 1 structured chat |
| 5 | Clean the extracted list | `extract.py` | nothing | none |
| 6 | For each fact, compare with stored facts | `conflicts.py` | nothing yet | none |
| 7 | Duplicate, or insert, or supersede | `conflicts.py` | `facts`, `memory_events` | 1 embedding per new fact |
| 8 | Commit | `manager.py` | all of the above, together | none |

If anything fails in steps 1 to 7, the whole transaction rolls back, and nothing is saved.

---

## 3. `extract.py`: from text to facts

### 3.1 Data shapes

```python
class ExtractedFact(BaseModel):
    relation: str      # e.g. "lives_in"
    value: str         # e.g. "Milan"

class ExtractionResult(BaseModel):
    facts: list[ExtractedFact]
```

The model must answer in exactly this JSON shape (see `C_model_access.md`, structured output).

### 3.2 Functions

| Function | What it does |
|---|---|
| `load_relation_types(conn)` | Reads `relation_types` and returns `{name: (cardinality, description)}`. |
| `build_prompt(relations)` | Builds the system prompt, listing every allowed relation with its description. |
| `extract_facts(text, relations)` | Calls the LLM, then cleans and filters the result. |

### 3.3 Anatomy of the prompt

| Part | Content | Purpose |
|---|---|---|
| Role | "You extract long-term facts about the USER from one message." | Sets the task. |
| Allowed relations | One line per relation: `- lives_in: Current city or country of residence` | Built from the database, so adding a row to `relation_types` changes what the model can extract, without code changes. |
| Rules | Only things the user states about themselves; ignore questions, greetings, thanks; ignore temporary things; keep values short and normalised; "I moved to X" means `lives_in = X`; one item per fact; return an empty list if nothing durable | Keeps the output clean and consistent. |
| Examples | Three short examples: a message with two facts, a "thanks" message, and a question | Few-shot examples help small models follow the format. |

The user message is sent separately as `Message: "<text>"`.

### 3.4 Cleaning after the model answers

The model's answer is not trusted blindly. `extract_facts` then:

1. Trims whitespace from the relation and value.
2. **Drops any relation not in `relation_types`** (protects against invented relation names).
3. Drops empty values.
4. Removes duplicates within the same message (same relation and same value, ignoring case).

### 3.5 What the extractor is meant to do

| Input | Intended result | Risk to be aware of |
|---|---|---|
| "I live in Turin and I work at Acme as a software engineer." | `lives_in=Turin`, `works_at=Acme`, `job_title=software engineer` | Works in your demo. |
| "Thanks, that was really helpful!" | nothing | Works in your demo. |
| "What's a good recipe for carbonara?" | nothing | Works in your demo. |
| "I just moved to Milan!" | `lives_in=Milan` | Works in your demo. |
| "I'm vegetarian." | nothing (no matching relation) | A real gap. Adding a `diet` relation fixes it (section 9). |
| "I used to live in Turin." | should be nothing, or a past fact | **Risk:** may be extracted as `lives_in=Turin`, which would wrongly replace the current city. The prompt does not cover past tense. |
| "I might move to Rome next year." | should be nothing (or `goal`) | **Risk:** may be extracted as `lives_in=Rome`. |
| "My sister lives in Rome." | should be a family fact, not `lives_in` | **Risk:** may be extracted as `lives_in=Rome`. |
| "I don't like mushrooms." | `dislikes=mushrooms` | Negation handling depends on the model. |

Rows marked "Risk" are design risks, not confirmed failures. They are the first things to test when evaluating the extractor.

---

## 4. `conflicts.py`: from fact to decision

### 4.1 The decision

For each extracted fact, `apply_fact` returns one of three outcomes.

```
 new fact (relation R, value V)
        │
        ▼
 find ACTIVE facts with the same user + relation R
        │
        ├── any of them equal to V, or ≥ 0.8 similar? ──YES──▶  DUPLICATE
        │                                                        confidence +0.05, no new row
        │
        └── NO ──▶ insert V as a new active fact
                       │
                       ├── R is "single" AND older active values exist ──▶ UPDATE
                       │       old rows: status = superseded, valid_to = now,
                       │       superseded_by = new row
                       │
                       └── otherwise ──▶ ADD
```

### 4.2 Outcomes in detail

| Outcome | When | `facts` changes | `memory_events` |
|---|---|---|---|
| `duplicate` | Same value already active (exact match ignoring case, or trigram similarity of 0.8 or more) | Existing row: `confidence = min(1, confidence + 0.05)`, `updated_at = now()` | `duplicate`, with the existing fact's id |
| `add` | New value and no older value to replace (any `multi` relation, or the first value of a `single` one) | New active row | `add`, with the new fact's id |
| `update` | New value for a `single` relation that already had a different active value | New active row inserted; old active rows of that relation get `status = superseded`, `valid_to = now()`, `superseded_by = <new id>` | `update`, with details `{"relation", "old": [...], "new": ...}` |

### 4.3 Values written on a new fact

| Column | Value |
|---|---|
| `importance` | `DEFAULT_IMPORTANCE[relation]`, or 0.5 if the relation has no entry |
| `confidence` | 0.8 (the column default) |
| `status` | `active` |
| `valid_from` | now (the moment of insertion) |
| `source_message_id` | the message that produced it |
| `embedding` | embedding of text like `lives in: Milan` (the relation name with underscores replaced by spaces) |

### 4.4 Duplicate matching

The check uses the `pg_trgm` extension's `similarity()` function on lowercase text. Trigram similarity compares overlapping three-letter chunks, so it catches small spelling differences. A new value at or above 0.8 counts as the same fact. The threshold is `DUPLICATE_SIMILARITY` in `config.py`.

Order matters: the duplicate check runs **before** the embedding call, so duplicates cost no model call.

### 4.5 Subtle behaviours worth knowing

| Behaviour | Consequence |
|---|---|
| "Newest statement wins" for single-value relations | No judgement about which is more likely true. The `conflicted` status exists but is never used. |
| A duplicate keeps the **old** wording and the **old** source message | Only confidence and `updated_at` change. |
| Spelling variants of a single-value fact may not count as duplicates | "Milan" then "Milano" may be below 0.8, so the second one would replace the first. |
| Similar-but-different values in a `multi` relation are added separately | "cycling" and "road cycling" can both exist. |
| `valid_from` is the time of insertion, not the time the user said it | Not an issue live, but evaluation scenarios with backdated messages will need a timestamp parameter. |
| Superseded rows are never reactivated | If the user moves back to Turin, a new Turin row is inserted. That is correct, and the unique index allows it because the old row is not active. |

### 4.6 The audit log

`log_event(conn, user_id, event_type, fact_id, details)` writes one row to `memory_events` for each decision. Together with the superseded rows, this lets you reconstruct exactly what the system believed and when.

---

## 5. `manager.py`: orchestration

| Function | Purpose |
|---|---|
| `ingest_user_message(user_id, text)` | The whole write flow (section 1). Returns a list of `(outcome, relation, value)` tuples, for example `[("update", "lives_in", "Milan")]`. An empty list means nothing durable was found. |
| `list_facts(user_id, include_history=True)` | Reads facts for display: relation, value, status, importance, confidence and the `valid_from` time as text. With `include_history=False`, only active facts. |

Notes:

- The connection comes from the shared pool, and the `with` block means "commit if everything worked, roll back if anything raised an error".
- `ingest_user_message` takes only user messages. Assistant replies are deliberately not stored, so the system does not learn from its own guesses.
- `list_facts` sorts by relation, then by the `valid_from` **text**, which has minute resolution. When two facts share the same minute, their order is not defined. That is why Milan appeared above Turin in your demo output.

---

## 6. `scripts/demo_ingest.py`: the demo

### 6.1 What it does

1. Deletes the `demo` user, if present (cascade removes their data), so every run starts clean.
2. Feeds seven messages through `ingest_user_message`, printing each outcome.
3. Prints the final facts table through `list_facts`.

Run it:

```bash
cd ~/llm_mem_sys/memory-system
poetry run python scripts/demo_ingest.py
```

### 6.2 Walkthrough of your actual run

| # | Message | Outcomes | Database effect |
|---|---|---|---|
| 1 | "I live in Turin and I work at Acme as a software engineer." | ADD `lives_in=Turin`, ADD `works_at=Acme`, ADD `job_title=software engineer` | 1 message, 3 facts, 3 `add` events |
| 2 | "I love cycling and I'm allergic to penicillin." | ADD `hobby=cycling`, ADD `allergic_to=penicillin` | 1 message, 2 facts, 2 `add` events |
| 3 | "Thanks, that was really helpful!" | nothing durable | 1 message (with embedding), no facts |
| 4 | "What's a good recipe for carbonara?" | nothing durable | 1 message, no facts |
| 5 | "Big news: I just moved to Milan!" | UPDATE `lives_in=Milan` | 1 message, 1 new fact, Turin becomes `superseded`, 1 `update` event |
| 6 | "I also enjoy climbing these days." | ADD `hobby=climbing` | 1 message, 1 fact, 1 `add` event (hobby is multi-valued) |
| 7 | "I really love cycling, it's my main hobby." | DUPLICATE `hobby=cycling` | 1 message, no new fact, cycling confidence 0.80 to 0.85, 1 `duplicate` event |

Totals after the run:

| Table | Rows | Breakdown |
|---|---|---|
| `messages` | 7 | All seven, including the two chit-chat ones |
| `facts` | 7 | 6 active + 1 superseded (Turin) |
| `memory_events` | 8 | 6 `add`, 1 `update`, 1 `duplicate` |

Model calls in total: 7 structured extractions, and 14 embeddings (7 messages plus 7 new facts; the duplicate is not embedded).

### 6.4 Why the chit-chat messages matter later

Messages 3 and 4 produce no facts, but they stay in `messages`. The baseline retrieval cannot tell they are useless, and it returned them in your comparison ("Thanks, that was really helpful!" and the carbonara question). Smart retrieval reads only `facts`, so it never sees them. This is the clearest example of why separating messages from facts helps.

---

## 7. Design decisions

| Decision | Reason |
|---|---|
| **Extract only from the user's messages** | Stops the system from storing the assistant's own statements as facts. |
| **Allowed relations come from the database** | Extending what memory can learn is one SQL `INSERT`, with no code change. |
| **The LLM supplies only `relation` and `value`** | Small models are unreliable at scoring; importance and confidence are decided by deterministic rules. |
| **Validate and filter after the LLM answers** | The model's output is untrusted input. |
| **Duplicate check before the embedding call** | Saves a model call and avoids storing near-identical vectors. |
| **Supersede instead of overwrite** | Keeps history for later questions and for the audit trail. |
| **Whole write in one transaction** | A message, its facts and its events are saved together or not at all. |
| **Log every decision** | Makes behaviour explainable and measurable in the final evaluation. |
| **Store chit-chat messages too** | Needed as the raw material for the baseline comparison and future summaries. |

---

## 8. Known gaps

| Gap | Impact |
|---|---|
| Past, hypothetical and third-person statements are not handled | "I used to live in...", "I might move to...", "My sister lives in..." could create wrong facts. This is the biggest correctness risk in the write path. |
| Only 13 relation types | Many real statements ("I'm vegetarian") produce no fact. |
| "Newest wins" conflict rule | No detection of genuinely ambiguous cases, such as two jobs at once. `conflicted` is unused. |
| Single-message extraction | No context from earlier turns, so "yes, that's right" or "same as before" yields nothing. |
| No correction handling | "No, I meant Rome, not Milan" is not recognised as a correction of the last fact. |
| No timestamps parameter | Cannot yet ingest historical messages with their original dates, which the evaluation will need. |
| Confidence is just a counter | Repetition adds 0.05; it does not reflect how certain the statement was. |
| Extraction quality depends on the 8B model | Misses and wrong relations are possible, and there is no automatic test for them yet. |
| User text is placed in the prompt unescaped | A crafted message could try to steer the extractor. Relation validation limits the damage but does not remove it. |
| Transaction stays open during the LLM call | Safe, but would not scale to many simultaneous users. |
| No tests | `tests/` is empty, so nothing checks the logic automatically. |

---

## 9. Common changes

### Teach memory a new kind of fact

Example: dietary pattern, so "I'm vegetarian" becomes a fact.

```sql
INSERT INTO relation_types (name, cardinality, description)
VALUES ('diet', 'single', 'Dietary pattern, e.g. vegetarian, vegan');
```

Then add an importance entry in `config.py`:

```python
DEFAULT_IMPORTANCE = {
    ...,
    "diet": 0.75,
}
```

The extraction prompt picks up the new relation automatically, because it is built from the table. The description is what the model reads, so make it clear. Without a `DEFAULT_IMPORTANCE` entry, the fact still works with the fallback of 0.5.

### Make duplicates stricter or looser

Change `DUPLICATE_SIMILARITY` in `config.py`. Lower values merge more near-matches, and higher values keep more variants as separate facts.

### Improve extraction

Add a short few-shot example to `build_prompt` in `extract.py` for any case it gets wrong, for example a past-tense statement mapped to an empty list. Re-run `demo_ingest.py` and the extractor-only snippet in section 3.6 to check the change.

### Inspect the decisions

```sql
SELECT created_at, event_type, details
FROM memory_events WHERE user_id = 'demo' ORDER BY id;
```

### Reset

```sql
DELETE FROM users WHERE id = 'demo';
```

---

## 10. Where the write path connects to the rest

| Connects to | How |
|---|---|
| **B. Storage design** | Writes to `users`, `messages`, `facts`, `memory_events`, and reads `relation_types`. |
| **C. Model access** | Uses `embed` (message and fact vectors), `chat_structured` (extraction), `get_pool` (transactions), and the importance and duplicate settings in `config.py`. |
| **E. Read path** | Produces the active and superseded facts that retrieval ranks. Retrieval reads only `status = 'active'` rows. |
| **F. Experiments** | `chat.py` calls `ingest_user_message` after each answer, so memory updates as you talk. |
| **G. Not started** | Summaries will consume old `messages`; smarter conflict handling will use the unused `conflicted` status and event type. |
