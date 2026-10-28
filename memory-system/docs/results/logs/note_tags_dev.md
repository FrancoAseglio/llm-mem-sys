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

## Results

(filled in after the runs)
