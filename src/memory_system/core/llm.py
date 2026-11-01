from collections.abc import Iterator

import numpy as np
import ollama
from pydantic import BaseModel

from memory_system.core.cache import DiskCache, make_key
from memory_system.core.config import (
    CACHE_PATH,
    CHAT_MODEL,
    EMBED_MODEL,
    LLM_TIMEOUT,
    MAX_TOKENS_CHAT,
    MAX_TOKENS_STRUCTURED,
)

# One client for every call, with a timeout (see config.LLM_TIMEOUT). It reads OLLAMA_HOST like
# the library's own functions, so the containers reach Ollama on the host.
_client = ollama.Client(timeout=LLM_TIMEOUT)

# Disk cache for deterministic calls. Off unless enable_cache() is called (the evaluation does;
# the chat never does).
_cache: DiskCache | None = None

# Embeddings of the last few texts, so one question embedded by several parts of a retrieval
# is sent to the model once. Always on: an embedding of a text never changes.
_memo: dict[str, np.ndarray] = {}
_MEMO_MAX = 512


def enable_cache(path: str = CACHE_PATH) -> DiskCache:
    """Cache embeddings and temperature-0 replies on disk. Returns the cache (for its counters)."""
    global _cache
    _cache = DiskCache(path)
    return _cache


def cache_stats() -> tuple[int, int] | None:
    """(hits, misses) of the disk cache, or None if it is off."""
    return None if _cache is None else (_cache.hits, _cache.misses)


def embed(text: str) -> np.ndarray:
    """Embed one text with the embedding model."""
    if text in _memo:
        return _memo[text].copy()
    key = make_key("embed", EMBED_MODEL, text)
    cached = _cache.get(key) if _cache else None
    if cached is not None:
        vec = np.frombuffer(cached, dtype=np.float32).copy()
    else:
        vec = np.asarray(
            _client.embed(model=EMBED_MODEL, input=text)["embeddings"][0],
            dtype=np.float32,
        )
        if _cache:
            _cache.put(key, vec.tobytes())
    if len(_memo) >= _MEMO_MAX:
        _memo.clear()
    _memo[text] = vec
    return vec.copy()


def chat(
    messages: list[dict], temperature: float = 0.3, num_ctx: int | None = None
) -> str:
    """Return the chat model's full reply. Cached on disk only at temperature 0.

    `num_ctx` asks for a context window of that many tokens (the full mode); None keeps the
    model's default, exactly as before, so the other modes' calls and cache keys are unchanged.
    """
    key = (
        make_key("chat", CHAT_MODEL, messages, temperature)
        if num_ctx is None
        else make_key("chat", CHAT_MODEL, messages, temperature, num_ctx)
    )
    use_cache = _cache is not None and temperature == 0
    if use_cache:
        cached = _cache.get(key)
        if cached is not None:
            return cached.decode()
    options = {"temperature": temperature, "num_predict": MAX_TOKENS_CHAT}
    if num_ctx is not None:
        options["num_ctx"] = num_ctx
    resp = _client.chat(model=CHAT_MODEL, messages=messages, options=options)
    if use_cache:
        _cache.put(key, resp.message.content.encode())
    return resp.message.content


def chat_stream(messages: list[dict], temperature: float = 0.3) -> Iterator[str]:
    """Yield the chat model's reply token by token."""
    for chunk in _client.chat(
        model=CHAT_MODEL,
        messages=messages,
        options={"temperature": temperature, "num_predict": MAX_TOKENS_CHAT},
        stream=True,
    ):
        yield chunk.message.content


def chat_structured[T: BaseModel](system: str, user: str, schema: type[T]) -> T:
    """Ask the model for JSON that must match a pydantic schema (temperature 0)."""
    key = make_key("structured", CHAT_MODEL, system, user, schema.model_json_schema())
    cached = _cache.get(key) if _cache else None
    if cached is not None:
        return schema.model_validate_json(cached.decode())
    resp = _client.chat(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        format=schema.model_json_schema(),
        options={"temperature": 0, "num_predict": MAX_TOKENS_STRUCTURED},
    )
    result = schema.model_validate_json(
        resp.message.content
    )  # a bad reply is not cached
    if _cache:
        _cache.put(key, resp.message.content.encode())
    return result
