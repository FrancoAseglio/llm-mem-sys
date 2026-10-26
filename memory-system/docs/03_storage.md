# 3. Storage design (the database)

`schema.sql` is the single source of truth. It creates everything on a fresh database.

## 1. Big picture

Memory has three layers, as in the project proposal:

| Layer | Table | Holds | Status |
|---|---|---|---|
| Recent memory | `messages` | Raw things the user said | In use |
| Fact memory | `facts` | Clean, dated, versioned statements ("lives in Milan") | In use |
| Summary memory | `summaries` | One-sentence episode notes written from messages; see [07_summaries.md](07_summaries.md) | In use. Not yet a compression of old history |

Supporting tables hold the rules and the bookkeeping:

| Table | Job | Status |
|---|---|---|
| `users` | One row per person; owns everything below | In use |
| `relation_types` | The allowed kinds of fact, one value or many, and routing text | In use |
| `memory_events` | Audit log of every decision the system makes | In use |
| `relations` | Knowledge-graph edges between entities | Table exists, not used yet |

## 2. Table reference

### 2.1 `users`

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT, primary key | Any string (`demo`, `franco`). No login system; it is a label. |
| `created_at` | TIMESTAMPTZ | Defaults to now. |

Every other table points here with `ON DELETE CASCADE`, so deleting a user deletes all their data in one statement.

### 2.2 `relation_types`

The rulebook for facts. A fact can only use a relation listed here (a foreign key enforces it).

| Column | Type | Notes |
|---|---|---|
| `name` | TEXT, primary key | For example `lives_in`. |
| `cardinality` | TEXT, `single` or `multi` | `single`: one current value at a time. `multi`: many values can be true together. |
| `description` | TEXT | Shown to the model in the extraction prompt, and embedded for routing in retrieval. Wording matters. |
| `routing_hint` | TEXT, optional | Extra text appended to the description when the question is matched to relation types. Only `dislikes` and `allergic_to` have one. |

Seeded with 13 rows:

| Cardinality | Relations |
|---|---|
| `single` (6) | `name`, `lives_in`, `works_at`, `job_title`, `partner`, `birthday` |
| `multi` (7) | `hobby`, `likes`, `dislikes`, `allergic_to`, `family_member`, `speaks`, `goal` |

This table is what lets the system tell a replacement from an addition: a new `lives_in` replaces the old one, a new `hobby` sits next to the others.

### 2.3 `messages`

| Column | Type | Notes |
|---|---|---|
| `id` | BIGSERIAL, primary key | |
| `user_id` | TEXT, foreign key to `users` | Cascade delete. |
| `session_id` | TEXT | Reserved for grouping a conversation. Never set. |
| `role` | TEXT, `user` or `assistant` | Only `user` rows are stored. |
| `content` | TEXT | The raw text. |
| `embedding` | vector(768) | Meaning of the text; used by baseline retrieval. |
| `importance` | REAL, 0 to 1, default 0.2 | Reserved. Not used. |
| `archived` | BOOLEAN, default false | Reserved: would mark a message replaced by a digest. Not used. |
| `summary_id` | BIGINT, foreign key to `summaries` | The note written from this message; set by the summaries layer, which links a message to one note only. `ON DELETE SET NULL`. The raw message is kept. |
| `created_at` | TIMESTAMPTZ | When it was said. Evaluation scenarios backdate it. |

Messages are stored even when they produce no fact, including chit-chat.

### 2.4 `facts` (the core table)

| Column | Type | Notes |
|---|---|---|
| `id` | BIGSERIAL, primary key | |
| `user_id` | TEXT, foreign key | Cascade delete. |
| `subject` | TEXT, default `user` | Who the fact is about. Always `user` today. |
| `relation` | TEXT, foreign key to `relation_types` | The kind of fact. |
| `value` | TEXT | The content (`Milan`, `cycling`), free text, not normalised. |
| `importance` | REAL, 0 to 1, default 0.5 | Set from `DEFAULT_IMPORTANCE` in `config.py` by relation (allergy 0.95, hobby 0.40). Not taken from the model. |
| `confidence` | REAL, 0 to 1, default 0.8 | Rises by 0.05 each time the same fact is repeated, capped at 1. |
| `status` | TEXT | `active`, `superseded`, `conflicted` or `archived`. See section 4. |
| `valid_from` | TIMESTAMPTZ | When the fact became true in memory. |
| `valid_to` | TIMESTAMPTZ | When it stopped. Set when superseded or archived. |
| `superseded_by` | BIGINT, self-reference | The fact that replaced this one. `ON DELETE SET NULL`. |
| `source_message_id` | BIGINT, foreign key to `messages` | The message the fact came from. `ON DELETE SET NULL`. |
| `access_count` | INTEGER, default 0 | How many times retrieval used this fact. |
| `last_accessed_at` | TIMESTAMPTZ | Last time retrieval used it. |
| `embedding` | vector(768) | Embedding of text like `lives in: Milan`; used by smart retrieval. |
| `created_at`, `updated_at` | TIMESTAMPTZ | `updated_at` changes on duplicates, supersession, archiving and conflict marking. |

### 2.5 `summaries`

| Column | Type | Notes |
|---|---|---|
| `id` | BIGSERIAL, primary key | |
| `user_id` | TEXT, foreign key | Cascade delete. |
| `topic` | TEXT | Short label. Not used. |
| `content` | TEXT | The note: one sentence starting "The user" or "The user's". |
| `period_start`, `period_end` | TIMESTAMPTZ | Oldest and newest date of the messages it was written from. The newest date is shown in the prompt ("Note from ..."). |
| `importance` | REAL, 0 to 1, default 0.3 | Not used: notes are not ranked by it. |
| `embedding` | vector(768) | Embedding of the note; notes are retrieved by meaning. |
| `created_at` | TIMESTAMPTZ | |

### 2.6 `relations` (not used yet)

Edges for a lightweight knowledge graph: `source` -- `relation` --> `target`, with `valid_from`, `valid_to` and an optional `fact_id` back to the fact that created it. Nothing reads or writes it; typed facts play the role of the graph for now.

### 2.7 `memory_events`

| Column | Type | Notes |
|---|---|---|
| `id` | BIGSERIAL, primary key | |
| `user_id` | TEXT, foreign key | Cascade delete. |
| `event_type` | TEXT | One of the types below. |
| `fact_id` | BIGINT, foreign key to `facts` | The fact concerned, if any. `ON DELETE SET NULL`. |
| `details` | JSONB | Free-form context, for example `{"relation": "lives_in", "old": ["Turin"], "new": "Milan"}`. |
| `created_at` | TIMESTAMPTZ | |

| Event type | Written when |
|---|---|
| `add` | A new fact is stored |
| `duplicate` | A fact already known is repeated; confidence goes up |
| `update` | A single-valued fact is replaced; old rows are superseded |
| `contradiction` | A like/hobby meets a matching dislike, or the reverse; the older one is superseded |
| `retract` | The user said something is not true; the matching fact is archived (or nothing matched) |
| `conflict` | A dependent fact (job title) is marked conflicted because its key fact (employer) changed |
| `reject` | A value was thrown away: not grounded in the message, or extraction failed; also a failed summarisation call (`reason`: `summarization failed`) |
| `retrieve` | A fact or episode note was used to answer a question (`details` lists the summary ids for notes) |
| `summarize` | One summary run over a batch of messages. `details`: `up_to` (last message id seen, which is where the next run starts), `messages`, `skipped` (questions, requests and thanks), `kept` (summary ids), `dropped` (sentences thrown away with the reason) |
| `archive` | Reserved. Not written yet. |

## 3. Indexes and constraints

| Index | On | Purpose |
|---|---|---|
| `messages_embedding_idx` | `messages.embedding`, HNSW, cosine | Fast nearest-neighbour search over messages (baseline retrieval) |
| `facts_embedding_idx` | `facts.embedding`, HNSW, cosine | Reserved: smart retrieval currently loads a user's active facts and scores them in Python, which is fine for small data |
| `summaries_embedding_idx` | `summaries.embedding`, HNSW, cosine | Reserved: note retrieval computes the similarity of all of a user's notes in one query and does not use the index |
| `facts_lookup_idx` | `facts (user_id, subject, relation)` where active | Fast lookups of current values during conflict checks |
| `facts_value_trgm_idx` | `facts.value`, GIN trigram | Fuzzy text matching |
| `messages_user_time_idx` | `messages (user_id, created_at DESC)` | Newest-first listing |
| `events_user_time_idx` | `memory_events (user_id, created_at DESC)` | Newest-first listing |

HNSW is an approximate nearest-neighbour index: very fast, with a tiny loss in recall. `vector_cosine_ops` matches the `<=>` cosine-distance operator used in queries.

### The duplicate guard

```sql
CREATE UNIQUE INDEX facts_unique_active
    ON facts (user_id, subject, relation, lower(value))
    WHERE status = 'active';
```

A user cannot have two active facts with the same relation and the same value (ignoring case). Superseded and archived rows are exempt, so history can repeat values (Milan, then Rome, then Milan again).

### What happens on delete

| Deleting... | Effect |
|---|---|
| A user | Cascades: all their messages, facts, summaries, relations and events go too. |
| A message | Facts that came from it stay, with `source_message_id` set to NULL. |
| A summary | Messages it covered stay, with `summary_id` set to NULL. |
| A fact | Events and relations that referenced it stay, with `fact_id` set to NULL. A fact it replaced loses its `superseded_by` link. |

## 4. Life of a fact

### Status values

| Status | Meaning | Set by | Read by retrieval |
|---|---|---|---|
| `active` | Currently believed true | A new, non-duplicate fact | Yes, the only status read |
| `superseded` | Was true, replaced by a newer value | A new value for a single relation, or a contradicting like/dislike | Only for questions about the past ([06](06_read_path.md), section 10) |
| `archived` | The user said it is no longer true | A retraction ("I'm not a teacher anymore") | No |
| `conflicted` | Cannot be trusted any more, but not known to be false | The key fact changed: a new employer makes the job title conflicted | No |

A later statement can bring a conflicted fact back: restating the job title supersedes the conflicted row with a new active one.

### Worked example: Turin to Milan

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

Nothing is deleted. The old row records what was believed, from when, until when, and what replaced it, and the log gets an `update` event.

### Outcomes for a new fact

| Situation | Outcome |
|---|---|
| Same relation, same or near-identical value already active | `duplicate`: confidence +0.05, no new row |
| `multi` relation, new value | `add`: a new active row next to the others |
| `single` relation, different value | `update`: new row inserted, old rows `superseded` |
| Like meets matching dislike (or reverse) | `contradiction`: new row inserted, the opposite `superseded` |
| User retracts a matching active fact | `retract`: the fact is `archived` |
| Employer changes and no title is restated | `update` or `retract` as above, plus the job title becomes `conflicted` |

"Near-identical" means trigram similarity of 0.8 or more (`DUPLICATE_SIMILARITY`). The full rules are in [05_write_path.md](05_write_path.md).

## 5. How data moves through the tables

| Event | Writes | Reads |
|---|---|---|
| User sends a message | `users` (if missing), `messages` with embedding | `relation_types` (to build the extraction prompt) |
| A fact is applied | `facts` (insert, confidence, status changes), `memory_events` | `relation_types`, existing `facts` of the same relation |
| Smart retrieval | `facts` (`access_count`, `last_accessed_at` of the facts used), `memory_events` (`retrieve`) | Active `facts`, `relation_types` |
| Baseline retrieval | nothing | `messages` by embedding distance |

Retrieval counts as a write because using a fact reinforces it. `evaluate.py` and `inspect_scores.py` read without touching, so measuring does not change memory.

## 6. Design decisions

| Decision | Reason |
|---|---|
| Supersede, never overwrite | Keeps history and an audit trail; makes "where did I live in June?" answerable later |
| A `status` column instead of separate history tables | One query shape; retrieval filters on `status = 'active'` |
| `relation_types` as a table | The cardinality rule lives in data; a new kind of fact is one `INSERT`; the foreign key keeps junk relation names out |
| Importance set by relation, not by the model | The 8B model rated nearly everything 1.0, which made importance useless |
| Embeddings on messages and facts | Messages serve the baseline comparison; facts serve smart retrieval |
| `valid_from` / `valid_to` as `TIMESTAMPTZ` | Time-aware facts, unambiguous across time zones |
| Partial unique index for active duplicates | The database itself prevents double-storing, not just the Python code |
| `memory_events` log | Every decision is traceable, which debugging and evaluation need |
| `TEXT` user ids | Simple for a prototype; a product would use UUIDs and real authentication |
| `ON DELETE CASCADE` from users | One statement resets or removes a user completely |
| Assistant replies are not stored | So the system does not "remember" its own guesses as facts |

## 7. Known gaps

| Gap | Impact |
|---|---|
| Only 13 relation types | "I'm vegetarian" is stored as a message and was filed as `hobby = vegetarianism` (seen in a manual chat): information outside the 13 types is dropped or forced into the nearest type. A row in `relation_types` fixes one such case. |
| `value` is free text | "Milan" and "Milano" count as different unless trigram matching catches them |
| `relations`, `summaries.topic/importance`, `messages.session_id/importance/archived` unused | Waiting for the graph feature and for consolidation of notes |
| A retraction cannot reach a `conflicted` fact | After an employer change, "I'm not a nurse anymore" logs a miss because the title is no longer active |
| `subject` is always `user` | No facts about other people |
| No rule ties `status` to `valid_to` | The code sets them together; the database would not stop an inconsistent row |
| Embedding size fixed at 768 | Changing the embedding model means recreating tables and re-embedding |

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
FROM memory_events WHERE user_id = 'demo' 
ORDER BY id 
DESC LIMIT 15;
```

```sql
-- Which message produced each fact
SELECT f.relation, f.value, f.status, m.content AS source_message
FROM facts f LEFT JOIN messages m ON m.id = f.source_message_id  
WHERE f.user_id = 'demo';
```

```sql
-- Add a new kind of fact (needs a DEFAULT_IMPORTANCE entry in config.py)
INSERT INTO relation_types (name, cardinality, description)
VALUES ('diet', 'single', 'Dietary pattern, e.g. vegetarian, vegan');
```

```sql
-- Reset one user completely
DELETE FROM users WHERE id = 'demo';
```

Use `\x auto` in `psql` for readable wide rows.
