# Hybrid read path: development record (step 2 of the hybrid plan, 2026-10-30)

Set M rejected the main hypothesis: on long histories the baseline's four raw messages answered more than smart's facts and notes ([../set_M/log.md](../set_M/log.md)). Step 1 made the current facts right (12 of 12 on M; smart 36 to 43 against the baseline's 47, reviewed; [change_rule_dev.md](change_rule_dev.md)). Step 2 tries to beat the baseline by keeping its recall and adding what facts do well.

This is **development on spent sets** (M and L). The honest test is a fresh blind set N (step 4), with success pre-registered as hybrid ≥ baseline + 3.

## The design

Two new modes; none, baseline and smart are unchanged ([../../06_read_path.md](../../06_read_path.md), section 11).

**`hybrid`**, in prompt order:

1. Up to 2 current fact lines, chosen by smart's gate (allergy pass included).
2. For a past question only: one timeline line with every value of the relation asked about, oldest first (`Lives in, oldest first: Stavanger -> Oslo -> Kristiansand (now)`). Retracted values are included and tagged `(ended)`.
3. The baseline's top 4 messages word for word. A message whose fact has since been superseded is marked `[outdated: now X]`; one whose fact was retracted is marked `[no longer true: X]`.

No episode notes. At most 7 lines against the baseline's 4.

**`full`**: every user message, oldest first (about 1,100 tokens per M user), with the context window set to 8192 for this mode only. It is a reference ceiling.

**Scoring:** an outdated value that appears only on a marked line is counted as "stale, marked", apart from "stale in prompt". Only hybrid writes marked lines, so the other modes' numbers do not change.

## Checks before any run (offline, no model)

- 26 new tests (274 in all), including 9 database tests: markers through a chain of moves, a retraction, a user who moved back, the timeline only on past questions, a retracted employer in the timeline, both switches, the baseline query unchanged, full oldest first.
- The baseline's query is untouched (`baseline_messages` runs the same SQL and also returns the ids), so hybrid's messages are exactly the baseline's.
- `chat()` gets a context size only for the full mode. The calls and cache keys of the other modes are unchanged.

## Runs

Both runs reuse the data stored by the step 1b runs (`--no-ingest`), so the facts are the ones that gave 12 of 12 on M and only the read path changes. Cache off, all four modes answered.

1. `make eval SET=M OUT=docs/results/logs/hybrid_M ARGS=--no-ingest`
2. `make eval SET=L OUT=docs/results/logs/hybrid_L ARGS=--no-ingest`
3. (optional) `make eval SET="A B C D E F G H I J" OUT=docs/results/regressions/A_to_J_hybrid ARGS=--no-ingest`

If M or L was deleted from the database since step 1b, drop `ARGS=--no-ingest` (it ingests again: slower, and the facts may differ slightly).

## Predictions (written before the runs)

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

## Results

(to be filled in after the runs)
