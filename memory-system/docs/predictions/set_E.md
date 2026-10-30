# Predictions before set E (written 2026-10-25, before running anything)

> Historical record: written before the run it describes and kept unchanged. File names, paths and numbers may be out of date; see [../README.md](../README.md) for the current docs.

Written after set E was added to `scripts/scenarios.py` and before any of steps 2-5 ran.
Nothing below has been checked against data.

## Step 2: goal extraction (offline check, 10 sentences not in set E)

Sentences:
1. I hope to visit Iceland one day.
2. My plan is to finish my master's degree by next year.
3. I'm trying to lose ten kilos before summer.
4. Someday I'd like to open my own bakery.
5. I'm working towards getting my pilot's licence.
6. I've been saving for a trip around South America.
7. I intend to write a novel.
8. I'm aiming to get promoted to team lead this year.
9. I'd really like to buy an electric car soon.
10. My dream is to climb Kilimanjaro.

- **Before**: 3-5 of 10 become `goal`. The rest come back empty (the rule "ignore temporary
  things" and the lack of any goal example push the model to drop them) or get filed as `likes`/`hobby`.
  Sentences 6 and 9 (saving / buying) are the most likely to be empty, like the boat.
- **Change**: one rule line and one example in the extractor prompt, saying that plans, hopes
  and saving towards something are `goal`. The `goal` description in
  `relation_types` is **not** changed: retrieval embeds that text for routing, so editing it would change
  routing for every question in A-C.
- **After**: 8-10 of 10 become `goal`. Risk: a value that keeps the verb ("run a marathon"
  vs "marathon"), which is fine for keyword checks.

## Step 3: safety bypass

Code only, nothing to predict. Facts are still capped at `k` and sorted by score.

## Step 4: regression on A B C

- `SAFETY_BYPASS=0`: identical to before (A 9/9 1.1, B 7/7 noise 0/2 1.1, C 10/10 noise 2/11 1.3).
  The bypass is a separate branch, so turning it off has to reproduce the old behaviour exactly.
- `SAFETY_BYPASS=1`: set A has no allergy facts, so no change. Allergy facts in B/C:
  - `b_drug_allergy_noise` ("dinner recipe", penicillin 0.35): **changes**. The `allergic_to`
    hint mentions recipes and cooking, so it is expected in the routing top-2, so penicillin is
    added. **B noise goes 0/2 -> 1/2.** This is exactly the case the user wants to stay out,
    and option A cannot keep it out.
  - `b_food_allergy` (peanuts, snack) and `b_correction` (walnuts): already retrieved, no change.
  - `c_rich_profile` restaurant question: shellfish already present, no change. Other C
    questions: `allergic_to` should not be in the top-2, so no change.
  - Expected: exactly 1 question changes (penicillin added). Average lines per question in B goes
    1.1 -> about 1.3.

## Step 5: set E

9 questions need a fact, and all 12 have an avoid list.

| Question | Bypass ON | Bypass OFF |
|---|---|---|
| food: what should I cook | sesame ✓ (rank top-2 through the cooking hint) | sesame likely **missing** (raw ~0.38-0.42) |
| food: snack ideas | sesame ✓ | sesame ✓ (rank 1 through the "snacks" hint, raw ~0.43 like peanuts) |
| food: where do I live / work | ✓, no allergy | ✓ |
| drug: headache | ibuprofen ✓ | ibuprofen ✓ probably (medicine question, raw ~0.45) |
| drug: what should I cook | ibuprofen **added = noise** | clean |
| drug: where do I live | ✓ clean | ✓ clean |
| drug: blood type (abstain) | ibuprofen **probably added = noise** (medical question routes to allergic_to) | clean |
| goals: marathon | ✓ if extracted (goal or hobby) | same |
| goals: Japanese | ✓, possibly stored as `speaks` = Japanese (wrong relation, still passes the keyword check) | same |
| goals: house | uncertain. "big purchase" may route to `likes` rather than `goal`. 50/50 | same |
| goals: cat (abstain) | clean | clean |

Totals, smart mode:
- **ON**: needed 8-9/9, noise 2/12 (the drug profile's cook and blood-type questions).
- **OFF**: needed 7-8/9 (cook question missing), noise 0/12.
- Mushrooms (dislike) are neither needed nor noise. They are expected to show up on the food profile's
  cook question in both modes.
- Baseline: needed about 8/9, noise high (4 lines of mostly filler every time, which often includes
  the profile's other facts).

Net expectation: the bypass buys about +1 needed fact for about +2 noise lines on E. Safety gain
and noise cost are about the same size, which is the trade-off the open question was about.
