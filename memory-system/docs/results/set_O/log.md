# Set O: the final blind test (2026-10-30)

Set O has 3 new users, 283 messages and 57 questions, with the question mix of M and N. The sentences that announce changes were worded unlike N's. It was written after the fixes from set N and frozen with its predictions ([../../predictions/set_O.md](../../predictions/set_O.md)) before any run. It was run once (`full.txt`, `full.json`), with ingestion, cache off, and four modes answering. It ran without a restart and took 58 minutes. **No change after this run is tested again.**

## Result

| Set O, 57 questions | Needed present (54) | Stale in prompt | Stale, marked | Avg lines | Answers, raw = reviewed | Stale in answer |
|---|---|---|---|---|---|---|
| Baseline | 46 | 18 | 0 | 4.0 | **44** | 2 |
| Smart | 42 | 11 | 0 | 2.5 | **39** | 7 |
| **Hybrid** | **50** | 16 | 2 | 5.1 | **47** | 5 |
| Full (whole history) | - | 19 | 0 | 94.3 | **52** | 1 |

**Hand review:** the three hand rules agreed with the keyword score in every mode.

- **Fruit salad:** smart, hybrid and full warn about kiwi; the baseline does not.
- **Barbecue:** smart, hybrid and full warn about mustard; the baseline does not.
- **Dessert:** every mode suggests a gluten-free dessert. The baseline found the gluten-free carrot cake among its four messages.

**Keyword misses, not re-scored (by the rule fixed before the run):**

- Hybrid's "No, you don't go climbing anymore. You mentioned selling all your gear" and "You don't play in an orchestra anymore" are right in substance. The checks look for "not anymore", "sold", "stopped" and similar words, and these answers use none of them.

If both had counted, hybrid would have 49. The pre-registered numbers stay as they are.

## Against the pre-registered hypotheses

| | Rule | Predicted | Found | Verdict |
|---|---|---|---|---|
| **H1 on O: hybrid better than the baseline** | d ≥ +3 | about +4.5, 65% chance | **d = +3** (47 against 44; hybrid only 7, baseline only 4) | **Met, at the threshold** |
| **H1-pooled: N and O together significant** | sign test, p < 0.05 | 55% chance | **15 against 7, p = 0.13** | **Not met** |
| H2: hybrid's outdated answers ≤ the baseline's | | about 1 against 4 | **5 against 2** | **Failed** |
| H3: smart − baseline ≤ −3 | | about −4 | −5 (39 against 44) | Met |
| H4: names 3 of 3, key facts at least 10 of 12 | | 3 of 3, about 10 | names **3 of 3**, key facts **8 of 12** | **Failed** on the key facts |

| Measure | Predicted | Found |
|---|---|---|
| Baseline | about 45 (40 to 49) | 44 |
| Smart | about 41 (36 to 45) | 39 |
| Hybrid | about 49.5 (45 to 53) | 47 |
| Full | about 47 (42 to 52) | 52, the top of the range |

## The write path did not carry over to new wording

| User | Wrong at the end | The message that was missed |
|---|---|---|
| Teodor | employer still Pixelgrad (his first); no partner (Matteo never stored); Ljubljana never stored as a city | "Ondaline in Ljubljana offered me a position and I said yes"; "Next month I start as test lead at Carsolux"; "There's someone new in my life: Matteo"; "First week in Ljubljana done" |
| Amara | city still Cardiff | "We're finally Edinburgh residents!" |
| Lieke | job title still senior copy editor | "From next week I'm a UX writer at Tegelhuis Studio" |

The rules of step 1 and the N fixes are word lists, written after seeing M's and N's sentences. On sentences worded otherwise they mostly kept the old value, which is the safe failure, but still a stale one. The name rule held (3 of 3).

## Where hybrid and the baseline differ

Hybrid only (7):
- **Timelines (2):** Teodor before Ljubljana (`Cluj -> Trieste (now)`) and Lieke before Leiden.
- **Allergy lines (2):** the fruit salad and the barbecue.
- **Same four messages as the baseline (3):** Teodor's brother's job, Lieke's parrot and Amara's cousin's citizenship interview (the trap). The baseline answered "I don't know" each time. These count, but they are model variance, not memory.

Baseline only (4):
- **Teodor: Where do I work now?** `Works at: Pixelgrad` (stale) was on top, and hybrid answered Pixelgrad. An outdated answer.
- **Lieke: What's my job title?** `Job title: senior copy editor` (stale) was on top. An outdated answer.
- **Lieke: Do I still go climbing?** Right in substance, a keyword miss (above).
- **Lieke: Which languages do I speak?** All three languages were stored, but Frisian did not pass the relevance gate, so two lines were shown and two languages answered.

Both wrong (6):
- **Teodor before Trieste:** the timeline lacks Ljubljana, which was never stored.
- **The orchestra:** hybrid's answer is a keyword miss.
- **Amara before Edinburgh:** "I don't know" in both modes.
- **Amara's husband:** both said he teaches maths. He now works as a pharmacist, but the message that says so was not among the four.
- **The signature and the bio:** hybrid's bio used the stale job title.

## The two blind long-history sets together

| N + O, 114 questions | Baseline | Smart | Hybrid | Full |
|---|---|---|---|---|
| Answers right | 89 | 81 | **97** | **102** |
| Outdated value in an answer | 6 | 13 | 7 | 3 |

- **Hybrid beat the baseline on both blind sets** (+5 and +3; 15 against 7 on differing questions). The direction holds; p = 0.13 is not proof. Of the 15 wins that can be traced:
  - 4 are timelines on past questions;
  - 5 are allergy lines on indirect questions;
  - 2 are current values on top;
  - 4 had the same messages as the baseline (model variance).
- **Hybrid's losses are its facts.** 6 of its 7 losses on N and O come from a fact that was wrong, stale or cut by the gate, placed above the right message.
- **Full beat everything** (102 of 114). These histories are about 1,100 tokens per user, small enough for the 8B model to read whole. A memory system has to earn its place on histories longer than the context window, or on cost: full used about 95 lines per question against hybrid's 5.
- **Smart alone lost to the baseline on every long set** (M, N, O).

## What this means for the project

The expected outcome, "better answers than traditional vector memory", is **supported in direction, not proven**. The hybrid design beat plain vector search on two blind sets written before their runs, by +5 and +3, but the combined test is not significant (p = 0.13). The reason it is not larger is clear and measured: the facts layer, built by an 8B model and word-list rules, is not reliable on new wording, and hybrid trusts it. At this history length, putting the whole history in the prompt is better than any memory, so the case for memory rests on longer histories and on prompt size, which these sets do not test.
