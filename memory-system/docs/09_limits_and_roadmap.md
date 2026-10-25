# 9. Limits and roadmap

Everything known to be missing or weak, in one place, and the planned work. Each limit points to the document that explains it.

## 1. Project goals not yet met

| Goal | State | What is missing |
|---|---|---|
| Compress history into summaries | Not started | The `summaries` table exists; nothing writes or reads it. No rule decides when messages are summarised or how a summary is retrieved |
| Improve conversational consistency | Partly | Answers to single questions are measured. There is no multi-turn test, and the assistant's own replies are not stored |
| Knowledge graph | Not used | The `relations` table is empty and unused. Typed facts play the role of the graph |

## 2. Limits of the evidence

See [07_evaluation.md](07_evaluation.md), section 7, for the full list. In short: the questions were written around the 13 fact types; every set has been seen; the sample is small; scoring is by keywords; one small model; the baseline is simple.

## 3. Limits of the system

| Area | Limit | Detail |
|---|---|---|
| Coverage | Only 13 relation types | Information outside the types is dropped or misfiled: "I'm vegetarian" was stored as `hobby = vegetarianism` in a manual chat. Questions outside those types cannot be answered from facts ([03](03_storage.md)) |
| Retrieval | Routing can veto a strong match | Japanese goal, set E ([06](06_read_path.md)) |
| Retrieval | An allergy outside the top-2 bypass can be lost | Sesame, set E |
| Retrieval | Abstain questions still get lines | A question with no answer can pull weakly related facts through |
| Retrieval | The routing cost is about one needed fact per set | Measured across the sets |
| Retrieval | Superseded facts are invisible | "Where did I live before?" cannot be answered |
| Write path | Junk made of message words passes grounding | "new position" ([05](05_write_path.md)) |
| Write path | An achieved goal stays a goal | "I got the promotion" |
| Write path | An abandoned hobby can be filed as a dislike | "I'm done with chess" |
| Write path | A negated like may be read as a retraction when the like already exists | Not reproduced: "I don't like jazz" on a fresh user stored `dislikes = jazz` correctly |
| Write path | A retraction cannot reach a `conflicted` fact | After an employer change |
| Write path | English-only rules | Negation words and fillers |
| Write path | Single-message extraction | "No, I meant Rome" is not a correction of the last turn |
| Write path | Only `works_at` to `job_title` is a dependency | |
| Model | An 8B model makes extraction slips and sometimes ignores a fact in its prompt | The rules compensate; they were built around its observed behaviour |
| Model | No retries or timeouts | A stalled Ollama stalls the script ([04](04_models.md)) |
| Scale | All active facts are loaded and scored in Python | Fine for dozens of facts per user |
| Scale | The transaction stays open during extraction | Not suited to many simultaneous users |
| Security | Stored values and user text are pasted into prompts unescaped | Relation validation limits the damage |
| Tests | The database tests share the main database | They use a throwaway user and clean up, but a separate test database would be safer |

## 4. Roadmap

In order. Each step is verified before the next begins.

1. **Summaries layer.**
   - Write the predictions and a blind set G first. G includes questions outside the 13 fact types (episodic questions such as "what trip did I mention?") where baseline may win.
   - Design: every N messages, or at the end of a conversation, the model writes a short summary stored in `summaries` with the ids of its source messages, so it is traceable. Retrieval consults summaries only when no fact answers the question well.
   - Measure: answer coverage on episodic questions, faithfulness (no invented details), and compression (summary length against source length).
2. **Consistency across turns.** A multi-turn scenario format and a measure of whether the assistant contradicts what it was told or what it said earlier.
3. **Final comparison on a fresh set.** None, baseline and smart, run once. The two held-back fixes (a strong-match override at about 0.60 raw similarity, and an allergy bypass up to relation rank 3) are measured blind as an ablation in the same run.
4. **Report.** The results with their limits, the decision log, and the known failures listed above.

## 5. Open questions

- Would a stronger model remove the need for the correction rules, or only change which slips remain?
- How much of the gate's performance survives a different embedding model? Every model has its own similarity range ([04](04_models.md), section 11).
- Are 13 relation types enough, or should unknown kinds of information become free-form facts?
- Should superseded facts be retrievable for questions about the past?
