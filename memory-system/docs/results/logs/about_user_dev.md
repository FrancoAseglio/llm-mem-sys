# Facts about other people: development record (step 1 of the improvement round)

Set L showed that the write path gives the user what a message says about someone else: "My sister Agathe lives in Montreal and works as an airline pilot" became the user's city and job (Montreal replaced Nantes), "it had ended up in Frankfurt" (a suitcase) became `lives_in`, and "my friend Pieter" became `partner` ([../set_L/log.md](../set_L/log.md)). The fix is a pure rule, `about_user` in `write/actions.py` ([05](../../05_write_path.md), section 4.3), applied to asserted `lives_in`, `works_at`, `job_title`, `birthday` and `partner` facts. `ABOUT_USER=0` switches it off.

This is **development on spent sets**. Set L is spent, so its re-run below shows whether the rule does what it was built for, not how well it generalises. Set M measures that.

## Checks before any run (offline, no model)

- The rule was tried on every message of sets A to L against every word their questions need or forbid, for the four self relations. It blocks only values that belong to someone else (a sister's or friend's name, Berlin in "My sister Anna lives in Berlin", Lisbon in "My sister Marta is getting married in Lisbon", Frankfurt) and no city, employer, job or birthday of a user.
- The partner messages of sets C, D, I, K and L were checked. One regression was found and fixed before freezing: set I's "Dario and I split up. I'm with Elena now." had no partner word, so "I'm with", "split up" and "broke up" were added.
- 16 new tests (15 pure, 1 database).

## Predictions (written before the runs)

Runs, cache off so they compare with the noise check (`../regressions/A_to_J_nocache.txt`, `../set_K/rerun_nocache.txt`):

1. Set L re-ingested with the rule (labelled development run).
2. Sets A to J re-ingested with the rule (regression).
3. Set K, sessions (regression).
4. The list of every value the rule rejected, from `memory_events`.

| Measure | Prediction |
|---|---|
| Values rejected on set L | Montreal, airline pilot, Frankfurt, Pieter; 4 to 6 in all, every one about someone else |
| Values rejected on A to J and K | 0 to 4, every one about someone else |
| Set L, smart with summaries | 20 to 21 or 22: the sister's-city question is fixed (about 90%); the job question becomes an abstain about 50% of the time (the sister's note may still bring "pilot"); the suitcase and hiking questions stay wrong (their notes lack the answer) |
| Set L, smart stale in answer | stays 0 or 1 ("Pieter" comes from the note too) |
| Set L, baseline | 28 (unchanged; the rule does not touch messages) |
| Sets A to J, memory-only numbers | identical to the noise check |
| Sets A to J, answers | within noise: 0 to 2 different per mode |
| Set K | identical probe by probe, or 1 different |

The rule is kept if no true user fact is rejected anywhere and no set loses a needed fact. If one is, it is reported here with the message that caused it.

## Results (2026-10-28)

Outputs: `about_user_L.txt` (this folder), `../regressions/A_to_J_about_user.txt`, `../set_K/about_user.txt`. The `.json` files were not kept (each run overwrites `eval_results.json`).

### Values the rule rejected (every eval user)

| User | Relation | Value | Right? |
|---|---|---|---|
| `eval_l_suitcase` | lives_in | Frankfurt | yes: where the suitcase ended up |
| `eval_l_hiking_plan` | partner | Pieter | yes: "my friend Pieter" |
| `eval_l_sister_trap` | lives_in | Montreal | yes: the sister's city |
| `eval_l_sister_trap` | job_title | airline pilot | yes: the sister's job |
| `eval_j_travels` | partner | Joel | harmless: Joel is the user's partner, already stored from "my partner Joel"; this was a repeat from a later message without a partner word ("a trip to Hanoi with Joel" or "because Joel has a project deadline"), so only a duplicate count was lost |

Five rejections, four on set L as predicted, one elsewhere; none removed a fact the user had.

### Set L (development re-run, labelled)

| Set L | Needed | Noise | Stale in prompt | Avg lines | Answers | Stale in answer |
|---|---|---|---|---|---|---|
| Baseline | 28/28 | 3/3 | 5 | 4.0 | 28/30 | 0 |
| Smart, first run | 20/28 | 2/3 | 2 | 1.7 | 20/30 | 1 |
| Smart, with the rule | 20/28 | 2/3 | 2 | 1.6 | **22/30** | 1 |

- **Fixed:** "Which city do I live in?" (Nantes stays active; answer "You live in Nantes") and "What's my job?" (no job stored; answer "I don't know", the sister's note in the prompt did not mislead the model).
- **Needed present did not move, and that is right:** the suitcase question had counted as "needed present" only because the wrong fact `Lives in: Frankfurt` contained the word. Now that line is gone, and the notes still lack Frankfurt.
- **Still wrong, as predicted:** the hiking companion. Pieter is no longer a partner, but the only note says "with Pieter", so the answer is still Pieter (smart's one stale answer). That is the notes layer (a changed plan keeps its first state), not the write path.

### Regression

- **Sets A to J:** every summary line (needed, noise, stale, lines, answers, stale in answer, both modes) is identical to the noise check.
- **Set K:** identical totals (none 2, baseline 16, smart 17; contradictions 0 and 1; stable 2 and 2; indirect 6 and 5) and the same hand-review list.

### Against the predictions

| Prediction | Result |
|---|---|
| 4 to 6 rejections on L, all about someone else | 4, all right |
| 0 to 4 elsewhere, all about someone else | 1, a harmless repeat of the user's real partner |
| L smart 20 to 22 | 22 |
| L stale in answer 0 or 1 | 1 (Pieter, from the note) |
| L baseline 28 | 28 |
| A to J and K within noise | identical |

**Decision: the rule is kept.** It removed every wrong fact it was built for on set L and changed nothing on sets A to K. This shows the rule does what it was built for on the stories that revealed the problem; whether it generalises is for set M.
