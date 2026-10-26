# Questions about the past: development log

Predictions: docs/predictions/set_I.md (written and committed before any run). Raw output of the
runs: set_I_first_run.txt (mechanism on, with answers), set_I_off.txt (control, `PAST_FACTS=0`, same
stored data, retrieval only), regress_A_to_H.txt (all other sets with the mechanism on).

## Change before the run

The unit test of the trigger rule showed that "What food did I use to dislike?" did not fire ("use
to" without the d). "did I use to" was added to the trigger list and the predictions file was
amended before set I was run. No run of set I existed at that point.

## Run: set I, once (2026-10-26)

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

## Diagnosis (stored facts and lines of the three scenarios that missed or surprised)

| Question | What happened | Cause |
|---|---|---|
| `i_job`, "Where did I work previously?" | Halvorsen is `archived`, not `superseded`; the prompt had only Pelican | "I left Halvorsen Marine, I now work at Pelican Software" is stored as a retraction plus a new value. The rule reads only superseded facts. Predicted at about 75% |
| `i_partner`, "Who was my partner before Elena?" | Dario is `archived`; the question was answered through a note ("after splitting up with Dario"), also with the rule off | Same write-path behaviour. The criterion was met by the notes layer, not by the mechanism |
| `i_two_moves`, "originally" | `Earlier: Valencia`, `Earlier: Ghent`, `Lives in: Gdansk` in the prompt; the answer was "I don't know" | The needed fact was present. Lines are ordered by similarity, so the oldest value came second; the 8B model did not pick it. A model failure, made more likely by the ordering |
| `i_flip`, "What food did I use to dislike?" | The answer was "Olives." | Correct in substance. The scoring requires a word such as "dislike", so it is counted as a miss as written |
| Controls, stale in prompt = 1 | The `i_partner` note mentions Dario | A true mention. It also appears with the rule off, so the mechanism did not cause it |

## Regression: sets A to H with the mechanism on (answers included)

| Sets | Expected | Result |
|---|---|---|
| A to F, smart | identical: needed 56/58, noise 16/46, stale 4, answers 58/61 | identical |
| G | only `g_past_home` changes | needed 13/17 to 14/17, answers 12/18 to 13/18, no other change in the totals |
| H | identical | identical (12/13, 2/3, 0, 1.1 lines, 13/14) |

## Not changed, on purpose

Two changes follow from the diagnosis: read facts archived by a retraction for past questions, and
order past lines oldest first. Neither was made, because set I is spent. Both are proposed for a
fresh set (docs/10_limits_and_roadmap.md).
