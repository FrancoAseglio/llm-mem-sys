# Predictions before set K (written 2026-10-28, before the runner exists)

Set K (`scripts/evaluation/scenarios/sets/set_k.json`, 6 stories, 44 user turns, 23 scored probes) is the first measure of consistency across turns. It is blind: it is run **once**, in the three modes together, after the runner is built. Nothing below has been checked against data.

Agreed scope (2026-10-28): three measures (no contradiction, stable answers, indirect use); consistency with the assistant's own earlier replies is left out, because replies are not stored.

## Design (frozen before the runner is written)

1. **Stories in sessions.** Each story is a list of sessions, oldest first, each dated N days ago. A session is a list of user turns. A turn may carry a **probe**: the fact it checks, its type (`direct`: asks for the fact; `indirect`: the fact matters but is not asked), `expect` (words the answer must contain) and `forbid` (an outdated or wrong value the answer must not contain).
2. **Runner.** A new script, `scripts/evaluate_sessions.py`; `evaluate.py` is not changed. Per story: a fresh user. For each turn, in order, every mode (`none`, `baseline`, `smart`) recalls its memory lines for the turn's text (`k = 4`, without touching usage counts, as in the evaluation), and the model answers at temperature 0 with **that mode's chat history of the current session** (the last 6 messages, as in the chat). Then the user turn is ingested **once** (the write path does not depend on the mode; replies are never stored), dated on the session's day, one minute after the previous turn. At the end of each session the notes are written and consolidation runs, as configured. Each session starts with an empty history, so between sessions only memory carries anything.
3. **What is kept per probe and mode:** the memory lines, the answer, `correct` (every `expect` group met), `forbid_raw` (a `forbid` word in the answer) and `forbid_in_prompt` (a `forbid` word in the memory lines).
4. **Hand review, rules fixed now.**
   - Every `forbid_raw` hit is read. It is cleared only if the answer uses the word to negate it or explicitly as the past ("you moved from Ljubljana"). Raw and reviewed counts are both reported.
   - The two allergy probes of type `indirect` (the Dijon sandwich and the vinaigrette) are scored by hand for every mode: correct only if the answer warns the user about mustard because of their allergy. Mentioning mustard is not enough, because any vinaigrette recipe mentions it.
5. **Measures.**
   - **Correct:** probes whose answer meets `expect` (23 probes).
   - **Contradictions:** probes with a reviewed `forbid` hit (13 probes have `forbid`). Lower is better.
   - **Stable facts:** a group is the probes of one fact in one story with at least two probes; probes asked before a change carry their own fact name (`city_before`, `employer_before`) and are not in any group. A group is stable when every probe in it is correct and none has a reviewed contradiction. 7 groups.
   - **Indirect use:** correct among the 10 indirect probes. Reported only.
6. **Not included:** any change to the memory system. The configuration is the current one (notes and consolidation on).

## Per probe (probability of a correct answer; in brackets, of a reviewed contradiction)

| Story | Probe | none | baseline | smart |
|---|---|---|---|---|
| k_move | Which city (before the move) | 0% | 95% | 95% |
| k_move | Where do I live these days? | 0% | 80% (10%) | 95% (2%) |
| k_move | Day trip from my city (indirect) | 0% | 55% (30%) | 75% (5%) |
| k_move | Which city am I based in? | 0% | 80% (10%) | 95% (2%) |
| k_move | Neighbourhoods in my city (indirect) | 0% | 60% (25%) | 75% (5%) |
| k_allergy | Ham sandwich with Dijon (indirect, by hand) | 5% | 80% | 85% |
| k_allergy | Vinaigrette tips (indirect, by hand) | 5% | 45% | 75% |
| k_allergy | What am I allergic to? | 0% | 90% | 95% |
| k_job | Email signature (before the change, indirect) | 0% | 85% | 55% |
| k_job | Where do I work now? | 0% | 85% (10%) | 85% (3%) |
| k_job | Email signature (after the change, indirect) | 0% | 70% (20%) | 55% (3%) |
| k_job | Which company am I with? | 0% | 80% (10%) | 85% (3%) |
| k_partner | Birthday message for my partner (indirect) | 0% | 80% (10%) | 80% (5%) |
| k_partner | Partner's name | 0% | 90% (5%) | 95% (3%) |
| k_partner | Gift card with their name (indirect) | 0% | 75% (10%) | 80% (5%) |
| k_same_session | Which city (before the move) | 0% | 95% | 95% |
| k_same_session | So where do I live now? (same session as the move) | 90% | 90% (10%) | 95% (5%) |
| k_same_session | Café near where I live (indirect) | 0% | 65% (30%) | 80% (5%) |
| k_same_session | Which city do I live in? | 0% | 80% (15%) | 95% (3%) |
| k_control | Which languages? | 0% | 90% | 90% |
| k_control | What's my name? | 0% | 70% | 95% |
| k_control | Which languages, reworded | 0% | 85% | 90% |
| k_control | Sign a note with my name (indirect) | 0% | 70% | 85% |

Reasons behind the main numbers:
- **Baseline** recalls the old and the new message side by side after a change. On direct questions the model usually picks the newer one; on indirect ones (a day trip, a café) it often follows the old city. It also says "I don't know" with the name in its lines (5 times in sets A to I).
- **Smart** never reads the replaced city or employer. Its risk is the gate: an indirect question ("write an email signature") may not route to the employer fact, and the vinaigrette question needs the allergy pass.
- **None** knows nothing across sessions; its only expected success is the question asked in the same session as the move, where the chat history holds the answer.

## Totals (the numbers to check)

| Measure | none | baseline | smart |
|---|---|---|---|
| Correct (23) | about 1 (0 to 2) | about 18 (15 to 21) | about 19.5 (17 to 22) |
| Contradictions, reviewed (13 probes) | 0 | about 2 (0 to 5) | about 0.5 (0 to 2) |
| Contradictions, raw | 0 | about 4 | about 1 |
| Stable facts (7) | 0 | about 3 (1 to 5) | about 4.5 (3 to 6) |
| Indirect correct (10) | about 0 | about 7 | about 7.5 |

## Success criteria (set before building)

1. **No contradictions:** smart has at most 1 reviewed contradiction, and fewer than baseline.
2. **Not less correct:** smart's correct count is at least baseline's.
3. **More stable:** smart has more stable facts than baseline.
4. **Sessions are isolated:** `none` gets at most 2 probes correct (otherwise the history leaks between sessions and the test measures nothing).
5. **In-session sanity:** "So where do I live now?" is correct in all three modes.

Reported only: indirect correct, `forbid` words in the prompt, every hand decision with its reason.

A failed criterion is reported as a failure. Expected outcome: 4 and 5 pass; 1 and 3 pass about 65% each; 2 is close to a coin flip, because baseline is strong when a fact never changes and smart may miss indirect questions at the gate. K is spent after its single run.
