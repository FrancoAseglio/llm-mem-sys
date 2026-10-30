# Results

Saved outputs of the evaluation runs, one folder per test set. They are historical records and are never edited. A `.json` file is the full per-question data of a run (`evaluate.py` writes `eval_results.json`, which is copied here), a `.txt` file is the printed output of a run, and a `.md` file is a written record.

| Folder | File | What it is |
|---|---|---|
| `set_G/` | `first_run.json` | set G, first run (smart memory without notes) |
| `set_G/` | `rerun_with_summaries.json` | set G, re-run with notes |
| `set_H/` | `first_run.json` | set H, blind, run once |
| `set_I/` | `first_run.txt` | set I, past questions, mechanism on |
| `set_I/` | `off.txt` | set I control, `PAST_FACTS=0` |
| `set_J/` | `off.json`, `on.json` | set J without and with consolidation |
| `set_J/` | `log.md` | what was run and found for set J |
| `set_K/` | `first_run.txt`, `first_run.json` | set K, consistency across sessions, run once (`evaluate_sessions.py`) |
| `set_K/` | `log.md` | the hand review, results and observations for set K |
| `regressions/` | `A_to_G_after_fix2.json` | sets A to G after the second fix |
| `regressions/` | `A_to_H.txt` | sets A to H with the past rule on |
| `regressions/` | `A_to_I_consolidation.txt` | sets A to I with consolidation on |
| `logs/` | `past_step.md` | the past-question step: runs, diagnosis |
| `logs/` | `summaries_dev.md` | development record of the summaries layer |
| `regressions/` | `A_to_J_nocache.txt` | sets A to J re-run from scratch, cache off (noise check) |
| `set_K/` | `rerun_nocache.txt` | set K re-run, cache off (noise check) |
| `logs/` | `noise_check.md` | the noise check: what changed between runs, and what it shows |
| `logs/` | `consolidation_v2_exploration.md` | grouping notes by code, on set J as a practice set; why consolidation stopped |
| `logs/` | `about_user_dev.md` | the check that drops facts about other people: predictions, development runs on spent sets |
| `logs/` | `note_tags_dev.md` | notes tagged with the facts stored from each message: predictions, development runs |
| `logs/` | `note_tags_L.txt` | set L re-run with tags, iteration 1 (development) |
| `regressions/` | `A_to_J_note_tags.txt` | sets A to J with tags, iteration 1 |
| `set_K/` | `note_tags.txt` | set K with tags, iteration 1 |
| `logs/` | `note_tags_v2_L.txt` | set L, iteration 2 (run with the `_names` bug) |
| `regressions/` | `A_to_J_note_tags_v2.txt` | sets A to J, iteration 2 (bug) |
| `set_K/` | `note_tags_v2.txt` | set K, iteration 2 (bug) |
| `logs/` | `note_tags_v2b_L.txt` | set L, iteration 2b |
| `regressions/` | `A_to_J_note_tags_v2b.txt` | sets A to J, iteration 2b (verbose) |
| `set_K/` | `note_tags_v2b.txt` | set K, iteration 2b |
| `logs/` | `note_window_L.txt` | set L, iteration 3 (note window counts the best fact) |
| `regressions/` | `A_to_J_note_window.txt` | sets A to J, iteration 3 (verbose, `--no-ingest`) |
| `set_K/` | `note_window.txt` | set K, iteration 3 |
| `logs/` | `first_person_L.txt` | set L, iteration 4 (`about_user` needs a first-person word) |
| `regressions/` | `A_to_J_first_person.txt` | sets A to J, iteration 4 (verbose) |
| `set_K/` | `first_person.txt` | set K, iteration 4 |
| `set_M/` | `full`, `facts_only`, `no_fact_window`, `no_about_user`, `no_note_tags` (`.txt`, `.json`) | set M, long histories: the full run and four ablations, run once each |
| `logs/` | `change_rule_dev.md` | current facts that stay right (change rule, name variants, known people): predictions, development runs |
| `logs/` | `change_rule_M`, `change_rule_L` (`.txt`, `.json`) | sets M and L with the change rule, iteration 1 (development) |
| `regressions/` | `A_to_J_change_rule` (`.txt`, `.json`) | sets A to J with the change rule, iteration 1 |
| `set_K/` | `change_rule` (`.txt`, `.json`) | set K with the change rule, iteration 1 |
| `set_M/` | `log.md` | set M: result, causes of every smart loss, the hypothesis, ablations |
| `logs/` | `about_user_L.txt` | set L re-run with the check (development, labelled) |
| `regressions/` | `A_to_J_about_user.txt` | sets A to J re-run with the check, cache off |
| `set_K/` | `about_user.txt` | set K re-run with the check, cache off |
| `set_L/` | `first_run.txt`, `first_run.json` | set L, blind, unseen data, run once (summaries on) |
| `set_L/` | `summaries_off.txt`, `summaries_off.json` | set L, same stored data, `SUMMARIES=0` |
| `set_L/` | `log.md` | set L: results, causes of every smart miss, predictions against results |

## Old names

Records and predictions written earlier mention the old flat file names. They were renamed, not changed:

| Old name | New path |
|---|---|
| `set_G_first_run.json` | `set_G/first_run.json` |
| `set_G_rerun_with_summaries.json` | `set_G/rerun_with_summaries.json` |
| `set_H_first_run.json` | `set_H/first_run.json` |
| `set_I_first_run.txt` | `set_I/first_run.txt` |
| `set_I_off.txt` | `set_I/off.txt` |
| `set_J_log.md` | `set_J/log.md` |
| `set_J_off.json`, `set_J_on.json` | `set_J/off.json`, `set_J/on.json` |
| `after_fix2_A_to_G.json` | `regressions/A_to_G_after_fix2.json` |
| `regress_A_to_H.txt` | `regressions/A_to_H.txt` |
| `regress_A_to_I_consolidation.txt` | `regressions/A_to_I_consolidation.txt` |
| `past_step_log.md` | `logs/past_step.md` |
| `summaries_dev_log.md` | `logs/summaries_dev.md` |

## Naming rule for new runs

`results/set_<X>/<run label>.<json|txt|md>`, for example `set_K/first_run.json`. Runs over several sets go in `regressions/` as `<first>_to_<last>[_label].<ext>`.
