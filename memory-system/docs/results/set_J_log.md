# Set J log: consolidation of notes (2026-10-26)

Record of what was run, in order, with what was found. Predictions and the frozen design: [../predictions/set_J.md](../predictions/set_J.md). Raw results: `set_J_off.json`, `set_J_on.json`, `regress_A_to_I_consolidation.txt`.

## 1. Run 1: consolidation not built (`set_J_off.json`)

- Baseline 25/25 needed, 26/26 answers. Smart 23/25 needed, 24/26 answers, 1.9 lines. Predicted about 22, 21, 20 and 19: I underestimated both modes.
- 16 renovation messages gave 11 notes. Three true sentences were dropped by the notes' faithfulness check (replayed by hand against `is_faithful`, assuming each cited only its own message; the event does not log citations):
  - "Henrik sprained his ankle while fixing the roof": 5/7 words matched; "brother-in-law" came from a message not cited.
  - "The old floor tiles contained asbestos, causing a two-week delay in the renovation": 6/10; a paraphrase plus context words.
  - "The user and their partner had to return a new oven due to a dent" and "... installed a grey granite countertop": rightly dropped for the invented "partner", but the facts were lost.
- Hanoi: the "moved to February" note existed but lost the window to the two December notes; the answer gave December 12.
- Write-path slip seen in passing: "Margit quit the band to move to Canada" stored `lives_in = Canada` for the user.
- Note slips that passed the check: "the user and their partner" (from "we") in three notes; "the user's friend Lotte" for a daughter.

## 2. Code (before run 2)

Built as frozen in section 1 of the predictions. Choices the design did not cover are listed there under "Implementation notes". My first database tests failed (4 of 12) because the test gave the first note the newest date, so the model's oldest-first numbering pointed at other notes; the code was right. 167 tests pass.

## 3. Run 2: consolidation on (`set_J_on.json`)

- Smart 24/25 needed, 25/26 answers, 1.7 lines; baseline unchanged.
- 9 digests from 19 notes: renovation 2, travels 4, band 0, control mix 3, recent 0.
- The model proposed 24 digests; 14 cited one note (dropped), one lost the name "Margit" (dropped), nine were kept.
- Compression: digests 1,092 characters for 1,388 of notes (0.79); summary text in use 3,155 against 3,133 of source messages (1.01; notes alone 1.10).
- Hanoi was answered correctly: the digest of the two December notes left room for the February note.
- The asbestos question still failed: no note existed to merge.

## 4. Regression, sets A to I (`regress_A_to_I_consolidation.txt`)

Identical to `regress_A_to_H.txt` and `set_I_first_run.txt` except set B: smart stale in prompt 1 to 0, average lines 1.4 to 1.2. One digest was written in A to I (I had predicted none), for `b_stale_flood`: it merged six Turin notes, one of them "The user lives in Turin." That note should not exist (the note prompt says to skip home city). Because the user later moved to Rome, the stale-source rule hides the digest and with it five harmless notes.

## 5. Digests checked by hand

| Digest | Verdict |
|---|---|
| #410 kitchen: cost 21,500, quote 18,000 by Tobias | Faithful to its notes; keeps the invented "partner" from them |
| #411 Henrik fixed the barn roof, the user painted the doors red | Faithful |
| #423 Reykjavik with Sunniva, flight delayed nine hours by a snowstorm | Faithful |
| #424 Marrakech cooking class, lamb tagine | Faithful |
| #425 Dolomites hailstorm broke the camera | Faithful |
| #426 Hanoi with Joel, flights for December 12 | Faithful to its notes, outdated by a newer note it could not merge |
| #444 chickens Hilde and Rosa, Rosa ate the lettuce | Faithful |
| #445 moved to Bergen, movers scratched the piano, "repaired by the removal company" | **Wrong inference**: the company paid for a technician |
| #446 rowing boat, oarlocks for 45 euros | Faithful |
| #456 (set B) lives in Turin, derby, coffee, transport, Po river | Faithful to its notes; restates a superseded city, hidden by the stale-source rule |
