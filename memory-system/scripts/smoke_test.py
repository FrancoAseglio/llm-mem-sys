"""Smoke test: Postgres + pgvector + Ollama (embeddings and structured output).

Run from the memory-system folder:
    poetry run python scripts/smoke_test.py
"""

import os

import numpy as np
import ollama
import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector
from pydantic import BaseModel

load_dotenv()
DB_URL = os.environ["DATABASE_URL"]
EMBED_MODEL = os.environ["EMBED_MODEL"]
CHAT_MODEL = os.environ["CHAT_MODEL"]


def embed(text: str) -> np.ndarray:
    vec = ollama.embed(model=EMBED_MODEL, input=text)["embeddings"][0]
    return np.asarray(vec, dtype=np.float32)


# --- 1. Embeddings + pgvector -------------------------------------------
print("1) Embeddings + vector search")
sample = [
    "I live in Milan and love cycling.",
    "My favourite food is carbonara.",
    "I work as a data engineer.",
]
with psycopg.connect(DB_URL) as conn:
    register_vector(conn)
    conn.execute("INSERT INTO users (id) VALUES ('smoke') ON CONFLICT DO NOTHING")
    for text in sample:
        conn.execute(
            "INSERT INTO messages (user_id, role, content, embedding) "
            "VALUES ('smoke', 'user', %s, %s)",
            (text, embed(text)),
        )
    query = embed("What city does the user live in?")
    rows = conn.execute(
        "SELECT content, embedding <=> %s AS distance FROM messages "
        "WHERE user_id = 'smoke' ORDER BY distance LIMIT 3",
        (query,),
    ).fetchall()
    for content, dist in rows:
        print(f"   {dist:.3f}  {content}")
    # clean up
    conn.execute("DELETE FROM users WHERE id = 'smoke'")
    conn.commit()
print(f"   embedding dimension: {len(query)} (schema expects 768)\n")


# --- 2. Structured fact extraction ----------------------------------------
print("2) Structured extraction with the chat model")


class Fact(BaseModel):
    relation: str
    value: str
    importance: float


class Facts(BaseModel):
    facts: list[Fact]


resp = ollama.chat(
    model=CHAT_MODEL,
    messages=[
        {
            "role": "system",
            "content": (
                "Extract durable facts about the user. Allowed relations: "
                "lives_in, works_at, job_title, hobby, likes, dislikes, allergic_to. "
                "importance is 0 to 1. Return JSON only."
            ),
        },
        {
            "role": "user",
            "content": "I just moved to Milan, I'm allergic to penicillin, and I started cycling.",
        },
    ],
    format=Facts.model_json_schema(),
    options={"temperature": 0},
)
print("  ", Facts.model_validate_json(resp.message.content))
print("\nAll good.")
