# Everyday commands. Run from this folder. `nice` keeps the Mac responsive while the model works.
# Variables: SET=I (a set letter, or "A B" for several), SCENARIO=dislike_noise (a scenario id),
# OUT=docs/results/set_M/full (a path without extension: .txt and .json are written next to it).
SHELL := /bin/bash
RUN = nice -n 10 poetry run

.PHONY: help test check format db chat scenarios inspect quick set answers eval sessions

help:
	@echo "SET UP"
	@echo "  make db                     create memory_db and its tables (safe to re-run)"
	@echo "  make chat [U=me]            talk to the assistant with memory (/mode, /facts, /quit)"
	@echo "CODE"
	@echo "  make test                   unit tests (about 1 s)"
	@echo "  make check                  lint, format check and tests; changes nothing (what CI runs)"
	@echo "  make format                 fix lint, format the code, then run check: run before every commit"
	@echo "LOOK"
	@echo "  make scenarios [SET=J]      list the scenarios (their ids), all sets or one"
	@echo "  make inspect SCENARIO=id    how each fact scores and why it was kept or dropped"
	@echo "EVALUATE"
	@echo "  make quick                  retrieval only, every set, stored data (seconds, no chat model)"
	@echo "  make set SET=I              ingest again and score retrieval only (after a write-path change)"
	@echo "  make answers SET=I          stored data, plus baseline and smart answers (cache on)"
	@echo "  make eval SET=M OUT=path    final run: ingest, no cache, verbose; saves OUT.txt and OUT.json"
	@echo "                              [ARGS=--no-ingest] reuses stored data; env switches pass through,"
	@echo "                              e.g. SUMMARIES=0 make eval SET=M OUT=... ARGS=--no-ingest"
	@echo "  make sessions [OUT=path]    consistency across sessions (set K), every mode, no cache"

test:
	poetry run pytest -q

check:
	poetry run ruff check .
	poetry run ruff format --check .
	poetry run pytest -q

format:
	poetry run ruff check --fix .
	poetry run ruff format .
	$(MAKE) check

db:
	createdb memory_db 2>/dev/null || true
	psql memory_db -q -f schema.sql

chat:
	poetry run python scripts/chat.py --user $(if $(U),$(U),me)

scenarios:
	poetry run python scripts/list_scenarios.py $(if $(SET),--set $(SET),)

inspect:
	@test -n "$(SCENARIO)" || { echo "usage: make inspect SCENARIO=dislike_noise  (ids: make scenarios)"; exit 1; }
	poetry run python scripts/inspect_scores.py --scenario $(SCENARIO)

quick:
	$(RUN) python scripts/evaluate.py --retrieval-only --no-ingest

set:
	@test -n "$(SET)" || { echo "usage: make set SET=I"; exit 1; }
	$(RUN) python scripts/evaluate.py --set $(SET) --retrieval-only

answers:
	@test -n "$(SET)" || { echo "usage: make answers SET=I"; exit 1; }
	$(RUN) python scripts/evaluate.py --set $(SET) --no-ingest

eval:
	@test -n "$(SET)" -a -n "$(OUT)" || { echo "usage: make eval SET=M OUT=docs/results/set_M/full [ARGS=--no-ingest]"; exit 1; }
	@mkdir -p $(dir $(OUT))
	set -o pipefail; NO_COLOR=1 $(RUN) python scripts/evaluate.py --set $(SET) --no-cache --verbose $(ARGS) | tee $(OUT).txt
	cp eval_results.json $(OUT).json

sessions:
	@$(if $(OUT),mkdir -p $(dir $(OUT)),true)
	set -o pipefail; NO_COLOR=1 $(RUN) python scripts/evaluate_sessions.py --no-cache --verbose $(if $(SCENARIO),--only $(SCENARIO),) $(if $(OUT),| tee $(OUT).txt,)
	$(if $(OUT),cp eval_sessions.json $(OUT).json,)
