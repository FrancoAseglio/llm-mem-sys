# Documentation

Prototype long-term memory for an LLM assistant. These documents explain what the system is, how each part works, how it was measured, and where it falls short. They describe the code as it is now.

## Reading order

| # | Document | Read it to learn |
|---|---|---|
| 1 | [01_overview.md](01_overview.md) | The problem, the design in one page, the vocabulary, the current status and results |
| 2 | [02_setup.md](02_setup.md) | How to install and run everything on a Mac, and how to fix common problems |
| 3 | [03_storage.md](03_storage.md) | The database: tables, fact statuses, constraints, handy queries |
| 4 | [04_models.md](04_models.md) | How the code talks to the local models and the database, and every tunable setting |
| 5 | [05_write_path.md](05_write_path.md) | What happens when the user says something: extraction, checks, updates |
| 6 | [06_read_path.md](06_read_path.md) | What happens when the user asks something: the relevance gate, ranking, the prompt |
| 7 | [07_summaries.md](07_summaries.md) | The summaries layer: episode notes written after the facts and read after them, the faithfulness check, consolidation into digests, results and gaps |
| 8 | [08_evaluation.md](08_evaluation.md) | How memory is measured, the test sets, the protocol, the results and what they do not prove |
| 9 | [09_findings.md](09_findings.md) | The experiments and mistakes that shaped the design, and the decision log |
| 10 | [10_limits_and_roadmap.md](10_limits_and_roadmap.md) | Everything known to be missing or weak, and what comes next |

Written predictions, made before runs, are kept unchanged in [predictions/](predictions/README.md). The predictions and the files in [results/](results/README.md) are historical records: the file paths they mention are those of the time, before the package was split into `core/`, `write/`, `read/` and `summaries/` ([01_overview.md](01_overview.md), code map).

## Quick paths

- **I want to run it:** 02, then `README.md` in the project root.
- **I want to understand it in 30 minutes:** 01, then the flow diagrams at the top of 05 and 06.
- **I want to change a setting:** the settings table in 04, then the tuning table in 06.
- **I want to trust the numbers:** 08, then the limits section of 10.
- **I want to know how history is kept:** 07.

## Conventions

- Paths are relative to the `memory-system/` folder.
- Commands are run from that folder with `poetry run`.
- "Smart" means this system's facts and notes; "baseline" means plain vector search over past messages; "hybrid" means the baseline's messages, marked when outdated, plus a few facts; "full" means the whole history in the prompt (a reference ceiling); "none" means no memory.
