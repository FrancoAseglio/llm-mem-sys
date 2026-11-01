# Evaluation

How the memory was measured, what was found, and what the evidence does not show. Every run's
data is in [`results/`](../results/README.md); the notebook [`notebooks/results.ipynb`](../notebooks/results.ipynb)
draws the charts, and the dashboard (`make dashboard`) shows every question and answer.

## Method

**Scenarios.** A scenario is a scripted life story: messages with backdated timestamps, then
questions. The runner (`evaluation/run.py`) replays the messages through the write path, then asks
every question in each mode (`none`, `baseline`, `smart`, `hybrid`, `full`; see
[design.md](design.md)). The sets are JSON files in `evaluation/scenarios/sets/`.

**Measures**, all keyword checks on lower-cased text:

| Measure | Question it answers |
|---|---|
| Needed fact present | Did the memory lines hold the words the question needs? |
| Noise present | Did they hold words that should not be there? |
| Stale in prompt / in answer | Did an outdated value reach the prompt (on a line not marked as old) or the answer? |
| Answer correct | Does the reply contain the expected words? (model at temperature 0) |

**Protocol.** Predictions were written and committed before every run of a new set. A *blind*
set was written before the change it tests and run once; after that it is *spent* and cannot
validate further tuning. Failed predictions were kept, not edited. Measuring never changes the
memory (retrieval with `touch=False`).

## Test sets

86 scenarios and 367 questions, all spent now.

| Sets | Questions | What they test |
|---|---|---|
| A to F | 71 | The 13 fact types: moves, job changes, allergies, corrections, noise, traps (A was the tuning set) |
| G, H | 34 | Episodes, plans and purchases that no fact type holds (the episode-notes layer) |
| I | 12 | Questions about the past |
| J | 26 | Merging old notes into digests |
| K | 23 probes | Consistency across sessions (its own runner, `evaluation/run_sessions.py`) |
| L | 30 | Unseen data: every question type mixed, written after A to K were spent |
| M, N, O | 171 | Long histories: three users per set with about 95 messages over 18 months |

## Results

**The headline: blind sets N and O** (114 questions, the final design against the control):

| | Baseline | Smart | **Hybrid** | Full |
|---|---|---|---|---|
| Right answers, N (57) | 45 | 42 | **50** | 50 |
| Right answers, O (57) | 44 | 39 | **47** | 52 |
| **N + O (114)** | 89 | 81 | **97** | 102 |
| Outdated value in an answer | 6 | 13 | 7 | 3 |

- **Hybrid beat the baseline on both blind sets**, meeting the pre-registered rule (at least +3)
  each time: +5 on N, +3 on O.
- **Not statistically significant:** on the questions where the two differ, hybrid alone was right
  on 15 and the baseline alone on 7 (sign test p = 0.13).
- **Facts alone (smart) lose on long histories**, here and on set M (baseline 48, smart 36 of 57).
  Each statement is a chance for the 8B extractor to mis-store a fact, and single-valued facts
  get replaced by incidental mentions. The raw messages do not have these errors.
- **The whole history (full) scored best.** At about 1,100 tokens per user it fits the model whole,
  so these sets cannot show memory beating the full history, only beating vector search.

**What facts do well**, from the earlier sets:

- **Outdated values:** on sets A to F, an outdated value reached the prompt 15 times with the
  baseline and 0 times with smart memory, since replaced facts are not read.
- **Less noise:** irrelevant text in 14 of 46 prompts instead of 42, with 1 to 2 memory lines
  instead of up to 4.
- **In hybrid,** they win on timelines for past questions, current values after a change, and
  allergies on indirect questions. Hybrid's losses come from wrong or stale facts.

**What facts do badly:** on the one set of unseen data (L), the baseline answered 28 of 30 and
smart 20. Half of smart's misses were facts stored wrongly (a sister's city saved as the user's).

## The project goals

| Goal | Outcome |
|---|---|
| Store memories over long periods | Done: messages, versioned facts, episode notes |
| Prioritise relevant information | Done: the relevance gate (far less noise) |
| Detect contradictory facts | Done: likes against dislikes, retractions, employer changes |
| Update outdated information | Done: superseded, never overwritten; outdated messages marked in hybrid |
| Compress history into summaries | Partly: notes help on episodes, but digests save only a fifth |
| Improve conversational consistency | Partly: across sessions (set K) smart 17 of 23 without contradictions, baseline 16 with one |
| Better answers than vector memory | Supported in direction, not proven (97 against 89, p = 0.13) |

## Limits

- **Every set is spent,** and the gate values were tuned on early sets; the scenarios and the
  system share a designer.
- **Small samples:** the headline rests on 114 questions in six users' histories.
- **Keyword scoring** marks a correct answer worded differently as wrong.
- **One small model** (llama3.1:8b) for extraction and answers; a stronger one would change the
  error mix.
- **Short histories:** about 1,100 tokens per user, below the length where memory is needed; the
  full history wins there.
- **A simple baseline:** the four most similar messages, as the project defines vector memory.

## The full record

The detailed documents (architecture, every set's results and predictions, the decision log and
the development history) are kept at the git tag
[`docs-archive`](https://github.com/FrancoAseglio/llm-mem-sys/tree/docs-archive/docs).
The predictions there were committed before each run, which the git history shows.
