# Predictions before set J (written 2026-10-26, before any consolidation code exists)

Set J (`scripts/evaluation/scenarios/set_j.py`, 5 scenarios, 26 questions) validates note
consolidation. It is blind. It is run **twice and only twice**: once now on the current system
(notes only, labelled "off"), and once after consolidation is built ("on"). It is never tuned on.
Nothing below has been checked against data.

Evidence for the need: the notes of the evaluation users are 1.03 times the length of the
messages they came from ([07_summaries.md](../07_summaries.md), section 9). Nothing is compressed.

## Proposed design (to be approved before any code; frozen once approved)

1. **Trigger.** After `summarize_pending`, a user is consolidated when they have at least
   `CONSOLIDATE_MIN` (6) live notes whose newest source message is older than
   `CONSOLIDATE_AGE_DAYS` (30). Newer notes are never touched.
2. **Grouping and writing.** One model call (temperature 0) gets the old notes, numbered, and
   returns digests: one or two sentences per topic, each citing the notes it merges. The prompt
   asks for names, places, numbers and times kept exactly, the final state when notes disagree,
   and other people's actions kept as theirs. A digest must cite at least 2 notes. Notes that no
   digest cites stay as they are.
3. **Checks (pure rules).** (a) `is_faithful` against the source messages of the cited notes
   (unchanged rule). (b) **Retention:** every number and every capitalised name in the cited
   notes must appear in the digest, except month and weekday names (so a final state can replace
   "December" with "February"). (c) **Shorter:** the digest must be shorter than the cited notes
   together. A digest that fails any check is dropped and logged; its notes stay live.
4. **Storage.** Schema change: `summaries.kind` (`note` or `digest`) and `summaries.digest_id`
   (a note points to the digest that replaced it). Nothing is deleted: notes stay, hidden.
   One `consolidate` event per run with the ids kept and the digests dropped with reasons.
   Messages are not touched.
5. **Retrieval.** Candidates are digests plus notes with no `digest_id`. Same gate (floor 0.42,
   window 0.08), same room (at most 2 lines after the facts), same no-repetition rule. The
   stale-source rule applies to a digest through the source messages of all its notes.
6. **Switch.** `CONSOLIDATE=0` turns it off. No new similarity threshold; nothing tuned on J.
7. **Not included:** routing for notes, the "say you don't know" prompt, past questions, removing
   or archiving messages.

## Implementation notes (written while coding, after run 1, before run 2)

Run 1 (consolidation off) was made before the design was explicitly approved; the design above
was then built as written. These points were not covered by it and were decided while coding.
None of them is a threshold, and none was chosen by looking at J's results:

- At most 40 old notes per model call (`CONSOLIDATE_BATCH`), oldest first. No J user comes near it.
- A digest that cites a note already merged by an earlier digest of the same run is dropped
  ("note already merged"). Checks run in the order: at least 2 notes, overlap, faithful, retention,
  shorter.
- A run that would send exactly the notes of the last run is skipped (the model would answer the same).
- Retention: plural weekdays ("Thursdays") count as weekday names; a capitalised word that starts
  any sentence of a note is not a name. Both fixes came from unit tests, not from J.
- Consequence of 3b as written, noticed before run 2: a day number is a number, so a digest that
  turns "December 12" into "February" is rejected for dropping "12". The Hanoi digest will either
  keep both dates or not exist. Not changed, because the design was frozen.

## Run protocol

- Run 1, now: `--set J`, modes baseline and smart (notes only), retrieval and answers. Saved to
  `docs/results/set_J_off.json`. This spends the "off" condition only.
- Run 2, after the code: the same command with consolidation on. Saved to `docs/results/set_J_on.json`.
  J is spent after this.
- Regression after run 2: sets A to F and G, H, I (all spent, labelled re-runs).

## Per question (probability the needed words reach the prompt)

| Scenario | Question | baseline | smart off | smart on | Main risk with consolidation |
|---|---|---|---|---|---|
| j_renovation | cabinets made of (oak) | 90% | 85% | 75% | digest keeps "green" as the final choice |
| j_renovation | why work stopped (asbestos) | 90% | 85% | 70% | cause dropped in a long kitchen digest |
| j_renovation | final cost (21,500) | 85% | 75% | 60% | retention rejects a digest that drops 18,000, or the answer gives the quote |
| j_renovation | who got hurt (Henrik) | 90% | 80% | 65% | misattribution: "the user fell off the ladder" |
| j_renovation | planted last week (tomato) | 90% | 85% | 85% | recent note, must not be digested |
| j_travels | Reykjavik with (Sunniva) | 90% | 85% | 70% | details from two trips merged into one digest |
| j_travels | learned to cook (tagine) | 90% | 85% | 65% | dish dropped |
| j_travels | flight delay (snow) | 90% | 80% | 60% | cause dropped |
| j_travels | camera (hail) | 85% | 80% | 70% | |
| j_travels | camera price (600) | 85% | 80% | 55% | number dropped, or digest rejected and the note loses the window to it |
| j_travels | Hanoi when (February) | 85% | 70% | 65% | a digest saying "December 12" sits next to the recent "February" note |
| j_band | instrument (fiddle) | 90% | 85% | 75% | |
| j_band | who moved to Canada (Margit + Canada) | 90% | 80% | 65% | misattribution to the user |
| j_band | EP name (Low Tide) | 85% | 80% | 65% | |
| j_band | first gig (Copper) | 85% | 80% | 65% | |
| j_band | Harbourfest crowd ("hundred") | 85% | 70% | 55% | written as "400", which the keyword misses |
| j_control_mix | city (Bergen) | 90% | 95% | 95% | from facts |
| j_control_mix | allergy (kiwi) | 90% | 95% | 95% | from facts |
| j_control_mix | movers damaged (piano) | 90% | 75% | 65% | |
| j_control_mix | chickens (Hilde + Rosa) | 85% | 80% | 70% | one name dropped |
| j_control_mix | oarlocks price (45) | 85% | 75% | 55% | number dropped |
| j_control_mix | bicycle (yellow) | 85% | 80% | 70% | |
| j_recent | inspection (brake) | 90% | 85% | 85% | nothing digested here |
| j_recent | swimming day (Tuesday) | 85% | 75% | 75% | |
| j_recent | spelling contest (second) | 85% | 80% | 80% | |

Other columns:
- `j_control_mix`, "What did I name my cat?": noise (Hilde or Rosa in the lines) baseline about 80%,
  off about 50%, on about 60% (a digest of the chickens is a closer match than one note). The answer
  abstains: off about 60%, on about 55%.
- `j_travels`, "Who did I go to Reykjavik with?": noise (Joel) off about 50% (the partner fact is
  routed in for a "who" question), on about 55%.
- Stale: "December 12" in the lines for Hanoi, baseline about 70%, off about 60%, on about 65%.
  "Aarhus" for the city question, off about 10%, on about 15%. "18,000" for the kitchen cost, baseline
  about 70%, off about 50%, on about 55% (the retention rule keeps it on purpose).

## Totals (the numbers to check)

| Metric | baseline | smart off | smart on |
|---|---|---|---|
| Needed present (25 questions with `needs`) | about 22 | **about 20** (range 17 to 22) | **about 17.5** (range 14 to 21) |
| Answers correct (26 questions with `expect`) | about 21 | about 19 | about 16.5 |
| Noise present (2 questions with `avoid`) | 2 | about 1 | about 1 |
| Average lines | about 4.0 | about 1.8 to 2.4 | about 1.6 to 2.2 |

## Compression (reported for run 2)

- Digests per user: j_renovation 2 to 3, j_travels 2 to 5, j_band 1 to 2, j_control_mix 2 to 4,
  j_recent **0**.
- About 30% of proposed digests dropped by the checks, most by the retention rule.
- Digest length divided by the length of the notes it replaces: **about 0.65** (range 0.45 to 0.85).
- Live summary text (digests plus undigested notes) divided by the source messages of the J users:
  about 0.75, against about 1.0 with consolidation off.

## Success criteria (set before building)

1. **Compression:** digest length over replaced notes at most 0.70, and live summary text over
   source messages below 0.85 on the J users.
2. **Retention:** needed-present with consolidation on is within 2 of off on J (off minus on at most 2).
3. **Final state:** "December 12" does not appear in the Hanoi answer, and "oak" is in the cabinets answer.
4. **Attribution:** no digest makes the user the one who fell off the ladder (Henrik) or moved to
   Canada (Margit); checked by hand.
5. **Age rule:** j_recent gets no digest, and no note newer than 30 days is digested anywhere.
6. **Faithfulness:** every digest of J checked by hand against its source messages; any invented or
   misattributed detail is reported.
7. **No regression:** sets A to F answers at least 58/61, needed at least 56/58, no outdated value in an
   answer; G, H, I re-runs within 1 of their last result. No digests at all are expected in A to I, because
   those users have fewer than 6 notes older than 30 days; any digest there is reported.

A failed criterion is reported as a failure. Expected outcome: criteria 1, 5 and 7 pass;
criterion 2 is close to a coin flip (a drop of about 2.5 is predicted); 3, 4 and 6 pass about 65% each.
