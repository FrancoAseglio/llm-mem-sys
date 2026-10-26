# 10. Limits and roadmap

Everything known to be missing or weak, in one place, and the planned work. Each limit points to the document that explains it.

## 1. Project goals not yet met

| Goal | State | What is missing |
|---|---|---|
| Compress history into summaries | Partly | Episode notes are written, checked and retrieved ([07](07_summaries.md)); they recover most episodic questions (set G 8 to 13 of 17 needed, set H 12 of 13). But they are not shorter than their sources (ratio 1.03): there is no consolidation of old notes into digests, and nothing archives or removes messages |
| Improve conversational consistency | Partly | Answers to single questions are measured. There is no multi-turn test, and the assistant's own replies are not stored |
| Knowledge graph | Not used | The `relations` table is empty and unused. Typed facts play the role of the graph |

## 2. Limits of the evidence

See [08_evaluation.md](08_evaluation.md), section 7, for the full list. In short: sets A to F were written around the 13 fact types and G and H are small; every set has been seen; scoring is by keywords, which mis-scores true past-tense notes; one small model; the baseline is simple.

## 3. Limits of the system

| Area | Limit | Detail |
|---|---|---|
| Coverage | Only 13 relation types | Information outside the types is dropped or misfiled: "I'm vegetarian" was stored as `hobby = vegetarianism` in a manual chat. Questions outside those types cannot be answered from facts ([03](03_storage.md)) |
| Retrieval | Routing can veto a strong match | Japanese goal, set E ([06](06_read_path.md)) |
| Retrieval | An allergy outside the top-2 bypass can be lost | Sesame, set E |
| Retrieval | Abstain questions still get lines | A question with no answer can pull weakly related facts through |
| Retrieval | The routing cost is about one needed fact per set | Measured across the sets |
| Retrieval | Superseded facts are invisible | "Where did I live before?" cannot be answered, and the stale-source rule also hides notes built on replaced facts |
| Summaries | Not compression | Notes are as long as their sources (3,061 against 2,971 characters); nothing merges old notes ([07](07_summaries.md), section 9) |
| Summaries | No routing for notes | A note about plans can match any question about plans; noise in sets A to F rose from 14/46 to 16/46 |
| Summaries | The checks are word-level | The faithfulness check catches invented names, places and numbers, not misattribution; a sentence citing too few messages is dropped; details can be omitted (a wedding speech, a rejection) |
| Summaries | One note per message, frozen relative times | A message shared by two sentences is linked to the first; "last month" stays in the text (the note date is shown) |
| Summaries | The newest messages have no note yet | The chat summarises after 6 new messages, so up to 5 wait |
| Summaries | English-only rules | The chatter filter and stopwords |
| Model | No "say you don't know" instruction | When memory returns nothing the model answers freely; the prompt change was held out |
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
| Scale | All active facts are loaded and scored in Python; all notes are compared in one query without the index | Fine for dozens of facts and notes per user |
| Scale | The transaction stays open during extraction | Not suited to many simultaneous users |
| Security | Stored values and user text are pasted into prompts unescaped | Relation validation limits the damage |
| Tests | The database tests share the main database | They use a throwaway user and clean up, but a separate test database would be safer |

## 4. Roadmap

In order. Each step is verified before the next begins. Done so far: facts, the write and read paths, and the first version of the summaries layer (sets G and H, [07](07_summaries.md)).

1. **Questions about the past.** A way to answer "where did I live before?": superseded facts, labelled with their dates, read only when the question asks about the past. This is its own step because it changes what the stale-source rule may hide.
2. **Consolidation.** Merge old notes of one user into shorter digests with their source ids, so the compression goal is measured and not just claimed: summary length against source length, and answers before and after.
3. **Routing for notes, and the "say you don't know" prompt.** Both address noise and invented answers seen in sets A to H. Each needs a fresh set, because G and H are spent.
4. **Consistency across turns.** A multi-turn scenario format and a measure of whether the assistant contradicts what it was told or what it said earlier. The assistant's own replies are not stored yet.
5. **Final comparison on a fresh set.** None, baseline and smart (with and without summaries), run once. The two held-back fixes (a strong-match override at about 0.60 raw similarity, and an allergy bypass up to relation rank 3) are measured blind as an ablation in the same run.
6. **Report.** The results with their limits, the decision log, and the known failures listed above.

## 5. Open questions

- Would a stronger model remove the need for the correction rules, or only change which slips remain?
- How much of the gate's performance survives a different embedding model? Every model has its own similarity range ([04](04_models.md), section 11).
- Are 13 relation types enough, or should unknown kinds of information become free-form facts?
- Should superseded facts be retrievable for questions about the past?
- Can notes be consolidated without losing the details (a price, a duration) that questions ask for?
- Should an episode be a separate kind of fact with a source message, instead of a free sentence?
