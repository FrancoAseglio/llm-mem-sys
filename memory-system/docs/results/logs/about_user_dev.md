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

## Results

(filled in after the runs)
