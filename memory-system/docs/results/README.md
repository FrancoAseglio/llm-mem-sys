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
| `regressions/` | `A_to_G_after_fix2.json` | sets A to G after the second fix |
| `regressions/` | `A_to_H.txt` | sets A to H with the past rule on |
| `regressions/` | `A_to_I_consolidation.txt` | sets A to I with consolidation on |
| `logs/` | `past_step.md` | the past-question step: runs, diagnosis |
| `logs/` | `summaries_dev.md` | development record of the summaries layer |

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
