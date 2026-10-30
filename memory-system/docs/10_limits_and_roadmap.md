# 10. Limits and roadmap

Everything known to be missing or weak, in one place, and the planned work. Each limit points to the document that explains it.

## 1. Project goals not yet met

| Goal | State | What is missing |
|---|---|---|
| Better answers than vector memory (the expected outcome) | Not met | Set M, long histories: baseline 48, smart 36 of 57; set L, short and fresh: 28 against 20 (26 after the fixes). Facts extracted by an 8B model are less reliable than the messages they come from, and the errors accumulate with length ([results/set_M/log.md](results/set_M/log.md)). Next: a hybrid read path |
| Compress history into summaries | Partly | Episode notes are written, checked and retrieved ([07](07_summaries.md)); they recover most episodic questions (set G 8 to 13 of 17 needed, set H 12 of 13). Old notes are merged into digests (set J) without losing answers, but the saving is small: digests are 0.79 of the notes they replace and summary text in use is 1.01 of its sources, so the pre-registered target failed. Keeping every detail caps it: merging every old note at that rate would still give 0.92. Nothing archives or removes messages |
| Improve conversational consistency | Partly | Measured across sessions on set K: smart 17 of 23 correct and no contradiction, baseline 16 and one; stability tied (2 of 7 facts each), so the pre-registered stability criterion failed. Consistency with the assistant's own replies is not measured (replies are not stored) |
| Knowledge graph | Not used | The `relations` table is empty and unused. Typed facts play the role of the graph |

## 2. Limits of the evidence

See [08_evaluation.md](08_evaluation.md), section 7, for the full list. In short: sets A to F were written around the 13 fact types and G and H are small; every set has been seen, and on the one fresh set (L) the baseline answered 28 of 30 against smart's 20; scoring is by keywords, which mis-scores true past-tense notes; one small model; the baseline is simple.

## 3. Limits of the system

| Area | Limit | Detail |
|---|---|---|
| Coverage | Only 13 relation types | Information outside the types is dropped or misfiled: "I'm vegetarian" was stored as `hobby = vegetarianism` in a manual chat. Questions outside those types cannot be answered from facts ([03](03_storage.md)) |
| Retrieval | Routing can veto a strong match | Japanese goal, set E ([06](06_read_path.md)) |
| Retrieval | An allergy outside the top-2 bypass can be lost | Sesame, set E |
| Retrieval | Abstain questions still get lines | A question with no answer can pull weakly related facts through |
| Retrieval | The routing cost is about one needed fact per set | Measured across the sets |
| Retrieval | Archived facts are invisible, and replaced ones are read only for past questions | "I left Halvorsen, I work at Pelican" and "we split up" archive the old value, so "Where did I work previously?" gets no line; the keyword trigger misses paraphrases ([06](06_read_path.md), section 10) |
| Retrieval | Past lines are ordered by similarity | The oldest value can come second and be missed by the model |
| Summaries | Little compression | Notes are as long as their sources; digests save about a fifth of the notes they replace, and most notes are never merged because the model proposes one-note digests ([07](07_summaries.md), section 12) |
| Summaries | A stale note hides a whole digest | The stale-source rule checks a digest through all its notes, so one note built on a replaced fact hides the harmless notes merged with it (set B) |
| Summaries | Day numbers block a final state | The retention rule exempts month and weekday names but not day numbers, so "December 12" cannot become "February" in a digest |
| Summaries | A wrong inference can pass into a digest | "Paid for a technician to repair" became "repaired by the removal company"; the checks are word-level |
| Summaries | No routing for notes | A note about plans can match any question about plans; noise in sets A to F rose from 14/46 to 16/46. Partly addressed: the note window now counts the best fact ([07](07_summaries.md), section 5) |
| Summaries | The checks are word-level | The faithfulness check catches invented names, places and numbers, not misattribution; a sentence citing too few messages is dropped; details can be omitted (a wedding speech, a rejection) |
| Summaries | One note per message, frozen relative times | A message shared by two sentences is linked to the first; "last month" stays in the text (the note date is shown) |
| Summaries | The newest messages have no note yet | The chat summarises after 6 new messages, so up to 5 wait |
| Summaries | English-only rules | The chatter filter and stopwords |
| Model | No "say you don't know" instruction | When memory returns nothing the model answers freely; the prompt change was held out |
| Model | The `(since date)` label is misread | Set K: "which you started learning on March 2" from `Speaks: Breton (since 2026-03-02)` |
| Model | The real-time instruction blocks local suggestions | Set K: with `Lives in: Pärnu` in the prompt, a café suggestion was declined |
| Read path | Replies come one turn late after a change | Facts are stored after the reply, so the reply to "I've moved" still sees the old city (set K) |
| Retrieval | Indirect questions lose the fact | Set K: 4 of smart's 6 misses had the fact in memory but not past the gate; set L: an email signature (both facts under the floor), a language goal stored as a hobby, a brother's wedding |
| Write path | Facts about other people are stored as the user's | Set L: "My sister Agathe lives in Montreal and works as an airline pilot" stored the user's city and job, and Montreal replaced the user's real city. **Partly fixed:** `about_user` ([05](05_write_path.md), 4.3) now rejects such values for `lives_in`, `works_at`, `job_title`, `birthday` and `partner` (set L re-run 20 to 22, A to K unchanged, [results/logs/about_user_dev.md](results/logs/about_user_dev.md)); it is a word list, not yet measured on fresh data |
| Write path | Incidental places and people get a fact kind | Set L: "my suitcase had ended up in Frankfurt" became `lives_in`; "my friend Pieter" became `partner`; a cat became a `family_member`. The first two are now rejected by `about_user`; the cat is not |
| Write path | Incidental mentions replace single-valued facts | Set M: "looking at houses in Rotterdam, prices in Utrecht are crazy" and "I now commute to Utrecht" each replaced the city; "Peatline has no office" became a job title; a transfer to Kristiansand stored no city. Over a long history these slips accumulate. **Partly fixed:** `signals_change` ([05](05_write_path.md), 4.4); measured in [results/logs/change_rule_dev.md](results/logs/change_rule_dev.md) |
| Write path | A name as the subject is not seen by `about_user` | Set M: "Callum is getting married in Dublin ... and asked me to give a speech" stored Dublin as the user's city ("me" passes the first-person rule). **Partly fixed:** stored partner and family names now count as someone else; other names (a friend not stored) still pass, but a city they bring needs change words |
| Write path | The same wording supersedes or archives | "I left Hollbach Clinic, I'm now at St Veit" superseded the old employer on set L; a similar sentence archived it on set I |
| Summaries | Notes skip what facts were supposed to hold | Set L: cello lessons, learning Finnish and a wedding were kept by neither layer. **Fixed:** each message is tagged with the facts stored from it and notes skip only what those hold; notes that only restate stored facts are dropped ([07](07_summaries.md), 4.2; [results/logs/note_tags_dev.md](results/logs/note_tags_dev.md)). Set L 22 to 26 |
| Summaries | A strong fact can hide the note that holds the answer | Since the note window counts the best fact, `Goal: trip to Hanoi` keeps out the notes with the date (set J). To revisit with the gate work |
| Summaries | A changed plan can keep its first state | Set L: "Pieter can't come, Brigid is joining instead" got no note; the only note said "with Pieter", and smart answered Pieter. **Fixed on set L** by the third prompt example (the hiking note now names Brigid) |
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

In order. Each step is verified before the next begins. Done so far: facts, the write and read paths, the first version of the summaries layer (sets G and H, [07](07_summaries.md)), the first version of the past-question rule (set I) and consolidation (set J, then closed).

1. **Consolidation: closed.** On set J digests did not cost answers (smart 24/26 without, 25/26 with; [08](08_evaluation.md)) but saved little (0.79 of the notes they replace; text in use 1.01 of sources). A time-boxed look at grouping by code showed that grouping is not the limit: with every detail kept, merging every old note would still leave 0.92 ([results/logs/consolidation_v2_exploration.md](results/logs/consolidation_v2_exploration.md)). Two options remain, not planned: shorter notes without the "The user …" framing (14% of note text; changes the notes layer for every set), or digests allowed to drop details (trades answers for length).
2. **Consistency across turns: measured (set K).** A session format and runner (`evaluate_sessions.py`). Smart and baseline about even (17 and 16 of 23; 0 and 1 contradictions; 2 and 2 stable facts). Smart's misses are mostly the gate on indirect questions, which belongs to step 5. Not done: consistency with the assistant's own replies.
3. **Questions about the past: first version done, follow-up open.** Replaced facts are read for past questions (set I, [08](08_evaluation.md)): 5 of 6 past questions had the needed value, answers 3 of 6, regression sets unchanged. Two follow-ups come from the misses and need a fresh set, because I is spent: (a) read facts archived by a retraction for past questions, or store "left X, now at Y" as a replacement; (b) order past lines oldest first. A pre-registered comparison with the current version is the test.
4. **Unseen data: measured (set L).** Baseline 28 of 30, smart 20 (facts only 16). Half of smart's misses are write-path errors: facts about other people stored as the user's, incidental places and people given a fact kind. Next, developed on spent sets and measured on a fresh set M: those write-path errors, the gap between notes and facts, then the gate items below.
5. **Long histories: measured (set M), hypothesis rejected.** Baseline 48, smart 36 of 57; the causes are wrong or missing current facts (incidental mentions replace single-valued facts), notes that lose details, and the gate. Next, before any more tuning: **a hybrid read path** (raw messages first, facts where they are strong), pre-registered on a fresh set. **Step 1 done:** current facts stay right (change rule, name variants, known people; set M current facts 6 to 12 of 12, smart 36 to 43, development run, [results/logs/change_rule_dev.md](results/logs/change_rule_dev.md)). Next: step 2, the hybrid read path.
6. **Routing for notes, the gate on indirect questions, and the "say you don't know" prompt.** Noise and invented answers seen in sets A to H, and the indirect questions set K lost at the gate (a signature, a note signed with the user's name, a vinaigrette for a mustard allergy). Each needs a fresh set.
7. **Final comparison on a fresh set.** None, baseline and smart (with and without summaries), run once. The two held-back fixes (a strong-match override at about 0.60 raw similarity, and an allergy bypass up to relation rank 3) are measured blind as an ablation in the same run.
8. **Report.** The results with their limits, the decision log, and the known failures listed above.

## 5. Open questions

- Would a stronger model remove the need for the correction rules, or only change which slips remain?
- How much of the gate's performance survives a different embedding model? Every model has its own similarity range ([04](04_models.md), section 11).
- Are 13 relation types enough, or should unknown kinds of information become free-form facts?
- Should a retraction that comes with a new value ("I left X, I work at Y") archive the old value, or supersede it?
- Can notes be consolidated without losing the details (a price, a duration) that questions ask for?
- Should an episode be a separate kind of fact with a source message, instead of a free sentence?
