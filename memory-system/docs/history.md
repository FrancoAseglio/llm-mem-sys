# History of the project

The development logs and the record of every test set, merged into one file in the order they were written (2026-10-24 to 2026-10-30). They are historical records: the text is unchanged except for the links and the heading levels. Run outputs they mention by file name (`full.json`, `change_rule_M.txt`, `../regressions/...`) are now rows of the tables in [../results/](../results/README.md) (see `runs.csv` for the run ids); the original files are at the git tag `raw-results`.

| # | Record |
|---|---|
| 1 | [Summaries layer: development log](#summaries) |
| 2 | [Questions about the past: development log](#past-step) |
| 3 | [Set J log: consolidation of notes (2026-10-26)](#set-j) |
| 4 | [Set K log: consistency across sessions (2026-10-28)](#set-k) |
| 5 | [Noise check: everything re-run from scratch (2026-10-28)](#noise-check) |
| 6 | [Consolidation version 2: exploration and decision to stop (2026-10-28)](#consolidation-v2) |
| 7 | [Set L: first results on unseen data (2026-10-28)](#set-l) |
| 8 | [Facts about other people: development record (step 1 of the improvement round)](#about-user) |
| 9 | [Notes that skip only what facts hold: development record (step 2 of the improvement round)](#note-tags) |
| 10 | [Set M: long, crowded histories (2026-10-29)](#set-m) |
| 11 | [Current facts that stay right: development record (step 1 of the hybrid plan, 2026-10-29)](#change-rule) |
| 12 | [Hybrid read path: development record (step 2 of the hybrid plan, 2026-10-30)](#hybrid) |
| 13 | [Set N: the blind test of the hybrid read path (2026-10-30)](#set-n) |
| 14 | [Fixes from set N: development record (2026-10-30)](#set-n-fixes) |
| 15 | [Set O: the final blind test (2026-10-30)](#set-o) |

<a id="summaries"></a>

## 1. Summaries layer: development log

What was run, what failed, what was changed. Newest last. Sets A to F are spent, G was run once
before the layer existed and re-run with it, H was run once (run 5).

### Run 1: sets A to F with summaries on (2026-10-26, retrieval only, existing data)

Criteria written before building (docs/predictions/set_H.md, criterion 5):

| Smart, sets A to F | Criterion | Result |
|---|---|---|
| Needed present | 55/58 or better | 55/58, met |
| Average lines | under 2.0 | 1.3 to 1.8, met |
| Stale in prompt | 0 | **3** (A 1, B 1, F 1), **not met** |
| Noise present | 14/46 or fewer | **17/46** (B 1, C 3, D 7, E 4, F 2), **not met** |

48 summaries were written for the 33 evaluation users. Reading them:

- The three "stale" prompts are all true statements that mention an old value, not outdated claims:
  "The user used to live in Turin when they were a student." (past_tense_trap),
  "The user thinks Turin is lovely in autumn." (b_stale_flood, a distractor message that produced
  no fact), "The user left Northwind and is now a product manager at Contoso."
  (f_employer_with_title). The stale-source rule worked where it applies: the summaries of
  superseded facts ("The user lives in Turin.", "The user used to work at Northwind...") were
  not retrieved. The keyword metric cannot tell a past-tense mention from a stale claim.
- About a dozen summaries were written about questions and thanks, although the prompt says to
  skip them ("The user asked how compound interest works.", "The user wants to remove a coffee
  stain.", "The user is studying."). The model ignored its own rule. These are the likely source of
  the extra noise, and the last two are inferences from questions, not statements by the user.
- Some summaries restate facts the prompt says to skip (allergies, city). Retrieval drops them when
  they add nothing to the chosen fact lines.

### Change 1: questions, requests and thanks are filtered by rule before the model sees them

`summary_rules.is_chatter`: a message that starts with a question word and ends with "?", or starts
with a request ("give me", "explain", "suggest", ...) or "thanks". A statement followed by a question
is kept. The messages still count as seen. Checked on the messages of all eight sets: only generic
filler is flagged, no statement is. This is a fix for a rule of the specification the model did not
follow; no threshold changed. It was derived from the A to F run, not from set H, which has not been run.

Not changed on purpose: summaries that truthfully mention an old value stay. A rule against them
would also remove the information needed for questions about the past ("where did I live before?"),
which is a separate step.

### Run 2: sets A to F from an empty database, with change 1 (retrieval only, then answers)

| Smart, sets A to F | Criterion | Run 1 | Run 2 |
|---|---|---|---|
| Needed present | 55/58 or better | 55/58 | 55/58, met |
| Average lines | under 2.0 | 1.3 to 1.8 | 1.3 to 1.8, met |
| Stale in prompt | 0 | 3 | **4** (A 1, B 1, F 2), not met |
| Noise present | 14/46 or fewer | 17/46 | **17/46**, not met |

Summaries fell from 48 to 38, so the question summaries were not the main source of the extra
noise: the diagnosis after run 1 was incomplete. Reading the nine prompts where a note sits next to
a flagged word:

- Seven are true notes that mention a word the test lists as bad: past-tense mentions ("used to
  live in Turin"), a correction ("not allergic to latex"), a restatement ("started a new position at
  Delta Labs", "got the promotion"), a change of employer. The stale and noise lists were written for
  facts, where a mention means a wrong fact.
- Two are real noise: unrelated goal notes (marathon, house) for "Which language am I trying to
  learn?", where facts had returned nothing, and a distractor message about Turin. Notes have no
  routing step, so a note about plans is a topical neighbour of any question about plans.

Answers on A to F, same run, with the model (retrieval lines are what failed, answers did not):

| Smart, answers correct | Layer off | Layer on |
|---|---|---|
| A / B / C / D / E / F | 9/10, 6/6, 11/12, 17/18, 7/8, 7/7 | 9/10, 6/6, 11/12, 17/18, 7/8, 7/7 |
| Total | 57/61 | 57/61 |

The same four smart answers are wrong as before; no stale value reached an answer (0/61).
Baseline stayed at 52/61 (one answer moved between sets A and D: run-to-run variation of the model).

Decision: the criterion is recorded as failed on the retrieved lines and met on the answers. No third
change was made to the retrieval.

### Run 3: set G re-run with summaries (labelled re-run: G had been seen)

| Set G, smart | First run | Re-run | Baseline |
|---|---|---|---|
| Needed present | 8/17 | 13/17 | 17/17 |
| Noise present | 0/4 | 2/4 | 4/4 |
| Stale in prompt | 0 | 0 | 1 |
| Answers correct | 8/18 | 12/18 | 16/18 |
| Average lines | 0.8 | 1.6 | 4.0 |

Criteria: episode and story questions 7/9 (needed 7/9: met at the threshold); the question about the
past still fails (separate step); "vegan" does not appear as a hobby (met); noise inside the predicted
range (2/4). Faithfulness checked by hand on all 11 summaries: none invents a detail; omissions
(the wedding speech, Kestrel's rejection) and one missing story (g_project).

Why g_project had no summary (the `summarize` event lists the dropped sentences):

1. "The user works at Brightline Logistics." was dropped as not faithful. **Bug**: the check matched
   statement words against the content words of the sources only, and "work" is a stopword, so the
   inflected "works" found no match (2 of 3 words, under 75%).
2. "The user is leading the move of Brightline Logistics' billing system ..." was dropped because the
   model cited only the second message and "Brightline" is in the first. Not changed: a sentence is
   checked against the messages it cites. A limit of the model's citations.

### Change 2: faithfulness matches against every source word (bug fix)

`is_faithful` now matches the statement's content words against all words of the cited messages,
stopwords included, as its docstring said. Names and numbers are checked as before. Derived from
set G, not from H. Sets A to G need to be re-ingested to see its effect.

### Run 4: sets A to G from an empty database, with changes 1 and 2

Smart, sets A to F: needed 56/58, noise 16/46, stale in prompt 4, average lines 1.3 to 1.8,
answers 58/61 (layer off: 55/58, 14/46, 0, 0.9 to 1.7, 57/61). Stale in answer 0/61. Baseline 52/61.
Set E improved (needed 7/9 to 8/9, answers 7/8 to 8/8); the recovered note "The user wants to learn
Japanese" is the likely cause. It is a side effect of the faithfulness fix, not a result of the gate.

Set G (labelled re-run): needed 13/17, noise 2/4, stale 0, answers 12/18; identical to run 3.
52 summaries for the 41 users (49 before change 2: three true sentences had been lost to the bug).

Status against the criteria written before building:
- A to F needed: met. Average lines: met. Answers: no regression, +1.
- A to F stale in prompt (0) and noise (14/46): not met, explained above (truthful mentions, topical
  neighbours of notes). Reported as failed.
- G episode and story questions: 7/9, at the threshold. Past question: not addressed (separate step).

### Run 5: set H, once, with answers (blind validation)

Predictions were written before any summaries code (docs/predictions/set_H.md). The set was run once
on the finished layer (changes 1 and 2), with baseline and smart in the same run. Nothing was changed
afterwards.

| Set H | Baseline | Smart with summaries |
|---|---|---|
| Needed present | 13/13 | 12/13 |
| Noise present | 3/3 | 2/3 |
| Stale in prompt | 0 | 0 |
| Average lines | 4.0 | 1.1 |
| Answers correct | 13/14 | 13/14 |

- The one needed-fact miss is the cancelled-conference question: the check looks for "cancel", and the
  correct note says the user is "not going after all". Reported as a miss of the keyword list, not
  edited.
- Smart matches the baseline's answers with about a quarter of the lines. H has 15 questions and
  was run once, so this is encouraging, not conclusive.

Compression, measured on the evaluation users after the run:

| What | Characters |
|---|---|
| Notes | 3,061 |
| Messages linked to a note | 2,971 |
| All user messages | 10,905 |

Notes are 1.03 times the size of the messages they came from, and 28% of all messages (the saving is
the questions and filler that are left out). The layer recovers episodes but does not shorten history.
The roadmap step for this is consolidation of notes into digests (docs/10_limits_and_roadmap.md).

<a id="past-step"></a>

## 2. Questions about the past: development log

Predictions: docs/predictions/set_I.md (written and committed before any run). Raw output of the
runs: set_I_first_run.txt (mechanism on, with answers), set_I_off.txt (control, `PAST_FACTS=0`, same
stored data, retrieval only), regress_A_to_H.txt (all other sets with the mechanism on).

### Change before the run

The unit test of the trigger rule showed that "What food did I use to dislike?" did not fire ("use
to" without the d). "did I use to" was added to the trigger list and the predictions file was
amended before set I was run. No run of set I existed at that point.

### Run: set I, once (2026-10-26)

Smart with the mechanism, against the criteria written before:

| Measure | Criterion | Result |
|---|---|---|
| Past questions, needed present | 5/6 or better | **5/6**, met (miss: `i_job`) |
| Past questions, answers correct | 4/6 or better | **3/6**, not met |
| Present-tense controls: needed present | 3/3 | 3/3, met |
| Present-tense controls: stale in prompt | 0 | **1**, not met (see below) |
| "Before" traps, no old city in the prompt | 2/2 | 2/2, met (baseline fails both) |
| Never-moved question | not a criterion | smart and baseline both abstained |
| `PAST_FACTS=0`, past questions needed present | 0/6 or 1/6 | 1/6, met |

Whole set (12 questions): baseline needed 8/9, noise 2/2, stale 3, 4.0 lines, answers 8/10; smart
needed 8/9, noise 0/2, stale 1, 1.6 lines, answers 7/10. With the mechanism off, smart needed was 4/9
and lines 1.1: the mechanism adds 4 needed facts (`i_move`, both `i_two_moves`, `i_flip`).

### Diagnosis (stored facts and lines of the three scenarios that missed or surprised)

| Question | What happened | Cause |
|---|---|---|
| `i_job`, "Where did I work previously?" | Halvorsen is `archived`, not `superseded`; the prompt had only Pelican | "I left Halvorsen Marine, I now work at Pelican Software" is stored as a retraction plus a new value. The rule reads only superseded facts. Predicted at about 75% |
| `i_partner`, "Who was my partner before Elena?" | Dario is `archived`; the question was answered through a note ("after splitting up with Dario"), also with the rule off | Same write-path behaviour. The criterion was met by the notes layer, not by the mechanism |
| `i_two_moves`, "originally" | `Earlier: Valencia`, `Earlier: Ghent`, `Lives in: Gdansk` in the prompt; the answer was "I don't know" | The needed fact was present. Lines are ordered by similarity, so the oldest value came second; the 8B model did not pick it. A model failure, made more likely by the ordering |
| `i_flip`, "What food did I use to dislike?" | The answer was "Olives." | Correct in substance. The scoring requires a word such as "dislike", so it is counted as a miss as written |
| Controls, stale in prompt = 1 | The `i_partner` note mentions Dario | A true mention. It also appears with the rule off, so the mechanism did not cause it |

### Regression: sets A to H with the mechanism on (answers included)

| Sets | Expected | Result |
|---|---|---|
| A to F, smart | identical: needed 56/58, noise 16/46, stale 4, answers 58/61 | identical |
| G | only `g_past_home` changes | needed 13/17 to 14/17, answers 12/18 to 13/18, no other change in the totals |
| H | identical | identical (12/13, 2/3, 0, 1.1 lines, 13/14) |

### Not changed, on purpose

Two changes follow from the diagnosis: read facts archived by a retraction for past questions, and
order past lines oldest first. Neither was made, because set I is spent. Both are proposed for a
fresh set (docs/10_limits_and_roadmap.md).

<a id="set-j"></a>

## 3. Set J log: consolidation of notes (2026-10-26)

Record of what was run, in order, with what was found. Predictions and the frozen design: [../../predictions/set_J.md](predictions/set_J.md). Raw results: `set_J_off.json`, `set_J_on.json`, `regress_A_to_I_consolidation.txt`.

### 1. Run 1: consolidation not built (`set_J_off.json`)

- Baseline 25/25 needed, 26/26 answers. Smart 23/25 needed, 24/26 answers, 1.9 lines. Predicted about 22, 21, 20 and 19: both modes were underestimated.
- 16 renovation messages gave 11 notes. Three true sentences were dropped by the notes' faithfulness check (replayed by hand against `is_faithful`, assuming each cited only its own message; the event does not log citations):
  - "Henrik sprained his ankle while fixing the roof": 5/7 words matched; "brother-in-law" came from a message not cited.
  - "The old floor tiles contained asbestos, causing a two-week delay in the renovation": 6/10; a paraphrase plus context words.
  - "The user and their partner had to return a new oven due to a dent" and "... installed a grey granite countertop": rightly dropped for the invented "partner", but the facts were lost.
- Hanoi: the "moved to February" note existed but lost the window to the two December notes; the answer gave December 12.
- Write-path slip seen in passing: "Margit quit the band to move to Canada" stored `lives_in = Canada` for the user.
- Note slips that passed the check: "the user and their partner" (from "we") in three notes; "the user's friend Lotte" for a daughter.

### 2. Code (before run 2)

Built as frozen in section 1 of the predictions. Choices the design did not cover are listed there under "Implementation notes". The first database tests failed (4 of 12) because the test gave the first note the newest date, so the model's oldest-first numbering pointed at other notes; the code was right. 167 tests pass.

### 3. Run 2: consolidation on (`set_J_on.json`)

- Smart 24/25 needed, 25/26 answers, 1.7 lines; baseline unchanged.
- 9 digests from 19 notes: renovation 2, travels 4, band 0, control mix 3, recent 0.
- The model proposed 24 digests; 14 cited one note (dropped), one lost the name "Margit" (dropped), nine were kept.
- Compression: digests 1,092 characters for 1,388 of notes (0.79); summary text in use 3,155 against 3,133 of source messages (1.01; notes alone 1.10).
- Hanoi was answered correctly: the digest of the two December notes left room for the February note.
- The asbestos question still failed: no note existed to merge.

### 4. Regression, sets A to I (`regress_A_to_I_consolidation.txt`)

Identical to `regress_A_to_H.txt` and `set_I_first_run.txt` except set B: smart stale in prompt 1 to 0, average lines 1.4 to 1.2. One digest was written in A to I (none had been predicted), for `b_stale_flood`: it merged six Turin notes, one of them "The user lives in Turin." That note should not exist (the note prompt says to skip home city). Because the user later moved to Rome, the stale-source rule hides the digest and with it five harmless notes.

### 5. Digests checked by hand

| Digest | Verdict |
|---|---|
| #410 kitchen: cost 21,500, quote 18,000 by Tobias | Faithful to its notes; keeps the invented "partner" from them |
| #411 Henrik fixed the barn roof, the user painted the doors red | Faithful |
| #423 Reykjavik with Sunniva, flight delayed nine hours by a snowstorm | Faithful |
| #424 Marrakech cooking class, lamb tagine | Faithful |
| #425 Dolomites hailstorm broke the camera | Faithful |
| #426 Hanoi with Joel, flights for December 12 | Faithful to its notes, outdated by a newer note it could not merge |
| #444 chickens Hilde and Rosa, Rosa ate the lettuce | Faithful |
| #445 moved to Bergen, movers scratched the piano, "repaired by the removal company" | **Wrong inference**: the company paid for a technician |
| #446 rowing boat, oarlocks for 45 euros | Faithful |
| #456 (set B) lives in Turin, derby, coffee, transport, Po river | Faithful to its notes; restates a superseded city, hidden by the stale-source rule |

<a id="set-k"></a>

## 4. Set K log: consistency across sessions (2026-10-28)

Predictions and the frozen design: [../../predictions/set_K.md](predictions/set_K.md). Raw output: `first_run.txt` (printed) and `first_run.json` (`eval_sessions.json`). Set K was run once, in the three modes together (`make sessions`, 326 s, llama3.1:8b). It is spent.

### 1. Hand review (rules fixed in the predictions)

| Answer | Mode | Rule | Decision |
|---|---|---|---|
| k_move, session 6: "You live in Ljubljana." | baseline | a forbidden word is cleared only if negated or explicitly past | Contradiction, kept |
| k_allergy, Dijon sandwich: "a classic and popular choice … if you enjoy ham and mustard" | none | correct only if it warns about the allergy | Not correct (the keyword had passed it on "mustard") |
| k_allergy, Dijon sandwich: "Considering your allergy to mustard … might not be the best choice" | baseline | same | Correct |
| k_allergy, Dijon sandwich: "Dijon mustard is a type of mustard, and you're allergic to mustard" | smart | same | Correct |
| k_allergy, vinaigrette tips | all three | same | Not correct: no answer warns |

Only one score changed (none, Dijon). The decisions were confirmed by the project owner.

### 2. Results after review

| Measure | none | baseline | smart | Predicted (baseline / smart) |
|---|---|---|---|---|
| Correct (23 probes) | 1 | 16 | 17 | 18 / 19.5 |
| Contradictions (13 probes with forbidden words) | 0 | 1 | 0 | 2 / 0.5 |
| Forbidden word in the memory lines (13) | 0 | 10 | 4 | not predicted |
| Stable facts (7 groups) | 0 | 2 | 2 | 3 / 4.5 |
| Indirect correct (10) | 0 | 6 | 5 | 7 / 7.5 |

| Criterion | Result |
|---|---|
| 1. Smart at most 1 contradiction, fewer than baseline | Passed, by one case (0 against 1) |
| 2. Smart at least as correct as baseline | Passed (17 against 16) |
| 3. Smart more stable than baseline | **Failed** (2 against 2) |
| 4. none at most 2 correct | Passed (1) |
| 5. The same-session question right in every mode | Passed |

Stable facts: baseline kept the same-session city and the languages; smart kept the moved city (k_move) and the partner.

### 3. Why answers failed

**Smart (6 misses).**
- Four are the gate, on questions that do not name the fact: "Sign this note with my name" (only the whaling note passed), the email signature after the job change (only the note passed, no `Works at` line), the vinaigrette (only the knives note; the allergy pass did not fire), "Which languages do I speak?" (French passed, Breton did not: window).
- One is the model: for "Recommend a café near where I live" the prompt held `Lives in: Pärnu`, but the answer declined, because the system prompt says it has no real-time information.
- One is shared by every mode: the signature before the job change (no mode wrote the employer).

**Baseline (7 misses).**
- Three are "I don't know" with the fact among its lines (the partner's name, the user's name twice), as in sets A to I.
- One is the contradiction: its own earlier questions ("Which city do I live in?", "Where do I live these days?") filled its four lines, so the only statement left was the old "I live in Ljubljana".
- The rest are the vinaigrette and the two signatures.

### 4. Observations outside the scores

- **The "since" date misleads the model.** Smart answered "You know French and Breton, which you started learning on March 2, 2026": the `(since 2026-03-02)` label of a fact line was read as when the user started learning. An invented detail that the keyword score counts as correct.
- **Smart replies one turn late after a change.** Facts are stored after the reply, so the reply to "I've moved to Bilbao" was written with `Lives in: Ljubljana` in the prompt ("I don't know anything about your move to Bilbao, as I only knew you lived in Ljubljana"); the same happened after the job change. Not scored.
- **Old names reach smart's lines through notes.** 4 of 13 probes: "The user left Brantley Analytics" (twice) and the note about the colleague Wilhelmina (twice). The model did not use them.
- **Baseline's memory fills with the user's own questions.** Over the sessions, past questions take most of its four lines (k_move, session 6: three of four).
- Every mode opened the first session with "Nice to chat with you again … I remember you", with nothing in memory: the model's habit, also seen in the chat.

### 5. What it shows

Across sessions, with only memory carrying facts, smart and baseline answered about the same (17 and 16 of 23). Smart never gave an outdated or wrong value; baseline did once. One case is not evidence of a difference, and the stability criterion failed. The predictions overrated smart (19.5 correct, 4.5 stable facts). The clearest lesson is where smart loses: the gate drops facts that indirect questions need, which points to routing (roadmap) rather than to memory itself.

<a id="noise-check"></a>

## 5. Noise check: everything re-run from scratch (2026-10-28)

Every single-question set (A to J) and the session set K were run again with the cache off (`--no-cache`), after re-ingesting every story. Any difference from the recorded runs is run-to-run noise. Two things besides the model calls changed: the calendar (two days later, and the system prompt states today's date) and the random order nothing depends on. All sets were already spent, so nothing was tuned here.

Outputs: `../regressions/A_to_J_nocache.txt` and `../set_K/rerun_nocache.txt`.

### Predicted (before the run)

Memory-only numbers identical or 0 to 2 different per set; answers correct 0 to 4 different per mode across A to J; set K 0 to 2 different per mode.

### Found

| Set | Memory-only numbers (needed, noise, stale, lines) | Answers correct |
|---|---|---|
| A, B, C, E, F, H, I, J | identical to the recorded runs | identical |
| D | identical | baseline 15/18 → 14/18 (the pizza question) |
| G | identical | smart 13/18 → 14/18 (the vegan dinner question; its needed fact is still missing, the answer passed anyway) |
| K | identical | identical, probe by probe |

Two of 286 answers in A to J changed (under 1%), one per mode, in opposite directions; no memory-only measure changed. The recorded A to J results come from `regressions/A_to_I_consolidation.txt` and `set_J/on.json`; set K from `set_K/first_run.txt`.

### What it shows and does not show

- The evaluation is reproducible: the same sets give the same numbers from scratch, so the gaps between modes are not run-to-run noise.
- It says nothing about new data. A gap that repeats exactly can still rest on few questions, and every set here was written by the same person who built the system. Fresh sets (L, then M) are the test of that.

<a id="consolidation-v2"></a>

## 6. Consolidation version 2: exploration and decision to stop (2026-10-28)

A time-boxed look at whether a second version of consolidation could meet the compression target that version 1 missed on set J ([../set_J/log.md](#set-j)). Set J is spent, so it was used as a practice set; nothing here is a validated result. No code of the system was changed.

### 1. The idea tested

Version 1 let the model both group notes and write digests, and 14 of its 24 proposed digests cited a single note. Version 2 would let code form the groups and the model only write one digest per group. `scripts/explore_groups.py` (read-only, no model calls) shows the groups code would form: two notes are linked when they share a capitalised name or when the similarity of their stored embeddings is at least `--min-sim`.

### 2. What the groups showed (the J users, notes older than 30 days)

| `--min-sim` | Old notes in groups | Groups |
|---|---|---|
| version 1 (the model grouped) | 19 of 36 | 9 digests |
| 0.75 | 21 of 36 | 9 |
| 0.70 | 29 of 36 | 9, by chaining different stories |

- **Similarity misses obvious topics.** The five kitchen notes of the renovation story are 0.70 to 0.74 apart, under the line; so are the rowing boat notes and the piano notes.
- **Shared names join unrelated episodes.** The Vienna train trip and the Hanoi plan were grouped only because Joel is in both; the band's EP and the festival because Ansel is in both. Place names (Reykjavik, Dolomites, Hanoi) grouped correctly. Code cannot tell a person from a place.
- **A lower threshold chains stories:** at 0.70 the first kitchen note links to the barn notes.

### 3. Why grouping cannot meet the target

Computed from the notes of run 2 (`set_J/on.json`):

| Quantity | Characters |
|---|---|
| The 36 old notes (the ones consolidation may merge) | 2,630 |
| Recent notes (never merged) | 821 |
| Source messages of all notes | 3,133 |

- If **every** old note were grouped and merged at version 1's rate (0.79), summary text in use would be (821 + 0.79 × 2,630) / 3,133 = **0.92** of the source messages. The target was below 0.85.
- Reaching 0.85 needs every old note merged at **0.70** or better.
- The retention rule makes a digest keep every name, number and place, so merging only removes repetition, and these notes repeat little. The largest overhead is elsewhere: 364 of the 2,630 characters (14%) are the "The user …" / "The user's …" / "and their partner" openings, and notes are 1.10 times the length of their messages.

### 4. Decision

Stop consolidation here. Grouping, the step version 2 would improve, is not what limits compression; keeping every detail is. Going further means either shorter notes (a change to the notes layer for every set) or digests that may drop details (which trades answers for length). Both are recorded as options in [../../10_limits_and_roadmap.md](10_limits_and_roadmap.md). The next step is consistency across turns.

<a id="set-l"></a>

## 7. Set L: first results on unseen data (2026-10-28)

Set L (10 stories, 30 questions, every question type) was written after sets A to K were spent, frozen with its predictions ([../../predictions/set_L.md](predictions/set_L.md)) and run **once** on the current system, cache off. Nothing was changed before or between the runs.

| File | What it is |
|---|---|
| `first_run.txt`, `first_run.json` | `evaluate.py --set L --no-cache --verbose`: ingest, notes, baseline and smart with summaries |
| `summaries_off.txt`, `summaries_off.json` | `SUMMARIES=0 evaluate.py --set L --no-ingest --no-cache --verbose`: same stored data, facts only |

### Results

| Set L, 30 questions | baseline | smart, summaries on | smart, summaries off |
|---|---|---|---|
| Answers correct | **28/30** | 20/30 | 16/30 |
| Needed present (28 with `needs`) | **28/28** | 20/28 | 16/28 |
| Noise present (3 with `avoid`) | 3/3 | 2/3 | 2/3 |
| Stale in prompt (5 with `stale`) | 5 | 2 | **0** |
| Stale in answer | **0** | 1 | **0** |
| Average lines | 4.0 | 1.7 | **0.9** |

- The hand rule (fruit salad, kiwi) changed nothing: both modes left kiwi out because of the allergy. Raw and reviewed counts are the same.
- The baseline gave the same 28/30, answer by answer, in both runs (a free noise check).
- Smart right and baseline wrong on 1 question (the name); the reverse on 9; both wrong on 1 (the wedding). A sign test on the 10 differing questions gives p of about 0.02: **on this set the baseline is better, and the gap is unlikely to be chance.**

By type (correct answers):

| Type | baseline | smart, on | smart, off |
|---|---|---|---|
| Direct (6) | 5 | 4 | 4 |
| Changes (6) | 6 | 5 | 5 |
| Past (4) | 4 | 3 | 3 |
| Episodes (7) | 7 | 5 | 1 |
| Indirect (4) | 4 | 2 | 2 |
| Traps (3) | 2 | 1 | 1 |

### Why smart missed 10 questions (summaries on)

| Question | Cause | Detail |
|---|---|---|
| Which city do I live in? (sister trap) | **Write path: third person** | "My sister Agathe lives in Montreal and works as an airline pilot" stored `lives_in = Montreal` and `job_title = airline pilot` for the user; Montreal superseded Nantes |
| What's my job? (abstain) | **Write path: third person** | Same message; answer "You're an airline pilot" |
| Where did the airline find my suitcase? | **Write path: wrong kind** | "It had ended up in Frankfurt" stored `lives_in = Frankfurt`; no note was written for that message; the model said it did not know |
| Who is coming hiking? | **Write path: wrong kind, and the note kept the first state** | "My friend Pieter" stored as `partner`; "Brigid is joining me instead" stored `family_member = Brigid`; the only note says "with Pieter". Answer "Pieter": smart's one stale answer |
| Which instrument am I learning? | **Write path: not extracted** | No `cello` fact and no `reject` event: the model never proposed it. No note either (below) |
| Write a short email signature | Gate (floor) | `works_at` raw 0.41, `name` 0.34, both under 0.42; nothing reached the prompt (the set K weakness) |
| "Thank you" in the language I'm learning | Gate (routing) | Stored as `hobby = Finnish`; routed out |
| What's my cat called? | Gate, probably the stale-source rule | `family_member = Pip` (a pet stored as family) did not pass; the note "adopted a cat called Pip with their boyfriend Corentin" did not appear, most likely because it is built on the archived Corentin fact. Not checked |
| Who was my partner before Odile? | Archived value | "Broke up" archived Corentin, which the past rule does not read (predicted) |
| When is my wedding? (trap) | Gate (floor), no note | `family_member = Fintan` raw 0.37; the baseline found the message at 0.64 because it contains "married". The baseline also failed (it said "I don't know") |

In short: **5 misses come from the write path** (a fact stored for the wrong person or of the wrong kind, or not stored), **4 from the gate**, 1 from archived values. The write-path errors are new: set A and H had third-person traps that passed, but here a sister's city and job, a friend and a place where luggage turned up all became facts about the user. Smart reads facts, not messages, so a wrong fact becomes a wrong answer and can even replace a right one (Montreal replaced Nantes). The baseline cannot make this mistake.

#### Notes missing for two stories

`eval_l_profile_maren` (11 messages) and `eval_l_indirect` (5) have no notes. The audit log shows one `summarize` event each, with `dropped: []`: the questions were skipped as chatter (5 and 3), and for the other messages the model returned no note at all. The notes prompt says "skip plain personal facts that are stored elsewhere", and the model applied it to cello lessons, learning Finnish and the brother's wedding. When extraction also misses such a message (cello), neither layer keeps it. That gap between the layers is a new limit.

#### Other observations

- **"I left Hollbach Clinic. I'm now a nurse at St Veit Hospital" superseded the old employer**, it did not archive it, so the past question was answered. In set I a similar sentence archived it. The write path is not consistent on this wording.
- `St Veit Hospital in Linz` was stored with the city inside the employer value.
- The two smart stale-in-prompt cases are notes: one true past mention ("broke up with Corentin"), and one outdated note (the hiking plan with Pieter).
- With summaries off, smart averaged 0.9 lines and never had a stale value in prompt or answer; it lost every episode but one.

### Predictions against results

| | Predicted | Found |
|---|---|---|
| Baseline answers | about 23.5 (21 to 26) | **28, above the range** |
| Smart, summaries on | about 21 (18 to 24) | 20, in range |
| Smart, summaries off | about 15.5 (13 to 18) | 16, in range |
| Needed present | 24 / 19 / 13 | 28 / 20 / 16 |
| Stale in prompt | about 4 / 0 to 2 / 0 | 5 / 2 / 0 |
| Average lines | 4.0 / about 1.5 / about 1.0 | 4.0 / 1.7 / 0.9 |

| Statement | Result |
|---|---|
| 1. Baseline answers about 2 more than smart with summaries | Direction right, size wrong: 8 more |
| 2. Smart never puts an outdated value in an answer | **Failed**: "Pieter" (from a wrong fact and an outdated note) |
| 3. Smart under 2 lines on average | Met (1.7) |
| 4. Summaries add about 5 correct answers | Close: 4 (16 to 20), all episodes |
| 5. Smart ahead on changes, behind on past, episodes, indirect | **Failed on changes** (5/6 against 6/6); behind on the others as predicted |
| 6. The archived clinic is missed with summaries off | **Failed in smart's favour**: the clinic was superseded, not archived |

Also: the predictions said 2 questions had `avoid`; the set has 3 (the abstain season question too). The predictions file is frozen and not edited.

What the predictions got wrong: they expected the gate to be the main weakness and the write path to be reliable on new wording. On unseen data, extraction of other people's facts and of incidental places was the larger problem, and the predictions underrated how well a raw-message baseline does when every story is short.

### What this means for the plan

- The improvement round should start with the write path: facts about other people (a sister's city and job, a friend), and places that are not the user's home. These errors are worse than a miss, because they replace a right fact.
- The gate on indirect questions stays (signature, wedding, the language goal).
- The notes prompt's "skip plain personal facts" rule needs a guard, so that a message whose facts were not stored still gets a note.
- Set L is now spent. Its stories may be used to develop these fixes; set M measures them.

<a id="about-user"></a>

## 8. Facts about other people: development record (step 1 of the improvement round)

Set L showed that the write path gives the user what a message says about someone else: "My sister Agathe lives in Montreal and works as an airline pilot" became the user's city and job (Montreal replaced Nantes), "it had ended up in Frankfurt" (a suitcase) became `lives_in`, and "my friend Pieter" became `partner` ([../set_L/log.md](#set-l)). The fix is a pure rule, `about_user` in `write/actions.py` ([05](05_write_path.md), section 4.3), applied to asserted `lives_in`, `works_at`, `job_title`, `birthday` and `partner` facts. `ABOUT_USER=0` switches it off.

This is **development on spent sets**. Set L is spent, so its re-run below shows whether the rule does what it was built for, not how well it generalises. Set M measures that.

### Checks before any run (offline, no model)

- The rule was tried on every message of sets A to L against every word their questions need or forbid, for the four self relations. It blocks only values that belong to someone else (a sister's or friend's name, Berlin in "My sister Anna lives in Berlin", Lisbon in "My sister Marta is getting married in Lisbon", Frankfurt) and no city, employer, job or birthday of a user.
- The partner messages of sets C, D, I, K and L were checked. One regression was found and fixed before freezing: set I's "Dario and I split up. I'm with Elena now." had no partner word, so "I'm with", "split up" and "broke up" were added.
- 16 new tests (15 pure, 1 database).

### Predictions (written before the runs)

Runs, cache off so they compare with the noise check (`../regressions/A_to_J_nocache.txt`, `../set_K/rerun_nocache.txt`):

1. Set L re-ingested with the rule (labelled development run).
2. Sets A to J re-ingested with the rule (regression).
3. Set K, sessions (regression).
4. The list of every value the rule rejected, from `memory_events`.

| Measure | Prediction |
|---|---|
| Values rejected on set L | Montreal, airline pilot, Frankfurt, Pieter; 4 to 6 in all, every one about someone else |
| Values rejected on A to J and K | 0 to 4, every one about someone else |
| Set L, smart with summaries | 20 to 21 or 22: the sister's-city question is fixed (about 90%); the job question becomes an abstain about 50% of the time (the sister's note may still bring "pilot"); the suitcase and hiking questions stay wrong (their notes lack the answer) |
| Set L, smart stale in answer | stays 0 or 1 ("Pieter" comes from the note too) |
| Set L, baseline | 28 (unchanged; the rule does not touch messages) |
| Sets A to J, memory-only numbers | identical to the noise check |
| Sets A to J, answers | within noise: 0 to 2 different per mode |
| Set K | identical probe by probe, or 1 different |

The rule is kept if no true user fact is rejected anywhere and no set loses a needed fact. If one is, it is reported here with the message that caused it.

### Results (2026-10-28)

Outputs: `about_user_L.txt` (this folder), `../regressions/A_to_J_about_user.txt`, `../set_K/about_user.txt`. The `.json` files were not kept (each run overwrites `eval_results.json`).

#### Values the rule rejected (every eval user)

| User | Relation | Value | Right? |
|---|---|---|---|
| `eval_l_suitcase` | lives_in | Frankfurt | yes: where the suitcase ended up |
| `eval_l_hiking_plan` | partner | Pieter | yes: "my friend Pieter" |
| `eval_l_sister_trap` | lives_in | Montreal | yes: the sister's city |
| `eval_l_sister_trap` | job_title | airline pilot | yes: the sister's job |
| `eval_j_travels` | partner | Joel | harmless: Joel is the user's partner, already stored from "my partner Joel"; this was a repeat from a later message without a partner word ("a trip to Hanoi with Joel" or "because Joel has a project deadline"), so only a duplicate count was lost |

Five rejections, four on set L as predicted, one elsewhere; none removed a fact the user had.

#### Set L (development re-run, labelled)

| Set L | Needed | Noise | Stale in prompt | Avg lines | Answers | Stale in answer |
|---|---|---|---|---|---|---|
| Baseline | 28/28 | 3/3 | 5 | 4.0 | 28/30 | 0 |
| Smart, first run | 20/28 | 2/3 | 2 | 1.7 | 20/30 | 1 |
| Smart, with the rule | 20/28 | 2/3 | 2 | 1.6 | **22/30** | 1 |

- **Fixed:** "Which city do I live in?" (Nantes stays active; answer "You live in Nantes") and "What's my job?" (no job stored; answer "I don't know", the sister's note in the prompt did not mislead the model).
- **Needed present did not move, and that is right:** the suitcase question had counted as "needed present" only because the wrong fact `Lives in: Frankfurt` contained the word. Now that line is gone, and the notes still lack Frankfurt.
- **Still wrong, as predicted:** the hiking companion. Pieter is no longer a partner, but the only note says "with Pieter", so the answer is still Pieter (smart's one stale answer). That is the notes layer (a changed plan keeps its first state), not the write path.

#### Regression

- **Sets A to J:** every summary line (needed, noise, stale, lines, answers, stale in answer, both modes) is identical to the noise check.
- **Set K:** identical totals (none 2, baseline 16, smart 17; contradictions 0 and 1; stable 2 and 2; indirect 6 and 5) and the same hand-review list.

#### Against the predictions

| Prediction | Result |
|---|---|
| 4 to 6 rejections on L, all about someone else | 4, all right |
| 0 to 4 elsewhere, all about someone else | 1, a harmless repeat of the user's real partner |
| L smart 20 to 22 | 22 |
| L stale in answer 0 or 1 | 1 (Pieter, from the note) |
| L baseline 28 | 28 |
| A to J and K within noise | identical |

**Decision: the rule is kept.** It removed every wrong fact it was built for on set L and changed nothing on sets A to K. This shows the rule does what it was built for on the stories that revealed the problem; whether it generalises is for set M.

### Addendum (2026-10-28): a first-person word is required

Set J showed a gap: "Margit quit the band to move to Canada" stored `lives_in = Canada` for the user, because no subject word stood before Canada. `about_user` now also requires a first-person word (I, me, my, we, our ...) anywhere in the message for a self fact or a partner. Checked offline on the 41 statements of sets A to L without one (none gives the user a fact) and measured in [note_tags_dev.md](#note-tags), iteration 4: 7 rejections in all, every one right, including Canada and "Second interview, this time at Orbital Freight".

<a id="note-tags"></a>

## 9. Notes that skip only what facts hold: development record (step 2 of the improvement round)

On set L two stories got no notes, and three messages were kept by neither layer: cello lessons, learning Finnish and a brother's wedding. The notes prompt said "skip plain personal facts stored elsewhere", and the model applied it to messages from which extraction had stored nothing ([../set_L/log.md](#set-l)). A changed plan also kept its first state ("with Pieter" after Brigid replaced him).

The change ([07](07_summaries.md), section 4.2): each message sent to the notes model is tagged with the facts first stored from it (`[stored: lives_in = Rome]` or `[stored: nothing]`), and the prompt skips only what the tag holds. A third example shows a plan whose companion changes, written in its final state. `NOTE_TAGS=0` restores the old prompt.

This is **development on spent sets**, like step 1 ([about_user_dev.md](#about-user)). Set M measures it.

### Predictions (written before the runs)

Runs, cache off, compared with the step 1 runs (`about_user_L.txt`, `../regressions/A_to_J_about_user.txt`, `../set_K/about_user.txt`):

| Measure | Reference | Prediction |
|---|---|---|
| Set L, notes written | 17 | 22 to 28 (cello, wedding, Finnish, Frankfurt, the hiking companion) |
| Set L, smart answers | 22/30 | about 24.5 (23 to 26): cello about 70%, Frankfurt about 60%, the wedding about 50%, the hiking companion about 50%, the Finnish "thank you" about 40%; the cat stays wrong (its note is hidden by the stale-source rule) |
| Set L, smart stale in answer | 1 | 0 or 1 (0 if the hiking note is written in its final state) |
| Sets A to J, notes written | 116 | 125 to 150 |
| Sets A to J, smart needed present | as in the reference | same, or 1 to 2 more |
| Sets A to F, smart noise present | 16/46 | 16 to 19 |
| Sets A to J, smart answers (sum) | 117 | 115 to 120 |
| Smart average lines per set | as in the reference | 0 to 0.3 more |
| Set K, smart correct | 17/23 | 16 to 18 (its misses are gate misses that notes do not touch) |
| Baseline, every set | as in the reference | unchanged except run-to-run noise (0 to 1 per set) |

The change is kept if set L gains at least 2 answers, no set loses more than 1 needed fact, smart's answers over A to J fall by at most 2, and smart's noise on A to F rises by at most 3. Otherwise it is reported here and reverted or reworked.

### Iteration 1: tags only (2026-10-28)

Outputs: `note_tags_L.txt`, `../regressions/A_to_J_note_tags.txt`, `../set_K/note_tags.txt`.

| Measure | Reference (step 1) | Predicted | Found |
|---|---|---|---|
| Set L, notes | 17 | 22 to 28 | 26 |
| Set L, smart answers | 22/30 | 23 to 26 | **26/30** |
| Set L, smart stale in answer | 1 | 0 or 1 | 0 |
| Sets A to J, notes | 116 | 125 to 150 | **165** |
| Sets A to F, smart noise present | 16/46 | 16 to 19 | **29/46** |
| Sets A to J, smart answers (sum) | 117 | 115 to 120 | 116 |
| Set K, smart correct | 17/23 | 16 to 18 | **19/23** (stable facts 3/7, indirect 7/10) |

Smart per set, reference then iteration 1 (needed; noise; avg lines; answers): A 9/9, 1.6, 9 then 9/9, 2.0, 9; B 7/7, 1/2, 1.2, 6 then 7/7, 1/2, 1.4, 6; **C** 10/10, 3/11, 1.5, 11 then 10/10, **8/11, 2.5**, 11; **D** 15/16, 7/17, 1.7, 17 then 15/16, **13/17, 2.8**, 17; E 8/9, 3/12, 1.3, 8 then 8/9, 4/12, 1.6, 8; F 7/7, 2/4, 1.8, 7 then 7/7, 3/4, 1.3, 7; G 14/17, 14 then 15/17, 15; H unchanged; I 8/9, 7 then 7/9, 6; J 24/25, 25 then 23/25, 24. Baseline unchanged everywhere.

- **What it fixed on set L:** cello ("The user has started taking cello lessons"), Frankfurt ("The user's suitcase ended up in Frankfurt"), the hiking companion (the note now says "with their cousin Brigid"; no stale answer) and the Finnish "thank you" ("kiitos"). The wedding note reached the prompt, but the model still said "I don't know" (as the baseline does).
- **What it broke: noise.** Without the old list of things to skip, the model wrote **profile notes** that only restate stored facts and bundle several of them: "The user lives in Bologna and works as an architect at Studio Verdi", "The user's partner is Marco and brother's name is Luca", "The user lives in Lisbon with their wife Ines and sister Marta" (also a wrong inference). Such a note matches many questions and carries the other facts with it. The tags did not stop the model writing them.
- **Against the criteria:** set L gained 4 (criterion at least 2: met); no set lost more than 1 needed fact (met; I and J lost 1 each); answers 116 (met); **noise on A to F rose by 13 (criterion at most 3: failed)**. As written in advance, the change is reworked, not kept as is.

### Iteration 2: drop notes that only restate stored facts

The fix is in code, not in the prompt, because the model ignored the tag for these messages. A note is dropped (reason "only stored facts") when **every message it cites is already held by the facts stored from it**: every name in the message is in a stored value, and at least 0.75 of its content words match a stored value or a word that states that kind of fact ("wife", "called" for `partner`; `RELATION_WORDS` in `summaries/rules.py`). 0.75 is the share already used by the faithfulness check; it was not tuned. `only_stored` was checked offline on 22 messages from sets C, D and L before any run: the profile messages count as only stored; cello, the wedding, Finnish, the running "before sunrise", both hiking messages (Pieter is a name no fact holds) and the coffee message do not.

#### Predictions for iteration 2 (written before the runs)

Compared with the step 1 reference, with the same criteria as before:

| Measure | Reference (step 1) | Iteration 1 | Prediction |
|---|---|---|---|
| Set L, notes | 17 | 26 | 21 to 26 |
| Set L, smart answers | 22/30 | 26/30 | 25 to 26 (the four fixes come from messages that are not only stored) |
| Sets A to J, notes | 116 | 165 | 120 to 145 |
| Sets A to F, smart noise present | 16/46 | 29/46 | 16 to 20 |
| Sets C and D, smart average lines | 1.5, 1.7 | 2.5, 2.8 | at most 1.9 and 2.1 |
| Sets A to J, smart answers (sum) | 117 | 116 | 115 to 119 |
| Set K, smart correct | 17/23 | 19/23 | 17 to 19 |

### Results of iteration 2 (2026-10-28): run with a bug

Outputs: `note_tags_v2_L.txt`, `../regressions/A_to_J_note_tags_v2.txt`, `../set_K/note_tags_v2.txt`.

| Measure | Reference (step 1) | Iteration 1 | Predicted | Iteration 2 |
|---|---|---|---|---|
| Set L, notes | 17 | 26 | 21 to 26 | 21 |
| Set L, smart answers | 22/30 | 26/30 | 25 to 26 | 26/30 |
| Sets A to J, notes | 116 | 165 | 120 to 145 | 123 |
| Sets A to F, smart noise present | 16/46 | 29/46 | 16 to 20 | **27/46** |
| Sets C and D, smart average lines | 1.5, 1.7 | 2.5, 2.8 | at most 1.9, 2.1 | **2.2, 2.6** |
| Sets A to J, smart answers (sum) | 117 | 116 | 115 to 119 | 115 |
| Set J, smart needed present | 24/25 | 23/25 | | **22/25** |
| Set K, smart correct | 17/23 | 19/23 | 17 to 19 | 18/23 |

**The rule did not run as designed.** `summaries/rules.py` already had a function `_names` (used by the consolidation checks), defined further down the file, and the new helper had the same name, so the old one replaced it. That one counts a mid-sentence "I" as a name, so every message like "My name is Giulia and I live in Bologna" kept its note ("The user lives in Bologna."), and those notes caused most of the noise left in C and D. The tests missed it because each of their messages began with "I". Fixed: the helper is now `_message_names`, with two tests on "... and I live in ...".

Also seen: notes that add a small detail to one stored fact pass by design ("The user plays the guitar in the evenings", "The user likes jazz music a lot", "The user's favourite kind of music is fado"); notes have no routing step, so they reach unrelated questions. Set J lost 2 needed facts against the reference: a renovation question whose cabinet note was worded differently in this run, and a `j_control_mix` question; not diagnosed (the A to J run is not verbose).

#### Predictions for iteration 2b (the fix, written before the runs)

| Measure | Iteration 2 | Prediction |
|---|---|---|
| Set L, smart answers | 26/30 | 25 to 26 |
| Sets A to J, notes | 123 | 110 to 125 |
| Sets A to F, smart noise present | 27/46 | 19 to 24: profile notes go, the detail notes stay. The criterion (at most 19) is likely to fail by a few |
| Sets C and D, smart average lines | 2.2, 2.6 | 1.7 to 2.0, 2.0 to 2.3 |
| Sets A to J, smart answers (sum) | 115 | 115 to 119 |
| Set J, smart needed present | 22/25 | 23 or 24 |
| Set K, smart correct | 18/23 | 17 to 19 |

If noise on A to F stays above 19, the trade is set out for a decision rather than kept silently: about 4 more answers on set L and 1 to 2 on set K, against a few more noisy prompts on the rich profiles of C and D.

### Results of iteration 2b (2026-10-28)

Outputs: `note_tags_v2b_L.txt`, `../regressions/A_to_J_note_tags_v2b.txt` (verbose), `../set_K/note_tags_v2b.txt`.

| Measure | Reference (step 1) | Iteration 2 (bug) | Predicted | Iteration 2b |
|---|---|---|---|---|
| Set L, smart answers | 22/30 | 26/30 | 25 to 26 | **26/30** (needed 25/28, stale in answer 0) |
| Set L, notes | 17 | 21 | | 20 |
| Sets A to J, notes | 116 | 123 | 110 to 125 | 108 |
| Sets A to F, smart noise present | 16/46 | 27/46 | 19 to 24 | **27/46** |
| Sets C and D, smart average lines | 1.5, 1.7 | 2.2, 2.6 | 1.7 to 2.0, 2.0 to 2.3 | 2.4, 2.4 |
| Sets A to J, smart answers (sum) | 117 | 115 | 115 to 119 | 115 |
| Set J, smart needed present | 24/25 | 22/25 | 23 or 24 | 23/25 |
| Set K, smart correct | 17/23 | 18/23 | 17 to 19 | 17/23 (stable 2/7) |

- **The profile notes are gone.** D now has 2 notes ("The user plays the guitar in the evenings", "The user's favourite kind of music is fado") and C has 4 ("enjoys running and usually goes out before sunrise", "dislikes coriander", "likes jazz music a lot", "would like to learn how to sail one day").
- **The noise left comes from those few detail notes**, each reaching 5 to 8 unrelated questions, because a note was compared only with other notes: as the best note it passed even next to a much stronger fact. Answers on C and D did not drop (11 and 17).
- **Set I lost 1 answer** ("Who was my partner before Elena?"): the note that used to carry Dario was not written in these runs. That is the archived-value problem (Dario is archived by "split up"), which has its own step. **Set J lost 1** (the kitchen-cabinets question; this run's notes lack the oak cabinets).
- **Against the criteria:** set L +4 (met); needed facts lost at most 1 per set (met); answers 115 (met, at the edge); **noise +11 (failed)**. Decision (2026-10-28): keep the tags and fix the note gate, below.

### Iteration 3: the note window counts the best fact

`select_summaries` measures the window (0.08) from the better of the best note and the best chosen fact (`NOTE_FACT_WINDOW`, on), instead of the best note only ([07](07_summaries.md), section 5). No new threshold. This is a read-side change, so it is run on the data stored by iteration 2b (`--no-ingest`): facts and notes are identical, and any difference comes from the window alone. Set K re-ingests by design, so its notes are written again.

#### Predictions for iteration 3 (written before the runs)

| Measure | Iteration 2b | Prediction |
|---|---|---|
| Sets A to F, smart noise present | 27/46 | 17 to 22 |
| Sets C and D, smart average lines | 2.4, 2.4 | 1.6 to 1.9 each |
| Set L, smart answers | 26/30 | 24 to 26 (risk: a note close to a strong fact, such as the hiking companion next to the hiking goal, is cut) |
| Set L, smart noise present | 3/3 | 2/3 (the sister's note leaves the city question; the job and season questions have no fact) |
| Sets A to J, smart answers (sum) | 115 | 114 to 118 (risk: story questions whose answer is in a note and whose fact is strong) |
| Sets A to J, smart needed present | as in 2b | the same, or 1 to 2 fewer |
| Set K, smart correct | 17/23 | 16 to 18 |
| Baseline | as in 2b | unchanged except run-to-run noise in its answers |

Kept if noise on A to F falls to 22 or below and set L keeps at least 24 answers and A to J at least 114. Otherwise reported and reworked or reverted.

### Results of iteration 3 (2026-10-28)

Outputs: `note_window_L.txt`, `../regressions/A_to_J_note_window.txt` (verbose), `../set_K/note_window.txt`. Run with `--no-ingest` on the data of iteration 2b, so the facts and notes are the same and every change comes from the window.

| Measure | Iteration 2b | Predicted | Iteration 3 |
|---|---|---|---|
| Sets A to F, smart noise present | 27/46 | 17 to 22 | **19/46** (B 1, C 3, D 10, E 3, F 2) |
| Sets C and D, smart average lines | 2.4, 2.4 | 1.6 to 1.9 each | 1.7, **2.1** |
| Set L, smart answers | 26/30 | 24 to 26 | **26/30** (noise 2/3, stale in prompt 1, 1.5 lines) |
| Sets A to J, smart answers (sum) | 115 | 114 to 118 | **113** |
| Sets A to J, smart stale in prompt | 5 (A 2, B 1, I 1, J 1) | | **0** |
| Set K, smart correct | 17/23 | 16 to 18 | 17/23 (stable 2/7) |

- **Noise is back near the reference** (19 against 16 before step 2) and smart's prompts on A to J no longer hold any outdated value: the stale notes were weak notes riding along with a strong fact.
- **Set J lost 2 answers, for two different reasons:**
  - "When am I going to Hanoi?": `Goal: trip to Hanoi` matches the question strongly, while the answer (the trip moved to February) is in the notes, which now fall outside the window. **A real cost of the rule:** a fact can name the topic without holding the answer.
  - "Who moved to Canada?": "Margit quit the band to move to Canada" had stored `lives_in = Canada` for the user, a wrong fact that `about_user` missed (no subject word before Canada). Before, the Margit note rescued the answer; now the strong wrong fact wins ("You moved to Canada"). **A step 1 gap, exposed.**
- **Against the criteria:** noise 19 (met), set L 26 (met), **A to J 113 (missed by 1)**.

### Iteration 4: `about_user` needs a first-person word

The Canada case is fixed where it starts: a self fact (`lives_in`, `works_at`, `job_title`, `birthday`, `partner`) is rejected when the message has no first-person word at all (I, me, my, we, our ...). [05](05_write_path.md), section 4.3. Checked offline before any run: of the 41 statements in sets A to L without a first-person word, none gives the user a fact (they are thanks, other people's news and things: "Margit quit the band", "Turin is lovely in autumn", "Second interview, this time at Orbital Freight"), and the 16 sample sentences of step 1 keep their verdicts. The Hanoi cost is kept and reported; it is not tuned away.

This changes the write path, so everything is ingested again.

#### Predictions for iteration 4 (written before the runs)

| Measure | Iteration 3 | Prediction |
|---|---|---|
| Values rejected as "about someone else" (all sets) | 5 (step 1) | 6 to 10, every one about someone else or not a fact about the user; Canada among them |
| Set J, "Who moved to Canada?" | wrong | right (about 80%) |
| Set J, "When am I going to Hanoi?" | wrong | still wrong (about 70%) |
| Sets A to J, smart answers (sum) | 113 | 114 (112 to 116; notes are written again, so run-to-run variation returns) |
| Sets A to F, smart noise present | 19/46 | 17 to 22 |
| Set L, smart answers | 26/30 | 25 to 26 |
| Set K, smart correct | 17/23 | 16 to 18 |

Kept if noise on A to F stays at 22 or below, set L at 24 or more and A to J at 114 or more. If A to J is again 113 because of note variation alone, that is reported as such and step 2 is closed with its trade written down, not tuned further.

### Results of iteration 4 (2026-10-28)

Outputs: `first_person_L.txt`, `../regressions/A_to_J_first_person.txt` (verbose), `../set_K/first_person.txt`. Everything ingested again.

| Measure | Iteration 3 | Predicted | Iteration 4 |
|---|---|---|---|
| Values rejected as "about someone else" | 5 (step 1) | 6 to 10, all right | **7**, all right: the 5 of step 1, Canada ("Margit quit the band to move to Canada") and Orbital Freight ("Second interview, this time at Orbital Freight": an interview, not an employer) |
| Set J, "Who moved to Canada?" | wrong ("You moved to Canada") | right (about 80%) | **still wrong, but no longer a wrong fact**: `lives_in = Canada` is gone, and this run's notes have no Margit-moved-to-Canada note, so the answer is "I don't know" |
| Set J, "When am I going to Hanoi?" | wrong | still wrong | still wrong |
| Sets A to J, smart answers | 113 | about 114 | **113** |
| Sets A to F, smart noise present | 19/46 | 17 to 22 | 19/46 |
| Set L, smart answers | 26/30 | 25 to 26 | 26/30 |
| Set K, smart correct | 17/23 | 16 to 18 | 17/23 |

Every per-question result on A to J is the same as iteration 3 except the Canada question, which went from a wrong answer to "I don't know". As written in advance, A to J at 113 because of note variation closes step 2 with its trade written down; it is not tuned further.

### Step 2 closed: what it changed

Against the step 1 reference (`about_user_L.txt`, `../regressions/A_to_J_about_user.txt`, `../set_K/about_user.txt`), smart memory:

| Measure | Step 1 | Step 2 (iteration 4) |
|---|---|---|
| Set L, answers | 22/30 | **26/30** |
| Set L, needed present | 20/28 | **25/28** |
| Set L, stale in answer | 1 | **0** |
| Sets A to J, answers | 117/133 | 113/133 |
| Sets A to J, needed present | 114/123 | 110/123 |
| Sets A to J, stale in prompt | 7 | **0** |
| Sets A to J, stale in answer | 1 | **0** |
| Sets A to F, noise present | 16/46 | 19/46 |
| Set K, correct | 17/23 | 17/23 |

What it does: messages that facts do not hold (lessons, a pet, a family event, where something ended up, a changed plan) now get notes, and notes never restate facts or ride along with a stronger fact. What it costs: four questions on sets I and J whose answer lives in a note next to a strong fact or in a note that a run did not write:

- "When am I going to Hanoi?" (J): `Goal: trip to Hanoi` sets the window, the date notes fall outside it. **The rule's real cost**, and the pattern long stories will have often (a plan with details that change). To revisit with the gate work (step 3), for example by letting a note through when it is about the same thing as the fact that sets the window.
- "What are my kitchen cabinets?" and "Who moved to Canada?" (J): the notes that held the answer were not written in these runs (note variation).
- "Who was my partner before Elena?" (I): the old partner is archived; the note that carried him was not written. Belongs to the archived-values step.

<a id="set-m"></a>

## 10. Set M: long, crowded histories (2026-10-29)

Set M (3 users, 92 to 100 messages each over about 18 months, 289 messages, 57 questions) was written after the step 1 and 2 fixes and frozen with its predictions ([../../predictions/set_M.md](predictions/set_M.md)) before any run. It tests the project's main hypothesis: on long histories, smart memory answers better than plain vector search.

| File | Run |
|---|---|
| `full.txt`, `full.json` | 1: the current system, baseline and smart |
| `facts_only.txt`, `facts_only.json` | 2: `SUMMARIES=0`, on the data of run 1 |
| `no_fact_window.txt`, `no_fact_window.json` | 3: `NOTE_FACT_WINDOW=0`, on the data of run 1 |
| `no_about_user.txt`, `no_about_user.json` | 4: `ABOUT_USER=0`, ingested again |
| `no_note_tags.txt`, `no_note_tags.json` | 5: `NOTE_TAGS=0`, ingested again |

Run 1 was started once, stopped during the ingestion of the first user (before any question was asked) to change a colour setting that turned out to have no effect, and started again. Ingestion deletes each user first, so the second start is the one run.

### Result

| Set M, 57 questions | Needed present (54) | Stale in prompt | Avg lines | Answers, raw | Answers, reviewed | Stale in answer |
|---|---|---|---|---|---|---|
| Baseline | **48/54** | 16 | 4.0 | **47/57** | **48/57** | 4 |
| Smart | 36/54 | 7 | 2.2 | 36/57 | 36/57 | 5 |

- **Reviewed:** the three hand rules changed one answer. The baseline's dinner (a one-pot tomato and basil pasta) is meat-free and has no aubergine, so it counts; smart's (chicken fajitas) does not. Both modes warned about shellfish and about penicillin.
- **Head to head:** both right on 34, both wrong on 7, **baseline only on 14, smart only on 2**. Sign test on the 16 differing questions: p of about 0.004.
- **The baseline was the same in all five runs** (47/57 raw, 48/54 needed), so the comparison is not run-to-run noise.

#### Against the pre-registered hypothesis

| | Pre-registered | Predicted | Found |
|---|---|---|---|
| H1: smart answers more than the baseline | d = smart − baseline; +3 or more: smart better; −3 or less: baseline better | about −2.5 ("no clear difference", leaning to the baseline) | **d = −12: the baseline is better on long histories** |
| H2: fewer outdated values in smart's answers | | holds | **fails**: 5 against 4 (raw) |
| H3: under 2 lines per question | | holds (about 1.8) | **fails**: 2.2 |
| Baseline answers | | about 39 (34 to 44) | **48, above the range** |
| Smart answers | | about 36.5 (32 to 41) | 36, in range |

The predictions were close for smart and poor for the baseline, as on set L: the everyday questions on the same topics ("best time to visit Japan?") did not crowd the statements out of the baseline's four lines as much as expected. Embedding similarity found the right statement among about 95 messages in 48 of 54 questions.

### Why smart lost: errors accumulate with length

The 14 questions only the baseline answered, by cause:

| Cause | Questions | What happened |
|---|---|---|
| **A current fact was wrong or missing** | 5 | Solveig's city stayed **Oslo**: "Fjordline transferred me to their office in Kristiansand" stored no city. Ruben's city ended on **Utrecht**: house hunting ("looking at houses in Rotterdam, prices in Utrecht are crazy") and "I now commute to Utrecht by train" each replaced the city. Ruben's job title became **"no office"** ("Peatline has no office"), which also broke his bio. Tamsin's music: "I quit the covers band ... joined a choir" kept `hobby = bass` and stored `job_title = choir member`, so smart said she plays bass |
| **A note lost or never written** | 5 | Iceland's puffins (the trip's notes were merged and the detail dropped), the half-marathon time, Kiwibyte's buyer, Joost's job, Esme's violin: each message is in the baseline's four lines word for word, while smart had no note that passed or kept the detail |
| **Other people** | 1 | "Where does Callum live now?": no Callum note passed the gate; the answer was "Bristol" |
| **A name variant split one employer in two** | 1 | `Fjordline Aquaculture` and `Fjordline` were stored as two employers, so "before Fjordline" read the wrong past value |
| **Notes and facts crowded out by family facts** | 1 | The summer trip: four `family_member` and city lines filled the prompt; the trip notes did not pass |
| **Diet not stored** | 1 | "I've gone vegetarian" reached no line for the dinner question |

Smart's two wins were past questions (the city before Oslo, the school before Clifton Down), where the baseline's four lines held the newer messages.

**The pattern:** each statement is one more chance for the 8B extractor to mis-store a fact, and a single-valued fact (city, job title) is replaced by whatever was extracted last, including incidental mentions (a commute, a house viewing, a friend's wedding city). Over 30 statements those mistakes accumulate, and smart trusts its facts. The baseline cannot make this kind of mistake: it hands the model the original sentences and lets it read them. Notes, which hold episodes, lose details when they are merged and pass at most two at a time.

Also seen: "When is my wedding?" was answered "You got married to Priya on April 29, 2025", read from the `(since 2025-04-29)` label of the partner fact (the known label problem). One note calls Ruben's brother Sem his "friend".

### Ablations (smart, answers raw)

| Run | Smart answers | Against run 1 | Predicted | Reading |
|---|---|---|---|---|
| 1, full | 36 | | | |
| 2, facts only | **17** | **−19** | about −8 | Notes carry most of what smart answers on long histories |
| 3, note window among notes only | 38 | +2 | −1 to +2 | within run noise (2 or less) |
| 4, `about_user` off | 34 | −2 | −2 to −4 | within run noise for answers, but the stored facts show the effect: Tamsin's city went Norwich → Glasgow → Dublin → Bristol → Dublin → **Exeter** (her friend's and her mum's cities) and her job became "senior paramedic" (her wife's); with the check on, all of these were blocked |
| 5, untagged notes | 37 | +1 | −1 to −3 | within run noise |

The baseline gave 47 in every run. Run timings varied (8 to 42 minutes) with the load on the machine; they do not affect results.

### What this means for the project

- **The main hypothesis is rejected on this evidence.** With an 8B model doing the extraction, structured facts are less reliable than the raw messages they come from, and the gap grows with history length instead of shrinking. Smart is better only on prompt size (2.2 against 4.0 lines) and on some past questions.
- **The parts are not useless.** `about_user` keeps other people's lives out of the facts (run 4), notes double what facts alone can answer (run 2), and on the short sets smart never let an outdated value through. But none of this beats giving the model the right four sentences.
- **The likely next design is a hybrid:** the baseline's raw messages as the main memory, with facts used where they are strong (current values, outdated values marked or filtered, allergies) rather than as a replacement. That is a new hypothesis and needs a fresh set.

<a id="change-rule"></a>

## 11. Current facts that stay right: development record (step 1 of the hybrid plan, 2026-10-29)

Set M showed that on long histories smart's current facts go wrong: 6 of 12 current-fact slots were right at the end (city, employer, job title and partner for three users; every city and every job title wrong). The causes: passing mentions replaced single values ("I now commute to Utrecht", a house viewing, a friend's wedding city, "Peatline has no office" as a job title), one employer was split in two by a name variant, a wife's new job became the user's, and a transfer to another city stored no city ([../set_M/log.md](#set-m)).

The changes ([05](05_write_path.md), sections 4.3 and 4.4):

1. **Change rule** (`signals_change`, switch `CHANGE_RULE`): a new city, employer, job title or partner replaces an active one only if the message says it changed (change words, not only a plan).
2. **Name variants** (`same_name`): one name containing the other is the same value, for duplicates and retractions.
3. **Known people**: stored partner and family names count as someone else in `about_user`.
4. **One extraction prompt line**: "my company transferred me to their office in X" means `lives_in = X`.

This is **development on spent sets** (M and L are spent). It prepares the facts for step 2, the hybrid read path; the valid test is a fresh set N.

### Checks before any run (offline, no model)

- Every replacement of a city, employer, job title or partner actually stored in the verbose runs of sets A to J, L and M (`../regressions/A_to_J_first_person.txt`, `first_person_L.txt`, `../set_M/full.txt`) was replayed through the rule. First version: it blocked all seven wrong replacements on M (the choir as a job, Callum's Dublin, Priya's hospital, Bristol while still a plan, "no office", the house viewing, the commute) and two right ones on sets C and F ("started a new position at Delta Labs", "I switched employers, I'm at Riverside Clinic now"). "New position", "switched" and "I'm at" were added before freezing; the replay then blocks only the seven wrong ones and keeps every real move, job change and new partner of sets A to M.
- On that replay, M's current facts would be 11 of 12; the twelfth (Kristiansand) depends on the new prompt line.
- 20 new tests (244 in all), including two database tests.

### Predictions (written before the runs)

Runs, cache off, with the new `make` targets:

1. `make eval SET=M OUT=docs/results/logs/change_rule_M` (development, labelled)
2. `make eval SET=L OUT=docs/results/logs/change_rule_L`
3. `make eval SET="A B C D E F G H I J" OUT=docs/results/regressions/A_to_J_change_rule`
4. `make sessions OUT=docs/results/set_K/change_rule`

| Measure | Reference | Prediction |
|---|---|---|
| Set M, current-fact slots right (12) | 6 | 10 to 12 (11 most likely; Kristiansand about 50%) |
| Set M, smart answers (57, raw) | 36 | about 40 (38 to 42): the three cities, Ruben's job title, "before Fjordline", Tamsin's city questions; the bio and the music question may stay wrong for other reasons |
| Set M, smart stale in answer | 5 | 2 or 3 |
| Set M, baseline | 47 | 47 (±1, noise) |
| Rejections "no change signalled" | | about 7 on M, every one wrong as a replacement; 0 to 2 elsewhere |
| Sets A to J, L, K | as in the step 2 runs | the same within noise (±2 per set and mode); the prompt line can change a few extractions anywhere |

Kept if M's current-fact slots reach at least 10, no set loses more than 1 needed fact, and no rejection drops a true change. Otherwise reported and reworked.

### Results of iteration 1 (2026-10-30)

Outputs (each as `.txt` and `.json`): `change_rule_M`, `change_rule_L`, `../regressions/A_to_J_change_rule`, `../set_K/change_rule`.

| Measure | Reference | Predicted | Found |
|---|---|---|---|
| Set M, smart answers (raw) | 36 | about 40 (38 to 42) | **41** |
| Set M, smart needed present | 36/54 | | 42/54 |
| Set M, smart stale in answer | 5 | 2 or 3 | **2** |
| Set M, baseline | 47 | 47 (±1) | 46 (one bike-count answer flipped: noise) |
| Set M, current-fact slots right (12) | 6 | 10 to 12 | **8 of the 11 visible** (Tamsin's job title did not reach any prompt) |
| Sets A to J, L, K | | the same within noise | smart identical on every question of A to J and on L (26) and K (17); the baseline moved by one question in A and D, in opposite directions |

Fixed on M: Ruben's city and job title, Tamsin's city, both past-city questions, "before Fjordline", and (note variation) the Iceland puffins. Two answers were lost to note variation (the brother's city, the wife's job).

**The criterion (at least 10 current-fact slots) failed**, because the run exposed three mistakes in the word lists, all on M:

| Wrong fact | Message | Mistake |
|---|---|---|
| Solveig's city stayed Oslo | "Fjordline transferred me to **their** office in Kristiansand" | `about_user` counted the possessive "their" as someone else; Kristiansand was extracted and then rejected as "about someone else" |
| Solveig's partner became Jonas | "My sister Ingvild got engaged to her partner Jonas" | the partner check only looked for a partner word, not whose partner it is |
| Tamsin's partner became Callum | "Callum is getting married in Dublin next spring and asked me to give a speech" | the same; Callum opens the sentence, so no subject word stands before him |

The rejections logged (`no change signalled` and `about someone else`) were otherwise all right: other people's cities and jobs, Bristol while still a plan, the house viewing, the commute, "choir member", "home" as a city.

### Iteration 1b: three fixes to `about_user`

1. **Possessives are not subjects:** his, her, their and its no longer mark someone else ("their office", "her name is Odile").
2. **Partners get the clause rule** of cities and jobs, with the partner nouns themselves ignored: "My sister Ingvild got engaged to her partner Jonas" is the sister's partner; "My wife is called Ines" is the user's.
3. **"X is getting married / engaged"** is news about X, unless "X and I" ("Priya and I are getting married").

Checked before any run: the 30 sample sentences of steps 1 and 1b keep their verdicts; the sweep over every message of sets A to M changes only in the right direction (Kristiansand and possessives pass; a sister's and a brother's wedding and Callum no longer give the user a partner); 4 more tests (248).

#### Predictions for iteration 1b (written before the runs)

Same runs as iteration 1; M with its `.txt` this time (`make eval` writes both).

| Measure | Iteration 1 | Prediction |
|---|---|---|
| Set M, current-fact slots right (12) | 8 of 11 visible | 11 or 12 |
| Set M, smart answers (raw) | 41 | about 43 (41 to 45): Solveig's city and partner; note variation ±2 |
| Set M, smart stale in answer | 2 | 0 to 2 |
| Set M, baseline | 46 | 46 to 47 |
| Sets A to J, L, K | | the same within noise |

Same criteria as before.

### Results of iteration 1b (2026-10-30)

Outputs (each as `.txt` and `.json`): `change_rule_1b_M`, `change_rule_1b_L`, `../regressions/A_to_J_change_rule_1b`, `../set_K/change_rule_1b`.

| Measure | Iteration 1 | Predicted | Iteration 1b |
|---|---|---|---|
| Set M, current-fact slots right (12) | 8 of 11 visible | 11 or 12 | **12 of 12** |
| Set M, smart answers (raw / reviewed) | 41 | about 43 (41 to 45) | **43 / 43** |
| Set M, smart needed present | 42/54 | | 43/54 |
| Set M, smart stale in answer | 2 | 0 to 2 | **1** |
| Set M, baseline (raw / reviewed) | 46 | 46 to 47 | 46 / 47 |
| Sets A to J, L, K, smart | | the same within noise | identical on every set of A to J; L 26, K 17 |

Head to head on M (reviewed): both right 38, baseline only 8, smart only 5, both wrong 6.

**All criteria met; the changes are kept.**

Every user now ends with the right city (Kristiansand, Bristol, Rotterdam), employer, job title and partner. Smart's remaining losses on M are not current facts: details that the baseline finds word for word and smart's notes lose or do not pass (a brother's move, a daughter's violin, the summer trip, the half-marathon time, a hobby that changed, Kiwibyte's buyer, a husband's job, a bio). Both modes miss Solveig's two past-city questions: smart's past lines are chosen by similarity, not by date, so "before Kristiansand" got Stavanger and "before Oslo" got Oslo (the known gap of the past rule).

### Step 1 closed: what it changed on set M

| Smart on set M | Before step 1 | After step 1 |
|---|---|---|
| Current-fact slots right (12) | 6 | **12** |
| Answers (reviewed, 57) | 36 | **43** |
| Gap to the baseline | −12 | **−4** |
| Stale in answer | 5 | **1** |

Development on a spent set, so not evidence that it generalises; it prepares the facts for step 2, the hybrid read path, which is meant to recover what the baseline still finds and smart does not.

<a id="hybrid"></a>

## 12. Hybrid read path: development record (step 2 of the hybrid plan, 2026-10-30)

Set M rejected the main hypothesis: on long histories the baseline's four raw messages answered more than smart's facts and notes ([../set_M/log.md](#set-m)). Step 1 made the current facts right (12 of 12 on M; smart 36 to 43 against the baseline's 47, reviewed; [change_rule_dev.md](#change-rule)). Step 2 tries to beat the baseline by keeping its recall and adding what facts do well.

This is **development on spent sets** (M and L). The valid test is a fresh blind set N (step 4), with success pre-registered as hybrid ≥ baseline + 3.

### The design

Two new modes; none, baseline and smart are unchanged ([../../06_read_path.md](06_read_path.md), section 11).

**`hybrid`**, in prompt order:

1. Up to 2 current fact lines, chosen by smart's gate (allergy pass included).
2. For a past question only: one timeline line with every value of the relation asked about, oldest first (`Lives in, oldest first: Stavanger -> Oslo -> Kristiansand (now)`). Retracted values are included and tagged `(ended)`.
3. The baseline's top 4 messages word for word. A message whose fact has since been superseded is marked `[outdated: now X]`; one whose fact was retracted is marked `[no longer true: X]`.

No episode notes. At most 7 lines against the baseline's 4.

**`full`**: every user message, oldest first (about 1,100 tokens per M user), with the context window set to 8192 for this mode only. It is a reference ceiling.

**Scoring:** an outdated value that appears only on a marked line is counted as "stale, marked", apart from "stale in prompt". Only hybrid writes marked lines, so the other modes' numbers do not change.

### Checks before any run (offline, no model)

- 26 new tests (274 in all), including 9 database tests: markers through a chain of moves, a retraction, a user who moved back, the timeline only on past questions, a retracted employer in the timeline, both switches, the baseline query unchanged, full oldest first.
- The baseline's query is untouched (`baseline_messages` runs the same SQL and also returns the ids), so hybrid's messages are exactly the baseline's.
- `chat()` gets a context size only for the full mode. The calls and cache keys of the other modes are unchanged.

### Runs

Both runs reuse the data stored by the step 1b runs (`--no-ingest`), so the facts are the ones that gave 12 of 12 on M and only the read path changes. Cache off, all four modes answered.

1. `make eval SET=M OUT=docs/results/logs/hybrid_M ARGS=--no-ingest`
2. `make eval SET=L OUT=docs/results/logs/hybrid_L ARGS=--no-ingest`
3. (optional) `make eval SET="A B C D E F G H I J" OUT=docs/results/regressions/A_to_J_hybrid ARGS=--no-ingest`

If M or L was deleted from the database since step 1b, drop `ARGS=--no-ingest` (it ingests again: slower, and the facts may differ slightly).

### Predictions (written before the runs)

Reference: the step 1b runs (`change_rule_1b_M`, `change_rule_1b_L`), raw answers.

| Measure | Reference | Prediction |
|---|---|---|
| M, baseline answers (57) | 46 | 46 (±1, noise) |
| M, smart answers | 43 | 43 (±2, notes vary) |
| **M, hybrid answers** | | **about 50 (47 to 52)** |
| M, full answers | | about 48 (43 to 53): wide, the 8B model has not been tested on 95 messages at once |
| M, hybrid stale in prompt (not marked) | baseline 16 | about 10 (8 to 12): only user facts can be marked, and only in the message that first gave them; trips, a brother's or a friend's city are not |
| M, hybrid stale, marked | | about 5 (3 to 7) |
| M, hybrid stale in answer | baseline 4, smart 1 | 1 or 2 |
| M, hybrid avg lines | baseline 4.0, smart 2.2 | about 5.2 |
| L, baseline / smart answers (30) | 27 / 26 | the same (±1) |
| **L, hybrid answers** | | **about 28 (26 to 29)** |
| L, full answers | | about 27 (24 to 29) |

Where the M gains should come from, question by question:

| Question | Base / smart in 1b | Expected for hybrid |
|---|---|---|
| Tamsin: Which city do I live in? | ✗ / ✓ | ✓: the `Lives in: Bristol` line, and the old cities marked |
| Tamsin: before Bristol; before Clifton Down School | ✗ / ✓ each | ✓ each: timeline |
| Ruben: before Rotterdam | ✗ / ✓ | ✓: timeline |
| Solveig: before Kristiansand; before Oslo | ✗ / ✗ each | ✓ each, about 70%: the timeline shows the order that past lines lost |
| The 8 baseline-only questions (brother's move, violin, summer trip, half marathon, music, Kiwibyte's buyer, Joost's job, bio) | ✓ / ✗ | kept, with one possibly lost to the extra lines |
| Ruben's brother, the wedding, the signature, the dinner | ✗ / ✗ | still wrong: nothing in hybrid addresses them (no user fact behind the brother's city; the `(since date)` label; vegetarian not stored) |

Expected sum: 46 − about 1 (distraction) + 1 (Tamsin's city) + about 2.5 (three timelines) + about 1.4 (Solveig) ≈ 50. That is d = hybrid − baseline ≈ +4 on M, just above the +3 that set N will require. On L the room is small (the baseline already has 27 of 30).

**Go to set N** if, on M, hybrid ≥ baseline + 2 (raw), hybrid's stale answers are ≤ the baseline's, and on L hybrid ≥ baseline − 1. Otherwise report it and rework before writing set N. Because this is development, a pass is not evidence: it only says hybrid is worth a blind test.

### Results (2026-10-30)

Outputs (each as `.txt` and `.json`): `hybrid_M`, `hybrid_L`. Run 3 (A to J) was not run.

| Measure | Reference | Predicted | Found |
|---|---|---|---|
| M, baseline answers (57) | 46 | 46 (±1) | 46 |
| M, smart answers | 43 | 43 (±2) | 43 |
| **M, hybrid answers** | | **about 50 (47 to 52)** | **50** |
| M, full answers | | about 48 (43 to 53) | **44**, below the baseline |
| M, needed present (54) | baseline 48, smart 43 | | hybrid **52** |
| M, hybrid stale in prompt (not marked) | baseline 16 | about 10 (8 to 12) | 11 |
| M, hybrid stale, marked | | about 5 (3 to 7) | 5 |
| M, hybrid stale in answer | baseline 4, smart 1 | 1 or 2 | 2 (both right answers that name the old value too: "moved from Trondheim to Galway", "switched from Brittany") |
| M, hybrid avg lines | | about 5.2 | 5.2 |
| L, baseline / smart answers (30) | 27 / 26 | the same (±1) | 27 / 26 |
| **L, hybrid answers** | | **about 28 (26 to 29)** | **28** |
| L, full answers | | about 27 (24 to 29) | 27 |

**The go criteria are met:** on M hybrid is baseline + 4 (at least + 2 needed), its stale answers are 2 against the baseline's 4, and on L hybrid is baseline + 1.

#### Head to head on M

Hybrid against the baseline: both right 44, **hybrid only 6, baseline only 2**, both wrong 5. A sign test on the 8 differing questions gives p of about 0.29. It is in the right direction, but it is not evidence, and M is spent.

Hybrid against smart: hybrid only 9, smart only 2.

The 6 gains are exactly the ones predicted:

| Question | What did it |
|---|---|
| Solveig: before Kristiansand; before Oslo | the timeline `Stavanger -> Oslo -> Kristiansand (now)`. Both modes were wrong before |
| Tamsin: before Bristol; before Clifton Down School | the timeline |
| Ruben: before Rotterdam | the timeline |
| Tamsin: Which city do I live in? | the `Lives in: Bristol` line, with the old cities marked |

Five of the six are past questions. On present questions hybrid kept the baseline's answers. The 8 questions smart had lost (violin, trip, half marathon, music, Kiwibyte's buyer, Joost's job, a brother's move) all came back, because the messages are the baseline's.

The 2 losses, both caused by what hybrid adds:

| Question | Cause |
|---|---|
| Ruben: Which languages do I speak? | Fact lines `Speaks: English`, `Speaks: Spanish` (Dutch was never extracted). The model answered from the incomplete facts, although the message above said "I speak Dutch and English" |
| Ruben: Write a one-line professional bio | The message "Hi, I'm Ruben. I'm a software engineer at Kiwibyte in Utrecht." carried three markers (`now head of engineering`, `now Peatline`, `now Rotterdam`). The bio left out the name, which the check requires. A marker covers the whole message, including the parts that are still true |

The 5 both-wrong questions are as predicted: the wedding (hybrid now says "Dublin", Callum's wedding, with `Partner: Priya` on top), the signature, Ruben's brother, the dinner, and the bike count.

On L the gains are Maren's name (fact line) and her wedding (a keyword pass: "your brother Fintan is getting married" is right). The loss is the suitcase flight: the lines were exactly the baseline's, and the answer was "I don't know". So the only difference was the header, which counts as noise.

#### Full is not a ceiling for this model

With the whole history (about 96 messages) the 8B model answered 44 on M, below the baseline's 46. It said "I don't know" with the answer in the prompt (partner, sister's job, sport, mum, cat, bio) and picked old values (Oslo, the Norwich school, the covers band). It won only on past questions and Ruben's brother. On this model, choosing a few lines and marking the old ones does better than giving everything. That part of the hybrid design is now supported by evidence, not only assumed.

#### What this means

Hybrid is worth a blind test. Its gains come from facts used where they are strong (order of past values, current value on top), on top of the baseline's recall. Its losses come from facts that are incomplete (multi-valued relations) and from markers covering whole messages. Both are candidates to change, but they were found on a spent set: if changed before set N, the change is labelled development, and set N measures the result blind.

<a id="set-n"></a>

## 13. Set N: the blind test of the hybrid read path (2026-10-30)

Set N has 3 new users, 283 messages and 57 questions, with the question mix of set M. It was written after the hybrid step and frozen with its predictions ([../../predictions/set_N.md](predictions/set_N.md)) before any run. It was run once (`full.txt`, `full.json`), with ingestion, cache off, and four modes answering. It ran without a restart and took 61 minutes.

### Result

| Set N, 57 questions | Needed present (54) | Stale in prompt | Stale, marked | Avg lines | Answers, raw | Answers, reviewed | Stale in answer |
|---|---|---|---|---|---|---|---|
| Baseline | 46 | 18 | 0 | 4.0 | 45 | **45** | 4 |
| Smart | 44 | 10 | 0 | 2.5 | 42 | **42** | 6 |
| **Hybrid** | **52** | 13 | 5 | 5.2 | 50 | **50** | **2** |
| Full (whole history) | - | 19 | 0 | 94.3 | 50 | **50** | 2 |

**Hand review.** The three hand rules (tree nuts, sesame, lactose) agreed with the keyword score in every mode, so reviewed = raw:

- **Cookies:** smart and hybrid warn about tree nuts; the baseline and full give generic advice.
- **Takeaway:** smart, hybrid and full warn about sesame; the baseline does not.
- **Dessert:** smart and hybrid suggest lactose-free desserts. Full suggests a strudel with oat milk, "lactose-friendly", which counts because it mentions the intolerance. The baseline suggests tiramisu.

### Against the pre-registered hypotheses

| | Rule | Predicted | Found | Verdict |
|---|---|---|---|---|
| **H1: hybrid better than the baseline** | d = hybrid − baseline ≥ +3 | d about +3 (0 to +6), 50% chance of +3 or more | **d = +5** (50 against 45) | **Met by the pre-registered rule. Not statistically significant:** hybrid only right on 8, baseline only on 3, sign test p of about 0.23 |
| H2: hybrid's outdated answers ≤ the baseline's | | hybrid about 2, baseline about 4 | 2 against 4 | **Met** |
| H3 (replication of M): smart − baseline ≤ −3 | | about −3 | −3 (42 against 45; smart only 8, baseline only 11) | **Met:** smart alone is still worse than vector search |

| Measure | Predicted | Found |
|---|---|---|
| Baseline | about 44 (39 to 48) | 45 |
| Smart | about 41 (36 to 45) | 42 |
| Hybrid | about 46.7 (42 to 50) | 50, the top of the range |
| Full | about 42 (37 to 47), "below the baseline, as on M" | **50, wrong**: equal to hybrid |
| Stale in prompt (baseline / smart / hybrid) | 15 / 5 / 10 | 18 / 10 / 13 |
| Stale, marked | about 5 | 5 |
| Average lines (smart / hybrid) | 2.1 / 5.2 | 2.5 / 5.2 |

### Where hybrid and the baseline differ

The 8 questions only hybrid answered:

| Question | Baseline's answer | What did it for hybrid |
|---|---|---|
| Marisol: Which city did I live in before Lyon? | "I don't know." | timeline `Valencia -> Lyon (now)` |
| Kwame: Where did I live before Manchester? | "I don't know." | timeline `Leeds -> Manchester (now)` |
| Henrike: Where do I work? | Elbquill Press (old) | fact line `Works at: Harbourlight Games` |
| Henrike: What's my job title? | senior editor (old) | fact line `Job title: narrative designer` |
| Marisol: cookies (hand) | generic advice | the allergy line (allergy pass) |
| Kwame: takeaway (hand) | generic advice | the allergy line |
| Henrike: dessert (hand) | tiramisu | the intolerance line (`Allergic to: lactose`) |
| Kwame: When is my driving test? (trap) | "I don't know." | none: the same four messages as the baseline. Counts as noise |

The 3 questions only the baseline answered. **All three were lost because the facts layer was wrong or cut short**, and the model trusted it over the messages:

| Question | Cause |
|---|---|
| Marisol: Where do I work now? | The active fact was still `Works at: Clinica Albereda`, her first employer: Pharmavert was never stored, so nothing replaced it. Hybrid answered from that line, although the message below said "I'm starting at Alpenmed". Smart was right through its notes |
| Henrike: Which languages do I speak? | Three `speaks` facts were stored and right, but hybrid shows at most 2 fact lines, so Danish was cut. The model answered "English and German" from the facts, although the message below names all three. **A design flaw, not an extraction error:** the cap of 2 splits a multi-valued answer |
| Henrike: Where does my brother live now? | The message "Malte moved to Vienna" was marked `[outdated: now Jonte]`. From that message the extractor had stored `name = Malte`, the brother's name as hers, and a later message replaced it with `name = Jonte`, her partner's. The wrong marker made the right message look outdated, and the model said "I don't know" |

Both wrong (4): Marisol's city, Kwame's car breakdowns, Kwame's signature, Henrike's bio.

- **Marisol's city:** every mode but full answered Lyon. The fact stayed `Lives in: Lyon`, because "Moved to Grenoble with Bastien" stored no city, and the baseline's four lines held only Lyon messages.
- **Car breakdowns:** smart and full counted two; the baseline listed both breakdowns but hedged; hybrid said "I don't know" with both in its lines.
- **Signature and bio:** asked "for me", the model said it did not know the name, or wrote a bio without it. In hybrid, Kwame's introduction carried four markers, one of them wrong (`[outdated: now Declan]`).

### The write path on fresh data

The step 1 fixes were developed on M, where the current facts reached 12 of 12. On N:

| Slot (city, employer, job title, partner) | Marisol | Kwame | Henrike |
|---|---|---|---|
| Right at the end | 2 of 4 (city stuck at Lyon, employer stuck at Clinica Albereda) | 4 of 4 | 4 of 4 (city `Altona`, a district of Hamburg; it went Kiel → Hamburg → Ottensen → Altona) |

That is 10 of 12, against 12 of 12 on the development set.

**A new error in every user: `name` is overwritten by other people's names.** Marisol became Lucia (her sister), Kwame became Declan (his friend), and Henrike became Malte, then Jonte. `name` is single-valued, and neither `about_user` nor the change rule covers it. In hybrid these errors become wrong markers (`[outdated: now Declan]` on "Hi, I'm Kwame"). That cost one answer here, and may explain the "I don't know your name" signatures.

### Full is not consistently below the baseline

On M, full scored 44 against the baseline's 46. On N it scored 50 against 45, level with hybrid. Over the two sets it is about level with the baseline (94 against 91) and below hybrid (94 against 100). On these histories (about 1,100 tokens per user), the 8B model can use everything about as well as it uses four chosen messages. Full has no way to tell old values from new apart from the dates. It answered Marisol's city right, the one question every other mode missed, but it said "I don't know" on her partner and her cookies. Full does not scale; it is a ceiling for this history length only.

### What this means

- **The project's expected outcome is met on its pre-registered test, narrowly and not significantly.** Hybrid answered 50 of 57 against the baseline's 45. The rule fixed before the run (+3) is passed; the sign test (8 against 3, p of about 0.23) is not significant. Taken with the development result on M (+4, also not significant), hybrid has beaten the baseline on both long-history sets it has seen. Each set is too small to prove it alone.
- **What helps is now clear.** All 7 gains that can be explained come from facts used where they are strong: timelines for past questions (2), current values on top (2), and allergies and intolerances on indirect questions (3).
- **What hurts is also clear.** All 3 losses come from the facts layer: a stale employer that was never replaced, the 2-line cap cutting a list, and a wrong marker from a corrupted `name`. Hybrid is only as good as its facts, and the facts still go wrong on fresh data.
- **Smart alone is worse than vector memory again** (H3, −3). The original hypothesis stays rejected; the hybrid one is supported.
- **Fixes the data suggests**, none of them made: keep `name` to first-person introductions; show every value of a multi-valued relation that passes the gate (or none); drop a marker whose new value is a different kind of thing. N is now spent, so any of these is development and needs a new blind set.

<a id="set-n-fixes"></a>

## 14. Fixes from set N: development record (2026-10-30)

Set N passed its pre-registered test: hybrid scored 50 against the baseline's 45. Every one of hybrid's 3 losses came from the facts layer ([../set_N/log.md](#set-n)). This step fixes the causes. It is **development on spent sets** (N, M and L). The valid test is a fresh blind set O, written after these runs.

### The changes

| # | Problem on N | Change | Where |
|---|---|---|---|
| 1 | Every user's `name` was overwritten by someone else's (Lucia, Declan, Malte, then Jonte; Tamsin became Callum on M too). The wrong `name` facts then produced wrong markers (`[outdated: now Jonte]` on "Malte moved to Vienna") | `about_user` gives the user a name only from a self-introduction: "I'm X", "I am X", "call me X", "I go by X", or a message with "my name" in it | `write/actions.py` ([05](05_write_path.md), 4.3) |
| 2 | "Moved to Grenoble with Bastien" stored no city. The message has no first-person word, so `about_user` rejected Grenoble | A sentence that opens with moved, started, got, joined, left, quit, began, bought, switched, relocated, transferred, finished or signed counts as first person | `write/actions.py` (4.3) |
| 3 | "I got a job at Pharmavert in Lyon" was rejected as "no change signalled", so the first employer stayed active, and hybrid answered with it | "got a job" / "got the job" is a change word for `works_at` | `write/actions.py` (4.4) |
| 4 | Hybrid showed 2 fact lines, so a list of three languages lost Danish | Every value of the first two kinds of fact that pass the gate, at most 4 lines | `read/hybrid.py` ([06](06_read_path.md), 11.1) |
| 5 | A marker named only the new value, so the model could not tell which part of a message changed (M: a bio dropped the still-true name; N: a brother's move looked outdated) | The marker names the old value and its kind: `[outdated: Lives in: Oslo -> now Kristiansand]`, `[no longer true: Works at: Brackwell Consulting]`; the header says the rest of the message may still be true | `read/hybrid_rules.py`, `assistant.py` (11.2) |

### Checks before any run (offline, no model)

- **Name questions still work:** every "What's my name?" question in sets B, C, D, G, H and L has an introduction that passes the new name rule.
- **Implicit subject is narrow:** across every message of sets A to N, it changes the verdict of two messages only, both in N ("Moved to Grenoble with Bastien" and "Bought a second-hand alto saxophone").
- **"got a job" is narrow:** it appears in two messages of all the sets. One is Marisol's. The other, "Priya got a job at the hospital", is still rejected (Priya is a known person, and "in the summer" is a plan).
- **Tests:** 14 more, 288 in all. They cover the name rule on the five set N sentences, the silent subject, "got a job", all three languages shown, `top_relations`, and the new marker format.

### Runs

The write path changed, so each run ingests again (no `--no-ingest`). Cache off, all four modes.

1. `make eval SET=N OUT=docs/results/logs/fixes_N`
2. `make eval SET=M OUT=docs/results/logs/fixes_M`
3. `make eval SET=L OUT=docs/results/logs/fixes_L`

Each long set takes about an hour.

### Predictions (written before the runs)

| Measure | Last run | Prediction |
|---|---|---|
| N: name right at the end (3 users) | 0 of 3 | 3 of 3 |
| N: city, employer, job title, partner right (12 slots) | 10 | 12 (11 to 12) |
| N: baseline | 45 | 45 (±1; the messages are the same) |
| N: smart | 42 | about 44 (41 to 46) |
| **N: hybrid** | 50 | **about 53 (50 to 55)**: likely gains are Marisol's employer, Henrike's languages and her brother's city; possible ones are Marisol's city (the `Lives in: Grenoble` line above messages about Lyon) and the signature or bio; re-ingestion moves facts and notes by about ±2 |
| N: full | 50 | 50 (±2) |
| M: name right (3 users) | 2 of 3 (Tamsin became Callum) | 3 of 3 |
| M: baseline / smart | 46 / 43 | the same (±2) |
| **M: hybrid** | 50 | **about 51 (48 to 53)**: Ruben's bio may come back (labelled marker); Ruben's languages stay wrong (Dutch is never extracted, so there is nothing to show) |
| **L: hybrid** | 28 | 28 (±1) |

**Go to set O** if on N the names are 3 of 3 and the slots at least 11 of 12, hybrid is at least 52 on N, and hybrid loses no more than 2 against its last run on M (50) or L (28). Otherwise report it and rework. A pass is not evidence, because N, M and L are spent. Set O decides.

### Results (2026-10-30)

Outputs (each as `.txt` and `.json`): `fixes_N`, `fixes_M`, `fixes_L`. All three were run, with ingestion and cache off.

| Measure | Last run | Predicted | Found |
|---|---|---|---|
| Name right at the end (N, 3 users) | 0 of 3 | 3 of 3 | **3 of 3** |
| Name right at the end (M, 3 users) | 2 of 3 | 3 of 3 | **3 of 3** |
| N: city, employer, job title, partner (12) | 10 | 12 (11 to 12) | **12** |
| N: baseline | 45 | 45 (±1) | 45 |
| N: smart | 42 | about 44 (41 to 46) | 40 |
| **N: hybrid** | 50 | **about 53 (50 to 55)** | **50** |
| N: hybrid stale in answer | 2 | | **0** |
| N: full | 50 | 50 (±2) | 50 |
| M: baseline / smart | 46 / 43 | the same (±2) | 46 / 42 |
| **M: hybrid** | 50 | about 51 (48 to 53) | 49 |
| L: hybrid | 28 | 28 (±1) | 28 |

**The write-path fixes worked:** every name is now right, and so is every key fact on N. Ruben's Dutch is now extracted on M, so his languages question is right too.

**The go criterion failed:** hybrid needed at least 52 on N and got 50. On N it gained the four answers the fixes aimed at: Marisol's city and employer, Henrike's brother and her three languages. It also lost four:

| Question | Cause |
|---|---|
| Marisol: Where does my sister live now? / What does my sister do? | Fix 4 showed every value of the top kinds: three `family_member` lines (Lucia, dad, and Bastien wrongly filed as family) above the messages. The model said "I don't know" with the sister's messages in the prompt |
| Henrike: Do I still go sailing? | "You don't know." An active `Hobby: dinghy sailing` sat above a message marked `[no longer true: Hobby: sailing]`, under the longer header |
| Kwame: When is my driving test? | The trap: the same lines as the baseline. It was right last time by chance |

On M the losses were similar: "Do I still drink coffee?" got "You don't know." with the same lines as the baseline, so the header is the likely cause, and the music question was answered from a wrong `Hobby: folk music` fact.

**Rework, read path only. Not run on N, M or L. Set O measures it, blind:**

1. Every value is shown only for list kinds of fact (`speaks`, `allergic_to`, `likes`, `dislikes`); other kinds show their best value. This keeps all three languages and drops the extra family names.
2. The short header of the set N run is back. The labelled markers stay.

<a id="set-o"></a>

## 15. Set O: the final blind test (2026-10-30)

Set O has 3 new users, 283 messages and 57 questions, with the question mix of M and N. The sentences that announce changes were worded unlike N's. It was written after the fixes from set N and frozen with its predictions ([../../predictions/set_O.md](predictions/set_O.md)) before any run. It was run once (`full.txt`, `full.json`), with ingestion, cache off, and four modes answering. It ran without a restart and took 58 minutes. **No change after this run is tested again.**

### Result

| Set O, 57 questions | Needed present (54) | Stale in prompt | Stale, marked | Avg lines | Answers, raw = reviewed | Stale in answer |
|---|---|---|---|---|---|---|
| Baseline | 46 | 18 | 0 | 4.0 | **44** | 2 |
| Smart | 42 | 11 | 0 | 2.5 | **39** | 7 |
| **Hybrid** | **50** | 16 | 2 | 5.1 | **47** | 5 |
| Full (whole history) | - | 19 | 0 | 94.3 | **52** | 1 |

**Hand review:** the three hand rules agreed with the keyword score in every mode.

- **Fruit salad:** smart, hybrid and full warn about kiwi; the baseline does not.
- **Barbecue:** smart, hybrid and full warn about mustard; the baseline does not.
- **Dessert:** every mode suggests a gluten-free dessert. The baseline found the gluten-free carrot cake among its four messages.

**Keyword misses, not re-scored (by the rule fixed before the run):**

- Hybrid's "No, you don't go climbing anymore. You mentioned selling all your gear" and "You don't play in an orchestra anymore" are right in substance. The checks look for "not anymore", "sold", "stopped" and similar words, and these answers use none of them.

If both had counted, hybrid would have 49. The pre-registered numbers stay as they are.

### Against the pre-registered hypotheses

| | Rule | Predicted | Found | Verdict |
|---|---|---|---|---|
| **H1 on O: hybrid better than the baseline** | d ≥ +3 | about +4.5, 65% chance | **d = +3** (47 against 44; hybrid only 7, baseline only 4) | **Met, at the threshold** |
| **H1-pooled: N and O together significant** | sign test, p < 0.05 | 55% chance | **15 against 7, p = 0.13** | **Not met** |
| H2: hybrid's outdated answers ≤ the baseline's | | about 1 against 4 | **5 against 2** | **Failed** |
| H3: smart − baseline ≤ −3 | | about −4 | −5 (39 against 44) | Met |
| H4: names 3 of 3, key facts at least 10 of 12 | | 3 of 3, about 10 | names **3 of 3**, key facts **8 of 12** | **Failed** on the key facts |

| Measure | Predicted | Found |
|---|---|---|
| Baseline | about 45 (40 to 49) | 44 |
| Smart | about 41 (36 to 45) | 39 |
| Hybrid | about 49.5 (45 to 53) | 47 |
| Full | about 47 (42 to 52) | 52, the top of the range |

### The write path did not carry over to new wording

| User | Wrong at the end | The message that was missed |
|---|---|---|
| Teodor | employer still Pixelgrad (his first); no partner (Matteo never stored); Ljubljana never stored as a city | "Ondaline in Ljubljana offered me a position and I said yes"; "Next month I start as test lead at Carsolux"; "There's someone new in my life: Matteo"; "First week in Ljubljana done" |
| Amara | city still Cardiff | "We're finally Edinburgh residents!" |
| Lieke | job title still senior copy editor | "From next week I'm a UX writer at Tegelhuis Studio" |

The rules of step 1 and the N fixes are word lists, written after seeing M's and N's sentences. On sentences worded otherwise they mostly kept the old value, which is the safe failure, but still a stale one. The name rule held (3 of 3).

### Where hybrid and the baseline differ

Hybrid only (7):
- **Timelines (2):** Teodor before Ljubljana (`Cluj -> Trieste (now)`) and Lieke before Leiden.
- **Allergy lines (2):** the fruit salad and the barbecue.
- **Same four messages as the baseline (3):** Teodor's brother's job, Lieke's parrot and Amara's cousin's citizenship interview (the trap). The baseline answered "I don't know" each time. These count, but they are model variance, not memory.

Baseline only (4):
- **Teodor: Where do I work now?** `Works at: Pixelgrad` (stale) was on top, and hybrid answered Pixelgrad. An outdated answer.
- **Lieke: What's my job title?** `Job title: senior copy editor` (stale) was on top. An outdated answer.
- **Lieke: Do I still go climbing?** Right in substance, a keyword miss (above).
- **Lieke: Which languages do I speak?** All three languages were stored, but Frisian did not pass the relevance gate, so two lines were shown and two languages answered.

Both wrong (6):
- **Teodor before Trieste:** the timeline lacks Ljubljana, which was never stored.
- **The orchestra:** hybrid's answer is a keyword miss.
- **Amara before Edinburgh:** "I don't know" in both modes.
- **Amara's husband:** both said he teaches maths. He now works as a pharmacist, but the message that says so was not among the four.
- **The signature and the bio:** hybrid's bio used the stale job title.

### The two blind long-history sets together

| N + O, 114 questions | Baseline | Smart | Hybrid | Full |
|---|---|---|---|---|
| Answers right | 89 | 81 | **97** | **102** |
| Outdated value in an answer | 6 | 13 | 7 | 3 |

- **Hybrid beat the baseline on both blind sets** (+5 and +3; 15 against 7 on differing questions). The direction holds; p = 0.13 is not proof. Of the 15 wins that can be traced:
  - 4 are timelines on past questions;
  - 5 are allergy lines on indirect questions;
  - 2 are current values on top;
  - 4 had the same messages as the baseline (model variance).
- **Hybrid's losses are its facts.** 6 of its 7 losses on N and O come from a fact that was wrong, stale or cut by the gate, placed above the right message.
- **Full beat everything** (102 of 114). These histories are about 1,100 tokens per user, small enough for the 8B model to read whole. A memory system has to earn its place on histories longer than the context window, or on cost: full used about 95 lines per question against hybrid's 5.
- **Smart alone lost to the baseline on every long set** (M, N, O).

### What this means for the project

The expected outcome, "better answers than traditional vector memory", is **supported in direction, not proven**. The hybrid design beat plain vector search on two blind sets written before their runs, by +5 and +3, but the combined test is not significant (p = 0.13). The reason it is not larger is clear and measured: the facts layer, built by an 8B model and word-list rules, is not reliable on new wording, and hybrid trusts it. At this history length, putting the whole history in the prompt is better than any memory, so the case for memory rests on longer histories and on prompt size, which these sets do not test.
