# B. Storage design (the database)

## 1. Big picture

Memory is split into three layers, matching the proposal:

| Layer | Table | Holds | Status |
|---|---|---|---|
| Recent memory | `messages` | Raw things the user said | In use |
| Fact memory | `facts` | Clean, dated, versioned statements ("lives in Milan") | In use |
| Summary memory | `summaries` | Condensed digests of old messages | Table exists, not used yet |

Three supporting tables hold the rules and bookkeeping:

| Table | Job | Status |
|---|---|---|
| `users` | One row per person, owns everything below | In use |
| `relation_types` | The allowed kinds of fact, and whether each holds one value or many | In use |
| `memory_events` | Audit log of every decision the system makes | In use |
| `relations` | Knowledge-graph edges between entities | Table exists, not used yet |

---

## 2. Table reference

### 2.1 `users`

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT, primary key | Any string you choose (`demo`, `franco`).  No login system, it is just a label. |
| `created_at` | TIMESTAMPTZ | Defaults to now. |

Every other table points here with `ON DELETE CASCADE`, so **deleting a user deletes all their data** in one statement.

### 2.2 `relation_types`

The rulebook for facts.  
A fact can only use a relation listed here (enforced by a foreign key).

| Column | Type | Notes |
|---|---|---|
| `name` | TEXT, primary key | For example `lives_in`. |
| `cardinality` | TEXT, `single` or `multi` | `single` = one current value at a time. `multi` = many values can be true together. |
| `description` | TEXT | Shown to the LLM in the extraction prompt, so wording matters. |

Seeded with 13 rows:

| Cardinality | Relations |
|---|---|
| `single` (6) | `name`, `lives_in`, `works_at`, `job_title`, `partner`, `birthday` |
| `multi` (7) | `hobby`, `likes`, `dislikes`, `allergic_to`, `family_member`, `speaks`, `goal` |

Why this table exists: it is what lets the system tell a **replacement** from an **addition**.  
A new `lives_in` replaces the old one.  
A new `hobby` sits next to the others.

### 2.3 `messages`

| Column | Type | Notes |
|---|---|---|
| `id` | BIGSERIAL, primary key | |
| `user_id` | TEXT, foreign key to `users` | Cascade delete. |
| `session_id` | TEXT | Reserved for grouping a conversation. **Never set yet.** |
| `role` | TEXT, `user` or `assistant` | Only `user` rows are stored today. |
| `content` | TEXT | The raw text. |
| `embedding` | vector(768) | Meaning of the text as 768 numbers. Used by the baseline retrieval. |
| `importance` | REAL, 0 to 1, default 0.2 | Reserved for compression decisions. Not used yet. |
| `archived` | BOOLEAN, default false | Reserved: set true once a message is summarised. Not used yet. |
| `summary_id` | BIGINT, foreign key to `summaries` | Reserved: which summary absorbed this message. `ON DELETE SET NULL`. Not used yet. |
| `created_at` | TIMESTAMPTZ | When it was said. |

### 3.4 `facts` (the core table)

| Column | Type | Notes |
|---|---|---|
| `id` | BIGSERIAL, primary key | |
| `user_id` | TEXT, foreign key | Cascade delete. |
| `subject` | TEXT, default `user` | Who the fact is about. Always `user` today. |
| `relation` | TEXT, foreign key to `relation_types` | The kind of fact. |
| `value` | TEXT | The content: `Milan`, `cycling`. Stored as free text, not normalised. |
| `importance` | REAL, 0 to 1, default 0.5 | Set from a table in `config.py` by relation (allergy 0.95, hobby 0.40). **Not** taken from the LLM. |
| `confidence` | REAL, 0 to 1, default 0.8 | Rises by 0.05 each time the same fact is repeated, capped at 1. |
| `status` | TEXT | `active`, `superseded`, `conflicted` or `archived`. See section 5. |
| `valid_from` | TIMESTAMPTZ, default now | When the fact became true in memory. |
| `valid_to` | TIMESTAMPTZ | When it stopped being true. Set when superseded. |
| `superseded_by` | BIGINT, self-reference to `facts` | Points to the fact that replaced this one. `ON DELETE SET NULL`. |
| `source_message_id` | BIGINT, foreign key to `messages` | The message the fact was extracted from. `ON DELETE SET NULL`. |
| `access_count` | INTEGER, default 0 | How many times retrieval has used this fact. |
| `last_accessed_at` | TIMESTAMPTZ | Last time retrieval used it. |
| `embedding` | vector(768) | Embedding of text like `lives in: Milan`. Used by smart retrieval. |
| `created_at`, `updated_at` | TIMESTAMPTZ | `updated_at` is bumped on duplicates and supersession. |

### 2.5 `summaries` (not used yet)

| Column | Type | Notes |
|---|---|---|
| `id` | BIGSERIAL, primary key | |
| `user_id` | TEXT, foreign key | Cascade delete. |
| `topic` | TEXT | Short label for what the summary covers. |
| `content` | TEXT | The summary text. |
| `period_start`, `period_end` | TIMESTAMPTZ | Date range of the messages it replaces. |
| `importance` | REAL, 0 to 1, default 0.3 | |
| `embedding` | vector(768) | So summaries can be retrieved by meaning. |
| `created_at` | TIMESTAMPTZ | |

Planned job: a background process groups old, low-importance messages, writes a summary, marks the messages `archived`, and links them through `messages.summary_id`.

### 2.6 `relations` (not used yet)

Edges for a lightweight knowledge graph: `source` -- `relation` --> `target` (for example `user` -- `sister_of` --> `Anna`), with `valid_from`, `valid_to` and an optional `fact_id` linking back to the fact that created it.  
It exists so family and social links can be queried as a graph later, but nothing writes to it today.

### 2.7 `memory_events`

| Column | Type | Notes |
|---|---|---|
| `id` | BIGSERIAL, primary key | |
| `user_id` | TEXT, foreign key | Cascade delete. |
| `event_type` | TEXT | One of `add`, `duplicate`, `update`, `conflict`, `summarize`, `archive`, `retrieve`. |
| `fact_id` | BIGINT, foreign key to `facts` | Which fact it concerns, if any. `ON DELETE SET NULL`. |
| `details` | JSONB | Free-form context, for example `{"relation": "lives_in", "old": ["Turin"], "new": "Milan"}`. |
| `created_at` | TIMESTAMPTZ | |

Event types in use today: `add`, `duplicate`, `update`, `retrieve`.  
The types `conflict`, `summarize` and `archive` are reserved for features not built yet.

---

## 3. Indexes and constraints

### 3.1 Indexes

| Index | On | Purpose |
|---|---|---|
| `messages_embedding_idx` | `messages.embedding`, HNSW, cosine | Fast nearest-neighbour search over messages (baseline retrieval). |
| `facts_embedding_idx` | `facts.embedding`, HNSW, cosine | Same for facts. **Not exercised yet:** smart retrieval currently loads all of a user's active facts and scores them in Python, which is fine for small data. |
| `summaries_embedding_idx` | `summaries.embedding`, HNSW, cosine | For future summary retrieval. |
| `facts_lookup_idx` | `facts (user_id, subject, relation)` where `status = 'active'` | Fast "what do we currently know about this relation" lookups during conflict checks. Partial index, so it ignores history. |
| `facts_value_trgm_idx` | `facts.value`, GIN trigram | Speeds up fuzzy text matching. |
| `messages_user_time_idx` | `messages (user_id, created_at DESC)` | Newest-first message listing per user. |
| `events_user_time_idx` | `memory_events (user_id, created_at DESC)` | Newest-first event listing per user. |

HNSW is an approximate nearest-neighbour index: very fast, with tiny recall loss. `vector_cosine_ops` matches the `<=>` cosine-distance operator used in queries.

### 3.2 The duplicate guard

```sql
CREATE UNIQUE INDEX facts_unique_active
    ON facts (user_id, subject, relation, lower(value))
    WHERE status = 'active';
```

A user cannot have two **active** facts with the same relation and the same value (ignoring case). Superseded or archived rows are exempt, so history can repeat values freely (for example living in Milan, then Rome, then Milan again).

### 3.4 What happens on delete

| Deleting... | Effect |
|---|---|
| A `user` | Cascades: all their messages, facts, summaries, relations and events go too. |
| A `message` | Facts that came from it stay, with `source_message_id` set to NULL. |
| A `summary` | Messages it covered stay, with `summary_id` set to NULL. |
| A `fact` | Events and relations that referenced it stay, with `fact_id` set to NULL. A fact that it replaced loses its `superseded_by` link. |

---

## 4. Life of a fact

### 4.1 Status values

| Status | Meaning | Used today |
|---|---|---|
| `active` | Currently believed true. The only status that retrieval reads. | Yes |
| `superseded` | Was true, replaced by a newer value. Kept as history. | Yes |
| `conflicted` | Two incompatible facts and the system cannot tell which is right. | Not yet |
| `archived` | Old and unimportant, retired from normal use. | Not yet |

### 4.2 Worked example: Turin to Milan

Message 1: "I live in Turin..." Message 5: "Big news: I just moved to Milan!"

After message 1:

| id | relation | value | status | valid_from | valid_to | superseded_by |
|---|---|---|---|---|---|---|
| 1 | lives_in | Turin | active | t1 | NULL | NULL |

After message 5 (`lives_in` is `single`, so the new value replaces the old):

| id | relation | value | status | valid_from | valid_to | superseded_by |
|---|---|---|---|---|---|---|
| 1 | lives_in | Turin | superseded | t1 | t5 | 7 |
| 7 | lives_in | Milan | active | t5 | NULL | NULL |

Nothing is deleted.  
The old row records **what was believed, from when, until when, and what replaced it**.  
The log gets an `update` event with `{"old": ["Turin"], "new": "Milan"}`.

### 4.3 Duplicate and multi-value behaviour

| Situation | Outcome |
|---|---|
| Same relation and same (or near-identical) value already active | `duplicate`: `confidence` goes up by 0.05, `updated_at` is bumped, no new row. |
| `multi` relation with a new value | `add`: new active row next to the others. |
| `single` relation with a different value | `update`: new row inserted, old rows marked `superseded`. |
| Brand-new relation for this user | `add`. |

"Near-identical" means trigram similarity of 0.8 or more (a setting in `config.py`).

---

## 5. How data moves through the tables

| Event | Writes | Reads |
|---|---|---|
| User sends a message | `users` (create if missing), `messages` (+ embedding) | `relation_types` (to build the extraction prompt) |
| A fact is extracted | `facts` (insert), `memory_events` | `relation_types`, existing active `facts` for the same relation |
| A fact is a duplicate | `facts` (confidence, `updated_at`), `memory_events` | existing active `facts` |
| A single-value fact is replaced | `facts` (insert new, mark old superseded), `memory_events` | existing active `facts` |
| Smart retrieval | `facts` (`access_count`, `last_accessed_at` for the facts it uses), `memory_events` (`retrieve`) | active `facts` for the user |
| Baseline retrieval | nothing | `messages` by embedding distance |

Retrieval counts as a write because using a fact reinforces it.  
The `compare.py` script avoids this on purpose, so comparing does not change memory.

---

## 6. Design decisions

| Decision | Reason |
|---|---|
| **Supersede, never overwrite** | Keeps history and an audit trail, and makes questions like "where did I live in June?" answerable later. |
| **A `status` column instead of separate tables for old facts** | One query shape for everything. Retrieval just filters on `status = 'active'`. |
| **`relation_types` as a table, not a hard-coded list** | The cardinality rule lives in data. Adding a new kind of fact is one `INSERT`, and the foreign key keeps junk relation names out. |
| **Importance set by relation, not by the LLM** | The 8B model rated nearly everything 1.0, which made importance useless. |
| **Embeddings on both `messages` and `facts`** | Messages serve the baseline comparison. Facts serve smart retrieval. Same database, same index type. |
| **`valid_from` / `valid_to` with `TIMESTAMPTZ`** | Time-aware facts, unambiguous across time zones. |
| **Partial unique index for active duplicates** | The database itself prevents double-storing, not just the Python code. |
| **`memory_events` log** | Every decision is traceable, which is essential for debugging and for the final evaluation. |
| **`TEXT` ids for users** | Simple and readable for a prototype. A real product would use UUIDs and real authentication. |
| **`ON DELETE CASCADE` from users** | One statement resets or removes a user completely. |
| **`BIGSERIAL` ids** | Auto-incrementing, simple, and big enough for any prototype. |

---

## 7. Known limits and gaps

| Gap | Impact |
|---|---|
| Only 13 relation types | A message like "I'm vegetarian" is stored as a message but produces no fact, because no relation fits. Adding rows to `relation_types` fixes this. |
| `value` is free text | "Milan" and "Milano" count as different values unless they are close enough for trigram matching to catch. |
| `conflicted` and `archived` statuses unused | Contradictions are resolved by "newest wins", not flagged. |
| `summaries`, `relations` unused; `messages.importance`, `archived`, `summary_id`, `session_id` unused | Waiting for the compression and graph features. |
| Assistant replies are not stored | Deliberate, so the system does not "remember" its own guesses as facts. |
| `subject` is always `user` | No facts about other people yet. |
| `facts_embedding_idx` unused for now | Becomes useful when a user has thousands of facts. |
| Embedding size fixed at 768 | Changing the embedding model means changing every `vector(768)`, recreating tables and re-embedding. |
| No rule linking `status` and `valid_to` | The code sets them together, but the database would not stop an inconsistent row. |

---

## 8. Handy queries

```sql
-- Current beliefs about a user
SELECT relation, value, importance, confidence
FROM facts
WHERE user_id = 'demo' AND status = 'active'
ORDER BY relation;
```
```sql
-- Full history of one relation
SELECT id, value, status, valid_from, valid_to, superseded_by
FROM facts
WHERE user_id = 'demo' AND relation = 'lives_in'
ORDER BY valid_from;
```
```sql
-- What the system decided, newest first
SELECT created_at, event_type, details
FROM memory_events
WHERE user_id = 'demo'
ORDER BY id DESC
LIMIT 15;
```
```sql
-- Which message produced each fact
SELECT f.relation, f.value, m.content AS source_message
FROM facts f
LEFT JOIN messages m ON m.id = f.source_message_id
WHERE f.user_id = 'demo';
```
```sql
-- Most used facts
SELECT relation, value, access_count, last_accessed_at
FROM facts
WHERE user_id = 'demo'
ORDER BY access_count DESC;
```
```sql
-- Add a new kind of fact (example)
INSERT INTO relation_types (name, cardinality, description)
VALUES ('diet', 'single', 'Dietary pattern, e.g. vegetarian');
```
```sql
-- Reset one user completely
DELETE FROM users WHERE id = 'demo';
```

Use `\x auto` for readable wide rows.

---
