# Results data

Every evaluation run of the project, as four CSV tables. They replace the per-run `.json` and `.txt` files that used to be in `docs/results/`. Those files are still available at the git tag `raw-results` (`git checkout raw-results -- memory-system/docs/results`), and the conversion was checked against them.

| File | One row per | Rows | From |
|---|---|---|---|
| `runs.csv` | run | 53 | every run, in the order it was made |
| `totals.csv` | run × test set × mode | 384 | the totals of every run: computed from its JSON, or read from the summary printed in its TXT when there was no JSON |
| `answers.csv` | run × question × mode | 4,725 | the 26 runs saved as JSON by `evaluate.py`: every question, its scores, the answer and the memory lines |
| `sessions.csv` | run × probe × mode | 207 | the 3 set K runs saved as JSON by `evaluate_sessions.py` |

The 24 runs that were saved only as printed text (intermediate development iterations and their regressions) have totals but no per-question rows.

## Columns

**runs.csv:** `order`, `run` (the id used in the other tables), `phase`, `description`. The phase is one of:

- `blind`: a test set's first and only run, written before the change it tests;
- `development`: a run on a spent set while changing the system;
- `regression`: re-running the older sets to check nothing broke;
- `ablation`: one switch turned off;
- `noise check`: the same run again, to measure run-to-run variation;
- `rerun`: a labelled re-run of a set.

**totals.csv**

| Column | Meaning |
|---|---|
| `set`, `mode` | the test set (A to O) and the memory mode: `none`, `baseline` (vector search over messages), `smart` (facts and notes), `hybrid` (messages, marked, plus facts), `full` (the whole history) |
| `questions` | questions in the set |
| `correct` / `answered` | right answers / questions with an answer check (raw keyword scores) |
| `needed` / `needed_of` | prompts that contained the words the question needs |
| `noise` / `noise_of` | prompts that contained words that should not be there |
| `stale_in_prompt` | prompts with an outdated value on an unmarked line |
| `stale_marked` | prompts with an outdated value only on lines hybrid marks as old |
| `stale_answer` | answers that contain an outdated value (for set K: contradictions) |
| `avg_lines` | memory lines per question |
| `source` | `json` or `txt` |

**answers.csv:** `run`, `set`, `scenario`, `kind` (what the scenario tests), `qtype`, `question`, `mode`, then 1/0 flags (empty when the question does not test it): `correct`, `needed_present`, `noise_present`, `stale_in_prompt`, `stale_marked`, `stale_in_answer`; then `lines`, `answer` and `memory` (the prompt lines joined with ` || `; empty for `full`, which is the whole history).

`qtype` is filled for the long-history sets M, N and O, from the frozen design of their predictions:

| `qtype` | Questions |
|---|---|
| `change` | a current value after a change |
| `past` | a value that was true before |
| `episode`, `detail` | something that happened, a number |
| `plan` | a plan that changed |
| `other` | other people |
| `indirect` | the fact matters but is not asked: an allergy, a signature, a bio |
| `direct`, `trap`, `abstain` | a plain fact, a question about someone else, a question with no answer in memory |

**sessions.csv:** `run`, `scenario`, `session`, `fact`, `type` (direct or indirect probe), `probe`, `mode`, `correct`, `forbid_in_answer`, `forbid_in_prompt`, `lines`, `answer`, `memory`.

## Notes

- **Scores are raw keyword scores.** Where a set's hand rules changed a count, the log in [../docs/history.md](../docs/history.md) says so. Two runs are affected: the baseline on set M is 48 reviewed against 47 raw (`M_full`), and 47 against 46 (`M_change_rule_1b`). On N and O the hand review agreed with the raw scores.
- **The blind runs that carry the main result** are `M_full`, `N_full` and `O_full`. Everything marked `development` was run on a set that was already spent.
- **New runs** are added by `make eval SET=X RUN=id PHASE=phase` (or `make sessions` for set K). The run's printed output goes to `runs/`, which git ignores, and `scripts/export_results.py` appends the rows here.
