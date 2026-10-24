# E. Read path (using memory when answering)

Everything that happens between "the user asks something" and "the model answers with memory in its prompt". The write path (category D) builds the memory. The read path decides which small part of it the model gets to see.

| File | Job |
|---|---|
| `src/memory_system/retrieve.py` | Smart ranked retrieval over facts, plus the plain vector baseline over messages |
| `src/memory_system/assistant.py` | Formats the chosen memories as text and builds the final prompt |

Used by `scripts/chat.py` (interactive) and `scripts/compare.py` (side-by-side test), both covered in category F.

---

## 1. The flow at a glance

```
 user question: "What's the weather like where I live?"
        │
        ▼
 assistant.recall(mode, user, question)
        │
        ├─ mode = smart ───▶ retrieve.retrieve()          reads: facts (active only)
        ├─ mode = baseline ─▶ retrieve.retrieve_baseline() reads: messages (user role)
        └─ mode = none ────▶ nothing
        │
        ▼
 list of memory lines  ["Lives in: Milan (since 2026-10-24)", ...]
        │
        ▼
 assistant.build_messages(mode, lines, history, question)
        │
        ▼
 [system prompt with memory] + [recent chat history] + [question]
        │
        ▼
 chat model (Ollama)  ──▶  answer
```

Retrieval happens **before** the model answers. Learning from the same message (write path) happens **after**, so the question never retrieves itself.

---

## 2. The three modes

| Mode | Memory source | What reaches the prompt |
|---|---|---|
| `smart` | `facts` table, only `status = 'active'` | A few ranked, filtered facts, formatted as short lines |
| `baseline` | `messages` table, role `user` | The top k most similar past messages, whatever they are |
| `none` | nothing | No memory block at all |

`baseline` imitates the common "vector memory" approach, so it is the control group. `none` shows what the model does with no help.

---

## 3. `retrieve.py`: smart retrieval

### 3.1 The result type

```python
@dataclass
class Memory:
    id: int            # facts.id
    relation: str      # "lives_in"
    value: str         # "Milan"
    since: datetime    # facts.valid_from
    score: float       # final ranking score
    pinned: bool       # included regardless of score
    parts: dict        # the five components, for debugging
```

### 3.2 Step by step

`retrieve(user_id, query, k=4, touch=True)`:

| # | Step |
|---|---|
| 1 | Embed the query (1 embedding call). |
| 2 | Load **every active fact** for the user, with its cosine similarity to the query computed by Postgres (`1 - (embedding <=> query)`). |
| 3 | For each fact, compute five components (section 3.3) and combine them into one score. |
| 4 | Sort by score, highest first. |
| 5 | Select: all **pinned** facts, plus the top `k` non-pinned facts whose score is at least `MIN_SCORE`. |
| 6 | If `touch=True`: bump `access_count` and `last_accessed_at` on the selected non-pinned facts, and log a `retrieve` event. |
| 7 | Return pinned facts first, then the rest in score order. |

Superseded facts (such as Turin) are never loaded, which is the main reason stale information cannot reach the prompt.

### 3.3 The five score components

Each component is between 0 and 1.

| Component | How it is computed | Meaning |
|---|---|---|
| `similarity` | raw cosine similarity, rescaled: `clamp((raw - SIM_FLOOR) / (SIM_CEIL - SIM_FLOOR))` | How related the fact is to the question |
| `importance` | the fact's stored `importance` | How much this kind of fact matters (allergy 0.95, hobby 0.40) |
| `recency` | `0.5 ** (age_days / RECENCY_HALF_LIFE_DAYS)` | How recently the fact was created, repeated or used |
| `usage` | `min(1, ln(1 + access_count) / ln(11))` | How often retrieval has used it |
| `confidence` | the fact's stored `confidence` | How established it is (rises with repetition) |

Age for recency is measured from the later of `updated_at` and `last_accessed_at`. So restating a fact (duplicate) or using it in an answer both make it "fresh" again.

### 3.4 The formula

```
score = 0.40 × similarity
      + 0.25 × importance
      + 0.20 × recency
      + 0.10 × usage
      + 0.05 × confidence
```

Weights come from `WEIGHTS` in `config.py`.

### 3.5 Worked example from your own run

Question: "What's the weather like where I live?"

| Fact | similarity | importance | recency | usage | confidence | Calculation | Score |
|---|---|---|---|---|---|---|---|
| lives_in = Milan | 0.40 | 0.70 | 1.00 | 0.00 | 0.80 | 0.16 + 0.175 + 0.20 + 0 + 0.04 | **0.575** |
| allergic_to = penicillin | 0.00 | 0.95 | 1.00 | 0.00 | 0.80 | 0 + 0.2375 + 0.20 + 0 + 0.04 | **0.478** |

- Milan passes `MIN_SCORE` (0.50), so it is included on merit. Its normalised similarity of 0.40 corresponds to a raw similarity of about 0.51.
- Penicillin scores below 0.50, but it is **pinned** (importance 0.95 is at least `PIN_IMPORTANCE` 0.90), so it is included anyway.
- Facts like `works_at = Acme` and the hobbies scored below 0.50 and were left out.

### 3.6 Selection rules

| Rule | Detail |
|---|---|
| Pinned facts | Every active fact with importance of at least `PIN_IMPORTANCE` (0.90) is always returned. With the default importance table, that is only `allergic_to`. |
| Threshold | Other facts need a score of at least `MIN_SCORE` (0.50). |
| Limit | At most `k` non-pinned facts. Pinned facts are extra, so the total can exceed `k`. |
| Empty result | If nothing passes, the memory list is empty and the prompt contains no memory block. |

### 3.7 What similarity a fact needs to pass

For a fresh fact (recency 1.0, confidence 0.8, never used), the minimum similarity needed to reach 0.50 depends on its importance:

| Importance | Example relation | Normalised similarity needed | Raw cosine similarity needed |
|---|---|---|---|
| 0.80 | family_member, partner | 0.15 | about 0.41 |
| 0.70 | lives_in | 0.21 | about 0.44 |
| 0.60 | works_at, job_title | 0.28 | about 0.46 |
| 0.50 | goal, speaks | 0.34 | about 0.49 |
| 0.40 | hobby, likes | 0.40 | about 0.51 |

Important facts need a weaker match to be included, and trivial facts need a stronger one. That is the intended effect of the importance weight.

### 3.8 How recency fades

`recency = 0.5 ^ (age / 90 days)`:

| Age | Recency |
|---|---|
| 0 days | 1.00 |
| 30 days | 0.79 |
| 90 days | 0.50 |
| 180 days | 0.25 |
| 365 days | 0.06 |

**Known problem (see section 9):** because recency contributes a flat 0.20 to a fresh fact's score and the threshold is 0.50, old facts get harder to retrieve over time. For `lives_in` (importance 0.7, confidence 0.8), the raw similarity needed to pass becomes:

| Age | Raw similarity needed |
|---|---|
| 0 days | about 0.44 |
| 30 days | about 0.48 |
| 90 days | about 0.54 |
| 180 days | about 0.59 |
| 365 days | about 0.62 |

Your measured similarity for the "where do I live" question was about 0.51. So after roughly three months without being used or repeated, "Lives in: Milan" would stop being retrieved for that question. Today's tests cannot show this, because every fact is seconds old.

### 3.9 Usage values

| `access_count` | `usage` |
|---|---|
| 0 | 0.00 |
| 1 | 0.29 |
| 3 | 0.58 |
| 5 | 0.75 |
| 10 or more | 1.00 |

### 3.10 Reinforcement ("touch")

When `touch=True` (the default, used by `chat.py`), selected non-pinned facts get `access_count + 1` and a fresh `last_accessed_at`. Used facts therefore rank higher next time and stay "fresh". Pinned facts are excluded so they do not reinforce themselves forever.

Side effect to be aware of: this is a feedback loop. A fact retrieved early gets a head start, which can entrench it. `compare.py` uses `touch=False` so that comparing never changes memory.

Each touching retrieval also writes one `retrieve` row to `memory_events`, with the query text and the returned fact ids.

---

## 4. `retrieve_baseline`: the control group

```sql
SELECT content, created_at, 1 - (embedding <=> query) AS similarity
FROM messages
WHERE user_id = ... AND role = 'user'
ORDER BY embedding <=> query
LIMIT k
```

| Property | Behaviour |
|---|---|
| Source | Raw user messages |
| Filtering | None. It always returns `k` rows if that many messages exist. |
| Ranking | Cosine similarity only |
| Staleness | No concept of it. Old and new statements compete equally. |
| Side effects | None (it never updates anything) |

Because it cannot say "nothing is relevant", chit-chat messages get returned. In your comparison it returned "Thanks, that was really helpful!" and an old carbonara question.

---

## 5. `assistant.py`: building the prompt

### 5.1 Functions

| Function | Purpose |
|---|---|
| `format_memory(m)` | Turns a `Memory` into a line such as `Lives in: Milan (since 2026-10-24)`. |
| `recall(mode, user_id, query, k=4, touch=True)` | Returns the list of memory lines for the chosen mode. |
| `build_messages(mode, memory_lines, history, user_text)` | Returns the full message list for the chat model. |

### 5.2 Display labels

Relation names are turned into readable labels:

| Relation | Label | Relation | Label |
|---|---|---|---|
| name | Name | dislikes | Dislikes |
| lives_in | Lives in | allergic_to | Allergic to |
| works_at | Works at | family_member | Family member |
| job_title | Job title | speaks | Speaks |
| partner | Partner | goal | Goal |
| birthday | Birthday | hobby | Hobby |
| likes | Likes | | |

A relation without a label falls back to its raw name. When you add a new relation type, add a label here too, for a cleaner prompt.

### 5.3 How the prompt is assembled

```
[system]    persona + today's date
            + (if there are memories) header + bullet list + usage instruction
[history]   previous chat turns (supplied by the caller)
[user]      the current question
```

The persona line is: "You are a friendly, concise assistant that remembers the user across conversations. Today is `<weekday day month year>`."

The usage instruction added when memories exist: use the memory only when relevant, do not list it unprompted, and do not mention having a memory system.

### 5.4 Example: smart mode prompt

```
system: You are a friendly, concise assistant that remembers the user across
        conversations. Today is Saturday 24 October 2026.

        What you currently know about the user:
        - Allergic to: penicillin (since 2026-10-24)
        - Lives in: Milan (since 2026-10-24)

        Use this only when it is relevant to the question. Do not list it
        unprompted and do not mention having a memory system.
user:   What's the weather like where I live?
```

### 5.5 Example: baseline mode prompt

```
system: You are a friendly, concise assistant that remembers the user across
        conversations. Today is Saturday 24 October 2026.

        Past messages from the user that may be relevant:
        - [2026-10-24] "I live in Turin and I work at Acme as a software engineer."
        - [2026-10-24] "Big news: I just moved to Milan!"
        - [2026-10-24] "I really love cycling, it's my main hobby."
        - [2026-10-24] "I also enjoy climbing these days."

        Use this only when it is relevant to the question. Do not list it
        unprompted and do not mention having a memory system.
user:   What's the weather like where I live?
```

The baseline hands the model raw evidence and lets it work out which statement is current. Smart mode hands over a conclusion.

### 5.6 Conversation history

- `chat.py` passes the last six history entries (three user and assistant exchanges).
- `compare.py` passes no history, so each mode is judged on the memory alone.
- History is short-term context inside one session. Memory is long-term knowledge across sessions. They are separate on purpose.

---

## 6. How the scripts use the read path

| Script | Flow |
|---|---|
| `chat.py` | `recall` (touch on) → `build_messages` → `chat_stream` → print answer → `ingest_user_message` (write path) |
| `compare.py` | `retrieve` with `touch=False` for smart; `recall` for baseline; no memory for none; each answered at temperature 0; prints the smart-mode score breakdown |

---

## 7. What your first comparison showed

### 7.1 Results

| | Weather question | Dinner question |
|---|---|---|
| **No memory** | Asked for the location | Generic fajita recipe |
| **Baseline** | Recalled Turin, Milan, cycling and climbing; answered about Milan | Recalled the old carbonara question and "Thanks!"; fixated on carbonara and gave no recipe |
| **Smart** | Recalled Milan (plus the pinned allergy); answered about Milan | Recalled only the pinned allergy; suggested fajitas |

### 7.2 What it proves and what it does not

| Claim | Verdict |
|---|---|
| Smart sends less noise into the prompt | **Shown.** One or two lines instead of four. |
| Stale facts never reach the prompt in smart mode | **Shown.** Turin was absent. |
| Baseline can be hijacked by similar-sounding old messages | **Shown** in the dinner test (carbonara). |
| Smart gives more accurate answers than baseline | **Not shown yet.** Both answered Milan correctly, because "I just moved to Milan" is explicit. This needs harder scenarios with ground truth. |

### 7.3 Problems the results exposed

| # | Problem | Detail |
|---|---|---|
| 1 | Both modes invented a weather forecast | The model has no weather tool. The 18°C and 12°C forecast was made up, and memory makes a made-up answer sound grounded. Evaluation questions should be answerable from memory alone, and the system prompt could say the assistant has no live data. |
| 2 | Pinning the allergy was noise here | Penicillin had 0.00 relevance to both questions, yet it was injected both times. Pinning by importance alone is too blunt. |
| 3 | Recency acts as a relevance gate | See section 3.8. Old but relevant facts will eventually be dropped. |
| 4 | Similarity is weak | Milan cleared the 0.50 threshold by only 0.075. Terse text like `lives in: Milan` and unused embedding prefixes are the likely causes. |
| 5 | The dinner test was badly designed | The data contained no food preferences, so smart memory correctly had nothing to offer. It says nothing about system quality. |

---

## 8. Tuning guide

All knobs are in `config.py`. Use the score breakdown printed by `compare.py` to see which component is responsible.

| Symptom | Likely cause | Try |
|---|---|---|
| A relevant fact is missing from the prompt | Score just under the threshold | Lower `MIN_SCORE`, or lower `SIM_FLOOR` |
| Irrelevant facts appear | Threshold too low, or importance and recency dominating | Raise `MIN_SCORE`, or lower the importance or recency weights |
| Something always appears whatever the question | It is pinned | Raise `PIN_IMPORTANCE` above 1.0 to switch pinning off |
| Facts disappear after a few months | Recency decay gate (3.8) | Raise `RECENCY_HALF_LIFE_DAYS`, lower the recency weight, or change how recency is used |
| Everything is returned | `SIM_CEIL` too low, or `MIN_SCORE` too low | Raise either |
| Same facts always win | Usage feedback loop | Lower the usage weight |
| Too many or too few lines | `k` | Change `--k` in the scripts, or the default in `retrieve()` |
| Facts are returned out of order of importance | Weights | Raise the importance weight |

Weights should sum to 1, so that scores stay comparable to `MIN_SCORE`. After any change, re-run `compare.py` on the same questions.

---

## 9. Smart versus baseline

| Aspect | Smart memory | Baseline vector memory |
|---|---|---|
| Source | `facts` (clean statements) | `messages` (raw text) |
| Handles outdated info | Yes, superseded facts are excluded | No |
| Can return "nothing relevant" | Yes (`MIN_SCORE`) | No, always returns `k` |
| Uses importance | Yes | No |
| Uses time | Yes (recency) | Only the date shown in the line |
| Learns from use | Yes (reinforcement) | No |
| Depends on extraction quality | Yes, so a missed fact is invisible to it | No, every message is searchable |
| Can answer questions about the past | No (superseded facts hidden) | Partly, if the message is retrieved |
| Model calls per retrieval | 1 embedding | 1 embedding |
| Database work | Loads all active facts, scores in Python | One indexed nearest-neighbour query |

The row "depends on extraction quality" is smart memory's main weakness. If the write path misses something, the read path never sees it, while the baseline still finds the raw message.

---

## 10. Design decisions

| Decision | Reason |
|---|---|
| **Retrieve from facts, not messages** | Clean, current, structured knowledge is shorter and less ambiguous than raw text. |
| **Only active facts** | The cheapest guarantee against stale information. |
| **A blended score, not similarity alone** | Importance, freshness and usage matter for what a person would actually want recalled. |
| **A minimum score** | Lets the system return nothing, which similarity-only retrieval cannot do. |
| **Pinning for critical facts** | Safety-relevant knowledge (allergies) should not depend on the wording of a question. |
| **Reinforcement on use** | Mimics memory strengthening, and gives the usage component a signal. |
| **Memory as short text lines with dates** | Compact prompt, and "since" gives the model a hint about currency. |
| **Instruction not to mention the memory system** | Avoids stilted answers like "According to my records...". |
| **`touch=False` for comparisons** | Experiments must not change what they measure. |
| **Baseline built on the same data** | A fair control: the same messages, the same model, only the retrieval differs. |
| **Python scoring over all active facts** | Simple, transparent and easy to tune. Fast enough for hundreds of facts per user. |

---

## 11. Known gaps and ideas

### Gaps

| Gap | Impact |
|---|---|
| Recency gates relevance | Old but relevant facts will be dropped over time (section 3.8). |
| Pinning ignores relevance | The allergy is injected into unrelated questions. |
| Weak similarity signal | Facts are embedded as `relation: value`, and embedding task prefixes are unused. |
| Superseded facts are invisible | "Where did I live before?" cannot be answered, even though the history is stored. |
| Summaries are not retrieved | Compression is not built yet. |
| No handling of question type | Questions about the past, the present and preferences are all treated the same. |
| Scoring loads all active facts | Fine for a prototype, but it does not scale to thousands per user, and the facts HNSW index is unused. |
| Memory text is trusted | A stored fact value is pasted into the prompt as is. A crafted message could try to plant instructions. |
| No live-data guard | The model can invent weather, news or prices. |
| Weights are hand-picked | Nothing has been measured yet, so the values are starting guesses. |
| Feedback loop in usage | Early winners can entrench. |
| Multi-valued facts compete for `k` | A user with many hobbies may see only some of them. |

### Ideas, untested

| Idea | Why it may help |
|---|---|
| Use similarity as a hard gate, then rank by importance, recency and usage | Separates "is it relevant?" from "how much does it matter?" |
| Apply recency only to forgetting, not retrieval | Staleness is already handled by supersession. |
| Pin only when relevant (for example, food allergies for food questions) | Keeps safety coverage without noise. |
| Embed natural sentences ("The user lives in Milan") and use the `search_query:` and `search_document:` prefixes | Likely a stronger similarity signal. |
| Detect time-related questions ("before", "last year") and include superseded facts | Makes history useful. |
| Add a "no live data" line to the system prompt | Prevents invented forecasts. |
| Hybrid ranking (vector similarity plus keyword match) | Catches exact terms the embedding misses. |

---

## 12. Where the read path connects to the rest

| Connects to | How |
|---|---|
| **B. Storage design** | Reads `facts` (active rows) and `messages`; writes `access_count`, `last_accessed_at` and `retrieve` events. |
| **C. Model access** | Uses `embed` for queries and `chat` or `chat_stream` for answers. All scoring settings live in `config.py`. |
| **D. Write path** | Depends on it completely: retrieval can only return what extraction stored and the conflict logic kept current. |
| **F. Experiments** | `compare.py` and `chat.py` are the two ways to exercise this code. |
| **G. Not started** | Summaries will become a third retrievable source, and the evaluation will measure smart against baseline with ground-truth scenarios. |
