# Predictions before set M (written 2026-10-29, before any run)

Set M (`scripts/evaluation/scenarios/sets/set_m.json`, 3 users, 289 messages, 57 questions) tests the question the project was built for: **is this memory better than plain vector search over a long, crowded history?** Sets A to L were short stories (4 to 18 messages), where the baseline's four most similar messages usually hold the answer. M was written after the step 1 and 2 fixes ([results/logs/about_user_dev.md](../history.md#about-user), [results/logs/note_tags_dev.md](../history.md#note-tags)) and before any run on it. It is run **once** on the current system, plus the ablations below. Nothing below has been checked against data.

## Design (frozen with the set)

1. **Users.** Solveig (92 messages over 548 days), Tamsin (97 over 560), Ruben (100 over 552). Each has about 30 statements and about 62 everyday questions to the assistant, spread evenly up to the last two weeks. About 15 of those questions per user are on the same topics as the user's life ("What's the best time of year to visit Japan?"), so they compete with the real statements for the baseline's four lines.
2. **Crowding, on purpose.** Two moves (Solveig), one move announced months before it happens (Tamsin), house hunting that names the new city long before the move (Ruben); two or three employers each, one of them left with "I left X"; a partner change (Solveig); family and friends with their own cities and jobs, some of whom move; three or four similar trips or concerts per user; plans that change their date or companion once or twice, one cancelled and revived (Mexico); two stolen bikes; repeated topics months apart. Old notes are old enough for consolidation.
3. **Questions (57).** 12 current values after a change, 7 past values, 11 episodes (one asks for a count), 4 numeric details, 5 plans that changed, 7 questions about other people, 5 indirect questions (3 scored by hand), 2 direct facts (one with three values), 1 trap and 3 abstain questions.
4. **Scoring.** The usual keyword checks. Three hand rules, fixed now, applied to every mode:
   - the seafood restaurant (`m_solveig`): correct only if the answer warns about shellfish because of the allergy;
   - the antibiotic (`m_tamsin`): correct only if the answer says to mention the penicillin allergy;
   - the dinner (`m_ruben`): correct only if the dish is meat-free and has no aubergine.
   Raw and reviewed counts are both reported; no other answer is re-scored. Keyword wording was checked before freezing so that "I don't know" cannot match a "no" or a "may".
5. **Not included:** any change to the system, the thresholds or the scoring after this file is committed.

## Runs, in this order, cache off

| # | Command | What it measures |
|---|---|---|
| 1 | `make eval SET=M OUT=docs/results/set_M/full` | the current system, baseline and smart (the headline) |
| 2 | `SUMMARIES=0 make eval SET=M OUT=docs/results/set_M/facts_only ARGS=--no-ingest` | smart with facts only, on the data of run 1 |
| 3 | `NOTE_FACT_WINDOW=0 make eval SET=M OUT=docs/results/set_M/no_fact_window ARGS=--no-ingest` | the note window measured among notes only (iteration 3 of step 2 off) |
| 4 | `ABOUT_USER=0 make eval SET=M OUT=docs/results/set_M/no_about_user` | facts about other people kept (step 1 off); ingests again |
| 5 | `NOTE_TAGS=0 make eval SET=M OUT=docs/results/set_M/no_note_tags` | the untagged notes prompt, no only-stored filter (step 2 off); ingests again |

Runs 2 and 3 read the data of run 1, so they come before the runs that ingest again. Each ablation changes one switch. The baseline is answered in every run, which gives four extra checks of run-to-run noise; differences of 2 or less between runs are treated as noise.

## The hypothesis and how it is judged

**H1 (pre-registered): on long, crowded histories, smart answers more questions correctly than the baseline.** With d = smart − baseline (run 1, reviewed counts, 57 questions):

| d | Verdict |
|---|---|
| +3 or more | smart is better on long histories |
| −2 to +2 | no clear difference |
| −3 or less | the baseline is better on long histories |

A sign test on the questions where the two differ is reported with it. Secondary, also pre-registered:

- **H2:** smart puts an outdated value in fewer answers than the baseline (18 questions have a `stale` list).
- **H3:** smart uses under 2 lines per question on average, against 4.0.

**Prediction: H1 fails.** about 39 for the baseline and 36.5 for smart, so "no clear difference", leaning to the baseline. H2 and H3 should hold. The reasons are below.

## Per question (probability of a correct answer)

| User | Question | Type | baseline | smart |
|---|---|---|---|---|
| solveig | Which city do I live in now? | change | 55% | 90% |
| solveig | Where did I live before Kristiansand? | past | 70% | 65% |
| solveig | Which city did I live in before Oslo? | past | 65% | 60% |
| solveig | Where do I work now? | change | 70% | 85% |
| solveig | Where did I work before Fjordline? | past | 80% | 60% |
| solveig | What's my partner's name? | change | 50% | 90% |
| solveig | What's my dog called? | episode | 85% | 70% |
| solveig | Where does my brother live now? | third person | 70% | 55% |
| solveig | Where does my sister work? | third person | 75% | 60% |
| solveig | When is the Japan trip? | plan change | 65% | 45% |
| solveig | Who did I go to Iceland with? | plan change | 70% | 50% |
| solveig | What animals did I see in Iceland? | episode | 80% | 65% |
| solveig | Which city did I visit with Tarek? | episode | 60% | 50% |
| solveig | I'm going to a seafood restaurant tonight. Anything I should watch out for? | indirect, by hand | 75% | 80% |
| solveig | Do I still drink coffee? | change | 60% | 75% |
| solveig | How much did my dry suit cost? | detail | 85% | 65% |
| solveig | What sport do I do these days? | change | 55% | 70% |
| solveig | What did I present at the conference in Rotterdam? | episode | 85% | 70% |
| solveig | What's my favourite film? | abstain | 60% | 80% |
| tamsin | Which city do I live in? | change | 65% | 90% |
| tamsin | Where did I live before Bristol? | past | 75% | 70% |
| tamsin | Which school do I work at? | change | 60% | 85% |
| tamsin | Where did I work before Clifton Down School? | past | 75% | 65% |
| tamsin | What does my wife do? | third person | 80% | 60% |
| tamsin | Which instrument is my daughter learning? | episode | 80% | 65% |
| tamsin | What tiles did we choose for the bathroom? | plan change | 65% | 50% |
| tamsin | How much did the bathroom cost? | detail | 85% | 65% |
| tamsin | Where are we going on our family trip next summer? | plan change | 70% | 50% |
| tamsin | Which concert did I enjoy most this year? | episode | 65% | 45% |
| tamsin | Where does Callum live now? | third person | 70% | 55% |
| tamsin | What was my half marathon time? | detail | 80% | 65% |
| tamsin | How did my Welsh exam go? | episode | 85% | 70% |
| tamsin | My doctor wants to prescribe me an antibiotic. What should I tell her? | indirect, by hand | 80% | 80% |
| tamsin | What kind of music do I make these days? | change | 50% | 60% |
| tamsin | When is my wedding? | trap | 50% | 45% |
| tamsin | Where does my mum live? | third person | 70% | 50% |
| tamsin | Write a one-line email signature for me. | indirect | 65% | 30% |
| tamsin | What's my favourite football team? | abstain | 60% | 80% |
| ruben | Which city do I live in? | change | 60% | 90% |
| ruben | Where did I live before Rotterdam? | past | 75% | 70% |
| ruben | Where do I work? | change | 55% | 80% |
| ruben | Which company did I work for before Peatline? | past | 75% | 60% |
| ruben | Which company bought Kiwibyte? | episode | 90% | 65% |
| ruben | What's my job title? | change | 55% | 75% |
| ruben | What's my husband's name? | direct | 90% | 90% |
| ruben | What does Joost do for a living? | third person | 80% | 60% |
| ruben | How many times has my bike been stolen? | episode count | 65% | 40% |
| ruben | How much did my second bike cost? | detail | 80% | 65% |
| ruben | Where does my brother live now? | third person | 55% | 50% |
| ruben | When are we going to Mexico? | plan change | 50% | 45% |
| ruben | Where did Joost and I go cycling? | episode | 85% | 65% |
| ruben | Suggest a dinner I could cook for myself tonight. | indirect, by hand | 50% | 50% |
| ruben | Which languages do I speak? | direct, three values | 80% | 50% |
| ruben | What's my cat called? | episode | 85% | 70% |
| ruben | Do I still go rowing? | change | 60% | 55% |
| ruben | Write a one-line professional bio for me. | indirect | 50% | 30% |
| ruben | What's my favourite board game? | abstain | 60% | 80% |

Reasons behind the main numbers:
- **The baseline** loses where crowding bites: current values after two changes (three city messages and a topical question compete; the model may pick an old one), partners (three Tarek messages against one Emil), and hobbies that changed. It stays strong on one-off episodes and numbers, which are said once, clearly.
- **Smart** wins on current values (facts are replaced, not added). It loses on plans that changed (a strong `goal` fact keeps the note with the new date out of the window, the Hanoi pattern of set J), on counting or comparing episodes (at most two notes), on other people (notes only), on signature-style questions (the gate), on three languages at once, and on past values that were archived.

## Totals

| Measure | baseline | smart |
|---|---|---|
| Answers correct, reviewed (57) | about 39 (34 to 44) | about 36.5 (32 to 41) |
| Outdated value in the answer (18 with `stale`) | about 4 (2 to 7) | about 1 (0 to 3) |
| Outdated value in the prompt (18) | about 13 | about 2 |
| Average lines | 4.0 | about 1.8 |

By type (expected correct):

| Type | Questions | baseline | smart |
|---|---|---|---|
| change | 12 | 6.9 | 9.5 |
| episode | 10 | 8.0 | 6.4 |
| past | 7 | 5.2 | 4.5 |
| third person | 7 | 5.0 | 3.9 |
| plan change | 5 | 3.2 | 2.4 |
| indirect | 5 | 3.2 | 2.7 |
| detail | 4 | 3.3 | 2.6 |
| abstain | 3 | 1.8 | 2.4 |
| direct | 2 | 1.7 | 1.4 |
| trap | 1 | 0.5 | 0.5 |
| episode count | 1 | 0.7 | 0.4 |

## Ablations (smart answers, against run 1)

| Run | Prediction | Why |
|---|---|---|
| 2, facts only | about 8 fewer (5 to 11) | episodes, details, plans and other people live in notes |
| 3, note window among notes only | about the same (−1 to +2) | plans that changed may gain (the date note passes next to the goal fact), other answers may get noisier prompts |
| 4, `about_user` off | 2 to 4 fewer | a brother's, a sister's and a friend's moves become the user's cities, which corrupts the past-city questions ("before Oslo" may become Copenhagen, "before Bristol" Dublin); a wife's and a husband's jobs become the user's |
| 5, untagged notes | 1 to 3 fewer | lessons, a pet, a hobby change and family jobs lose their notes again |

## Known risks, written in on purpose

- **Two past questions may read archived values** ("I left the Nordhavn Institute", "I left Lumenor"). On set L the same wording superseded the old employer instead; it is not consistent.
- **A goal fact can hide the answer** for the three plans that changed (Japan, the summer trip, Mexico).
- **The model may answer from today's date** for relative plans ("next April", "next summer"); the questions avoid relative wording where they can.
- **Run length.** About 289 extractions plus notes and digests per ingest; runs 1, 4 and 5 take roughly 20 to 30 minutes each.
