# Predictions before set O (written 2026-10-30, before any run)

Set O (`scripts/evaluation/scenarios/sets/set_o.json`, 3 users, 283 messages, 57 questions) is the **final** blind test of the hybrid read path. It was written after the fixes from set N ([results/logs/set_N_fixes_dev.md](../history.md#set-n-fixes)) and the two read-path corrections that followed them. It is run **once**. No system change after this run is tested again: whatever O shows goes into the report. Nothing below has been checked against data.

## The system under test

The hybrid mode as of this commit:
- **Write path:** a name only from a self-introduction; a silent "I" after an opening verb; "got a job" as a change word.
- **Read path:** current facts of the best two kinds (every value only for languages, allergies, likes and dislikes), one timeline for past questions, the baseline's 4 messages with labelled markers (`[outdated: Lives in: Oslo -> now Kristiansand]`), and the short header.

The two read-path corrections (list kinds only, short header) were never run before O.

## Design (frozen with the set)

1. **Same design and question mix as M and N, new people.** 12 current values after a change, 7 past values, 11 episodes (one asks for a count), 4 numeric details, 5 plans that changed, 7 questions about other people, 5 indirect questions (3 scored by hand), 2 direct facts (one with three values), 1 trap and 3 abstain questions.
2. **Users.**
   - **Teodor:** 95 messages over 554 days. Cluj, then Ljubljana, then Trieste; two employers left; a partner change; a trip whose date and companion change; the orchestra given up for woodworking.
   - **Amara:** 95 messages over 557 days. A move to Edinburgh talked about about 300 days before it happens; an employer left; two promotions; netball given up for the cello; two plans that change; a husband who retrains.
   - **Lieke:** 93 messages over 551 days. A move with her employer, then a new job; a house move that is delayed; a sister who moves; climbing given up.
3. **Not a copy of N's sentences.** The stories mirror N's structure, so the question mix is the same. But the sentences that announce changes were deliberately worded unlike N's: "Ondaline offered me a position and I said yes", "Last day at Ondaline today", "We're finally Edinburgh residents", "No more orchestra for me". The write-path fixes were made on N's wording, so this keeps O from rewarding them for matching it.
4. **Scoring.** The usual keyword checks, raw and reviewed. Three hand rules, fixed now, applied to every mode:
   - the fruit salad (`o_teodor`): correct only if the answer warns about kiwi because of his allergy;
   - the barbecue (`o_amara`): correct only if the answer warns about mustard because of her allergy;
   - the dessert (`o_lieke`): correct only if the dessert is gluten-free or the answer mentions her coeliac disease.

   No other answer is re-scored. "I don't know" (and "You don't know") match no expected word of a non-abstain question (checked before freezing).
5. **Not included:** any change to the system, the thresholds or the scoring after this file is committed.

## The run

| # | Command | What it measures |
|---|---|---|
| 1 | `make eval SET=O OUT=docs/results/set_O/full` | ingest, then baseline, smart, hybrid and full, cache off |

If the run is stopped during ingestion (before any question is asked), it may be started again. Any other restart is reported.

## Hypotheses and how they are judged

**H1 (on O alone): hybrid answers more questions correctly than the baseline.** d = hybrid − baseline, reviewed counts:

| d | Verdict |
|---|---|
| +3 or more | hybrid is better (met again, as on N) |
| −2 to +2 | no clear difference |
| −3 or less | the baseline is better |

**H1-pooled (the significance test, fixed now): the blind runs of N and O together.** A sign test (two-sided, exact binomial) on every question of the two blind runs where hybrid and the baseline differ. That is `results/set_N/full.json` (hybrid only right on 8, the baseline only on 3) plus this run. **Significant if p < 0.05.**

N was run with the hybrid of that time and O with the hybrid of this commit. The pooled test therefore asks "did hybrid, as developed, beat the baseline on blind long histories?", not "is one fixed version better". The report will say so.

For reference, computed before the run, the wins O needs for the pool to reach p < 0.05:

| Baseline-only questions on O | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| Hybrid-only questions needed on O | 4 | 5 | 7 | 9 | 10 | 12 |

(A repeat of N, 8 against 3, would give 16 against 6 pooled, p = 0.052: just short.)

Secondary, also pre-registered:
- **H2:** hybrid puts an outdated value in no more answers than the baseline.
- **H3:** smart alone answers fewer than the baseline (d = smart − baseline ≤ −3), as on M and N.
- **H4 (write path):** the user's name is right at the end for 3 of 3 users, and at least 10 of the 12 key facts (city, employer, job title, partner) are right.
- **Reported, not judged:** full, stale values marked in the prompt, and average lines.

## Predictions

Calibrated on the runs of M and N with the current write path (`fixes_M`, `fixes_N`), where the baseline scored 46 and 45, smart 42 and 40, hybrid 49 and 50, and full 44 and 50.

| Measure | Prediction |
|---|---|
| Baseline | about 45 (40 to 49) |
| Smart | about 41 (36 to 45) |
| **Hybrid** | **about 49.5 (45 to 53)** |
| Full | about 47 (42 to 52) |
| **d = hybrid − baseline** | **about +4.5 (+1 to +8); "+3 or more" about a 65% chance** |
| Hybrid only / baseline only on O | about 7 against 2.5 |
| **H1-pooled significant** | **about a 55% chance** (it needs roughly 6 or more hybrid-only questions against at most 1 to 2) |
| Outdated value in the answer | baseline about 4, smart about 3, hybrid about 1 |
| H4: names right / key facts right | 3 of 3 / about 10 of 12. Amara's "moving to Edinburgh one day" may move her city early, and the reworded change sentences are untested |
| Average lines | baseline 4.0, smart about 2.4, hybrid about 5.3, full about 95 |

Where hybrid and the baseline are expected to differ: the 7 past questions (timelines), current values after two changes (fact lines on top), and the three hand-scored allergy and intolerance questions. Expected risks for hybrid: a wrong fact above the right message (the pattern of every hybrid loss so far), and family questions if a wrong family fact comes first.
