# Fixes from set N: development record (2026-10-30)

Set N passed its pre-registered test: hybrid scored 50 against the baseline's 45. Every one of hybrid's 3 losses came from the facts layer ([../set_N/log.md](../set_N/log.md)). This step fixes the causes. It is **development on spent sets** (N, M and L). The honest test is a fresh blind set O, written after these runs.

## The changes

| # | Problem on N | Change | Where |
|---|---|---|---|
| 1 | Every user's `name` was overwritten by someone else's (Lucia, Declan, Malte, then Jonte; Tamsin became Callum on M too). The wrong `name` facts then produced wrong markers (`[outdated: now Jonte]` on "Malte moved to Vienna") | `about_user` gives the user a name only from a self-introduction: "I'm X", "I am X", "call me X", "I go by X", or a message with "my name" in it | `write/actions.py` ([05](../../05_write_path.md), 4.3) |
| 2 | "Moved to Grenoble with Bastien" stored no city. The message has no first-person word, so `about_user` rejected Grenoble | A sentence that opens with moved, started, got, joined, left, quit, began, bought, switched, relocated, transferred, finished or signed counts as first person | `write/actions.py` (4.3) |
| 3 | "I got a job at Pharmavert in Lyon" was rejected as "no change signalled", so the first employer stayed active, and hybrid answered with it | "got a job" / "got the job" is a change word for `works_at` | `write/actions.py` (4.4) |
| 4 | Hybrid showed 2 fact lines, so a list of three languages lost Danish | Every value of the first two kinds of fact that pass the gate, at most 4 lines | `read/hybrid.py` ([06](../../06_read_path.md), 11.1) |
| 5 | A marker named only the new value, so the model could not tell which part of a message changed (M: a bio dropped the still-true name; N: a brother's move looked outdated) | The marker names the old value and its kind: `[outdated: Lives in: Oslo -> now Kristiansand]`, `[no longer true: Works at: Brackwell Consulting]`; the header says the rest of the message may still be true | `read/hybrid_rules.py`, `assistant.py` (11.2) |

## Checks before any run (offline, no model)

- **Name questions still work:** every "What's my name?" question in sets B, C, D, G, H and L has an introduction that passes the new name rule.
- **Implicit subject is narrow:** across every message of sets A to N, it changes the verdict of two messages only, both in N ("Moved to Grenoble with Bastien" and "Bought a second-hand alto saxophone").
- **"got a job" is narrow:** it appears in two messages of all the sets. One is Marisol's. The other, "Priya got a job at the hospital", is still rejected (Priya is a known person, and "in the summer" is a plan).
- **Tests:** 14 more, 288 in all. They cover the name rule on the five set N sentences, the silent subject, "got a job", all three languages shown, `top_relations`, and the new marker format.

## Runs

The write path changed, so each run ingests again (no `--no-ingest`). Cache off, all four modes.

1. `make eval SET=N OUT=docs/results/logs/fixes_N`
2. `make eval SET=M OUT=docs/results/logs/fixes_M`
3. `make eval SET=L OUT=docs/results/logs/fixes_L`

Each long set takes about an hour.

## Predictions (written before the runs)

| Measure | Last run | Prediction |
|---|---|---|
| N: name right at the end (3 users) | 0 of 3 | 3 of 3 |
| N: city, employer, job title, partner right (12 slots) | 10 | 12 (11 to 12) |
| N: baseline | 45 | 45 (±1; the messages are the same) |
| N: smart | 42 | about 44 (41 to 46) |
| **N: hybrid** | 50 | **about 53 (50 to 55)**: likely gains are Marisol's employer, Henrike's languages and her brother's city; possible ones are Marisol's city (the `Lives in: Grenoble` line above messages about Lyon) and the signature or bio; re-ingestion moves facts and notes by about ±2 |
| N: full | 50 | 50 (±2) |
| M: name right (3 users) | 2 of 3 (Tamsin became Callum) | 3 of 3 |
| M: baseline / smart | 46 / 43 | the same (±2) |
| **M: hybrid** | 50 | **about 51 (48 to 53)**: Ruben's bio may come back (labelled marker); Ruben's languages stay wrong (Dutch is never extracted, so there is nothing to show) |
| **L: hybrid** | 28 | 28 (±1) |

**Go to set O** if on N the names are 3 of 3 and the slots at least 11 of 12, hybrid is at least 52 on N, and hybrid loses no more than 2 against its last run on M (50) or L (28). Otherwise report it and rework. A pass is not evidence, because N, M and L are spent. Set O decides.

## Results (2026-10-30)

Outputs (each as `.txt` and `.json`): `fixes_N`, `fixes_M`, `fixes_L`. All three were run, with ingestion and cache off.

| Measure | Last run | Predicted | Found |
|---|---|---|---|
| Name right at the end (N, 3 users) | 0 of 3 | 3 of 3 | **3 of 3** |
| Name right at the end (M, 3 users) | 2 of 3 | 3 of 3 | **3 of 3** |
| N: city, employer, job title, partner (12) | 10 | 12 (11 to 12) | **12** |
| N: baseline | 45 | 45 (±1) | 45 |
| N: smart | 42 | about 44 (41 to 46) | 40 |
| **N: hybrid** | 50 | **about 53 (50 to 55)** | **50** |
| N: hybrid stale in answer | 2 | | **0** |
| N: full | 50 | 50 (±2) | 50 |
| M: baseline / smart | 46 / 43 | the same (±2) | 46 / 42 |
| **M: hybrid** | 50 | about 51 (48 to 53) | 49 |
| L: hybrid | 28 | 28 (±1) | 28 |

**The write-path fixes worked:** every name is now right, and so is every key fact on N. Ruben's Dutch is now extracted on M, so his languages question is right too.

**The go criterion failed:** hybrid needed at least 52 on N and got 50. On N it gained the four answers the fixes aimed at: Marisol's city and employer, Henrike's brother and her three languages. It also lost four:

| Question | Cause |
|---|---|
| Marisol: Where does my sister live now? / What does my sister do? | Fix 4 showed every value of the top kinds: three `family_member` lines (Lucia, dad, and Bastien wrongly filed as family) above the messages. The model said "I don't know" with the sister's messages in the prompt |
| Henrike: Do I still go sailing? | "You don't know." An active `Hobby: dinghy sailing` sat above a message marked `[no longer true: Hobby: sailing]`, under the longer header |
| Kwame: When is my driving test? | The trap: the same lines as the baseline. It was right last time by luck |

On M the losses were similar: "Do I still drink coffee?" got "You don't know." with the same lines as the baseline, so the header is the likely cause, and the music question was answered from a wrong `Hobby: folk music` fact.

**Rework, read path only. Not run on N, M or L. Set O measures it, blind:**

1. Every value is shown only for list kinds of fact (`speaks`, `allergic_to`, `likes`, `dislikes`); other kinds show their best value. This keeps all three languages and drops the extra family names.
2. The short header of the set N run is back. The labelled markers stay.
