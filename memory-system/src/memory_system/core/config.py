import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]
CHAT_MODEL = os.environ.get("CHAT_MODEL", "llama3.1:8b")
# Disk cache of deterministic model calls, used by the evaluation only (see core/cache.py).
CACHE_PATH = os.environ.get("LLM_CACHE_PATH", ".cache/llm.sqlite")
EMBED_MODEL = os.environ.get(
    "EMBED_MODEL", "nomic-embed-text"
)  # 768 dims, matches schema.sql

# Importance per relation type. The small local LLM rates almost everything 1.0, so it is not asked.
DEFAULT_IMPORTANCE = {
    "allergic_to": 0.95,
    "family_member": 0.80,
    "partner": 0.80,
    "name": 0.80,
    "lives_in": 0.70,
    "birthday": 0.70,
    "works_at": 0.60,
    "job_title": 0.60,
    "speaks": 0.50,
    "goal": 0.50,
    "hobby": 0.40,
    "likes": 0.40,
    "dislikes": 0.40,
}

# A new value this similar (trigram similarity) to an existing one counts as a duplicate.
DUPLICATE_SIMILARITY = 0.8

# ---- Retrieval: a relevance gate (floor, window, routing), then a ranking among what passes ----
# Evidence for these values: docs/09_findings.md.

# Floor: a fact needs raw cosine similarity >= this to the question. Fragile (one example per side).
MIN_RELEVANCE = 0.42

# Window: keep only facts within this of the best candidate, to drop topical neighbours.
RELATIVE_WINDOW = 0.08

# Routing: only facts whose relation type is among the N best matches for the question. 0 = off.
ROUTING_TOP_N = int(os.environ.get("ROUTING_TOP_N", "2"))

# Safety bypass: these relations skip the floor and window when routing ranks them in the top N,
# so an allergy is not lost to a loosely worded food question. SAFETY_BYPASS=0 switches it off.
SAFETY_RELATIONS = {"allergic_to"}
SAFETY_BYPASS = os.environ.get("SAFETY_BYPASS", "1") != "0"

# Ranking: score = sum(weight * component), each component in [0, 1]. Orders facts and picks the top k.
WEIGHTS = {
    "similarity": 0.50,
    "importance": 0.25,
    "usage": 0.10,
    "confidence": 0.10,
    "recency": 0.05,
}
# For ranking only, raw similarity is rescaled from [SIM_FLOOR, SIM_CEIL] to [0, 1].
SIM_FLOOR = 0.35
SIM_CEIL = 0.75
# A fact untouched for this many days counts as half as fresh.
RECENCY_HALF_LIFE_DAYS = 90

# Pinning (always include very important facts) is off: 1.01 is above any importance.
PIN_IMPORTANCE = 1.01

# ---- Questions about the past: replaced (superseded) facts, read only for such questions ----
# PAST_FACTS=0 switches it off. At most this many past lines, placed before the active ones.
PAST_FACTS = os.environ.get("PAST_FACTS", "1") != "0"
PAST_MAX_LINES = 2

# ---- Hybrid mode: the baseline's messages, plus a few facts (docs/06_read_path.md, section 11) ----
# Current facts above the messages, chosen by smart's gate (allergy pass included): the best
# HYBRID_FACT_RELATIONS kinds of fact, one line each, except that a list kind (languages,
# allergies, likes, dislikes) shows every value that passes; at most HYBRID_FACT_MAX lines.
# Set N: a cap of 2 lines showed two of three languages; every value of every kind then filled
# the prompt with family names (fixes_N), so only list kinds are expanded.
HYBRID_FACT_RELATIONS = 2
HYBRID_FACT_MAX = 4
HYBRID_LIST_RELATIONS = frozenset({"speaks", "allergic_to", "likes", "dislikes"})
# Mark messages whose facts changed or were retracted. HYBRID_MARKERS=0 switches marking off.
HYBRID_MARKERS = os.environ.get("HYBRID_MARKERS", "1") != "0"
# One timeline line (every value of one relation, oldest first) for questions about the past.
# HYBRID_TIMELINE=0 switches it off.
HYBRID_TIMELINE = os.environ.get("HYBRID_TIMELINE", "1") != "0"

# ---- Full mode: the user's whole history in the prompt (a reference ceiling, not a design) ----
# Context window asked of the chat model for full-mode answers only, so nothing is cut silently.
FULL_NUM_CTX = int(os.environ.get("FULL_NUM_CTX", "8192"))

# ---- Write path: drop facts the message gives to someone else (write/actions.about_user) ----
# ABOUT_USER=0 switches the check off, for ablations.
ABOUT_USER = os.environ.get("ABOUT_USER", "1") != "0"
# A new value replaces the current city, employer, job title or partner only if the message says
# it changed (write/actions.signals_change). CHANGE_RULE=0 switches it off, for ablations.
CHANGE_RULE = os.environ.get("CHANGE_RULE", "1") != "0"

# ---- Summaries: episode notes written from messages, shown when they pass the same gate ----
# SUMMARIES=0 switches the layer off (nothing is written or shown), for ablations.
SUMMARIES = os.environ.get("SUMMARIES", "1") != "0"

# Each message sent to the notes model shows the facts already stored from it ("[stored: ...]"),
# so notes skip only what facts really hold. NOTE_TAGS=0 restores the untagged prompt.
NOTE_TAGS = os.environ.get("NOTE_TAGS", "1") != "0"
# With tags on, a note is dropped when every message it cites is already held by its stored facts:
# each name in the message is in a stored value and this share of its content words is covered.
# The same share as SUMMARY_FAITHFUL_MIN; not tuned.
NOTE_STORED_MIN = 0.75

# A note must come within RELATIVE_WINDOW of the best line overall, facts included, not only of
# the best note, so a weak note does not ride along with a strong fact. NOTE_FACT_WINDOW=0: notes only.
NOTE_FACT_WINDOW = os.environ.get("NOTE_FACT_WINDOW", "1") != "0"

# At most this many summary lines per question; facts keep priority within the k lines.
SUMMARY_MAX_LINES = 2

# Messages summarised per model call, and how many new messages trigger a summary in the chat.
SUMMARY_BATCH = 12
SUMMARY_EVERY = 6

# A summary sentence is kept only if at least this share of its content words is in its sources.
SUMMARY_FAITHFUL_MIN = 0.75

# ---- Consolidation: old notes of one user merged into shorter digests (docs/predictions/set_J.md) ----
# CONSOLIDATE=0 switches it off: nothing is merged and retrieval reads the plain notes, as before.
CONSOLIDATE = os.environ.get("CONSOLIDATE", "1") != "0"

# A user is consolidated when at least CONSOLIDATE_MIN live notes are older than CONSOLIDATE_AGE_DAYS
# (by the date of their newest source message). Newer notes are never merged.
CONSOLIDATE_MIN = 6
CONSOLIDATE_AGE_DAYS = 30

# Most old notes sent to the model in one call (the oldest first); the rest wait for the next run.
CONSOLIDATE_BATCH = 40
