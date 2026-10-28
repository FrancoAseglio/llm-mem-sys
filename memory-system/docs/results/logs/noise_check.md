# Noise check: everything re-run from scratch (2026-10-28)

Every single-question set (A to J) and the session set K were run again with the cache off (`--no-cache`), after re-ingesting every story. Any difference from the recorded runs is run-to-run noise. Two things besides the model calls changed: the calendar (two days later, and the system prompt states today's date) and the random order nothing depends on. All sets were already spent, so nothing was tuned here.

Outputs: `../regressions/A_to_J_nocache.txt` and `../set_K/rerun_nocache.txt`.

## Predicted (before the run)

Memory-only numbers identical or 0 to 2 different per set; answers correct 0 to 4 different per mode across A to J; set K 0 to 2 different per mode.

## Found

| Set | Memory-only numbers (needed, noise, stale, lines) | Answers correct |
|---|---|---|
| A, B, C, E, F, H, I, J | identical to the recorded runs | identical |
| D | identical | baseline 15/18 → 14/18 (the pizza question) |
| G | identical | smart 13/18 → 14/18 (the vegan dinner question; its needed fact is still missing, the answer passed anyway) |
| K | identical | identical, probe by probe |

Two of 286 answers in A to J changed (under 1%), one per mode, in opposite directions; no memory-only measure changed. The recorded A to J results come from `regressions/A_to_I_consolidation.txt` and `set_J/on.json`; set K from `set_K/first_run.txt`.

## What it shows and does not show

- The evaluation is reproducible: the same sets give the same numbers from scratch, so the gaps between modes are not run-to-run luck.
- It says nothing about new data. A gap that repeats exactly can still rest on few questions, and every set here was written by the same person who built the system. Fresh sets (L, then M) are the test of that.
