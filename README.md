# LLM long-term memory

A prototype long-term memory for an LLM assistant, running fully on one machine. It remembers
what a user says across conversations, keeps track of facts that change ("I moved to Milan"),
and gives the model only what is relevant to the question. It is measured against plain vector
search over past messages, the usual way assistants remember.

## Result

On two blind test sets (114 questions about users with long, changing histories), the final
design answered more questions than vector search:

| Memory | Right answers |
|---|---|
| Vector search over messages (baseline) | 89 |
| Extracted facts only | 81 |
| **Hybrid: messages, marked when outdated, plus facts** | **97** |
| The whole history in the prompt (reference) | 102 |

The gain met the pre-registered rule on both sets but is not statistically significant
(p = 0.13). Facts work best as annotations on the raw conversation, not as a replacement for it.
Details and limits: [docs/evaluation.md](docs/evaluation.md).

## How it works

- **Three layers** in Postgres: the messages, structured facts extracted from them
  (`lives_in = Milan`, `allergic_to = peanuts`), and one-sentence notes about episodes.
- **Write path:** a local model extracts facts from each message; pure rules check them (is the
  value in the message? is it about the user? is it a real change?). A new value replaces the old
  one, which is kept as history, never overwritten.
- **Read path:** facts pass a relevance gate (similarity floor, relative window, routing by kind),
  so the prompt holds only what matters. The final *hybrid* mode reads the most similar messages
  and labels the outdated ones: `"I've moved to Oslo" [outdated: Lives in: Oslo -> now Kristiansand]`.

More in [docs/design.md](docs/design.md).

## Quick start (Docker)

Everything runs in containers except Ollama, which stays on the Mac: Docker on macOS cannot use
the GPU, and the models would take minutes per answer.

```bash
brew install ollama
brew services start ollama
ollama pull llama3.1:8b
ollama pull nomic-embed-text
make up
```

Then open http://localhost:8000: the dashboard shows every evaluation question with each mode's
memory and answer, and lets you ask stored users new questions. The database starts with the
evaluation users already loaded (`db/snapshot.sql.gz`).

- `make shell` opens a shell in the project container, where every `make` command works.
- `make down` stops the containers and keeps the database; `docker compose down -v` deletes it.
- Postgres is also reachable from the Mac on port 5434 (`DB_PORT` in `.env` changes it).

## Local setup (without Docker)

Needs Python 3.12 with Poetry, Postgres 17 with pgvector, and Ollama with the two models above.

```bash
poetry install --with analysis,dashboard
cp .env.example .env
```

Set `DATABASE_URL` in `.env` to your Postgres database, then create the tables and check that
everything answers:

```bash
make db
poetry run python scripts/smoke_test.py
```

## Everyday commands

`make help` lists them all. The main ones:

| Command | Does |
|---|---|
| `make check` | lint, format check and tests (what CI runs) |
| `make chat` | talk to the assistant with memory (`/mode`, `/facts`, `/quit`) |
| `make dashboard` | the dashboard at http://localhost:8000 |
| `make quick` | retrieval scores on stored data, in seconds |
| `make eval SET=M RUN=id PHASE=development` | a full run of a test set, added to `results/` |
| `make notebook` | re-run the results notebook |
| `make figures` | save the charts as PDFs in `report/figures/` |
| `make snapshot` | save the evaluation users' memory to `db/snapshot.sql.gz` |

## Repository

```
src/memory_system/   the memory: core/ (config, database, models), write/, read/, summaries/
evaluation/          test sets (scenarios/), the runners, scoring, the analysis behind the charts
dashboard/           the local web dashboard (FastAPI)
results/             every evaluation run as CSV tables, with a data dictionary
notebooks/           results.ipynb, the charts
scripts/             chat, score inspector, scenario list, smoke test, database snapshot
db/                  schema.sql and the evaluation snapshot
docs/                design.md and evaluation.md
report/              the project proposal and the report
tests/               unit and database tests, mirroring the packages
```

The detailed development documents, every set's predictions and the full history are kept at the
git tag [`docs-archive`](https://github.com/FrancoAseglio/llm-mem-sys/tree/docs-archive/docs).

## License

[MIT](LICENSE).

## Acknowledgements

Parts of the code, tests and documentation, notably the evaluation tooling, the results notebook,
the dashboard and the Docker setup, were written with the help of Claude (Anthropic), working
from my design and instructions. All experiments were run and checked locally, and the
predictions for every test set were written before its run.
