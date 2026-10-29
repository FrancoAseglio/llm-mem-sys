# Current facts that stay right: development record (step 1 of the hybrid plan, 2026-10-29)

Set M showed that on long histories smart's current facts go wrong: 6 of 12 current-fact slots were right at the end (city, employer, job title and partner for three users; every city and every job title wrong). The causes: passing mentions replaced single values ("I now commute to Utrecht", a house viewing, a friend's wedding city, "Peatline has no office" as a job title), one employer was split in two by a name variant, a wife's new job became the user's, and a transfer to another city stored no city ([../set_M/log.md](../set_M/log.md)).

The changes ([05](../../05_write_path.md), sections 4.3 and 4.4):

1. **Change rule** (`signals_change`, switch `CHANGE_RULE`): a new city, employer, job title or partner replaces an active one only if the message says it changed (change words, not only a plan).
2. **Name variants** (`same_name`): one name containing the other is the same value, for duplicates and retractions.
3. **Known people**: stored partner and family names count as someone else in `about_user`.
4. **One extraction prompt line**: "my company transferred me to their office in X" means `lives_in = X`.

This is **development on spent sets** (M and L are spent). It prepares the facts for step 2, the hybrid read path; the honest test is a fresh set N.

## Checks before any run (offline, no model)

- Every replacement of a city, employer, job title or partner actually stored in the verbose runs of sets A to J, L and M (`../regressions/A_to_J_first_person.txt`, `first_person_L.txt`, `../set_M/full.txt`) was replayed through the rule. First version: it blocked all seven wrong replacements on M (the choir as a job, Callum's Dublin, Priya's hospital, Bristol while still a plan, "no office", the house viewing, the commute) and two right ones on sets C and F ("started a new position at Delta Labs", "I switched employers, I'm at Riverside Clinic now"). "New position", "switched" and "I'm at" were added before freezing; the replay then blocks only the seven wrong ones and keeps every real move, job change and new partner of sets A to M.
- On that replay, M's current facts would be 11 of 12; the twelfth (Kristiansand) depends on the new prompt line.
- 20 new tests (244 in all), including two database tests.

## Predictions (written before the runs)

Runs, cache off, with the new `make` targets:

1. `make eval SET=M OUT=docs/results/logs/change_rule_M` (development, labelled)
2. `make eval SET=L OUT=docs/results/logs/change_rule_L`
3. `make eval SET="A B C D E F G H I J" OUT=docs/results/regressions/A_to_J_change_rule`
4. `make sessions OUT=docs/results/set_K/change_rule`

| Measure | Reference | Prediction |
|---|---|---|
| Set M, current-fact slots right (12) | 6 | 10 to 12 (11 most likely; Kristiansand about 50%) |
| Set M, smart answers (57, raw) | 36 | about 40 (38 to 42): the three cities, Ruben's job title, "before Fjordline", Tamsin's city questions; the bio and the music question may stay wrong for other reasons |
| Set M, smart stale in answer | 5 | 2 or 3 |
| Set M, baseline | 47 | 47 (±1, noise) |
| Rejections "no change signalled" | | about 7 on M, every one wrong as a replacement; 0 to 2 elsewhere |
| Sets A to J, L, K | as in the step 2 runs | the same within noise (±2 per set and mode); the prompt line can change a few extractions anywhere |

Kept if M's current-fact slots reach at least 10, no set loses more than 1 needed fact, and no rejection drops a true change. Otherwise reported and reworked.

## Results

(filled in after the runs)
