# Everyday commands. Run from this folder. `nice` keeps the Mac responsive while the model works.
RUN = nice -n 10 poetry run
ALL = A B C D E F G H I

.PHONY: help test quick set answers fresh lint format

help:
	@echo "make test          unit tests (about 1 s)"
	@echo "make quick         retrieval only, all sets, stored data (seconds, no chat model)"
	@echo "make set S=I       ingest and score one set, retrieval only"
	@echo "make answers S=I   score one set on stored data, with baseline and smart answers"
	@echo "make fresh S=I     as 'answers' but ingest again and ask the model for everything"
	@echo "make lint          ruff check"
	@echo "make format        ruff format"

test:
	poetry run pytest -q

quick:
	$(RUN) python scripts/evaluate.py --set $(ALL) --retrieval-only --no-ingest

set:
	$(RUN) python scripts/evaluate.py --set $(S) --retrieval-only

answers:
	$(RUN) python scripts/evaluate.py --set $(S) --no-ingest

fresh:
	$(RUN) python scripts/evaluate.py --set $(S) --no-cache

lint:
	poetry run ruff check .

format:
	poetry run ruff format .
