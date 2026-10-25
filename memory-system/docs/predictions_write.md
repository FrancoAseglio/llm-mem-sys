# Predictions for the write-path fixes (written 2026-10-25, before any code change)

Written before steps 2-5 ran. Nothing below has been checked against data. The retrieval gate
(`retrieve.py`, config thresholds) is frozen; sets A-E are spent and nothing will be tuned on them.

Known bugs this work targets:
(a) "I'm not allergic to peanuts, I'm allergic to walnuts" leaves peanuts active.
(b) Junk values not in the message ("new job" from "...a new position at Delta Labs!").
(c) After an employer change the old `job_title` stays active.
(d) The `conflicted` status is never used.

## Fix 1: retraction (`action: "retract"`)

**Will solve**
- (a) when the extractor emits `retract allergic_to=peanuts` and the stored value matches.
  The fact is archived (kept, `valid_to` set) and a `retract` event is logged.
- Any "not X, but Y" or "I no longer X" on a multi-valued relation, where nothing used to
  remove X.

**Will not solve**
- Depends on the 8B model setting `action` correctly. I expect it to do so on explicit
  "I'm not X" wording most of the time, but not for every phrasing ("scratch that", "turns out...").
- Matching uses the existing check (exact, or trigram similarity >= 0.8). Singular/plural
  pairs fall below 0.8 (`peanut` vs `peanuts` is about 0.67), so `retract peanut` will **miss**
  a stored `peanuts`. The miss is logged as a `retract` event with no fact id.
- Risk of the opposite error: negative-sounding assertions ("I can't stand olives",
  "I really dislike mushrooms", "I can't eat gluten at all") may be emitted as retractions.
  A retraction with no matching fact stores nothing, so that dislike/intolerance would be **lost**.
  I expect 0-2 such losses across A-E.
- Corrections that span two messages ("No, I meant Rome") are still not handled.

## Fix 2: grounding check

Rule: reject a value unless it shares a content word (4+ letters, not a stopword) with the
message. Words match if one is a prefix of the other or they share the first 5 letters
(walnut/walnuts, sail/sailing, anchovy/anchovies).

**Will solve**
- Values made only of words absent from the message, e.g. `job_title = new job` from
  "...a new position at Delta Labs!".
- Also `job_title = new job` in A `job_change`, even though "new job" is in that message,
  because "new" and "job" are under 4 letters, so the value has no content word at all.

**Will not solve / will break**
- Junk built from message words passes: `job_title = new position`, `works_at = Delta Labs employee`.
- Short values are always rejected: names like Max, Eva, Leo; `egg`, `tea`, `art`. None of the
  values stored today in A-E is under 4 letters (`eggs`, `Ines`, `Luca`, `Anna`, `Rome`, `fado` are
  all 4+), so I expect no loss in A-E. This is a real cost for future data.
- Legitimate normalisation is rejected: "I'm a dev" -> `software developer`, "born 3/3" -> `March 3`.

## Fix 3: likes/dislikes contradiction

**Will solve**: `likes=X` arriving when `dislikes=X` is active (same exact/trigram check), and
the reverse. The newer one wins, the old one is superseded, and a `contradiction` event is logged.

**Will not solve**: near-miss wording (`jazz` vs `jazz music`), cross-relation clashes
(`hobby=running` vs `dislikes=running`), or a dislike phrased as a retraction of a like
(that goes through fix 1 instead). No A-E scenario has a likes/dislikes overlap, so **no A-E change**.

## Fix 4: `conflicted` job title on employer change

**Will solve**: (c) and (d). When `works_at` is replaced (or retracted) and the same message
sets no `job_title`, the active `job_title` becomes `conflicted`. Retrieval reads only
`status='active'`, so it disappears from prompts. A later `job_title` supersedes it through the
normal path.

**Will not solve / side effects**
- "What's my job title?" after a job change now gets nothing (abstain) instead of a possibly
  stale title. That is the intended trade, but it loses titles that did survive the move.
- If the message contains a junk `job_title` that passes grounding, the old title is
  superseded by junk, not conflicted.
- Only `works_at` -> `job_title`. Other dependencies (moving city -> `works_at`) are untouched.

## Expected changes in stored facts, A-E re-ingest

Some drift from the changed extractor prompt (new field, new rule, new example) is expected:
0-3 wording differences elsewhere (e.g. `jazz music` vs `jazz`).

| Scenario | Before | Expected after |
|---|---|---|
| A `job_change` | `job_title=new job` active, `software engineer` superseded | `new job` **rejected** (not stored), `software engineer` **conflicted** |
| B `b_correction` | `peanuts` and `walnuts` both active | `peanuts` **archived**, `walnuts` active (about 70%: needs the retract and a matching value) |
| C `c_new_job` | `designer` active | `designer` **conflicted** |
| D `d_job_switch` | `data analyst` superseded by `accountant` | unchanged. If the model also emits `retract works_at=Bluefin`, Bluefin is archived instead of superseded |
| A `past_tense_trap` | only `lives_in=Milan` | unchanged (a `retract lives_in=Turin` would match nothing) |
| any dislike/intolerance (A `dislike_noise`, B `b_indirect_dislike`, C coriander, D anchovies/gluten, E mushrooms) | stored | stored. Small risk (0-2) of being lost as a mis-labelled retraction |
| everything else | | unchanged |

## Expected changes in A-E retrieval results (retrieval only)

- B `b_correction` "Which nuts am I allergic to?": stale `peanut` **leaves the prompt**
  (B "stale in prompt" goes down by 1), still needs `walnut` ✓.
- A `job_change` "Where do I work?": if `new job` used to reach the prompt, one line fewer.
  Needed (globex) and stale (acme) unchanged.
- C `c_new_job` "Where do I work?": `designer` can no longer reach the prompt. Needed ✓ and noise
  ✓ unchanged; lines may go down by 1.
- All other questions: identical.

---

# Predictions for set F (written after the A-E re-ingest, before running F)

What the A-E re-ingest showed, which shapes these numbers: in `b_correction` the model labelled
**both** halves of "not peanuts, walnuts" as `retract`, so peanuts was archived but walnuts was
**never stored**. Over-retraction of the asserted half is the main risk. I had predicted the risk for
dislikes, not for the second half of a correction.

| Scenario | Expected stored facts | Confidence | Main risk |
|---|---|---|---|
| `f_correction_allergy` ("latex is fine for me, it's pollen I'm allergic to") | latex `archived`, pollen `active` | latex archived ~50% (no "not" in the sentence); pollen active ~55% | pollen emitted as retract and lost (as walnuts was); or latex left active |
| `f_no_longer_hobby` ("I don't play chess anymore; ... my hobby is pottery") | chess `archived`, pottery `active` | chess archived ~70%; pottery active ~65% | pottery labelled retract; "playing chess" vs "chess" wording misses the 0.8 trigram match |
| `f_vague_promotion` ("finally got the promotion") | teacher `active`, nothing new | ~35% | model invents a title. "manager"/"senior teacher" -> **rejected** by grounding (logged). "promotion"/"promoted" -> **passes** grounding and supersedes teacher. I give: junk stored ~40%, junk rejected ~30%, nothing extracted ~30% |
| `f_like_to_dislike` (spicy food) | likes `superseded` by dislikes, event `contradiction` | ~55% | values differ ("spicy food" vs "spicy"), so no match and both active; or "gone off" read as a retract of likes (likes archived, also acceptable) |
| `f_dislike_to_like` (opera) | dislikes `superseded` by likes, event `contradiction` | ~65% | model files it as hobby, or "can't stand" first time is stored as a retract (nothing stored), then a plain add |
| `f_employer_no_title` (Riverside Clinic) | works_at Saint Mary's `superseded`, nurse `conflicted` | ~75% | model re-emits job_title=nurse from nowhere: "nurse" is not in the message, so rejected and it does not shield the old title, fine; or `switched employers` produces no works_at value |
| `f_employer_with_title` (Northwind -> Contoso, product manager) | Northwind superseded or archived, sales rep `superseded` by product manager, nothing `conflicted` | ~80% | product manager labelled retract and lost; "sales rep" value grounded only by "sales", fine |

Retrieval questions in F (secondary, retrieval only):
- `f_correction_allergy` needs pollen: ~55%; latex stale in prompt: ~50%.
- `f_no_longer_hobby` needs pottery: ~65%.
- `f_vague_promotion` "Where do I work?": hillside ✓ ~90%; "job title" noise (promot*) ~40%.
- `f_like_to_dislike` "food do I enjoy?": `spicy` noise ~60%, since even if the like is superseded the
  dislike can be routed in through its food hint.
- `f_dislike_to_like` needs opera ✓ ~85% (any opera line counts, so not discriminating).
- `f_employer_no_title` "Where do I work?" riverside ✓ ~80%; "job title" nurse absent ~75%.
- `f_employer_with_title` contoso ✓ ~85%, product manager ✓ ~75%.

Overall: I expect 4-5 of the 7 F scenarios to end in exactly the intended stored state.
