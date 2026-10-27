# Summaries layer: development log

What was run, what failed, what was changed. Newest last. Sets A to F are spent, G was run once
before the layer existed and re-run with it, H was run once (run 5).

## Run 1: sets A to F with summaries on (2026-10-26, retrieval only, existing data)

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

## Change 1: questions, requests and thanks are filtered by rule before the model sees them

`summary_rules.is_chatter`: a message that starts with a question word and ends with "?", or starts
with a request ("give me", "explain", "suggest", ...) or "thanks". A statement followed by a question
is kept. The messages still count as seen. Checked on the messages of all eight sets: only generic
filler is flagged, no statement is. This is a fix for a rule of the specification the model did not
follow; no threshold changed. It was derived from the A to F run, not from set H, which has not been run.

Not changed on purpose: summaries that truthfully mention an old value stay. A rule against them
would also remove the information needed for questions about the past ("where did I live before?"),
which is a separate step.

## Run 2: sets A to F from an empty database, with change 1 (retrieval only, then answers)

| Smart, sets A to F | Criterion | Run 1 | Run 2 |
|---|---|---|---|
| Needed present | 55/58 or better | 55/58 | 55/58, met |
| Average lines | under 2.0 | 1.3 to 1.8 | 1.3 to 1.8, met |
| Stale in prompt | 0 | 3 | **4** (A 1, B 1, F 2), not met |
| Noise present | 14/46 or fewer | 17/46 | **17/46**, not met |

Summaries fell from 48 to 38, so the question summaries were not the main source of the extra
noise: my diagnosis after run 1 was incomplete. Reading the nine prompts where a note sits next to
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

## Run 3: set G re-run with summaries (labelled re-run: G had been seen)

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

## Change 2: faithfulness matches against every source word (bug fix)

`is_faithful` now matches the statement's content words against all words of the cited messages,
stopwords included, as its docstring said. Names and numbers are checked as before. Derived from
set G, not from H. Sets A to G need to be re-ingested to see its effect.

## Run 4: sets A to G from an empty database, with changes 1 and 2

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

## Run 5: set H, once, with answers (blind validation)

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
