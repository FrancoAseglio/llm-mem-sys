"""The inspector's view of the live memory: the pure helpers, then the queries on Postgres.

The pure tests need no services (the template test needs the dashboard group, and is skipped
without it, as in CI). The database test needs the Postgres database from .env, like
the other DB tests (CI provides one); it stores one user, reads it back and deletes it.
"""

from datetime import UTC, datetime

import pytest

from dashboard import memory

DAY = datetime(2026, 1, 1, tzinfo=UTC)


def fact(value, status="active", relation="lives_in", subject="user", month=1):
    return memory.Fact(
        subject=subject,
        relation=relation,
        value=value,
        status=status,
        valid_from=DAY.replace(month=month),
        valid_to=None,
        confidence=0.8,
    )


def test_split_facts_puts_the_users_own_facts_first():
    facts = [
        fact("Galway", subject="Ingrid"),
        fact("Oslo", "superseded", month=1),
        fact("Bergen", month=3),
        fact("bass", "archived", relation="hobby", month=2),
    ]
    current, old = memory.split_facts(facts)
    assert [f.value for f in current] == ["Bergen", "Galway"]
    assert [f.value for f in old] == ["bass", "Oslo"]  # newest first
    assert current[1].name == "Ingrid · Lives in"


def test_timelines_show_only_relations_with_a_history():
    facts = [
        fact("Bergen", month=3),
        fact("Oslo", "superseded", month=1),
        fact("chess", relation="hobby"),
        fact("piano", relation="hobby"),  # two current hobbies: no history
        fact("Dublin", "superseded", subject="Ingrid", month=1),
        fact("Galway", subject="Ingrid", month=2),
    ]
    assert memory.timelines(facts) == [
        "Ingrid · Lives in, oldest first: Dublin -> Galway (now)",
        "Lives in, oldest first: Oslo -> Bergen (now)",
    ]


def test_group_users_puts_chat_users_before_the_evaluation():
    users = [memory.User("eval_n_marisol", 95, 9), memory.User("me", 3, 1)]
    groups = memory.group_users(users)
    assert [(name, [u.id for u in us]) for name, us in groups] == [
        ("chat", ["me"]),
        ("evaluation", ["eval_n_marisol"]),
    ]


def test_has_model_accepts_the_latest_tag():
    installed = {"llama3.1:8b", "nomic-embed-text:latest"}
    assert memory.has_model(installed, "nomic-embed-text")
    assert memory.has_model(installed, "llama3.1:8b")
    assert not memory.has_model(installed, "llama3.1:70b")


def test_ollama_status_when_it_is_not_running(monkeypatch):
    import ollama

    class Down:
        def __init__(self, **kwargs):
            pass

        def list(self):
            raise ConnectionError("refused")

    monkeypatch.setattr(ollama, "Client", Down)
    check = memory.ollama_status()
    assert not check.ok
    assert "brew services start ollama" in check.detail


def test_code_filter_escapes_and_marks_commands():
    pytest.importorskip("fastapi")  # the template helpers need the dashboard group
    from dashboard.templating import code_spans

    assert str(code_spans("run `ollama serve` <now>")) == (
        "run <code>ollama serve</code> &lt;now&gt;"
    )


USER = "test_dashboard_inspector"


@pytest.fixture
def stored_user():
    from memory_system.core.db import get_pool

    with get_pool().connection() as c:
        c.execute("DELETE FROM users WHERE id = %s", (USER,))
        c.execute("INSERT INTO users (id) VALUES (%s)", (USER,))
        c.execute(
            "INSERT INTO messages (user_id, role, content) VALUES (%s, 'user', 'Hi')",
            (USER,),
        )
        for value, status in (("Oslo", "superseded"), ("Bergen", "active")):
            c.execute(
                "INSERT INTO facts (user_id, relation, value, status, valid_from) "
                "VALUES (%s, 'lives_in', %s, %s, %s)",
                (USER, value, status, DAY.replace(month=1 if value == "Oslo" else 3)),
            )
        c.commit()
    yield USER
    with get_pool().connection() as c:
        c.execute("DELETE FROM users WHERE id = %s", (USER,))
        c.commit()


def test_user_memory_reads_the_database(stored_user):
    users = {u.id: u for u in memory.list_users()}
    assert (users[USER].messages, users[USER].facts) == (1, 1)
    mem = memory.user_memory(USER)
    assert (mem.messages, mem.notes) == (1, 0)
    assert [f.value for f in mem.current] == ["Bergen"]
    assert [f.value for f in mem.old] == ["Oslo"]
    assert mem.timelines == ["Lives in, oldest first: Oslo -> Bergen (now)"]
