# Notes that skip only what facts hold: development record (step 2 of the improvement round)

On set L two stories got no notes, and three messages were kept by neither layer: cello lessons, learning Finnish and a brother's wedding. The notes prompt said "skip plain personal facts stored elsewhere", and the model applied it to messages from which extraction had stored nothing ([../set_L/log.md](../set_L/log.md)). A changed plan also kept its first state ("with Pieter" after Brigid replaced him).

The change ([07](../../07_summaries.md), section 4.2): each message sent to the notes model is tagged with the facts first stored from it (`[stored: lives_in = Rome]` or `[stored: nothing]`), and the prompt skips only what the tag holds. A third example shows a plan whose companion changes, written in its final state. `NOTE_TAGS=0` restores the old prompt.

This is **development on spent sets**, like step 1 ([about_user_dev.md](about_user_dev.md)). Set M measures it.

## Predictions (written before the runs)

Runs, cache off, compared with the step 1 runs (`about_user_L.txt`, `../regressions/A_to_J_about_user.txt`, `../set_K/about_user.txt`):

| Measure | Reference | Prediction |
|---|---|---|
| Set L, notes written | 17 | 22 to 28 (cello, wedding, Finnish, Frankfurt, the hiking companion) |
| Set L, smart answers | 22/30 | about 24.5 (23 to 26): cello about 70%, Frankfurt about 60%, the wedding about 50%, the hiking companion about 50%, the Finnish "thank you" about 40%; the cat stays wrong (its note is hidden by the stale-source rule) |
| Set L, smart stale in answer | 1 | 0 or 1 (0 if the hiking note is written in its final state) |
| Sets A to J, notes written | 116 | 125 to 150 |
| Sets A to J, smart needed present | as in the reference | same, or 1 to 2 more |
| Sets A to F, smart noise present | 16/46 | 16 to 19 |
| Sets A to J, smart answers (sum) | 117 | 115 to 120 |
| Smart average lines per set | as in the reference | 0 to 0.3 more |
| Set K, smart correct | 17/23 | 16 to 18 (its misses are gate misses that notes do not touch) |
| Baseline, every set | as in the reference | unchanged except run-to-run noise (0 to 1 per set) |

The change is kept if set L gains at least 2 answers, no set loses more than 1 needed fact, smart's answers over A to J fall by at most 2, and smart's noise on A to F rises by at most 3. Otherwise it is reported here and reverted or reworked.

## Iteration 1: tags only (2026-10-28)

Outputs: `note_tags_L.txt`, `../regressions/A_to_J_note_tags.txt`, `../set_K/note_tags.txt`.

| Measure | Reference (step 1) | Predicted | Found |
|---|---|---|---|
| Set L, notes | 17 | 22 to 28 | 26 |
| Set L, smart answers | 22/30 | 23 to 26 | **26/30** |
| Set L, smart stale in answer | 1 | 0 or 1 | 0 |
| Sets A to J, notes | 116 | 125 to 150 | **165** |
| Sets A to F, smart noise present | 16/46 | 16 to 19 | **29/46** |
| Sets A to J, smart answers (sum) | 117 | 115 to 120 | 116 |
| Set K, smart correct | 17/23 | 16 to 18 | **19/23** (stable facts 3/7, indirect 7/10) |

Smart per set, reference then iteration 1 (needed; noise; avg lines; answers): A 9/9, 1.6, 9 then 9/9, 2.0, 9; B 7/7, 1/2, 1.2, 6 then 7/7, 1/2, 1.4, 6; **C** 10/10, 3/11, 1.5, 11 then 10/10, **8/11, 2.5**, 11; **D** 15/16, 7/17, 1.7, 17 then 15/16, **13/17, 2.8**, 17; E 8/9, 3/12, 1.3, 8 then 8/9, 4/12, 1.6, 8; F 7/7, 2/4, 1.8, 7 then 7/7, 3/4, 1.3, 7; G 14/17, 14 then 15/17, 15; H unchanged; I 8/9, 7 then 7/9, 6; J 24/25, 25 then 23/25, 24. Baseline unchanged everywhere.

- **What it fixed on set L:** cello ("The user has started taking cello lessons"), Frankfurt ("The user's suitcase ended up in Frankfurt"), the hiking companion (the note now says "with their cousin Brigid"; no stale answer) and the Finnish "thank you" ("kiitos"). The wedding note reached the prompt, but the model still said "I don't know" (as the baseline does).
- **What it broke: noise.** Without the old list of things to skip, the model wrote **profile notes** that only restate stored facts and bundle several of them: "The user lives in Bologna and works as an architect at Studio Verdi", "The user's partner is Marco and brother's name is Luca", "The user lives in Lisbon with their wife Ines and sister Marta" (also a wrong inference). Such a note matches many questions and carries the other facts with it. The tags did not stop the model writing them.
- **Against the criteria:** set L gained 4 (criterion at least 2: met); no set lost more than 1 needed fact (met; I and J lost 1 each); answers 116 (met); **noise on A to F rose by 13 (criterion at most 3: failed)**. As written in advance, the change is reworked, not kept as is.

## Iteration 2: drop notes that only restate stored facts

The fix is in code, not in the prompt, because the model ignored the tag for these messages. A note is dropped (reason "only stored facts") when **every message it cites is already held by the facts stored from it**: every name in the message is in a stored value, and at least 0.75 of its content words match a stored value or a word that states that kind of fact ("wife", "called" for `partner`; `RELATION_WORDS` in `summaries/rules.py`). 0.75 is the share already used by the faithfulness check; it was not tuned. `only_stored` was checked offline on 22 messages from sets C, D and L before any run: the profile messages count as only stored; cello, the wedding, Finnish, the running "before sunrise", both hiking messages (Pieter is a name no fact holds) and the coffee message do not.

### Predictions for iteration 2 (written before the runs)

Compared with the step 1 reference, with the same criteria as before:

| Measure | Reference (step 1) | Iteration 1 | Prediction |
|---|---|---|---|
| Set L, notes | 17 | 26 | 21 to 26 |
| Set L, smart answers | 22/30 | 26/30 | 25 to 26 (the four fixes come from messages that are not only stored) |
| Sets A to J, notes | 116 | 165 | 120 to 145 |
| Sets A to F, smart noise present | 16/46 | 29/46 | 16 to 20 |
| Sets C and D, smart average lines | 1.5, 1.7 | 2.5, 2.8 | at most 1.9 and 2.1 |
| Sets A to J, smart answers (sum) | 117 | 116 | 115 to 119 |
| Set K, smart correct | 17/23 | 19/23 | 17 to 19 |

## Results of iteration 2 (2026-10-28): run with a bug

Outputs: `note_tags_v2_L.txt`, `../regressions/A_to_J_note_tags_v2.txt`, `../set_K/note_tags_v2.txt`.

| Measure | Reference (step 1) | Iteration 1 | Predicted | Iteration 2 |
|---|---|---|---|---|
| Set L, notes | 17 | 26 | 21 to 26 | 21 |
| Set L, smart answers | 22/30 | 26/30 | 25 to 26 | 26/30 |
| Sets A to J, notes | 116 | 165 | 120 to 145 | 123 |
| Sets A to F, smart noise present | 16/46 | 29/46 | 16 to 20 | **27/46** |
| Sets C and D, smart average lines | 1.5, 1.7 | 2.5, 2.8 | at most 1.9, 2.1 | **2.2, 2.6** |
| Sets A to J, smart answers (sum) | 117 | 116 | 115 to 119 | 115 |
| Set J, smart needed present | 24/25 | 23/25 | | **22/25** |
| Set K, smart correct | 17/23 | 19/23 | 17 to 19 | 18/23 |

**The rule did not run as designed.** `summaries/rules.py` already had a function `_names` (used by the consolidation checks), defined further down the file, and the new helper had the same name, so the old one replaced it. That one counts a mid-sentence "I" as a name, so every message like "My name is Giulia and I live in Bologna" kept its note ("The user lives in Bologna."), and those notes caused most of the noise left in C and D. The tests missed it because each of their messages began with "I". Fixed: the helper is now `_message_names`, with two tests on "... and I live in ...".

Also seen: notes that add a small detail to one stored fact pass by design ("The user plays the guitar in the evenings", "The user likes jazz music a lot", "The user's favourite kind of music is fado"); notes have no routing step, so they reach unrelated questions. Set J lost 2 needed facts against the reference: a renovation question whose cabinet note was worded differently in this run, and a `j_control_mix` question; not diagnosed (the A to J run is not verbose).

### Predictions for iteration 2b (the fix, written before the runs)

| Measure | Iteration 2 | Prediction |
|---|---|---|
| Set L, smart answers | 26/30 | 25 to 26 |
| Sets A to J, notes | 123 | 110 to 125 |
| Sets A to F, smart noise present | 27/46 | 19 to 24: profile notes go, the detail notes stay. The criterion (at most 19) is likely to fail by a few |
| Sets C and D, smart average lines | 2.2, 2.6 | 1.7 to 2.0, 2.0 to 2.3 |
| Sets A to J, smart answers (sum) | 115 | 115 to 119 |
| Set J, smart needed present | 22/25 | 23 or 24 |
| Set K, smart correct | 18/23 | 17 to 19 |

If noise on A to F stays above 19, the trade is set out for a decision rather than kept silently: about 4 more answers on set L and 1 to 2 on set K, against a few more noisy prompts on the rich profiles of C and D.

## Results of iteration 2b (2026-10-28)

Outputs: `note_tags_v2b_L.txt`, `../regressions/A_to_J_note_tags_v2b.txt` (verbose), `../set_K/note_tags_v2b.txt`.

| Measure | Reference (step 1) | Iteration 2 (bug) | Predicted | Iteration 2b |
|---|---|---|---|---|
| Set L, smart answers | 22/30 | 26/30 | 25 to 26 | **26/30** (needed 25/28, stale in answer 0) |
| Set L, notes | 17 | 21 | | 20 |
| Sets A to J, notes | 116 | 123 | 110 to 125 | 108 |
| Sets A to F, smart noise present | 16/46 | 27/46 | 19 to 24 | **27/46** |
| Sets C and D, smart average lines | 1.5, 1.7 | 2.2, 2.6 | 1.7 to 2.0, 2.0 to 2.3 | 2.4, 2.4 |
| Sets A to J, smart answers (sum) | 117 | 115 | 115 to 119 | 115 |
| Set J, smart needed present | 24/25 | 22/25 | 23 or 24 | 23/25 |
| Set K, smart correct | 17/23 | 18/23 | 17 to 19 | 17/23 (stable 2/7) |

- **The profile notes are gone.** D now has 2 notes ("The user plays the guitar in the evenings", "The user's favourite kind of music is fado") and C has 4 ("enjoys running and usually goes out before sunrise", "dislikes coriander", "likes jazz music a lot", "would like to learn how to sail one day").
- **The noise left comes from those few detail notes**, each reaching 5 to 8 unrelated questions, because a note was compared only with other notes: as the best note it passed even next to a much stronger fact. Answers on C and D did not drop (11 and 17).
- **Set I lost 1 answer** ("Who was my partner before Elena?"): the note that used to carry Dario was not written in these runs. That is the archived-value problem (Dario is archived by "split up"), which has its own step. **Set J lost 1** (the kitchen-cabinets question; this run's notes lack the oak cabinets).
- **Against the criteria:** set L +4 (met); needed facts lost at most 1 per set (met); answers 115 (met, at the edge); **noise +11 (failed)**. Decision (2026-10-28): keep the tags and fix the note gate, below.

## Iteration 3: the note window counts the best fact

`select_summaries` measures the window (0.08) from the better of the best note and the best chosen fact (`NOTE_FACT_WINDOW`, on), instead of the best note only ([07](../../07_summaries.md), section 5). No new threshold. This is a read-side change, so it is run on the data stored by iteration 2b (`--no-ingest`): facts and notes are identical, and any difference comes from the window alone. Set K re-ingests by design, so its notes are written again.

### Predictions for iteration 3 (written before the runs)

| Measure | Iteration 2b | Prediction |
|---|---|---|
| Sets A to F, smart noise present | 27/46 | 17 to 22 |
| Sets C and D, smart average lines | 2.4, 2.4 | 1.6 to 1.9 each |
| Set L, smart answers | 26/30 | 24 to 26 (risk: a note close to a strong fact, such as the hiking companion next to the hiking goal, is cut) |
| Set L, smart noise present | 3/3 | 2/3 (the sister's note leaves the city question; the job and season questions have no fact) |
| Sets A to J, smart answers (sum) | 115 | 114 to 118 (risk: story questions whose answer is in a note and whose fact is strong) |
| Sets A to J, smart needed present | as in 2b | the same, or 1 to 2 fewer |
| Set K, smart correct | 17/23 | 16 to 18 |
| Baseline | as in 2b | unchanged except run-to-run noise in its answers |

Kept if noise on A to F falls to 22 or below and set L keeps at least 24 answers and A to J at least 114. Otherwise reported and reworked or reverted.

## Results of iteration 3 (2026-10-28)

Outputs: `note_window_L.txt`, `../regressions/A_to_J_note_window.txt` (verbose), `../set_K/note_window.txt`. Run with `--no-ingest` on the data of iteration 2b, so the facts and notes are the same and every change comes from the window.

| Measure | Iteration 2b | Predicted | Iteration 3 |
|---|---|---|---|
| Sets A to F, smart noise present | 27/46 | 17 to 22 | **19/46** (B 1, C 3, D 10, E 3, F 2) |
| Sets C and D, smart average lines | 2.4, 2.4 | 1.6 to 1.9 each | 1.7, **2.1** |
| Set L, smart answers | 26/30 | 24 to 26 | **26/30** (noise 2/3, stale in prompt 1, 1.5 lines) |
| Sets A to J, smart answers (sum) | 115 | 114 to 118 | **113** |
| Sets A to J, smart stale in prompt | 5 (A 2, B 1, I 1, J 1) | | **0** |
| Set K, smart correct | 17/23 | 16 to 18 | 17/23 (stable 2/7) |

- **Noise is back near the reference** (19 against 16 before step 2) and smart's prompts on A to J no longer hold any outdated value: the stale notes were weak notes riding along with a strong fact.
- **Set J lost 2 answers, for two different reasons:**
  - "When am I going to Hanoi?": `Goal: trip to Hanoi` matches the question strongly, while the answer (the trip moved to February) is in the notes, which now fall outside the window. **A real cost of the rule:** a fact can name the topic without holding the answer.
  - "Who moved to Canada?": "Margit quit the band to move to Canada" had stored `lives_in = Canada` for the user, a wrong fact that `about_user` missed (no subject word before Canada). Before, the Margit note rescued the answer; now the strong wrong fact wins ("You moved to Canada"). **A step 1 gap, exposed.**
- **Against the criteria:** noise 19 (met), set L 26 (met), **A to J 113 (missed by 1)**.

## Iteration 4: `about_user` needs a first-person word

The Canada case is fixed where it starts: a self fact (`lives_in`, `works_at`, `job_title`, `birthday`, `partner`) is rejected when the message has no first-person word at all (I, me, my, we, our ...). [05](../../05_write_path.md), section 4.3. Checked offline before any run: of the 41 statements in sets A to L without a first-person word, none gives the user a fact (they are thanks, other people's news and things: "Margit quit the band", "Turin is lovely in autumn", "Second interview, this time at Orbital Freight"), and the 16 sample sentences of step 1 keep their verdicts. The Hanoi cost is kept and reported; it is not tuned away.

This changes the write path, so everything is ingested again.

### Predictions for iteration 4 (written before the runs)

| Measure | Iteration 3 | Prediction |
|---|---|---|
| Values rejected as "about someone else" (all sets) | 5 (step 1) | 6 to 10, every one about someone else or not a fact about the user; Canada among them |
| Set J, "Who moved to Canada?" | wrong | right (about 80%) |
| Set J, "When am I going to Hanoi?" | wrong | still wrong (about 70%) |
| Sets A to J, smart answers (sum) | 113 | 114 (112 to 116; notes are written again, so run-to-run variation returns) |
| Sets A to F, smart noise present | 19/46 | 17 to 22 |
| Set L, smart answers | 26/30 | 25 to 26 |
| Set K, smart correct | 17/23 | 16 to 18 |

Kept if noise on A to F stays at 22 or below, set L at 24 or more and A to J at 114 or more. If A to J is again 113 because of note variation alone, that is reported as such and step 2 is closed with its trade written down, not tuned further.

## Results of iteration 4 (2026-10-28)

Outputs: `first_person_L.txt`, `../regressions/A_to_J_first_person.txt` (verbose), `../set_K/first_person.txt`. Everything ingested again.

| Measure | Iteration 3 | Predicted | Iteration 4 |
|---|---|---|---|
| Values rejected as "about someone else" | 5 (step 1) | 6 to 10, all right | **7**, all right: the 5 of step 1, Canada ("Margit quit the band to move to Canada") and Orbital Freight ("Second interview, this time at Orbital Freight": an interview, not an employer) |
| Set J, "Who moved to Canada?" | wrong ("You moved to Canada") | right (about 80%) | **still wrong, but no longer a wrong fact**: `lives_in = Canada` is gone, and this run's notes have no Margit-moved-to-Canada note, so the answer is "I don't know" |
| Set J, "When am I going to Hanoi?" | wrong | still wrong | still wrong |
| Sets A to J, smart answers | 113 | about 114 | **113** |
| Sets A to F, smart noise present | 19/46 | 17 to 22 | 19/46 |
| Set L, smart answers | 26/30 | 25 to 26 | 26/30 |
| Set K, smart correct | 17/23 | 16 to 18 | 17/23 |

Every per-question result on A to J is the same as iteration 3 except the Canada question, which went from a wrong answer to "I don't know". As written in advance, A to J at 113 because of note variation closes step 2 with its trade written down; it is not tuned further.

## Step 2 closed: what it changed

Against the step 1 reference (`about_user_L.txt`, `../regressions/A_to_J_about_user.txt`, `../set_K/about_user.txt`), smart memory:

| Measure | Step 1 | Step 2 (iteration 4) |
|---|---|---|
| Set L, answers | 22/30 | **26/30** |
| Set L, needed present | 20/28 | **25/28** |
| Set L, stale in answer | 1 | **0** |
| Sets A to J, answers | 117/133 | 113/133 |
| Sets A to J, needed present | 114/123 | 110/123 |
| Sets A to J, stale in prompt | 7 | **0** |
| Sets A to J, stale in answer | 1 | **0** |
| Sets A to F, noise present | 16/46 | 19/46 |
| Set K, correct | 17/23 | 17/23 |

What it does: messages that facts do not hold (lessons, a pet, a family event, where something ended up, a changed plan) now get notes, and notes never restate facts or ride along with a stronger fact. What it costs: four questions on sets I and J whose answer lives in a note next to a strong fact or in a note that a run did not write:

- "When am I going to Hanoi?" (J): `Goal: trip to Hanoi` sets the window, the date notes fall outside it. **The rule's real cost**, and the pattern long stories will have often (a plan with details that change). To revisit with the gate work (step 3), for example by letting a note through when it is about the same thing as the fact that sets the window.
- "What are my kitchen cabinets?" and "Who moved to Canada?" (J): the notes that held the answer were not written in these runs (note variation).
- "Who was my partner before Elena?" (I): the old partner is archived; the note that carried him was not written. Belongs to the archived-values step.
