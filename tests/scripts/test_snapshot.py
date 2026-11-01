"""The database snapshot (scripts/snapshot.py): written, then loaded back the way the Postgres
container loads it on its first start (psql, after the schema).

Needs the Postgres database from .env, like the other DB tests, and psql for the loading half.
"""

import gzip
import importlib.util
import io
import shutil
import subprocess
from pathlib import Path

import pytest

from memory_system.core.config import DATABASE_URL
from memory_system.core.db import get_pool

spec = importlib.util.spec_from_file_location(
    "snapshot", Path(__file__).resolve().parents[2] / "scripts" / "snapshot.py"
)
snapshot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snapshot)

USER = "eval_test_snapshot"
CHAT_USER = "test_snapshot_chat"


def delete_users(conn):
    conn.execute("DELETE FROM users WHERE id IN (%s, %s)", (USER, CHAT_USER))
    conn.commit()


@pytest.fixture
def conn():
    with get_pool().connection() as c:
        delete_users(c)
        for user in (USER, CHAT_USER):
            c.execute("INSERT INTO users (id) VALUES (%s)", (user,))
        (message,) = c.execute(
            "INSERT INTO messages (user_id, role, content) "
            "VALUES (%s, 'user', 'I moved to Bergen') RETURNING id",
            (USER,),
        ).fetchone()
        (new,) = c.execute(
            "INSERT INTO facts (user_id, relation, value, source_message_id) "
            "VALUES (%s, 'lives_in', 'Bergen', %s) RETURNING id",
            (USER, message),
        ).fetchone()
        c.execute(
            "INSERT INTO facts (user_id, relation, value, status, superseded_by) "
            "VALUES (%s, 'lives_in', 'Oslo', 'superseded', %s)",
            (USER, new),
        )
        c.execute(
            "INSERT INTO messages (user_id, role, content) "
            "VALUES (%s, 'user', 'private chat')",
            (CHAT_USER,),
        )
        c.commit()
        yield c
        delete_users(c)


def written(conn, pattern=snapshot.USERS) -> str:
    out = io.BytesIO()
    snapshot.dump(conn, out, pattern)
    return out.getvalue().decode()


def test_only_evaluation_users_are_written(conn):
    sql = written(conn)
    assert USER in sql
    assert CHAT_USER not in sql and "private chat" not in sql
    assert sql.count("COPY ") == len(snapshot.TABLES)
    assert "session_replication_role = replica" in sql


@pytest.mark.skipif(shutil.which("psql") is None, reason="needs psql")
def test_a_snapshot_loads_back_with_its_links(conn):
    sql = written(conn, USER)
    delete_users(conn)
    subprocess.run(
        ["psql", DATABASE_URL, "-q", "-v", "ON_ERROR_STOP=1"],
        input=gzip.decompress(gzip.compress(sql.encode())),
        check=True,
    )
    rows = conn.execute(
        """SELECT old.value, new.value FROM facts old
           JOIN facts new ON new.id = old.superseded_by
           WHERE old.user_id = %s""",
        (USER,),
    ).fetchall()
    assert rows == [("Oslo", "Bergen")]  # the superseded_by link survived
    # The sequences were moved past the copied ids: a new row gets a fresh one.
    conn.execute(
        "INSERT INTO messages (user_id, role, content) VALUES (%s, 'user', 'x')",
        (USER,),
    )
    conn.commit()
