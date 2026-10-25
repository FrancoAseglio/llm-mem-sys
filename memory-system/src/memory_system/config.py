import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]
CHAT_MODEL = os.environ.get("CHAT_MODEL", "llama3.1:8b")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")  # 768 dims, matches schema.sql

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
# Evidence for these values: docs/findings.md.

# Floor: a fact needs raw cosine similarity >= this to the question. Fragile (one example per side).
MIN_RELEVANCE = 0.42

# Window: keep only facts within this of the best candidate, to drop topical neighbours.
RELATIVE_WINDOW = 0.08

# Routing: only facts whose relation type is among the N best matches for the question. 0 = off.
ROUTING_TOP_N = int(os.environ.get("ROUTING_TOP_N", "2"))

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
