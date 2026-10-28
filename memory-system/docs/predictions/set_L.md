# Predictions before set L (written 2026-10-28, before the run)

Set L (`scripts/evaluation/scenarios/sets/set_l.json`, 10 stories, 30 questions) is the first measure on unseen data. It was written after sets A to K were spent and before any change to the system, and it is run **once**, on the current system. Nothing below has been checked against data.

Agreed scope (2026-10-28): one file of single questions, every question type mixed at a natural rate. Multi-session stories are left out: the loader allows one format per set letter, so they would need a second set, and set K already measures sessions.

## Design (frozen with the set)

1. **Question types (30):** 6 direct facts, 6 changes, 4 past questions, 7 episodes or plans, 4 indirect questions, 3 traps (one third-person statement read as the user's, two abstain questions). Every story has chit-chat between its messages. Two rich profiles carry 7 and 6 questions; one episode is told over three messages; one plan changes its companion.
2. **Two smart columns, both pre-registered:** smart with summaries on (the current system, the headline number) and smart with `SUMMARIES=0` (facts only, on the same stored data). Baseline is in both runs; its second run is a free check of run-to-run noise.
3. **Runs, in order, cache off:**
   - `make fresh SET=L`: ingest, notes and digests, baseline and smart answers. Output saved as `results/set_L/first_run.txt`, and `eval_results.json` copied to `results/set_L/first_run.json`;
   - `SUMMARIES=0 nice -n 10 poetry run python scripts/evaluate.py --set L --no-ingest --no-cache`, saved as `results/set_L/summaries_off.txt` and `summaries_off.json`.
4. **Scoring:** the usual keyword checks (`expect`, `needs`, `avoid`, `stale`). One hand rule, fixed now: the fruit-salad question (`l_profile_maren`) is correct only if the answer warns about kiwi or leaves it out because of the allergy; a salad that merely contains kiwi is wrong. Raw and reviewed counts are both reported. No other answer is re-scored by hand; keyword misses that read as correct are listed, not counted.
5. **Not included:** any change to the memory system, the scoring or the thresholds. The two held-back fixes (strong-match override, allergy bypass to rank 3) stay off.

## Known risks, written in on purpose

- **Two past questions read archived values.** "I left Hollbach Clinic" and "Corentin and I broke up" are the natural ways to say it, and the write path stores the old value as `archived`, which the past rule does not read ([06](../06_read_path.md), section 10). Facts alone should miss both. With summaries on, a note ("adopted a cat with her boyfriend Corentin") may carry the old partner.
- **One indirect question is the set K weakness** (an email signature needs `name` and `works_at`). The "second of two languages" weakness is also present, as a direct question. Each appears once, not stacked.
- **The language goal may be routed out.** "I've started learning Finnish" is probably stored as `goal` or `hobby`; for "the language I'm learning", routing may rank `speaks` first and drop it, as with the Japanese goal of set E.
- **The job title may be `conflicted`.** Zuzana's employer changes; the new message restates "nurse", which should keep the title, but the dependency rule may mark it `conflicted` and hide it.
- **A note can bring back an old name.** The cat note mentions Corentin, so "Who is my partner?" may count a stale word in smart's prompt. That is a true past-tense mention, scored as stale by the keyword check, as on sets A to F.
- **The wedding trap.** "My brother Fintan is getting married" may be read as the user's own plan by the extraction or a note.

## Per question (probability of a correct answer)

| Story | Question | Type | baseline | smart, summaries on | smart, summaries off |
|---|---|---|---|---|---|
| maren | What's my name? | direct | 85% | 95% | 95% |
| maren | Which languages do I speak? (both) | direct | 80% | 55% | 55% |
| maren | Which instrument am I learning? | direct | 90% | 80% | 80% |
| maren | Fruit salad for my lunch (hand rule, kiwi) | indirect | 60% | 60% | 60% |
| maren | Email signature (name and employer) | indirect | 75% | 30% | 30% |
| maren | When is my wedding? (brother's) | trap | 70% | 65% | 45% |
| maren | Favourite season (abstain) | trap | 60% | 75% | 80% |
| zuzana | Which city do I live in? | change | 75% | 90% | 90% |
| zuzana | Where did I live before Linz? | past | 80% | 75% | 75% |
| zuzana | Where do I work? | change | 70% | 80% | 80% |
| zuzana | Which clinic did I work at before? (archived) | past | 75% | 35% | 15% |
| zuzana | What do I think of coffee these days? | change | 65% | 65% | 65% |
| zuzana | What's my job? | direct | 85% | 70% | 70% |
| suitcase | Where was the suitcase found? | episode | 90% | 75% | 5% |
| suitcase | How much did the airline pay? | episode | 85% | 70% | 5% |
| suitcase | On which flight was it lost? | episode | 90% | 75% | 5% |
| hiking | Who is coming hiking? (companion changed) | change | 75% | 60% | 25% |
| hiking | Where am I going hiking? | episode | 90% | 70% | 45% |
| partner | Who is my partner? | change | 65% | 80% | 75% |
| partner | Who was my partner before Odile? (archived) | past | 75% | 45% | 15% |
| partner | What's my cat called? | episode | 90% | 70% | 5% |
| job | Where do I work now? | change | 70% | 90% | 90% |
| job | Where did I work before Morrow Biotech? | past | 80% | 75% | 75% |
| indirect | Which sea is closest to where I live? | indirect | 80% | 70% | 70% |
| indirect | "Thank you" in the language I'm learning | indirect | 75% | 45% | 45% |
| sister | Which city do I live in? (sister elsewhere) | direct | 85% | 95% | 95% |
| sister | What's my job? (abstain; the sister is a pilot) | trap | 60% | 70% | 75% |
| marathon | How long did my half marathon take? | episode | 90% | 70% | 5% |
| marathon | In which city did I run it? | episode | 90% | 75% | 5% |
| birthday | When is my birthday? | direct | 85% | 90% | 90% |

Reasons behind the main numbers:
- **Baseline** searches the raw messages, so it is strong on episodes and on past questions (the old message is still there), and it is hurt by changes (old and new messages side by side) and by "I don't know" with the fact in its lines.
- **Smart with summaries** wins on changes and simple facts, and loses some episodes (a note must be written, pass its check and pass the gate) and indirect questions (the gate).
- **Smart without summaries** cannot answer episodes at all; past questions on archived values fail.

## Totals (the numbers to check)

| Measure | baseline | smart, summaries on | smart, summaries off |
|---|---|---|---|
| Answers correct (30) | about 23.5 (21 to 26) | about 21 (18 to 24) | about 15.5 (13 to 18) |
| Needed present (28 questions with `needs`) | about 24 | about 19 | about 13 |
| Stale in prompt (5 questions with `stale`) | about 4 | 0 to 2 (true mentions in notes) | 0 |
| Noise present (2 questions with `avoid`) | about 2 | about 0.5 | about 0.5 |
| Average lines | 4.0 | about 1.5 | about 1.0 |
| Stale in answer | 0 to 2 | 0 | 0 |

By type (expected correct):

| Type | baseline | smart, on | smart, off |
|---|---|---|---|
| Direct (6) | 5.1 | 4.9 | 4.9 |
| Changes (6) | 4.2 | 4.7 | 4.3 |
| Past (4) | 3.1 | 2.3 | 1.8 |
| Episodes (7) | 6.3 | 5.1 | 0.8 |
| Indirect (4) | 2.9 | 2.1 | 2.1 |
| Traps (3) | 1.9 | 2.1 | 2.0 |

## Statements to check after the run

1. **Baseline answers about 2 more questions than smart with summaries.** On unseen data, with every question type mixed, I do not expect smart to win on answers. If smart ties or wins, this prediction failed in smart's favour.
2. **Smart never puts an outdated value in an answer** (0), and baseline does 0 to 2 times.
3. **Smart sends under 2 lines on average,** against 4.0.
4. **Summaries add about 5 correct answers** (15.5 to 21), almost all of them episodes.
5. **Smart is ahead on changes and behind on past questions, episodes and indirect questions.**
6. **The archived clinic is missed by smart without summaries.**

Each is checked as written; misses are reported, not edited.
