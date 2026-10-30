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

## Results of iteration 1 (2026-10-30)

Outputs (each as `.txt` and `.json`): `change_rule_M`, `change_rule_L`, `../regressions/A_to_J_change_rule`, `../set_K/change_rule`.

| Measure | Reference | Predicted | Found |
|---|---|---|---|
| Set M, smart answers (raw) | 36 | about 40 (38 to 42) | **41** |
| Set M, smart needed present | 36/54 | | 42/54 |
| Set M, smart stale in answer | 5 | 2 or 3 | **2** |
| Set M, baseline | 47 | 47 (±1) | 46 (one bike-count answer flipped: noise) |
| Set M, current-fact slots right (12) | 6 | 10 to 12 | **8 of the 11 visible** (Tamsin's job title did not reach any prompt) |
| Sets A to J, L, K | | the same within noise | smart identical on every question of A to J and on L (26) and K (17); the baseline moved by one question in A and D, in opposite directions |

Fixed on M: Ruben's city and job title, Tamsin's city, both past-city questions, "before Fjordline", and (note variation) the Iceland puffins. Two answers were lost to note variation (the brother's city, the wife's job).

**The criterion (at least 10 current-fact slots) failed**, because the run exposed three mistakes in the word lists, all on M:

| Wrong fact | Message | Mistake |
|---|---|---|
| Solveig's city stayed Oslo | "Fjordline transferred me to **their** office in Kristiansand" | `about_user` counted the possessive "their" as someone else; Kristiansand was extracted and then rejected as "about someone else" |
| Solveig's partner became Jonas | "My sister Ingvild got engaged to her partner Jonas" | the partner check only looked for a partner word, not whose partner it is |
| Tamsin's partner became Callum | "Callum is getting married in Dublin next spring and asked me to give a speech" | the same; Callum opens the sentence, so no subject word stands before him |

The rejections logged (`no change signalled` and `about someone else`) were otherwise all right: other people's cities and jobs, Bristol while still a plan, the house viewing, the commute, "choir member", "home" as a city.

## Iteration 1b: three fixes to `about_user`

1. **Possessives are not subjects:** his, her, their and its no longer mark someone else ("their office", "her name is Odile").
2. **Partners get the clause rule** of cities and jobs, with the partner nouns themselves ignored: "My sister Ingvild got engaged to her partner Jonas" is the sister's partner; "My wife is called Ines" is the user's.
3. **"X is getting married / engaged"** is news about X, unless "X and I" ("Priya and I are getting married").

Checked before any run: the 30 sample sentences of steps 1 and 1b keep their verdicts; the sweep over every message of sets A to M changes only in the right direction (Kristiansand and possessives pass; a sister's and a brother's wedding and Callum no longer give the user a partner); 4 more tests (248).

### Predictions for iteration 1b (written before the runs)

Same runs as iteration 1; M with its `.txt` this time (`make eval` writes both).

| Measure | Iteration 1 | Prediction |
|---|---|---|
| Set M, current-fact slots right (12) | 8 of 11 visible | 11 or 12 |
| Set M, smart answers (raw) | 41 | about 43 (41 to 45): Solveig's city and partner; note variation ±2 |
| Set M, smart stale in answer | 2 | 0 to 2 |
| Set M, baseline | 46 | 46 to 47 |
| Sets A to J, L, K | | the same within noise |

Same criteria as before.

## Results of iteration 1b (2026-10-30)

Outputs (each as `.txt` and `.json`): `change_rule_1b_M`, `change_rule_1b_L`, `../regressions/A_to_J_change_rule_1b`, `../set_K/change_rule_1b`.

| Measure | Iteration 1 | Predicted | Iteration 1b |
|---|---|---|---|
| Set M, current-fact slots right (12) | 8 of 11 visible | 11 or 12 | **12 of 12** |
| Set M, smart answers (raw / reviewed) | 41 | about 43 (41 to 45) | **43 / 43** |
| Set M, smart needed present | 42/54 | | 43/54 |
| Set M, smart stale in answer | 2 | 0 to 2 | **1** |
| Set M, baseline (raw / reviewed) | 46 | 46 to 47 | 46 / 47 |
| Sets A to J, L, K, smart | | the same within noise | identical on every set of A to J; L 26, K 17 |

Head to head on M (reviewed): both right 38, baseline only 8, smart only 5, both wrong 6.

**All criteria met; the changes are kept.**

Every user now ends with the right city (Kristiansand, Bristol, Rotterdam), employer, job title and partner. Smart's remaining losses on M are not current facts: details that the baseline finds word for word and smart's notes lose or do not pass (a brother's move, a daughter's violin, the summer trip, the half-marathon time, a hobby that changed, Kiwibyte's buyer, a husband's job, a bio). Both modes miss Solveig's two past-city questions: smart's past lines are chosen by similarity, not by date, so "before Kristiansand" got Stavanger and "before Oslo" got Oslo (the known gap of the past rule).

## Step 1 closed: what it changed on set M

| Smart on set M | Before step 1 | After step 1 |
|---|---|---|
| Current-fact slots right (12) | 6 | **12** |
| Answers (reviewed, 57) | 36 | **43** |
| Gap to the baseline | −12 | **−4** |
| Stale in answer | 5 | **1** |

Development on a spent set, so not evidence that it generalises; it prepares the facts for step 2, the hybrid read path, which is meant to recover what the baseline still finds and smart does not.
