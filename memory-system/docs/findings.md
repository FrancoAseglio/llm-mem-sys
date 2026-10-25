# Findings from the retrieval experiments

Short record of the one-off experiments that shaped the current gate. The scripts were removed;
the settings they produced live in `config.py` and `relation_types.routing_hint`.
All numbers are exploratory: sets A-C had been seen when they were measured.

## 1. Embedding format does not help

Compared seven ways of embedding a fact against the question: the stored `relation: value`
text, a natural sentence ("The user lives in Milan."), nomic's `search_query:` /
`search_document:` prefixes, both combined, the raw source message, and max(sentence, message).
None separated relevant from irrelevant facts clearly better than the stored format, so facts
are still embedded as `relation: value`. Relevance had to come from the gate instead.

## 2. Floor + relative window

An absolute similarity threshold alone cannot work: a topical neighbour (lives_in=Rome, 0.50)
can outscore a needed fact in another question (allergic_to=peanuts for "a quick snack", 0.44).
Fitted on set A, checked on B, then C:

- `MIN_RELEVANCE = 0.42`: middle of the 0.40 (must reject) to 0.44 (must accept) window.
  Rests on one example per side, so it is fragile.
- `RELATIVE_WINDOW = 0.08`: feasible range about 0.05 to just under 0.11.
  Removes neighbours that are far below the best match for the same question.

## 3. Relation routing: top-2 with hints

Compare the question with each relation type's text (`name: description` + optional
`routing_hint`) and only let facts of the `ROUTING_TOP_N` best types through. It reuses the
query embedding, so no extra model call. On 30 questions from sets A-C:

| | irrelevant lines / question | needed facts present |
|---|---|---|
| floor + window | 0.70 | 26/26 |
| + routing top-2, no hints | 0.13 | 24/26 |
| + routing top-2, with hints | 0.13 | 26/26 |

Without hints, food questions routed to `likes` instead of `allergic_to` ("a quick snack").
The two hints (`allergic_to`, `dislikes`) were written after seeing those misses, so they are
a design choice, not evidence. Set D was written before routing existed and was run once.

## 4. Known retrieval limits found on set E (not fixed)

- **Top-2 routing vetoes a strong match.** "Which language am I trying to learn?" vs
  `goal = learn Japanese`: raw similarity 0.70, far above the floor, but `goal` ranked 4th
  among relation types, so routing dropped it. The fact was there and matched; routing hid it.
- **Allergy just outside the bypass.** `allergic_to = sesame` (raw 0.42) for a food question:
  `allergic_to` ranked 3rd, so the safety bypass (top-2 only) did not apply and the floor removed it.
- **Proposed fix, NOT implemented:** a strong-match override (a fact with raw similarity of about 0.60
  or more skips routing) and an allergy bypass for routing rank <= 3. It is reserved as a
  pre-registered ablation for a final fresh set, so that set can measure it blind.
