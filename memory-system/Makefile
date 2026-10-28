# Everyday commands. Run from this folder. `nice` keeps the Mac responsive while the model works.
# Variables: SET=I (a set letter, or "A B" for several), SCENARIO=dislike_noise (a scenario id).
RUN = nice -n 10 poetry run

.PHONY: help test check format scenarios inspect quick set answers fresh sessions

help:
	@echo "CODE"
	@echo "  make test                   unit tests (about 1 s)"
	@echo "  make check                  lint, format check and tests; changes nothing"
	@echo "  make format                 fix lint, format the code, then run check: run before every commit"
	@echo "LOOK"
	@echo "  make scenarios [SET=J]      list the scenarios (their ids), all sets or one"
	@echo "  make inspect SCENARIO=id    how each fact scores and why it was kept or dropped"
	@echo "EVALUATE"
	@echo "  make quick                  retrieval only, every set, stored data (seconds, no chat model)"
	@echo "  make set SET=I              ingest again and score retrieval only"
	@echo "  make answers SET=I          stored data, plus baseline and smart answers"
	@echo "  make fresh SET=I            as answers but ingest again and ignore the cache: final runs"
	@echo "  make sessions [SCENARIO=id] consistency across sessions (set K), every mode, with answers"

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

fresh:
	@test -n "$(SET)" || { echo "usage: make fresh SET=I"; exit 1; }
	$(RUN) python scripts/evaluate.py --set $(SET) --no-cache

sessions:
	$(RUN) python scripts/evaluate_sessions.py $(if $(SCENARIO),--only $(SCENARIO),) --verbose
