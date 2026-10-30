# Set N: the blind test of the hybrid read path (2026-10-30)

Set N has 3 new users, 283 messages and 57 questions, with the question mix of set M. It was written after the hybrid step and frozen with its predictions ([../../predictions/set_N.md](../../predictions/set_N.md)) before any run. It was run once (`full.txt`, `full.json`), with ingestion, cache off, and four modes answering. It ran without a restart and took 61 minutes.

## Result

| Set N, 57 questions | Needed present (54) | Stale in prompt | Stale, marked | Avg lines | Answers, raw | Answers, reviewed | Stale in answer |
|---|---|---|---|---|---|---|---|
| Baseline | 46 | 18 | 0 | 4.0 | 45 | **45** | 4 |
| Smart | 44 | 10 | 0 | 2.5 | 42 | **42** | 6 |
| **Hybrid** | **52** | 13 | 5 | 5.2 | 50 | **50** | **2** |
| Full (whole history) | - | 19 | 0 | 94.3 | 50 | **50** | 2 |

**Hand review.** The three hand rules (tree nuts, sesame, lactose) agreed with the keyword score in every mode, so reviewed = raw:

- **Cookies:** smart and hybrid warn about tree nuts; the baseline and full give generic advice.
- **Takeaway:** smart, hybrid and full warn about sesame; the baseline does not.
- **Dessert:** smart and hybrid suggest lactose-free desserts. Full suggests a strudel with oat milk, "lactose-friendly", which counts because it mentions the intolerance. The baseline suggests tiramisu.

## Against the pre-registered hypotheses

| | Rule | Predicted | Found | Verdict |
|---|---|---|---|---|
| **H1: hybrid better than the baseline** | d = hybrid − baseline ≥ +3 | d about +3 (0 to +6), 50% chance of +3 or more | **d = +5** (50 against 45) | **Met by the pre-registered rule. Not statistically significant:** hybrid only right on 8, baseline only on 3, sign test p of about 0.23 |
| H2: hybrid's outdated answers ≤ the baseline's | | hybrid about 2, baseline about 4 | 2 against 4 | **Met** |
| H3 (replication of M): smart − baseline ≤ −3 | | about −3 | −3 (42 against 45; smart only 8, baseline only 11) | **Met:** smart alone is still worse than vector search |

| Measure | Predicted | Found |
|---|---|---|
| Baseline | about 44 (39 to 48) | 45 |
| Smart | about 41 (36 to 45) | 42 |
| Hybrid | about 46.7 (42 to 50) | 50, the top of the range |
| Full | about 42 (37 to 47), "below the baseline, as on M" | **50, wrong**: equal to hybrid |
| Stale in prompt (baseline / smart / hybrid) | 15 / 5 / 10 | 18 / 10 / 13 |
| Stale, marked | about 5 | 5 |
| Average lines (smart / hybrid) | 2.1 / 5.2 | 2.5 / 5.2 |

## Where hybrid and the baseline differ

The 8 questions only hybrid answered:

| Question | Baseline's answer | What did it for hybrid |
|---|---|---|
| Marisol: Which city did I live in before Lyon? | "I don't know." | timeline `Valencia -> Lyon (now)` |
| Kwame: Where did I live before Manchester? | "I don't know." | timeline `Leeds -> Manchester (now)` |
| Henrike: Where do I work? | Elbquill Press (old) | fact line `Works at: Harbourlight Games` |
| Henrike: What's my job title? | senior editor (old) | fact line `Job title: narrative designer` |
| Marisol: cookies (hand) | generic advice | the allergy line (allergy pass) |
| Kwame: takeaway (hand) | generic advice | the allergy line |
| Henrike: dessert (hand) | tiramisu | the intolerance line (`Allergic to: lactose`) |
| Kwame: When is my driving test? (trap) | "I don't know." | none: the same four messages as the baseline. Counts as noise |

The 3 questions only the baseline answered. **All three were lost because the facts layer was wrong or cut short**, and the model trusted it over the messages:

| Question | Cause |
|---|---|
| Marisol: Where do I work now? | The active fact was still `Works at: Clinica Albereda`, her first employer: Pharmavert was never stored, so nothing replaced it. Hybrid answered from that line, although the message below said "I'm starting at Alpenmed". Smart was right through its notes |
| Henrike: Which languages do I speak? | Three `speaks` facts were stored and right, but hybrid shows at most 2 fact lines, so Danish was cut. The model answered "English and German" from the facts, although the message below names all three. **A design flaw, not an extraction error:** the cap of 2 splits a multi-valued answer |
| Henrike: Where does my brother live now? | The message "Malte moved to Vienna" was marked `[outdated: now Jonte]`. From that message the extractor had stored `name = Malte`, the brother's name as hers, and a later message replaced it with `name = Jonte`, her partner's. The wrong marker made the right message look outdated, and the model said "I don't know" |

Both wrong (4): Marisol's city, Kwame's car breakdowns, Kwame's signature, Henrike's bio.

- **Marisol's city:** every mode but full answered Lyon. The fact stayed `Lives in: Lyon`, because "Moved to Grenoble with Bastien" stored no city, and the baseline's four lines held only Lyon messages.
- **Car breakdowns:** smart and full counted two; the baseline listed both breakdowns but hedged; hybrid said "I don't know" with both in its lines.
- **Signature and bio:** asked "for me", the model said it did not know the name, or wrote a bio without it. In hybrid, Kwame's introduction carried four markers, one of them wrong (`[outdated: now Declan]`).

## The write path on fresh data

The step 1 fixes were developed on M, where the current facts reached 12 of 12. On N:

| Slot (city, employer, job title, partner) | Marisol | Kwame | Henrike |
|---|---|---|---|
| Right at the end | 2 of 4 (city stuck at Lyon, employer stuck at Clinica Albereda) | 4 of 4 | 4 of 4 (city `Altona`, a district of Hamburg; it went Kiel → Hamburg → Ottensen → Altona) |

That is 10 of 12, against 12 of 12 on the development set.

**A new error in every user: `name` is overwritten by other people's names.** Marisol became Lucia (her sister), Kwame became Declan (his friend), and Henrike became Malte, then Jonte. `name` is single-valued, and neither `about_user` nor the change rule covers it. In hybrid these errors become wrong markers (`[outdated: now Declan]` on "Hi, I'm Kwame"). That cost one answer here, and may explain the "I don't know your name" signatures.

## Full is not consistently below the baseline

On M, full scored 44 against the baseline's 46. On N it scored 50 against 45, level with hybrid. Over the two sets it is about level with the baseline (94 against 91) and below hybrid (94 against 100). On these histories (about 1,100 tokens per user), the 8B model can use everything about as well as it uses four chosen messages. Full has no way to tell old values from new apart from the dates. It answered Marisol's city right, the one question every other mode missed, but it said "I don't know" on her partner and her cookies. Full does not scale; it is a ceiling for this history length only.

## What this means

- **The project's expected outcome is met on its pre-registered test, narrowly and not significantly.** Hybrid answered 50 of 57 against the baseline's 45. The rule fixed before the run (+3) is passed; the sign test (8 against 3, p of about 0.23) is not significant. Taken with the development result on M (+4, also not significant), hybrid has beaten the baseline on both long-history sets it has seen. Each set is too small to prove it alone.
- **What helps is now clear.** All 7 gains that can be explained come from facts used where they are strong: timelines for past questions (2), current values on top (2), and allergies and intolerances on indirect questions (3).
- **What hurts is also clear.** All 3 losses come from the facts layer: a stale employer that was never replaced, the 2-line cap cutting a list, and a wrong marker from a corrupted `name`. Hybrid is only as good as its facts, and the facts still go wrong on fresh data.
- **Smart alone is worse than vector memory again** (H3, −3). The original hypothesis stays rejected; the hybrid one is supported.
- **Fixes the data suggests**, none of them made: keep `name` to first-person introductions; show every value of a multi-valued relation that passes the gate (or none); drop a marker whose new value is a different kind of thing. N is now spent, so any of these is development and needs a new blind set.
