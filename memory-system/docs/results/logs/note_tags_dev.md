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

## Results of iteration 2

(filled in after the runs)
