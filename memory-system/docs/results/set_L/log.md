# Set L: first results on unseen data (2026-10-28)

Set L (10 stories, 30 questions, every question type) was written after sets A to K were spent, frozen with its predictions ([../../predictions/set_L.md](../../predictions/set_L.md)) and run **once** on the current system, cache off. Nothing was changed before or between the runs.

| File | What it is |
|---|---|
| `first_run.txt`, `first_run.json` | `evaluate.py --set L --no-cache --verbose`: ingest, notes, baseline and smart with summaries |
| `summaries_off.txt`, `summaries_off.json` | `SUMMARIES=0 evaluate.py --set L --no-ingest --no-cache --verbose`: same stored data, facts only |

## Results

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
- Smart right and baseline wrong on 1 question (the name); the reverse on 9; both wrong on 1 (the wedding). A sign test on the 10 differing questions gives p of about 0.02: **on this set the baseline is better, and the gap is unlikely to be luck.**

By type (correct answers):

| Type | baseline | smart, on | smart, off |
|---|---|---|---|
| Direct (6) | 5 | 4 | 4 |
| Changes (6) | 6 | 5 | 5 |
| Past (4) | 4 | 3 | 3 |
| Episodes (7) | 7 | 5 | 1 |
| Indirect (4) | 4 | 2 | 2 |
| Traps (3) | 2 | 1 | 1 |

## Why smart missed 10 questions (summaries on)

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

### Notes missing for two stories

`eval_l_profile_maren` (11 messages) and `eval_l_indirect` (5) have no notes. The audit log shows one `summarize` event each, with `dropped: []`: the questions were skipped as chatter (5 and 3), and for the other messages the model returned no note at all. The notes prompt says "skip plain personal facts that are stored elsewhere", and the model applied it to cello lessons, learning Finnish and the brother's wedding. When extraction also misses such a message (cello), neither layer keeps it. That gap between the layers is a new limit.

### Other observations

- **"I left Hollbach Clinic. I'm now a nurse at St Veit Hospital" superseded the old employer**, it did not archive it, so the past question was answered. In set I a similar sentence archived it. The write path is not consistent on this wording.
- `St Veit Hospital in Linz` was stored with the city inside the employer value.
- The two smart stale-in-prompt cases are notes: one true past mention ("broke up with Corentin"), and one outdated note (the hiking plan with Pieter).
- With summaries off, smart averaged 0.9 lines and never had a stale value in prompt or answer; it lost every episode but one.

## Predictions against results

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

What I got wrong: I expected the gate to be the main weakness and the write path to be reliable on new wording. On unseen data, extraction of other people's facts and of incidental places was the larger problem, and I underrated how well a raw-message baseline does when every story is short.

## What this means for the plan

- The improvement round should start with the write path: facts about other people (a sister's city and job, a friend), and places that are not the user's home. These errors are worse than a miss, because they replace a right fact.
- The gate on indirect questions stays (signature, wedding, the language goal).
- The notes prompt's "skip plain personal facts" rule needs a guard, so that a message whose facts were not stored still gets a note.
- Set L is now spent. Its stories may be used to develop these fixes; set M measures them.
