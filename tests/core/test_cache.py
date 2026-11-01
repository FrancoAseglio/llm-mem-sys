"""The disk cache and the in-process embedding memo (no Ollama needed)."""

from types import SimpleNamespace

import numpy as np
import pytest
from pydantic import BaseModel

from memory_system.core import llm
from memory_system.core.cache import DiskCache, make_key


class Answer(BaseModel):
    value: str


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    """No cache and an empty memo for every test; count the calls the 'model' receives."""
    monkeypatch.setattr(llm, "_cache", None)
    monkeypatch.setattr(llm, "_memo", {})
    calls = SimpleNamespace(embed=0, chat=0, options=[])

    def fake_embed(model, input):
        calls.embed += 1
        return {"embeddings": [[1.0, 2.0, 3.0]]}

    def fake_chat(model, messages, options=None, format=None, stream=False):
        calls.chat += 1
        calls.options.append(options)
        content = '{"value": "x"}' if format else "reply"
        return SimpleNamespace(message=SimpleNamespace(content=content))

    monkeypatch.setattr(llm._client, "embed", fake_embed)
    monkeypatch.setattr(llm._client, "chat", fake_chat)
    return calls


def test_key_depends_on_every_part():
    assert make_key("a", 1) == make_key("a", 1)
    assert make_key("a", 1) != make_key("a", 2)
    assert make_key("chat", "m1", "hi") != make_key("chat", "m2", "hi")


def test_disk_cache_counts_hits_and_misses():
    cache = DiskCache(":memory:")
    assert cache.get("k") is None
    cache.put("k", b"v")
    assert cache.get("k") == b"v"
    assert (cache.hits, cache.misses) == (1, 1)


def test_embedding_memo_asks_the_model_once_without_a_disk_cache(fresh):
    a = llm.embed("hello")
    b = llm.embed("hello")
    assert fresh.embed == 1
    assert np.array_equal(a, b)


def test_embedding_memo_returns_copies(fresh):
    a = llm.embed("hello")
    a[0] = 99.0
    assert llm.embed("hello")[0] == 1.0


def test_disk_cache_serves_a_second_process_run(fresh):
    llm._cache = DiskCache(":memory:")
    llm.embed("hello")
    llm._memo.clear()  # as if the process had restarted
    again = llm.embed("hello")
    assert fresh.embed == 1
    assert again.dtype == np.float32 and list(again) == [1.0, 2.0, 3.0]


def test_chat_is_cached_only_at_temperature_zero(fresh):
    llm._cache = DiskCache(":memory:")
    msgs = [{"role": "user", "content": "hi"}]
    llm.chat(msgs, temperature=0)
    llm.chat(msgs, temperature=0)
    assert fresh.chat == 1
    llm.chat(msgs, temperature=0.3)
    llm.chat(msgs, temperature=0.3)
    assert fresh.chat == 3


def test_structured_reply_is_cached_and_validated(fresh):
    llm._cache = DiskCache(":memory:")
    first = llm.chat_structured("sys", "user", Answer)
    second = llm.chat_structured("sys", "user", Answer)
    assert first == second == Answer(value="x")
    assert fresh.chat == 1


def test_a_different_prompt_misses_the_cache(fresh):
    llm._cache = DiskCache(":memory:")
    llm.chat_structured("sys", "one", Answer)
    llm.chat_structured("sys", "two", Answer)
    assert fresh.chat == 2


def test_no_cache_means_every_call_goes_to_the_model(fresh):
    msgs = [{"role": "user", "content": "hi"}]
    llm.chat(msgs, temperature=0)
    llm.chat(msgs, temperature=0)
    assert fresh.chat == 2
    assert llm.cache_stats() is None


def test_every_call_has_a_token_cap(fresh):
    llm.chat([{"role": "user", "content": "hi"}])
    llm.chat([{"role": "user", "content": "hi"}], num_ctx=8192)
    llm.chat_structured("sys", "user", Answer)
    caps = [o["num_predict"] for o in fresh.options]
    assert caps == [llm.MAX_TOKENS_CHAT, llm.MAX_TOKENS_CHAT, llm.MAX_TOKENS_STRUCTURED]


def test_the_cap_is_not_part_of_the_cache_key(fresh, monkeypatch):
    """Replies cached before the cap existed are still found."""
    cache = DiskCache(":memory:")
    monkeypatch.setattr(llm, "_cache", cache)
    messages = [{"role": "user", "content": "hi"}]
    cache.put(make_key("chat", llm.CHAT_MODEL, messages, 0), b"cached reply")
    assert llm.chat(messages, temperature=0) == "cached reply"
    assert fresh.chat == 0


def test_the_client_has_a_timeout():
    assert llm._client._client.timeout.read == llm.LLM_TIMEOUT
