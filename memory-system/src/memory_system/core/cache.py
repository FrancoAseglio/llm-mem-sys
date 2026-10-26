"""A small disk cache for model calls that give the same answer every time.

Used by the evaluation only (see llm.enable_cache). With temperature 0 the same prompt gives the
same reply, so a second run of an unchanged set can read its extractions, summaries, embeddings
and answers from disk instead of asking the model again. The key holds the model name and the
whole input, so changing a prompt or a model name misses the cache by itself. After
`ollama pull` of a new version of the same model name, delete the cache file.
"""

import hashlib
import json
import sqlite3
from pathlib import Path


def make_key(*parts) -> str:
    """Stable key for any JSON-serialisable parts."""
    raw = json.dumps(parts, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


class DiskCache:
    def __init__(self, path: str | Path):
        path = Path(path)
        if str(path) != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path))
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value BLOB NOT NULL)"
        )
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> bytes | None:
        row = self._db.execute("SELECT value FROM kv WHERE key = ?", (key,)).fetchone()
        if row is None:
            self.misses += 1
            return None
        self.hits += 1
        return row[0]

    def put(self, key: str, value: bytes) -> None:
        self._db.execute("INSERT OR REPLACE INTO kv VALUES (?, ?)", (key, value))
        self._db.commit()
