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

# Importance per relation type. The small local LLM rates almost everything 1.0, so we don't ask it.
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

# ---- Summaries: episode notes written from messages, shown when they pass the same gate ----
# SUMMARIES=0 switches the layer off (nothing is written or shown), for ablations.
SUMMARIES = os.environ.get("SUMMARIES", "1") != "0"

# At most this many summary lines per question; facts keep priority within the k lines.
SUMMARY_MAX_LINES = 2

# Messages summarised per model call, and how many new messages trigger a summary in the chat.
SUMMARY_BATCH = 12
SUMMARY_EVERY = 6

# A summary sentence is kept only if at least this share of its content words is in its sources.
SUMMARY_FAITHFUL_MIN = 0.75
