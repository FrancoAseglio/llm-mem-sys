# Predictions before set I (written 2026-10-26, before any past-question code exists)

Set I (`scripts/scenarios/set_i.py`, 7 scenarios, 12 questions) validates the past-question mechanism.
It is blind: run **once**, after the mechanism is built. Nothing below has been checked against data.
Evidence for the need: set G (`g_past_home`, "Where did I live before Leeds?") fails because
superseded facts are never read.

## Design as approved (frozen before the first run)

1. **Trigger.** A pure rule `is_past_question(query)`: the question contains one of "used to",
   "did I use to", "before", "previously", "formerly", "originally", "in the past", "back then",
   "prior to" (whole words, case-insensitive). English only. Every other question behaves exactly as before.
2. **What is read.** Only facts with status `superseded` (replaced by a newer value, or flipped
   between like and dislike). Not `archived` (the user said it was not true) and not `conflicted`.
3. **Gate.** The same as for active facts: floor 0.42, window 0.08 measured among the superseded
   facts, routing top 2. The allergy bypass does not apply. At most 2 past lines, best raw similarity
   first. A past value equal to an active value of the same relation is skipped.
4. **Prompt.** Past lines come first, then active facts fill `k - len(past)`, then notes fill the
   room left (the stale-source rule for notes is unchanged). Line format:
   `Earlier: Lives in: Bergen (until 2026-09-01)`.
5. **Switch.** `PAST_FACTS=0` turns it off. No new thresholds; nothing tuned on I.
6. **Not included:** changes to extraction, to the gate values, or to the notes layer.

Amendment made before any run on set I: the unit test caught that "What food did I use to dislike?"
(question form, "use to" without the d) did not fire, so "did I use to" was added to the list. This was
found by a test on my own wording, not by running the set.

## Per question (smart with the mechanism; baseline = 4 raw messages)

| Scenario | Question | baseline | smart + past |
|---|---|---|---|
| i_move | Which city did I live in before Tallinn? | present about 90% | present about 85% |
| i_move | Which city do I live in now? (control) | present; old city also present about 85% | present 95%, old city absent about 95% |
| i_job | Where did I work previously? | present about 85% | present about 75% (job extraction risk) |
| i_job | Where do I work now? (control) | present; old employer also present about 80% | present about 90%, old absent about 95% |
| i_two_moves | Where did I live originally? | present about 75% | present about 70% (two past facts, two slots) |
| i_two_moves | Where did I live before Gdansk? | present about 85% | present about 80% |
| i_flip | What food did I use to dislike? | present about 90% | present about 65% (flip must be stored as superseded; line must contain "dislike") |
| i_partner | Who was my partner before Elena? | present about 85% | present about 65% (extraction of "split up, with Elena now" is uncertain) |
| i_partner | Who is my partner? (control) | present; old partner also present about 70% | present about 85%, old absent about 90% |
| i_trap_before | tips for stretching before a run | noise (a location message) about 60% | noise about 10% |
| i_trap_before | cook before my guests arrive | noise about 60% | noise about 10% |
| i_never_moved | Where did I live before? | answers with Leiden about 55% | abstains about 40% (nothing is superseded, but the active city may still reach the prompt) |

## Criteria (smart with the mechanism)

| Measure | Criterion |
|---|---|
| The 6 past questions: needed present | 5/6 or better (expected 4 to 5) |
| The 6 past questions: answers correct | 4/6 or better |
| The 3 present-tense controls: needed present, old value absent | 3/3, 0 stale in prompt |
| The 2 'before' traps: no old city in the prompt | 2/2 |
| The never-moved question | Not a criterion; reported |
| Control run with `PAST_FACTS=0` (retrieval only, no tuning) | past questions needed present 0/6 or 1/6 |
| Sets A to F with the mechanism on | Identical to the current run (needed 56/58, noise 16/46, stale 4, answers 58/61): no question there contains a trigger word |
| Set G with the mechanism on (a labelled re-run) | Only `g_past_home` changes, to needed present (about 80%) |
| Set H | Identical (no trigger word in its questions) |

## Known risks written down in advance

- The trigger is a keyword list: "How long was I at my job before it closed?" would fire, and a past
  question worded another way ("Where was home when I was a student?") would not.
- The 8B extraction may store "Dario and I split up. I'm with Elena now." as one partner fact or none;
  then Dario is never `superseded` and the question cannot be answered. That is an extraction limit,
  not a failure of this mechanism, and will be reported as such.
- `valid_to` is the date of the message that replaced the value, so "until" is exact only if the
  message was dated; the evaluation backdates messages, a live chat uses the current time.
