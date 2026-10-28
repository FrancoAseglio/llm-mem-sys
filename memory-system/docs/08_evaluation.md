# 8. Evaluation

How the memory is measured, what the test sets are, the rules that keep the measurement honest, the results so far, and what those results do not prove.

## 1. What is compared

Each scripted life story is replayed message by message with backdated timestamps. Then every question is asked three ways:

| Mode | Memory in the prompt |
|---|---|
| `none` | nothing |
| `baseline` | the 4 most similar past user messages (traditional vector memory) |
| `smart` | the facts that pass the relevance gate, then up to 2 episode notes in the room left ([07_summaries.md](07_summaries.md)), at most 4 lines in all. `SUMMARIES=0` gives facts only |

## 2. What is measured

Without the language model (fast, objective, deterministic):

| Metric | Question it answers | Better |
|---|---|---|
| Needed fact present | Did the memory lines contain the words the question needs (`needs`)? | higher |
| Noise present | Did they contain words that should not be there (`avoid`)? | lower |
| Stale in prompt | Did an outdated value (`stale`) reach the prompt? | lower |
| Lines | How many memory lines went into the prompt? | lower, if the needed fact is there |

With the language model (slower, noisier, run at temperature 0):

| Metric | Question it answers |
|---|---|
| Answer correct | Does the reply contain the right words? Every group in `expect` needs at least one of its words |
| Stale in answer | Does the reply contain an outdated word? |

All checks are keyword matches on lower-cased text. They are objective but crude: a correct answer worded differently counts as wrong, and a lucky word counts as right.

## 3. The test sets

61 scenarios, 143 questions, in `scripts/evaluation/scenarios/sets/` (one JSON file per set, with its status label).

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
| K | 6 | 23 probes | **Blind**, not yet run: consistency across sessions, written before its runner; in its own format (`"format": "sessions"`), run by `scripts/evaluate_sessions.py`, not by `evaluate.py` | Multi-session stories: a move, an allergy, an employer change, a partner with a distractor, a move inside one session, a control where nothing changes; direct and indirect probes |

A **blind** set is written before the change it tests and run once. After that it is **spent**: it has influenced decisions, so it can no longer validate anything. Today every set is spent or tuning (G was re-run once with the layer, which is why its second result is labelled as a re-run).

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

`make quick`, `make set SET=I`, `make answers SET=I` and `make fresh SET=I` wrap the common cases ([02_setup.md](02_setup.md), "Keeping the Mac cool").

**Cache and answers.** `evaluate.py` caches embeddings and temperature-0 replies in `.cache/llm.sqlite`, so re-running an unchanged set takes seconds and prints `cache: N hits, M misses`. A first run of a new set misses the cache by construction, so blind sets are unaffected. `--no-cache` forces fresh calls and is the mode for a final comparison. By default only baseline and smart answers are generated (`--answers none baseline smart` for all three); the no-memory column then shows `-`.

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
| All sets are seen | The gate values (0.42, 0.08) and the two routing hints were chosen after seeing sets A to C; D to F were blind but are now spent. Performance on fresh data is probably lower |
| Small samples | 143 questions, 61 stories; one rich profile carries many of the questions; H, I and J were one run each (15, 12 and 26 questions) |
| Crude scoring | Keyword matching on lower-cased text |
| One small model | llama3.1:8b for extraction and answers; results may differ with another model |
| Single questions | Consistency across several turns is not measured |
| Keyword scoring of notes | The `needs`, `avoid` and `stale` word lists were written for facts and mis-score true past-tense notes and paraphrases ("not going after all") |
| A simple baseline | The four most similar messages, as the project defines traditional vector memory; stronger baselines exist |
| Written by the developers | The scenarios and the system share a designer |

## 8. Next

- The two follow-ups to set I, measured on a fresh set: past questions that also read facts archived by a retraction, and past lines ordered oldest first ([10_limits_and_roadmap.md](10_limits_and_roadmap.md)).
- A second version of consolidation that compresses more, measured on a fresh set (J is spent); see [10_limits_and_roadmap.md](10_limits_and_roadmap.md).
- A multi-turn consistency measure.
- One final comparison of none, baseline and smart on a fresh set, with the two pre-registered fixes (strong-match override, wider allergy bypass) measured blind.
