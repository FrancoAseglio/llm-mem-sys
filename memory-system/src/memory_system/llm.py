from collections.abc import Iterator

import numpy as np
import ollama
from pydantic import BaseModel

from memory_system.config import CHAT_MODEL, EMBED_MODEL


def embed(text: str) -> np.ndarray:
    vec = ollama.embed(model=EMBED_MODEL, input=text)["embeddings"][0]
    return np.asarray(vec, dtype=np.float32)


def chat(messages: list[dict], temperature: float = 0.3) -> str:
    resp = ollama.chat(model=CHAT_MODEL, messages=messages, options={"temperature": temperature})
    return resp.message.content


def chat_stream(messages: list[dict], temperature: float = 0.3) -> Iterator[str]:
    for chunk in ollama.chat(
        model=CHAT_MODEL, messages=messages, options={"temperature": temperature}, stream=True
    ):
        yield chunk.message.content


def chat_structured[T: BaseModel](system: str, user: str, schema: type[T]) -> T:
    """Ask the model for JSON that must match a pydantic schema."""
    resp = ollama.chat(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        format=schema.model_json_schema(),
        options={"temperature": 0},
    )
    return schema.model_validate_json(resp.message.content)
