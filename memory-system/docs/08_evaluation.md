# 8. Evaluation

How the memory is measured, what the test sets are, the rules that keep the measurement honest, the results so far, and what those results do not prove.

## 1. What is compared

Each scripted life story is replayed message by message with backdated timestamps. Then every question is asked three ways:

| Mode | Memory in the prompt |
|---|---|
| `none` | nothing |
| `baseline` | the 4 most similar past user messages (traditional vector memory) |
| `smart` | the facts that pass the relevance gate, then up to 2 episode notes in the room left ([07_summaries.md](07_summaries.md)), at most 4 lines in all. `SUMMARIES=0` gives facts only |
| `hybrid` | the current facts of the best two kinds (at most 4 lines), one timeline line for a past question, then the baseline's 4 messages, marked when a fact they gave has changed ([06_read_path.md](06_read_path.md), section 11) |
| `full` | every past user message: a reference ceiling, not a design. Not scored for needed facts or noise, since it holds everything |

## 2. What is measured

Without the language model (fast, objective, deterministic):

| Metric | Question it answers | Better |
|---|---|---|
| Needed fact present | Did the memory lines contain the words the question needs (`needs`)? | higher |
| Noise present | Did they contain words that should not be there (`avoid`)? | lower |
| Stale in prompt | Did an outdated value (`stale`) reach the prompt on a line not marked as old? | lower |
| Stale, marked | Was it there only on lines the hybrid mode marks as old (`[outdated: ...]`, `[no longer true: ...]`, a timeline)? Always 0 for the other modes, whose numbers are therefore unchanged | reported, not judged |
| Lines | How many memory lines went into the prompt? | lower, if the needed fact is there |

With the language model (slower, noisier, run at temperature 0):

| Metric | Question it answers |
|---|---|
| Answer correct | Does the reply contain the right words? Every group in `expect` needs at least one of its words |
| Stale in answer | Does the reply contain an outdated word? |

All checks are keyword matches on lower-cased text. They are objective but crude: a correct answer worded differently counts as wrong, and a lucky word counts as right.

## 3. The test sets

86 scenarios, 367 questions (set K's 23 probes included), in `scripts/evaluation/scenarios/sets/` (one JSON file per set, with its status label).

| Set | Scenarios | Questions | Status | What it tests |
|---|---|---|---|---|
| A | 9 | 10 | **Tuning**: the gate was tuned on it, so it cannot validate anything | Moves, job changes, many hobbies, a dislike as noise, family, third-person and past-tense traps, an abstain question |
| B | 8 | 8 | **Spent**: held out when written, but the floor and window were chosen after seeing it | Indirect dislikes, allergies, paraphrased job, a flood of stale messages, precision, a correction |
| C | 3 | 12 | **Spent**: blind when written (before the relative window) | One rich profile of 17 messages with ten questions, including abstain; a double move; a new job |
| D | 3 | 19 | **Spent**: blind, written before routing existed | A second rich profile of 18 messages with fifteen questions; a small profile with safety questions; a job switch |
| E | 3 | 12 | **Spent**: blind, written before the safety bypass and the goal prompt | Food and drug allergies against unrelated questions; goals |
| F | 7 | 10 | **Spent**: blind, write path only, written after the write-path fixes | Corrections, like-to-dislike flips, an employer change with and without a title, a vague promotion |
| G | 9 | 19 | **Spent**: blind when written (before any summaries code), run once without summaries, then re-run with them (a labelled re-run) | Episodes, plans and stories that no fact type holds, a question about the past, a story told over several messages |
| H | 7 | 15 | **Spent**: blind validation of the summaries layer, written before its code, run once | A bake, an injury, a purchase, an adoption, a control profile of plain facts, third-person traps, a cancelled plan |
| I | 7 | 12 | **Spent**: blind validation of the past-question mechanism, written before its code, run once | Past questions after a move, a job change, two moves, a like-to-dislike flip and a partner change; present-tense controls; two "before" traps; a user who never moved |
| J | 5 | 26 | **Spent**: blind validation of consolidation, written before its code; run once without it and once with it | Users with 10 to 16 episode messages: a renovation story, a year of trips, a band story with other people, typed facts mixed with episodes, and a control user whose messages are all under 30 days old |
| K | 6 | 23 probes | **Spent**: blind, consistency across sessions, written before its runner, run once; in its own format (`"format": "sessions"`), run by `scripts/evaluate_sessions.py`, not by `evaluate.py` | Multi-session stories: a move, an allergy, an employer change, a partner with a distractor, a move inside one session, a control where nothing changes; direct and indirect probes |
| L | 10 | 30 | **Spent**: blind, unseen data, written after A to K were spent and before any change; run once, with summaries on and off | Every question type mixed: direct facts, changes, past questions, episodes, indirect questions, a third-person trap and abstain questions |
| M | 3 | 57 | **Spent**: blind, long crowded histories (92 to 100 messages each), written after the step 1 and 2 fixes, run once with four ablations | The main hypothesis: is smart better than vector search on long histories? Moves, job changes, other people, similar trips, plans that change, many everyday questions on the same topics |
| N | 3 | 57 | **Spent**: blind, long crowded histories (93 to 95 messages each), the design and question mix of M with new people, written after the hybrid step, run once | Hybrid against the baseline (the plan's success criterion, [predictions/set_N.md](predictions/set_N.md)); smart against the baseline again |
| O | 3 | 57 | **Blind**: the final test; long crowded histories, the design and question mix of M and N with new people and differently worded changes, written after the set N fixes, before any run | Hybrid against the baseline, alone and pooled with N for significance ([predictions/set_O.md](predictions/set_O.md)) |

A **blind** set is written before the change it tests and run once. After that it is **spent**: it has influenced decisions, so it can no longer validate anything. Today every set is spent or tuning (L was the first run on unseen data) (G was re-run once with the layer, which is why its second result is labelled as a re-run).

### Scenario format

```python
{
  "id": "move_city", "kind": "stale",
  "messages": [(days_ago, "text"), ...],       # order does not matter; the runner sorts them
  "questions": [{
      "q": "Which city do I live in?",
      "expect": [["milan"]],                   # groups of words; the answer needs one from each group
      "needs": ["milan"],                      # must appear in the memory lines
      "avoid": ["turin"],                      # must NOT appear in the memory lines (noise)
      "stale": ["turin"],                      # outdated words, reported separately
  }],
}
```

`expect` may be left out to score retrieval only. The loader in `scripts/evaluation/scenarios/__init__.py` adds the `set` letter.

## 4. Rules of the protocol

1. **Write predictions before running** and keep them unchanged ([predictions/](predictions/)).
2. **Run a blind set once.** Re-running after tuning turns it into a tuning set.
3. **Do not tune on a spent set.** A change to the gate or the extraction needs a new set written beforehand.
4. **Report misses.** Predictions that failed are kept and discussed, not edited.
5. **Measuring does not change memory.** `evaluate.py` and `inspect_scores.py` retrieve with `touch=False`.
6. **Extraction is deterministic** (temperature 0), so a full re-ingest from an empty database reproduced identical numbers on sets A to F. Summaries are also written at temperature 0; the layer-on A to G run reproduced the earlier set G numbers.
7. **`--no-ingest` reads whatever is stored.** If a scenario's data is stale or incomplete (for example after an interrupted ingest), the numbers are wrong. Re-run without `--no-ingest` when in doubt.

## 5. How to run

```bash
# ingest everything and run retrieval-only (about 3 minutes)
poetry run python scripts/evaluate.py --set A B C D E F --retrieval-only

# reuse ingested data (seconds)
poetry run python scripts/evaluate.py --set A B C D E F --retrieval-only --no-ingest

# include model answers (about 5 minutes on the stored data)
poetry run python scripts/evaluate.py --set A B C D E F --no-ingest

# one scenario, with stored facts and recalled lines
poetry run python scripts/evaluate.py --only b_stale_flood --verbose

# why each fact was kept or dropped
poetry run python scripts/inspect_scores.py --scenario b_stale_flood
```

`make quick`, `make set SET=I`, `make answers SET=I` and `make eval SET=I OUT=docs/results/set_I/name` wrap the common cases; `make eval` is the final-run form (no cache, verbose, output saved as `name.txt` and `name.json`) ([02_setup.md](02_setup.md), "Keeping the Mac cool").

**Cache and answers.** `evaluate.py` caches embeddings and temperature-0 replies in `.cache/llm.sqlite`, so re-running an unchanged set takes seconds and prints `cache: N hits, M misses`. A first run of a new set misses the cache by construction, so blind sets are unaffected. `--no-cache` forces fresh calls and is the mode for a final comparison. By default the baseline, smart, hybrid and full answers are generated (`--answers` lists the modes; add `none` for the no-memory answers); the no-memory column then shows `-`. The full mode's prompt lines are not saved in the `.json` (they are the whole history, the same for every question); verbose output prints their count. The session runner (set K) still compares none, baseline and smart only.

Results are also saved to `eval_results.json` (git-ignored). The code is split into `evaluate.py` (arguments, ingest, the loop), `evaluation/metrics.py` (scoring) and `evaluation/report.py` (printing).

To add a set: write `scripts/evaluation/scenarios/sets/set_k.json` (the next letter; copy the shape of an existing file) with its `label`, and write the predictions first. Nothing needs registering, the loader reads every `set_*.json`. When the predictions are committed, freeze the set: add `"set_k.json": "<hash>"` to `scenarios/frozen.json` (the hash is `shasum -a 256 set_k.json`). `tests/evaluation/test_scenarios.py` then fails if the file is edited afterwards, and checks the shape of every set.

Session sets (set K) have their own runner: `poetry run python scripts/evaluate_sessions.py --verbose` (or `make sessions`) replays every story turn by turn in the three modes and writes `eval_sessions.json`. Its keyword scores are provisional until the hand review described in [predictions/set_K.md](predictions/set_K.md).

The summaries layer runs inside the evaluation: after each scenario's ingest, `summarize_pending` writes the notes (printing how many), and `--verbose` prints them. `SUMMARIES=0 poetry run python scripts/evaluate.py ...` is the layer-off control.

## 6. Results

Smart against baseline, per set. Counts are questions that test the metric.

| Set | Needed present (base / smart) | Noise present (base / smart) | Stale in prompt (base / smart) | Avg lines (base / smart) | Answers correct (base / smart) |
|---|---|---|---|---|---|
| A | 8/9 / **9/9** | none defined | 4 / **0** | 3.0 / **1.1** | 7/10 / **9/10** |
| B | 6/7 / **7/7** | 1/2 / 1/2 | 2 / **0** | 4.0 / **1.1** | 4/6 / **6/6** |
| C | 10/10 / 10/10 | 11/11 / **2/11** | 2 / **0** | 3.8 / **1.3** | 10/12 / **11/12** |
| D | 15/16 / 15/16 | 16/17 / **7/17** | 2 / **0** | 3.8 / **1.7** | 16/18 / **17/18** |
| E | **8/9** / 7/9 | 10/12 / **3/12** | 0 / 0 | 4.0 / **1.0** | **8/8** / 7/8 |
| F | 7/7 / 7/7 | 4/4 / **1/4** | 5 / **0** | 2.4 / **0.9** | 7/7 / 7/7 |
| **All** | 54/58 / 55/58 | 42/46 / **14/46** | 15 / **0** | | 52/61 / **57/61** |

An outdated value also reached the baseline's answer once (set F); never the smart answer.

### Sets A to F with the summaries layer

Same stored facts; the layer on or off. Criteria were written before the layer was built ([predictions/set_H.md](predictions/set_H.md)). Final numbers, after the two changes described in [results/logs/summaries_dev.md](results/logs/summaries_dev.md):

| Smart, sets A to F | Layer off | Layer on | Criterion | Result |
|---|---|---|---|---|
| Needed present | 55/58 | 56/58 | 55/58 or better | met |
| Average lines | 0.9 to 1.7 | 1.3 to 1.8 | under 2.0 | met |
| Stale in prompt | 0 | 4 | 0 | **not met** |
| Noise present | 14/46 | 16/46 | 14/46 or fewer | **not met** |
| Answers correct | 57/61 | 58/61 | no regression | met |
| Stale in answer | 0 | 0 | 0 | met |

The two failed criteria were read prompt by prompt. Of the stale cases, the notes are true past-tense statements ("The user used to live in Turin ...") or restatements that the keyword test counts as stale, because its word lists were written for facts. Part of the extra noise is the same kind (true mentions); the rest is real: notes have no routing step, so a note about goals came back for a question about a language when facts had returned nothing. The failures are reported as failures; no threshold was changed to hide them.

### Sets G and H: questions outside the 13 fact types

| Set | Mode | Needed present | Noise present | Stale in prompt | Avg lines | Answers correct |
|---|---|---|---|---|---|---|
| G | baseline | 17/17 | 4/4 | 1 | 4.0 | 16/18 |
| G | smart, first run (no summaries) | 8/17 | 0/4 | 0 | 0.8 | 8/18 |
| G | smart, re-run with summaries | 13/17 | 2/4 | 0 | 1.6 | 12/18 |
| H (run once) | baseline | 13/13 | 3/3 | 0 | 4.0 | 13/14 |
| H (run once) | smart with summaries | 12/13 | 2/3 | 0 | 1.1 | 13/14 |

- **The layer closes most of the gap on questions that facts cannot hold** (G: 8 to 13 of 17, answers 8 to 12 of 18) but did not reach the baseline on G.
- **On H, which was blind, smart matches the baseline's answers (13/14 each) with a quarter of the lines** (1.1 against 4.0). Noise is lower in the prompt, not absent (2/3 against 3/3). H has 15 questions, so this is one run on a small set.
- **One H miss is the metric, not the memory:** the cancelled-conference question needs the word "cancel", while the correct note says the user is "not going after all". It was reported as a miss, not edited.
- **Compression is not shown.** The notes are as long as the messages they came from: 3,061 characters of notes against 2,971 of linked source messages (1.03). Against all the stored messages of the evaluation users (10,905 characters) the notes are 28%, but most of that saving is questions and filler that are left out. The layer improves recall of episodes; it does not yet shorten history ([07_summaries.md](07_summaries.md), section 9).

### Set I: questions about the past

The mechanism ([06_read_path.md](06_read_path.md), section 10) was written after the predictions, which were committed before the first run. Smart with the mechanism, against the criteria; full diagnosis in [results/logs/past_step.md](results/logs/past_step.md).

| Measure | Criterion | Result |
|---|---|---|
| Past questions, needed present | 5/6 or better | **5/6**, met |
| Past questions, answers correct | 4/6 or better | **3/6**, not met |
| Present-tense controls, needed present and no old value | 3/3 and 0 stale | needed 3/3; **1 stale**, not met (a true mention in a note; also present with the rule off) |
| "Before" traps, nothing from the old city | 2/2 | 2/2 (baseline fails both) |
| Rule off (`PAST_FACTS=0`): past questions needed present | 0/6 or 1/6 | 1/6 |

| Set I, 12 questions | Needed | Noise | Stale in prompt | Avg lines | Answers |
|---|---|---|---|---|---|
| Baseline | 8/9 | 2/2 | 3 | 4.0 | 8/10 |
| Smart, rule off (retrieval only) | 4/9 | 0/2 | 1 | 1.1 | not run |
| Smart, rule on | 8/9 | 0/2 | 1 | 1.6 | 7/10 |

- **The rule works where the old value was replaced** (a move, two moves, a like-to-dislike flip): the old value reaches the prompt only for questions that ask for it, and the "before" traps stay clean.
- **It does not reach values the write path archives.** "I left Halvorsen Marine, I now work at Pelican" and "we split up, I'm with Elena now" store the old value as `archived` (a retraction), and the rule reads only `superseded` facts. This was predicted as a risk for the partner case and missed for the job case.
- **The answer shortfall is partly the model and the scoring:** one correct answer ("Olives.") lacks the word the check requires; one answer was "I don't know" with the fact in the prompt.
- **Other sets are unchanged:** A to F and H identical, G changed only on its past question (one more needed fact, one more correct answer).

### Set J: consolidation of notes

Run once on the system without consolidation (run 1), then once with it (run 2), with the model calls cached so the notes were identical in both runs. Predictions and the frozen design: [predictions/set_J.md](predictions/set_J.md).

| Set J, 26 questions | Needed | Noise | Stale in prompt | Avg lines | Answers |
|---|---|---|---|---|---|
| Baseline | 25/25 | 2/2 | 4 | 4.0 | 26/26 |
| Smart, consolidation off (run 1) | 23/25 | 1/2 | 3 | 1.9 | 24/26 |
| Smart, consolidation on (run 2) | 24/25 | 1/2 | 3 | 1.7 | 25/26 |

| Compression on the J users | Characters | Ratio |
|---|---|---|
| Notes / their source messages | 3,451 / 3,133 | 1.10 |
| Digests / the notes they replaced (9 digests from 19 notes) | 1,092 / 1,388 | **0.79** |
| Summary text in use / source messages | 3,155 / 3,133 | **1.01** |

| Criterion (set before building) | Result |
|---|---|
| 1. Compression: digests at most 0.70 of their notes, text in use below 0.85 of sources | **Failed** (0.79, 1.01) |
| 2. Retention: needed present with consolidation within 2 of without | Passed (24 against 23) |
| 3. Final state: oak cabinets, no "December 12" in the Hanoi answer | Passed |
| 4. Attribution: no digest makes the user the one who fell or moved | Passed, weakly: those notes were never merged or never written |
| 5. Age rule: nothing merged in `j_recent`, no note under 30 days merged | Passed |
| 6. Faithfulness checked by hand (10 digests, including one in set B) | No invented detail; one wrong inference (the removal company "repaired" the piano it paid a technician to repair); one inherited invented "partner" |
| 7. No regression on A to I | Passed: identical to the last regression, except B (stale in prompt 1 to 0, a side effect explained in [07](07_summaries.md), section 12.4) |

- **The baseline was perfect on J.** One clear message per episode is the easy case for vector search over messages.
- **My prediction for consolidation was too pessimistic** (about 17.5 needed present predicted, 24 found), and too optimistic for compression (0.65 predicted, 0.79 found).
- **The two smart misses in run 1 had other causes.** The asbestos note was dropped by the notes' faithfulness check (a true paraphrase failed the 75% word share), and the "moved to February" note lost the window to the two December notes. Consolidation fixed the second only because one digest took the place of two notes.

### Set K: consistency across sessions

Six stories told over several sessions; each session starts with no chat history, so only memory carries facts between them. The three modes answer every turn side by side. Predictions and design: [predictions/set_K.md](predictions/set_K.md); hand review and details: `results/set_K/log.md`.

| Set K, 23 probes (after the hand review) | none | baseline | smart |
|---|---|---|---|
| Correct | 1 | 16 | 17 |
| Contradictions (13 probes with an outdated or wrong value) | 0 | 1 | 0 |
| Forbidden word in the memory lines (13) | 0 | 10 | 4 |
| Stable facts (7: every probe of one fact right) | 0 | 2 | 2 |
| Indirect probes correct (10) | 0 | 6 | 5 |

- **About even.** Smart answered one more probe and never used an outdated value; baseline did once ("You live in Ljubljana" after the move). One case is not a difference. The stability criterion failed (2 against 2), and the predictions overrated smart (19.5 correct predicted).
- **Smart loses at the gate on indirect questions.** Four of its six misses had the fact in memory but not in the prompt: a note signed "with my name", an email signature, a vinaigrette (the allergy pass did not fire), the second of two languages.
- **Baseline loses to its own questions and to "I don't know".** Its past questions fill its four lines over time, which caused its one contradiction; three times it said "I don't know" with the fact in its lines.
- **Outside the scores:** the `(since date)` label of a fact was read as a start date ("which you started learning on March 2"), and smart replies to a change one turn late, because facts are stored after the reply.

### Set L: unseen data

The first measure on data written after every other set was spent, before any change, run once. Predictions: [predictions/set_L.md](predictions/set_L.md); causes of every miss: `results/set_L/log.md`.

| Set L, 30 questions | Needed | Noise | Stale in prompt | Avg lines | Answers | Stale in answer |
|---|---|---|---|---|---|---|
| Baseline | 28/28 | 3/3 | 5 | 4.0 | **28/30** | 0 |
| Smart, summaries on | 20/28 | 2/3 | 2 | 1.7 | 20/30 | 1 |
| Smart, summaries off | 16/28 | 2/3 | 0 | 0.9 | 16/30 | 0 |

- **On unseen data the baseline is clearly better.** It answered 8 more questions; smart was right where the baseline was wrong once, the reverse 9 times (sign test p of about 0.02). Predicted: baseline about 23.5, smart about 21, facts only about 15.5.
- **Half of smart's misses are write-path errors, not gate errors.** A sister's city and job were stored as the user's (Montreal replaced Nantes), "my suitcase ended up in Frankfurt" became `lives_in = Frankfurt`, a friend became a `partner`, and a hobby was never extracted. Smart answers from facts, so a wrong fact becomes a wrong answer; the baseline reads the messages and cannot make this mistake. One of these errors gave smart its first outdated answer.
- **The rest are known weaknesses:** the gate on indirect questions (a signature, a language goal, a wedding), and an archived partner the past rule cannot read.
- **What still holds:** with facts only, smart had no outdated value in prompt or answer and used 0.9 lines against 4.0. Summaries added 4 answers, all episodes.
- **Two stories got no notes,** because the notes prompt skips "plain personal facts stored elsewhere" and the model applied that to messages whose facts were not stored.

### Set M: long histories, the main hypothesis

Three users with 92 to 100 messages over about 18 months; written after the fixes of steps 1 and 2, run once, plus four ablations. Predictions: [predictions/set_M.md](predictions/set_M.md); every smart loss explained: `results/set_M/log.md`.

| Set M, 57 questions | Needed | Stale in prompt | Avg lines | Answers (reviewed) | Stale in answer |
|---|---|---|---|---|---|
| Baseline | **48/54** | 16 | 4.0 | **48/57** | 4 |
| Smart | 36/54 | 7 | 2.2 | 36/57 | 5 |
| Smart, facts only | 16/54 | 3 | 1.2 | 17/57 | 2 |

- **The hypothesis is rejected:** d = −12 (pre-registered threshold −3 for "the baseline is better"); the baseline was right and smart wrong on 14 questions, the reverse on 2 (sign test p of about 0.004).
- **Why:** errors accumulate with length. Each statement is a chance for the 8B extractor to mis-store a fact, and single-valued facts are replaced by incidental mentions: a house viewing and a commute moved Ruben back to Utrecht, a transfer to Kristiansand stored no city, "Peatline has no office" became a job title. Notes lose details when merged and pass two at a time. The baseline hands the model the original sentences.
- **Ablations:** notes matter most (facts only: 17 against 36); switching off `about_user`, the note tags or the note window changed answers by 2 or less (run noise), although `about_user` visibly kept other people's cities and jobs out of the facts.

### Set N: the hybrid read path, blind

The design and question mix of M with three new users; written after the hybrid step ([06_read_path.md](06_read_path.md), section 11) and run once. Predictions: [predictions/set_N.md](predictions/set_N.md); every difference explained: `results/set_N/log.md`.

| Set N, 57 questions | Needed | Stale in prompt (marked) | Avg lines | Answers (reviewed) | Stale in answer |
|---|---|---|---|---|---|
| Baseline | 46/54 | 18 | 4.0 | 45/57 | 4 |
| Smart | 44/54 | 10 | 2.5 | 42/57 | 6 |
| **Hybrid** | **52/54** | 13 (5) | 5.2 | **50/57** | **2** |
| Full | - | 19 | 94.3 | 50/57 | 2 |

- **H1 met by the pre-registered rule:** d = hybrid − baseline = +5 (threshold +3). Not statistically significant: hybrid only right on 8, the baseline only on 3 (sign test p of about 0.23). On the development set M it was +4.
- **The gains are facts used where they are strong:** timelines on past questions (2), current values on top (2), allergies on indirect questions (3); one more is noise. **The 3 losses all come from the facts layer:** an employer never replaced, the 2-line cap cutting a list of three languages, and a wrong marker from a `name` fact overwritten by other people's names.
- **H2 met** (outdated answers 2 against 4); **H3 met:** smart alone is again worse than the baseline (−3).
- **Full** (the whole history) scored 50, level with hybrid; on M it scored 44. It is a ceiling for this history length, not a design.

### What the results show

- **Outdated facts never reach the prompt** with smart memory (0 against 15). This is the clearest result and follows directly from the design: superseded, archived and conflicted facts are not read.
- **Far less irrelevant text:** in 14 of 46 prompts against 42 of 46, and 1.0 to 1.7 lines instead of 2.4 to 4.0.
- **The needed fact arrives about as often** (55 against 58 possible, baseline 54). Smart lost one needed fact on set E that baseline kept.
- **Answers are a little better:** 57 against 52 of 61 (58 with summaries).

### Why the answer gap is small, and what is behind it

Five questions separate the modes. Smart is right and baseline wrong on 7, the reverse on 2, and both wrong on 2. A sign test on those nine differing questions gives p of about 0.18, so the gap is suggestive, not significant.

Looking at the wrong answers:

- **Baseline says "I don't know" with the fact in the prompt** five times (name three times, city twice). The fact was among four raw messages and the model did not use it. Smart never did this when the fact was retrieved. A plausible reason is that raw messages are noisier than a line like `Name: Giulia`; this has not been tested.
- **Smart fails even with the fact present** twice: the mushroom question (the prompt had `Dislikes: mushrooms`, the model answered "I don't know what you're cooking") and the restaurant question in set C (both shellfish and coriander were in the prompt, the answer mentioned only shellfish, and scoring needs both). These are failures of the 8B model, not of memory.
- **Two retrieval misses** produced the other wrong smart answers: the music question in set D and the Japanese goal in set E (section 8 of [06_read_path.md](06_read_path.md)).

### Prediction outcomes worth knowing

Predictions are kept unchanged in [predictions/](predictions/). Outcomes: on set E, two facts predicted to be found (the sesame snack question and the Japanese goal) were missed, and the blood-type abstain question stayed clean in memory's favour; the gluten and boat misses were traced to the floor and to extraction. For the write path, the first version of the retraction rule lost the second half of "not peanuts, walnuts"; this was found on a re-ingest and fixed by `normalize_actions`.

## 7. What these results do not prove

| Limit | Why it matters |
|---|---|
| Sets A to F were written around the 13 fact types | Every scenario there asks about something the system stores. Sets G and H test other questions and show where the baseline is stronger (G), but G and H are small and G was seen once before its re-run |
| All sets are seen | The gate values (0.42, 0.08) and the two routing hints were chosen after seeing sets A to C; D to F were blind but are now spent. On fresh data (set L) smart answered 20 of 30, against 28 for the baseline |
| Small samples | 230 questions, 74 stories; one rich profile carries many of the questions; H, I and J were one run each (15, 12 and 26 questions) |
| Crude scoring | Keyword matching on lower-cased text |
| One small model | llama3.1:8b for extraction and answers; results may differ with another model |
| Few multi-turn data | Consistency across sessions was measured once (set K, 23 probes); consistency with the assistant's own replies is not measured |
| Keyword scoring of notes | The `needs`, `avoid` and `stale` word lists were written for facts and mis-score true past-tense notes and paraphrases ("not going after all") |
| A simple baseline | The four most similar messages, as the project defines traditional vector memory; stronger baselines exist |
| Written by the developers | The scenarios and the system share a designer |

## 8. Next

- **A hybrid read path, measured on a fresh set:** raw messages as the main memory, with facts used where they are strong (current values, marking or filtering outdated messages, allergies). Set M rejected facts as a replacement for messages ([results/set_M/log.md](results/set_M/log.md)).
- The write-path errors found on set L (facts about other people stored as the user's, incidental places stored as home, a friend as a partner) and the gap between notes and facts, measured on a fresh set (M) with the gate fixes ([10_limits_and_roadmap.md](10_limits_and_roadmap.md)).
- The two follow-ups to set I, measured on a fresh set: past questions that also read facts archived by a retraction, and past lines ordered oldest first ([10_limits_and_roadmap.md](10_limits_and_roadmap.md)).
- A second version of consolidation that compresses more, measured on a fresh set (J is spent); see [10_limits_and_roadmap.md](10_limits_and_roadmap.md).
- One final comparison of none, baseline and smart on a fresh set, with the two pre-registered fixes (strong-match override, wider allergy bypass) measured blind.
