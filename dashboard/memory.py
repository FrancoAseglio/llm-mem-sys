"""The live memory behind the inspector page: stored users and facts (Postgres) and each mode's
prompt and answer for a new question (Postgres and Ollama).

Read-only: questions are recalled with touch=False, as in the evaluation, so asking changes no
access counts and stores nothing. The memory system is imported only when a function needs it,
so the results page works without a .env, a database or a model; when one of them is missing,
the functions raise Unavailable with a message the page can show.
"""

import time
from dataclasses import dataclass
from datetime import datetime

from dashboard.data import Line, line_kind
from memory_system.read.hybrid_rules import timeline_line
from memory_system.read.labels import label

DEFAULT_MODES = ["baseline", "smart", "hybrid", "full"]
EVAL_PREFIX = "eval_"  # users the evaluation ingests: eval_<scenario id>


class Unavailable(Exception):
    """The database or the model cannot be reached; the message says which and what to do."""


@dataclass
class User:
    id: str
    messages: int
    facts: int  # current facts


@dataclass
class Fact:
    subject: str
    relation: str
    value: str
    status: str  # active, superseded, conflicted or archived
    valid_from: datetime
    valid_to: datetime | None
    confidence: float

    @property
    def name(self) -> str:
        """'Lives in' for the user's own facts, 'sister · Lives in' for someone else's."""
        own = label(self.relation)
        return own if self.subject == "user" else f"{self.subject} · {own}"


@dataclass
class UserMemory:
    user: str
    messages: int
    notes: int  # episode notes and digests that retrieval can still use
    current: list[Fact]
    old: list[Fact]  # superseded, archived and conflicted facts, newest first
    timelines: list[str]


@dataclass
class ModeMemory:
    """What one mode puts in the prompt for a question (the answer comes separately)."""

    mode: str
    lines: int
    memory: list[Line]
    system: str  # the whole system prompt, memory lines included


@dataclass
class Check:
    """One service the inspector needs: whether it answers, and what to do if not."""

    name: str
    ok: bool
    detail: str


# ---- Pure helpers (tested without services) ----


def split_facts(facts: list[Fact]) -> tuple[list[Fact], list[Fact]]:
    """(current facts, the user's own first, by name; every other fact, newest first)."""
    current = sorted(
        (f for f in facts if f.status == "active"),
        key=lambda f: (f.subject != "user", f.name, f.value),
    )
    old = sorted(
        (f for f in facts if f.status != "active"),
        key=lambda f: f.valid_from,
        reverse=True,
    )
    return current, old


def timelines(facts: list[Fact]) -> list[str]:
    """One line per (subject, relation) that has a history, in the words hybrid uses for a past
    question: 'Lives in, oldest first: Oslo -> Bergen (now)'. `facts` in any order; a relation
    whose values are all current has no history and no line."""
    chains: dict[tuple[str, str], list[Fact]] = {}
    for f in sorted(facts, key=lambda f: f.valid_from):
        chains.setdefault((f.subject, f.relation), []).append(f)
    out = []
    for (subject, relation), chain in sorted(chains.items()):
        if all(f.status == "active" for f in chain):
            continue  # several current values of a list relation (hobbies) are no history
        line = timeline_line(relation, [(f.value, f.status) for f in chain])
        if line:
            out.append(line if subject == "user" else f"{subject} · {line}")
    return out


def has_model(installed: set[str], wanted: str) -> bool:
    """Whether Ollama has `wanted` ('nomic-embed-text' matches 'nomic-embed-text:latest')."""
    return wanted in installed or (
        ":" not in wanted and f"{wanted}:latest" in installed
    )


def group_users(users: list[User]) -> list[tuple[str, list[User]]]:
    """Chat users first, then the evaluation's users, for the user menu."""
    chat = [u for u in users if not u.id.startswith(EVAL_PREFIX)]
    evaluation = [u for u in users if u.id.startswith(EVAL_PREFIX)]
    return [
        (name, us) for name, us in (("chat", chat), ("evaluation", evaluation)) if us
    ]


# ---- Database ----


def _database_url() -> str:
    try:
        from memory_system.core.config import DATABASE_URL
    except KeyError as e:
        raise Unavailable(
            "DATABASE_URL is not set. Copy .env.example to .env in the repository root."
        ) from e
    return DATABASE_URL


def _query(sql: str, params: tuple = ()) -> list[tuple]:
    """Run one read query on a short-lived connection, failing fast when Postgres is down."""
    import psycopg

    try:
        with psycopg.connect(_database_url(), connect_timeout=3) as conn:
            return conn.execute(sql, params).fetchall()
    except psycopg.OperationalError as e:
        raise Unavailable(
            "Postgres is not reachable (is it running? `brew services start "
            f"postgresql@17`): {str(e).strip()}"
        ) from e


def list_users() -> list[User]:
    rows = _query(
        """SELECT u.id,
                  (SELECT count(*) FROM messages m WHERE m.user_id = u.id AND m.role = 'user'),
                  (SELECT count(*) FROM facts f WHERE f.user_id = u.id AND f.status = 'active')
           FROM users u ORDER BY u.id"""
    )
    return [User(*row) for row in rows]


def user_memory(user_id: str) -> UserMemory:
    facts = [
        Fact(*row)
        for row in _query(
            """SELECT subject, relation, value, status, valid_from, valid_to, confidence
               FROM facts WHERE user_id = %s ORDER BY valid_from, id""",
            (user_id,),
        )
    ]
    ((messages, notes),) = _query(
        """SELECT (SELECT count(*) FROM messages WHERE user_id = %s AND role = 'user'),
                  (SELECT count(*) FROM summaries WHERE user_id = %s AND digest_id IS NULL)""",
        (user_id, user_id),
    )
    current, old = split_facts(facts)
    return UserMemory(user_id, messages, notes, current, old, timelines(facts))


# ---- Service status ----


def _model_names() -> tuple[str, str]:
    """(chat model, embedding model) from the configuration, or its defaults without a .env."""
    import os

    try:
        from memory_system.core.config import CHAT_MODEL, EMBED_MODEL
    except KeyError:
        return (
            os.environ.get("CHAT_MODEL", "llama3.1:8b"),
            os.environ.get("EMBED_MODEL", "nomic-embed-text"),
        )
    return CHAT_MODEL, EMBED_MODEL


def database_status() -> Check:
    try:
        ((users,),) = _query("SELECT count(*) FROM users")
    except Unavailable as e:
        return Check("Postgres", False, str(e))
    return Check("Postgres", True, f"connected, {users} stored users")


def ollama_status() -> Check:
    """Ollama answers and has both models. Asks the local server only (2 s at most)."""
    import ollama

    wanted = _model_names()
    try:
        installed = {m.model for m in ollama.Client(timeout=2).list().models}
    except Exception:
        return Check(
            "Ollama",
            False,
            "not running: start it with `brew services start ollama` (or `ollama serve`)",
        )
    missing = [m for m in wanted if not has_model(installed, m)]
    if missing:
        pulls = ", ".join(f"`ollama pull {m}`" for m in missing)
        return Check("Ollama", False, f"running, but missing a model: {pulls}")
    return Check("Ollama", True, f"running, {wanted[0]} and {wanted[1]}")


def status() -> list[Check]:
    return [database_status(), ollama_status()]


# ---- Prompt and answer (Postgres and Ollama) ----


def prompt(mode: str, user_id: str, question: str, k: int = 4) -> ModeMemory:
    """The memory lines and system prompt `mode` builds for the question, as in the
    evaluation (same k, touch=False)."""
    _database_url()
    from memory_system.assistant import build_messages, recall

    try:
        lines = recall(mode, user_id, question, k, touch=False)
    except Exception as e:  # the embedding model or the database
        raise Unavailable(
            f"Retrieval failed; is Ollama running (`brew services start ollama`)? {e}"
        ) from e
    system = build_messages(mode, lines, [], question)[0]["content"]
    memory = [] if mode == "full" else [Line(t, line_kind(t)) for t in lines]
    return ModeMemory(mode, len(lines), memory, system)


def answer(mode: str, user_id: str, question: str, k: int = 4) -> tuple[str, float]:
    """(the chat model's answer, seconds taken), at temperature 0 as in the evaluation."""
    _database_url()
    from memory_system.assistant import build_messages, recall
    from memory_system.core.config import FULL_NUM_CTX
    from memory_system.core.llm import chat

    start = time.monotonic()
    try:
        lines = recall(mode, user_id, question, k, touch=False)
        reply = chat(
            build_messages(mode, lines, [], question),
            temperature=0,
            num_ctx=FULL_NUM_CTX if mode == "full" else None,
        )
    except Exception as e:
        raise Unavailable(
            f"The model did not answer; is Ollama running (`brew services start ollama`)? {e}"
        ) from e
    return reply, time.monotonic() - start
