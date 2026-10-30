# Predictions before set N (written 2026-10-30, before any run)

Set N (`scripts/evaluation/scenarios/sets/set_n.json`, 3 users, 283 messages, 57 questions) is the blind test of the hybrid read path. Hybrid was built and checked on the spent sets M and L ([results/logs/hybrid_dev.md](../results/logs/hybrid_dev.md)): 50 against the baseline's 46 on M, and 28 against 27 on L. Those runs were development. N was written after them and before any run on it. It is run **once**. Nothing below has been checked against data.

## Design (frozen with the set)

1. **Same design as M, new people.** The question mix is set M's, type for type. It was frozen on 2026-10-29, before hybrid existed, so N is not tilted toward what hybrid does well. The mix: 12 current values after a change, 7 past values, 11 episodes (one asks for a count), 4 numeric details, 5 plans that changed, 7 questions about other people, 5 indirect questions (3 scored by hand), 2 direct facts (one with three values), 1 trap and 3 abstain questions.
2. **Users.**
   - **Marisol:** 95 messages over 552 days. Two moves (Valencia, Lyon, Grenoble), two employers left, a partner change, a trip whose date and companion both change, a hobby given up for another.
   - **Kwame:** 95 messages over 558 days. A move first mentioned about 300 days before it happens, an employer left, two promotions, a hobby that changes, two plans that change, a wife who retrains.
   - **Henrike:** 93 messages over 549 days. A move with her employer, then a new job, a flat move that is delayed, a brother who moves, sailing given up.
   - Each user has about 32 statements and about 61 everyday questions to the assistant, spread over the whole history. 15 of those questions per user are on the same topics as the user's life.
3. **Crowding on purpose, as in M:** cities named in passing (a 10K race in the old city, a parent's visit), other people's cities and jobs, similar trips (two users went to Lisbon), and repeated topics months apart.
4. **Scoring.** The usual keyword checks, raw and reviewed. Three hand rules, fixed now, applied to every mode:
   - the cookies (`n_marisol`): correct only if the answer warns about tree nuts because of her allergy;
   - the takeaway (`n_kwame`): correct only if the answer warns about sesame because of his allergy;
   - the dessert (`n_henrike`): correct only if the dessert is dairy-free or the answer mentions her lactose intolerance.

   No other answer is re-scored. "I don't know" cannot match any expected word of a non-abstain question (checked before freezing).
5. **Not included:** any change to the system, the thresholds or the scoring after this file is committed.

## The run

| # | Command | What it measures |
|---|---|---|
| 1 | `make eval SET=N OUT=docs/results/set_N/full` | ingest, then baseline, smart, hybrid and full answers, cache off (the headline) |

No ablations. If the run is stopped during ingestion (before any question is asked), it may be started again: ingestion deletes each user first. Any other restart is reported.

## Hypotheses and how they are judged

**H1 (pre-registered, the plan's success criterion): on long, crowded histories, hybrid answers more questions correctly than the baseline.** With d = hybrid − baseline (reviewed counts, 57 questions):

| d | Verdict |
|---|---|
| +3 or more | hybrid is better on long histories: **the goal "better answers than vector memory" is met on this set** |
| −2 to +2 | no clear difference |
| −3 or less | the baseline is better |

A sign test on the questions where the two differ is reported with it. A d of +3 with a p above 0.05 is reported as "met by the pre-registered rule, not statistically significant".

Secondary, also pre-registered:

- **H2:** hybrid puts an outdated value in no more answers than the baseline (19 questions have a `stale` list).
- **H3 (a replication of M):** smart answers fewer questions than the baseline (d = smart − baseline ≤ −3).
- **Reported, not judged:** full (the whole history), stale values marked in the prompt, and average lines.

## Predictions

Calibrated on M. I underpredicted the baseline on L and on M by about 9 questions, so the numbers below start from each mode's rate per question type on M (`hybrid_M`), adjusted where N differs. Two of N's past questions follow a single move, which is easier for the baseline than M's two-move users.

| Type | n | Baseline on M | Smart on M | Hybrid on M | Baseline on N | Smart on N | Hybrid on N |
|---|---|---|---|---|---|---|---|
| Current value after a change | 12 | 11 | 11 | 12 | 10 | 10 | 10.5 |
| Past value | 7 | 2 | 5 | 7 | 3.2 | 5 | 6 |
| Episode (one count) | 11 | 10 | 9 | 10 | 9.4 | 8.2 | 9.3 |
| Numeric detail | 4 | 4 | 3 | 4 | 3.7 | 3 | 3.7 |
| Changed plan | 5 | 5 | 4 | 5 | 4 | 3.5 | 4 |
| Other people | 7 | 6 | 4 | 6 | 5.6 | 4.2 | 5.6 |
| Indirect (3 by hand) | 5 | 3 | 2 | 2 | 3 | 2.7 | 3 |
| Direct (one with 3 values) | 2 | 2 | 2 | 1 | 1.8 | 1.6 | 1.5 |
| Trap | 1 | 0 | 0 | 0 | 0.4 | 0.3 | 0.4 |
| Abstain | 3 | 3 | 3 | 3 | 2.7 | 2.7 | 2.7 |
| **Total (reviewed)** | 57 | 47* | 43 | 50* | **about 44 (39 to 48)** | **about 41 (36 to 45)** | **about 46.7 (42 to 50)** |

\* M's raw counts plus the hand review of the earlier runs; hybrid's M answers were not hand-reviewed.

| Measure | Prediction |
|---|---|
| **d = hybrid − baseline** | **about +3 (0 to +6); I give "+3 or more" about a 50% chance.** Almost all of the gain should come from the past questions (timelines). Elsewhere hybrid should equal the baseline, minus about 0.5 from the extra lines (the two M losses: an incomplete multi-valued fact, a marker over a still-true message) |
| d = smart − baseline (H3) | about −3 (−7 to +1) |
| Full | about 42 (37 to 47): below the baseline, as on M |
| Outdated value in the answer (19 with `stale`) | baseline about 4, smart about 1, hybrid about 2 |
| Outdated value in the prompt, not marked | baseline about 15, smart about 5, hybrid about 10 |
| Stale, marked (hybrid) | about 5 |
| Average lines | baseline 4.0, smart about 2.1, hybrid about 5.2, full about 95 |

Where I expect hybrid and the baseline to differ:

| Question | Expected |
|---|---|
| Marisol: before Grenoble; before Lyon. Kwame: before Manchester; before Tidemoor Rail. Henrike: before Harbourlight Games; before Hamburg | the timeline should win most of these for hybrid; the baseline will win some too, because single moves are easier |
| Kwame: job title (graduate engineer, engineer, senior engineer) | a fact line helps hybrid |
| Henrike: languages (three values) | a risk for hybrid if a language was not extracted (the M loss) |
| Signature and bio (Kwame, Henrike) | a risk for hybrid: markers on the introduction message |

If H1 fails, hybrid still does no harm against the baseline, and its gain is limited to past questions. In that case the honest headline is "a marked timeline helps questions about the past", not "better than vector memory".
