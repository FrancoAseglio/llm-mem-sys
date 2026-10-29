# Set M: long, crowded histories (2026-10-29)

Set M (3 users, 92 to 100 messages each over about 18 months, 289 messages, 57 questions) was written after the step 1 and 2 fixes and frozen with its predictions ([../../predictions/set_M.md](../../predictions/set_M.md)) before any run. It tests the project's main hypothesis: on long histories, smart memory answers better than plain vector search.

| File | Run |
|---|---|
| `full.txt`, `full.json` | 1: the current system, baseline and smart |
| `facts_only.txt`, `facts_only.json` | 2: `SUMMARIES=0`, on the data of run 1 |
| `no_fact_window.txt`, `no_fact_window.json` | 3: `NOTE_FACT_WINDOW=0`, on the data of run 1 |
| `no_about_user.txt`, `no_about_user.json` | 4: `ABOUT_USER=0`, ingested again |
| `no_note_tags.txt`, `no_note_tags.json` | 5: `NOTE_TAGS=0`, ingested again |

Run 1 was started once, stopped during the ingestion of the first user (before any question was asked) to change a colour setting that turned out to have no effect, and started again. Ingestion deletes each user first, so the second start is the one run.

## Result

| Set M, 57 questions | Needed present (54) | Stale in prompt | Avg lines | Answers, raw | Answers, reviewed | Stale in answer |
|---|---|---|---|---|---|---|
| Baseline | **48/54** | 16 | 4.0 | **47/57** | **48/57** | 4 |
| Smart | 36/54 | 7 | 2.2 | 36/57 | 36/57 | 5 |

- **Reviewed:** the three hand rules changed one answer. The baseline's dinner (a one-pot tomato and basil pasta) is meat-free and has no aubergine, so it counts; smart's (chicken fajitas) does not. Both modes warned about shellfish and about penicillin.
- **Head to head:** both right on 34, both wrong on 7, **baseline only on 14, smart only on 2**. Sign test on the 16 differing questions: p of about 0.004.
- **The baseline was the same in all five runs** (47/57 raw, 48/54 needed), so the comparison is not run-to-run noise.

### Against the pre-registered hypothesis

| | Pre-registered | Predicted | Found |
|---|---|---|---|
| H1: smart answers more than the baseline | d = smart − baseline; +3 or more: smart better; −3 or less: baseline better | about −2.5 ("no clear difference", leaning to the baseline) | **d = −12: the baseline is better on long histories** |
| H2: fewer outdated values in smart's answers | | holds | **fails**: 5 against 4 (raw) |
| H3: under 2 lines per question | | holds (about 1.8) | **fails**: 2.2 |
| Baseline answers | | about 39 (34 to 44) | **48, above the range** |
| Smart answers | | about 36.5 (32 to 41) | 36, in range |

I predicted smart well and the baseline badly, as on set L: the everyday questions on the same topics ("best time to visit Japan?") did not crowd the statements out of the baseline's four lines as much as I expected. Embedding similarity found the right statement among about 95 messages in 48 of 54 questions.

## Why smart lost: errors accumulate with length

The 14 questions only the baseline answered, by cause:

| Cause | Questions | What happened |
|---|---|---|
| **A current fact was wrong or missing** | 5 | Solveig's city stayed **Oslo**: "Fjordline transferred me to their office in Kristiansand" stored no city. Ruben's city ended on **Utrecht**: house hunting ("looking at houses in Rotterdam, prices in Utrecht are crazy") and "I now commute to Utrecht by train" each replaced the city. Ruben's job title became **"no office"** ("Peatline has no office"), which also broke his bio. Tamsin's music: "I quit the covers band ... joined a choir" kept `hobby = bass` and stored `job_title = choir member`, so smart said she plays bass |
| **A note lost or never written** | 5 | Iceland's puffins (the trip's notes were merged and the detail dropped), the half-marathon time, Kiwibyte's buyer, Joost's job, Esme's violin: each message is in the baseline's four lines word for word, while smart had no note that passed or kept the detail |
| **Other people** | 1 | "Where does Callum live now?": no Callum note passed the gate; the answer was "Bristol" |
| **A name variant split one employer in two** | 1 | `Fjordline Aquaculture` and `Fjordline` were stored as two employers, so "before Fjordline" read the wrong past value |
| **Notes and facts crowded out by family facts** | 1 | The summer trip: four `family_member` and city lines filled the prompt; the trip notes did not pass |
| **Diet not stored** | 1 | "I've gone vegetarian" reached no line for the dinner question |

Smart's two wins were past questions (the city before Oslo, the school before Clifton Down), where the baseline's four lines held the newer messages.

**The pattern:** each statement is one more chance for the 8B extractor to mis-store a fact, and a single-valued fact (city, job title) is replaced by whatever was extracted last, including incidental mentions (a commute, a house viewing, a friend's wedding city). Over 30 statements those mistakes accumulate, and smart trusts its facts. The baseline cannot make this kind of mistake: it hands the model the original sentences and lets it read them. Notes, which hold episodes, lose details when they are merged and pass at most two at a time.

Also seen: "When is my wedding?" was answered "You got married to Priya on April 29, 2025", read from the `(since 2025-04-29)` label of the partner fact (the known label problem). One note calls Ruben's brother Sem his "friend".

## Ablations (smart, answers raw)

| Run | Smart answers | Against run 1 | Predicted | Reading |
|---|---|---|---|---|
| 1, full | 36 | | | |
| 2, facts only | **17** | **−19** | about −8 | Notes carry most of what smart answers on long histories |
| 3, note window among notes only | 38 | +2 | −1 to +2 | within run noise (2 or less) |
| 4, `about_user` off | 34 | −2 | −2 to −4 | within run noise for answers, but the stored facts show the effect: Tamsin's city went Norwich → Glasgow → Dublin → Bristol → Dublin → **Exeter** (her friend's and her mum's cities) and her job became "senior paramedic" (her wife's); with the check on, all of these were blocked |
| 5, untagged notes | 37 | +1 | −1 to −3 | within run noise |

The baseline gave 47 in every run. Run timings varied (8 to 42 minutes) with the load on the machine; they do not affect results.

## What this means for the project

- **The main hypothesis is rejected on this evidence.** With an 8B model doing the extraction, structured facts are less reliable than the raw messages they come from, and the gap grows with history length instead of shrinking. Smart is better only on prompt size (2.2 against 4.0 lines) and on some past questions.
- **The parts are not useless.** `about_user` keeps other people's lives out of the facts (run 4), notes double what facts alone can answer (run 2), and on the short sets smart never let an outdated value through. But none of this beats giving the model the right four sentences.
- **The likely next design is a hybrid:** the baseline's raw messages as the main memory, with facts used where they are strong (current values, outdated values marked or filtered, allergies) rather than as a replacement. That is a new hypothesis and needs a fresh set.
