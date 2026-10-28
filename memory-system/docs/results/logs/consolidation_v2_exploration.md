# Consolidation version 2: exploration and decision to stop (2026-10-28)

A time-boxed look at whether a second version of consolidation could meet the compression target that version 1 missed on set J ([../set_J/log.md](../set_J/log.md)). Set J is spent, so it was used as a practice set; nothing here is a validated result. No code of the system was changed.

## 1. The idea tested

Version 1 let the model both group notes and write digests, and 14 of its 24 proposed digests cited a single note. Version 2 would let code form the groups and the model only write one digest per group. `scripts/explore_groups.py` (read-only, no model calls) shows the groups code would form: two notes are linked when they share a capitalised name or when the similarity of their stored embeddings is at least `--min-sim`.

## 2. What the groups showed (the J users, notes older than 30 days)

| `--min-sim` | Old notes in groups | Groups |
|---|---|---|
| version 1 (the model grouped) | 19 of 36 | 9 digests |
| 0.75 | 21 of 36 | 9 |
| 0.70 | 29 of 36 | 9, by chaining different stories |

- **Similarity misses obvious topics.** The five kitchen notes of the renovation story are 0.70 to 0.74 apart, under the line; so are the rowing boat notes and the piano notes.
- **Shared names join unrelated episodes.** The Vienna train trip and the Hanoi plan were grouped only because Joel is in both; the band's EP and the festival because Ansel is in both. Place names (Reykjavik, Dolomites, Hanoi) grouped correctly. Code cannot tell a person from a place.
- **A lower threshold chains stories:** at 0.70 the first kitchen note links to the barn notes.

## 3. Why grouping cannot meet the target

Computed from the notes of run 2 (`set_J/on.json`):

| Quantity | Characters |
|---|---|
| The 36 old notes (the ones consolidation may merge) | 2,630 |
| Recent notes (never merged) | 821 |
| Source messages of all notes | 3,133 |

- If **every** old note were grouped and merged at version 1's rate (0.79), summary text in use would be (821 + 0.79 × 2,630) / 3,133 = **0.92** of the source messages. The target was below 0.85.
- Reaching 0.85 needs every old note merged at **0.70** or better.
- The retention rule makes a digest keep every name, number and place, so merging only removes repetition, and these notes repeat little. The largest overhead is elsewhere: 364 of the 2,630 characters (14%) are the "The user …" / "The user's …" / "and their partner" openings, and notes are 1.10 times the length of their messages.

## 4. Decision

Stop consolidation here. Grouping, the step version 2 would improve, is not what limits compression; keeping every detail is. Going further means either shorter notes (a change to the notes layer for every set) or digests that may drop details (which trades answers for length). Both are recorded as options in [../../10_limits_and_roadmap.md](../../10_limits_and_roadmap.md). The next step is consistency across turns.
