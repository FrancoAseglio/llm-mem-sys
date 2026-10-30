# Predictions before set G (written 2026-10-26, before running anything)

Set G (`scripts/scenarios/set_g.py`, 9 scenarios, 19 questions) is blind and is run once on the
**current** system (no summaries layer yet). Nothing below has been checked against data. The
gate, the extraction and the weights are frozen; no tuning on G before this first run.

The set is deliberately outside what the system was built for: 12 of the 19 questions need
episodes, details or the past, which the 13 typed facts do not hold. The questions were written by
the system's author, so they are biased toward its weak points; the control questions are there to
show what is unaffected.

## Per scenario

| Scenario | Question | none | baseline | smart (current) |
|---|---|---|---|---|
| g_trip | What trip did I tell you about? | wrong | needed present, correct | **needed missing**, wrong ("I don't know") |
| g_trip | Who did I go hiking with? | wrong | present, correct | missing (about 30% chance `family_member` captures Ingrid) |
| g_wedding | Where is my sister's wedding? | wrong | present, correct | missing; a `family_member` fact for the sister is possible but it will not contain Lisbon |
| g_wedding | What am I doing at the wedding? | wrong | present, correct | missing |
| g_diet_misfile | What are my hobbies? | wrong | cello present, but noise (vegan) present, as baseline returns four messages | cello present; **"vegan" appears as a hobby or in the lines about 40% of the time** (the misfiling seen in a manual test) |
| g_diet_misfile | Can you suggest something for dinner? | wrong | present, answer mentions vegan or dairy about 60% of the time | needed ("vegan") missing about 60% of the time; hit if misfiled as like/dislike/hobby |
| g_past_home | Where do I live now? | wrong | present; **stale (Porto) in the lines about 50%** | present, stale 0 |
| g_past_home | Where did I live before Leeds? | wrong | present, correct | **missing, always**: superseded facts are never read |
| g_training | What am I training for? | wrong | present, correct | about 50% (a `goal` fact if the model extracts one) |
| g_project | What project am I leading at work? | wrong | present, correct | missing (about 90%) |
| g_project | When is the deadline for it? | wrong | present, correct | missing (about 90%) |
| g_jobsearch | How did my job search go? | wrong | present (Orbital is in the offer and start messages) | present about 60% via `works_at = Orbital Freight`; the answer will say where the user works, not tell the story, but keyword scoring may still count it |
| g_jobsearch | Which company turned me down? | wrong | present about 70% (6 messages, 4 recalled) | missing (about 90%) |
| g_jobsearch | Where do I work? | wrong | present | present |
| g_control_facts | What's my name? | wrong | present | present |
| g_control_facts | Which languages do I speak? | wrong | present | present |
| g_control_facts | Can you suggest a quick snack? | n/a | hazelnut present about 50%; noise present | hazelnut present, noise absent |
| g_abstain | Do I have any pets? | correct (abstains) | noise present (the neighbour's dog message); answer correct about 70%, the rest treat the dog as mine | nothing recalled, abstains about 85% |
| g_abstain | What's my favourite colour? | correct | noise present; answer correct about 85% | nothing recalled, abstains about 90% |

## Totals (the numbers to check)

| Metric | baseline | smart (current) |
|---|---|---|
| Needed fact present (17 questions with `needs`) | about 14 | **about 8**. Baseline wins on coverage |
| Noise present (4 questions with `avoid`) | 3 to 4 of 4 | 0 to 2 of 4 |
| Stale in prompt (1 question) | 0 to 1 | 0 |
| Answers correct (18 questions with `expect`) | about 13 | about 9 |

Pre-registered claims:

- On the 12 episode, past and misfile questions, **baseline's needed-present count will exceed smart's by at least 4**. If not, the assumed weakness is wrong.
- Smart's two clean wins are the noise and abstain questions, and the stale count.
- On the 7 control questions (name, languages, snack, current home, where I work, both abstains) smart will be at least as good as baseline on needed-present.
- The most likely surprise: the model's extraction capturing episode details as `goal`, `hobby` or `family_member` facts, making smart score higher than predicted on the trip, wedding and training questions.

## What the summaries layer must achieve (set before it is built)

Measured on set G, second run, and on sets A to F:

1. **Episode and story questions** (g_trip, g_wedding, g_project, g_jobsearch, 9 questions): needed-present within 2 of the baseline's count.
2. **Past question** (g_past_home, "before Leeds"): answered correctly, with the old home labelled as past, and "Where do I live now?" still free of the old value.
3. **No regression**: sets A to F keep needed fact 55/58 or better, stale in prompt 0, and noise at or below 14/46. Smart's average lines on those sets must stay under 2.0.
4. **Misfiling**: "vegan" must not appear for the hobbies question.
5. **Faithfulness**: every claim in a stored summary traceable to a source message. Checked by hand on all summaries produced for set G.
6. **Compression**: the average summary at most half the length of its source messages. Reported, not a pass/fail criterion.

If these fail, they are reported as failures, and G is spent after its second run.
