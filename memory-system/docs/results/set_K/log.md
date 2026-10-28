# Set K log: consistency across sessions (2026-10-28)

Predictions and the frozen design: [../../predictions/set_K.md](../../predictions/set_K.md). Raw output: `first_run.txt` (printed) and `first_run.json` (`eval_sessions.json`). Set K was run once, in the three modes together (`make sessions`, 326 s, llama3.1:8b). It is spent.

## 1. Hand review (rules fixed in the predictions)

| Answer | Mode | Rule | Decision |
|---|---|---|---|
| k_move, session 6: "You live in Ljubljana." | baseline | a forbidden word is cleared only if negated or explicitly past | Contradiction, kept |
| k_allergy, Dijon sandwich: "a classic and popular choice … if you enjoy ham and mustard" | none | correct only if it warns about the allergy | Not correct (the keyword had passed it on "mustard") |
| k_allergy, Dijon sandwich: "Considering your allergy to mustard … might not be the best choice" | baseline | same | Correct |
| k_allergy, Dijon sandwich: "Dijon mustard is a type of mustard, and you're allergic to mustard" | smart | same | Correct |
| k_allergy, vinaigrette tips | all three | same | Not correct: no answer warns |

Only one score changed (none, Dijon). The decisions were confirmed by the project owner.

## 2. Results after review

| Measure | none | baseline | smart | Predicted (baseline / smart) |
|---|---|---|---|---|
| Correct (23 probes) | 1 | 16 | 17 | 18 / 19.5 |
| Contradictions (13 probes with forbidden words) | 0 | 1 | 0 | 2 / 0.5 |
| Forbidden word in the memory lines (13) | 0 | 10 | 4 | not predicted |
| Stable facts (7 groups) | 0 | 2 | 2 | 3 / 4.5 |
| Indirect correct (10) | 0 | 6 | 5 | 7 / 7.5 |

| Criterion | Result |
|---|---|
| 1. Smart at most 1 contradiction, fewer than baseline | Passed, by one case (0 against 1) |
| 2. Smart at least as correct as baseline | Passed (17 against 16) |
| 3. Smart more stable than baseline | **Failed** (2 against 2) |
| 4. none at most 2 correct | Passed (1) |
| 5. The same-session question right in every mode | Passed |

Stable facts: baseline kept the same-session city and the languages; smart kept the moved city (k_move) and the partner.

## 3. Why answers failed

**Smart (6 misses).**
- Four are the gate, on questions that do not name the fact: "Sign this note with my name" (only the whaling note passed), the email signature after the job change (only the note passed, no `Works at` line), the vinaigrette (only the knives note; the allergy pass did not fire), "Which languages do I speak?" (French passed, Breton did not: window).
- One is the model: for "Recommend a café near where I live" the prompt held `Lives in: Pärnu`, but the answer declined, because the system prompt says it has no real-time information.
- One is shared by every mode: the signature before the job change (no mode wrote the employer).

**Baseline (7 misses).**
- Three are "I don't know" with the fact among its lines (the partner's name, the user's name twice), as in sets A to I.
- One is the contradiction: its own earlier questions ("Which city do I live in?", "Where do I live these days?") filled its four lines, so the only statement left was the old "I live in Ljubljana".
- The rest are the vinaigrette and the two signatures.

## 4. Observations outside the scores

- **The "since" date misleads the model.** Smart answered "You know French and Breton, which you started learning on March 2, 2026": the `(since 2026-03-02)` label of a fact line was read as when the user started learning. An invented detail that the keyword score counts as correct.
- **Smart replies one turn late after a change.** Facts are stored after the reply, so the reply to "I've moved to Bilbao" was written with `Lives in: Ljubljana` in the prompt ("I don't know anything about your move to Bilbao, as I only knew you lived in Ljubljana"); the same happened after the job change. Not scored.
- **Old names reach smart's lines through notes.** 4 of 13 probes: "The user left Brantley Analytics" (twice) and the note about the colleague Wilhelmina (twice). The model did not use them.
- **Baseline's memory fills with the user's own questions.** Over the sessions, past questions take most of its four lines (k_move, session 6: three of four).
- Every mode opened the first session with "Nice to chat with you again … I remember you", with nothing in memory: the model's habit, also seen in the chat.

## 5. What it shows

Across sessions, with only memory carrying facts, smart and baseline answered about the same (17 and 16 of 23). Smart never gave an outdated or wrong value; baseline did once. One case is not evidence of a difference, and the stability criterion failed. The predictions overrated smart (19.5 correct, 4.5 stable facts). The clearest lesson is where smart loses: the gate drops facts that indirect questions need, which points to routing (roadmap) rather than to memory itself.
