# Predictions before set H (written 2026-10-26, before any summaries code exists)

Set H (`scripts/scenarios/set_h.py`, 7 scenarios, 15 questions) validates the summaries layer. It is
blind: it is run **once**, after the layer is built, and never on the old system. The "before"
evidence is the first run of set G (`docs/results/set_G_first_run.json`). Nothing below has been
checked against data.

## Design as approved (frozen before the first run)

1. A summary is a short, self-contained statement about something the user said, stored in
   `summaries`; its source messages point to it through `messages.summary_id`.
2. `summarize_pending(user_id)` summarises the messages that have no summary yet. It runs after an
   evaluation ingest and, in the chat, every 6 messages. It logs a `summarize` event.
3. Faithfulness check in code: every content word of a statement must appear in its source
   messages (the grounding test used for facts). A failing statement is dropped and logged.
4. Retrieval: summaries pass the same gate as facts (same floor 0.42 and window 0.08, no routing)
   and share the same 4 lines. No new threshold and nothing tuned on G or H.
5. **Stale-source rule:** a summary is skipped at retrieval if any of its source messages produced
   a fact that is no longer active. Without it, a summary of "I live in Turin" would bring back a
   value that facts have superseded and break the 0-stale record.
6. Facts keep priority; the write path is unchanged. Not included: the past-question mechanism and
   the "say you don't know" prompt change; each is its own step.

## Per question (smart with summaries, and baseline)

| Scenario | Question | baseline | smart + summaries |
|---|---|---|---|
| h_bake | What did I bake last weekend? | present, correct (about 90%) | present about 80% |
| h_injury | How did I hurt my wrist? | present, correct | present about 75% |
| h_injury | How long did I wear the cast? | present, correct | present about 55%; the duration is the detail a summary may drop |
| h_purchase | What did I buy from my neighbour? | present, correct | present about 80% |
| h_purchase | How much did it cost? | present, correct | present about 55%; the price may be dropped |
| h_adoption | What kind of animal did I adopt? | present about 85% (5 messages, 4 recalled) | present about 80% |
| h_adoption | What is my dog called? | present about 85% | present about 85% |
| h_adoption | What did my dog chew? | present about 70% | present about 55% |
| h_control_facts | name, city, job (3 questions) | present, correct | present about 85% each, from facts |
| h_control_facts | dish for dinner at a restaurant | shellfish present about 60%; **noise present** | shellfish present about 85%; noise about 25% (a summary of the name or city message) |
| h_third_person | Where am I travelling next month? | **noise present** (Peru in the lines); the answer abstains about 70% | **a summary may say the user is travelling to Peru, about 35%**; otherwise abstains |
| h_third_person | What's my brother's name? | noise (Raul) present; abstains about 85% | abstains about 85% |
| h_cancelled | Am I going to the Lyon conference? | both messages present, correct about 80% | cancellation kept about 65%; **a summary saying "going" without the cancellation about 35%** |

## Totals (the numbers to check)

| Metric | baseline | smart + summaries |
|---|---|---|
| Needed present (13 questions with `needs`) | about 12 | **about 9** (range 7 to 11) |
| Noise present (3 questions with `avoid`) | 3 of 3 | about 1 of 3 (range 0 to 2) |
| Answers correct (14 questions with `expect`) | about 12 | about 9 |
| Average lines | about 4.0 | about 1.5 to 2.2; duplication of fact and summary lines on the control questions pushes it above the 0.8 to 1.7 of the old system |

## Success criteria (set before building, applied to H and to a labelled re-run of G)

1. **Episodes and stories:** on the 9 questions of h_bake, h_injury, h_purchase, h_adoption and h_cancelled,
   the needed-present count of smart is within 2 of the baseline's. On G, the 9 episode and story
   questions go from 3/9 to at least 7/9 (baseline 9/9).
2. **Third person:** neither "peru" nor "cusco" nor "raul" appears in the lines for the two abstain
   questions.
3. **Cancelled plan:** the cancellation is in the lines (the "cancel" need is met) and no live version
   of the plan is shown in its place.
4. **No pollution:** noise on the restaurant question stays absent.
5. **No regression on sets A to F:** needed 55/58 or better, stale in prompt 0, noise at or below 14/46,
   average lines under 2.0.
6. **Faithfulness:** every summary produced for sets G and H checked by hand against its sources; any
   invented detail is reported.
7. **Compression:** average summary length divided by source length, reported only.

A failed criterion is reported as a failure. H is spent after its single run; the layer is not tuned on it.
The re-run of G is labelled a re-run: G was already seen.
