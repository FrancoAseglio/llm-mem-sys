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
| 7 | [07_evaluation.md](07_evaluation.md) | How memory is measured, the test sets, the protocol, the results and what they do not prove |
| 8 | [08_findings.md](08_findings.md) | The experiments and mistakes that shaped the design, and the decision log |
| 9 | [09_limits_and_roadmap.md](09_limits_and_roadmap.md) | Everything known to be missing or weak, and what comes next |

Written predictions, made before runs, are kept unchanged in [predictions/](predictions/).

## Quick paths

- **I want to run it:** 02, then `README.md` in the project root.
- **I want to understand it in 30 minutes:** 01, then the flow diagrams at the top of 05 and 06.
- **I want to change a setting:** the settings table in 04, then the tuning table in 06.
- **I want to trust the numbers:** 07, then the limits section of 09.

## Conventions

- Paths are relative to the `memory-system/` folder.
- Commands are run from that folder with `poetry run`.
- "Smart" means this system; "baseline" means plain vector search over past messages; "none" means no memory.
