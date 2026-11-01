"""Save the evaluation users' memory to db/snapshot.sql.gz, so a fresh database can start with it.

    poetry run python scripts/snapshot.py            # write db/snapshot.sql.gz (make snapshot)
    poetry run python scripts/snapshot.py --load     # load it into DATABASE_URL (make snapshot-load)

Only the evaluation's users (eval_<scenario id>, synthetic data) are written; chat users stay
private. The file is plain SQL with one COPY block per table and the sequences moved past the
copied ids, so it loads after db/schema.sql into an empty database: the Postgres container does
this by itself on its first start (docker compose up), `--load` does it for any other database.

Loading switches foreign-key checks off for the session (the rows were consistent in the source
database and refer to each other in both directions), which needs a superuser: the container's
user is one, and so is the default user of a Homebrew Postgres.
"""

import argparse
import gzip
import io
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "db" / "snapshot.sql.gz"
USERS = "eval\\_%"  # LIKE pattern: the evaluation's users only

# Every table that holds a user's memory, with the column that names the user. The order does
# not matter for loading (foreign keys are off), but parents first keeps the file readable.
TABLES = [
    ("users", "id"),
    ("summaries", "user_id"),
    ("messages", "user_id"),
    ("facts", "user_id"),
    ("relations", "user_id"),
    ("memory_events", "user_id"),
]
SEQUENCES = ["summaries", "messages", "facts", "relations", "memory_events"]


def header(users: int) -> str:
    return (
        "-- Memory of the evaluation users, written by scripts/snapshot.py "
        f"({users} users).\n"
        "-- Load after db/schema.sql into an empty database (see the script).\n"
        "SET client_encoding = 'UTF8';\n"
        "SET session_replication_role = replica;  -- no foreign-key checks while loading\n\n"
    )


def footer() -> str:
    """Foreign keys back on, and each id sequence moved past the copied rows (quietly)."""
    lines = [
        f"  PERFORM setval(pg_get_serial_sequence('{t}', 'id'), "
        f"COALESCE((SELECT max(id) FROM {t}), 0) + 1, false);"
        for t in SEQUENCES
    ]
    return (
        "\nSET session_replication_role = DEFAULT;\nDO $$\nBEGIN\n"
        + "\n".join(lines)
        + "\nEND\n$$;\n"
    )


def columns(conn, table: str) -> list[str]:
    rows = conn.execute(
        """SELECT column_name FROM information_schema.columns
           WHERE table_schema = 'public' AND table_name = %s ORDER BY ordinal_position""",
        (table,),
    ).fetchall()
    return [r[0] for r in rows]


def dump(conn, out: io.BufferedIOBase, pattern: str = USERS) -> int:
    """Write the SQL for every user whose id matches `pattern`. Returns the number of users."""
    ((users,),) = conn.execute(
        "SELECT count(*) FROM users WHERE id LIKE %s", (pattern,)
    ).fetchall()
    out.write(header(users).encode())
    for table, key in TABLES:
        cols = ", ".join(columns(conn, table))
        out.write(f"COPY {table} ({cols}) FROM stdin;\n".encode())
        query = f"COPY (SELECT {cols} FROM {table} WHERE {key} LIKE %s ORDER BY 1) TO STDOUT"
        with conn.cursor().copy(query, (pattern,)) as copy:
            for block in copy:
                out.write(bytes(block))
        out.write(b"\\.\n\n")
    out.write(footer().encode())
    return users


def write_snapshot(path: Path = SNAPSHOT) -> int:
    import psycopg

    from memory_system.core.config import DATABASE_URL

    with psycopg.connect(DATABASE_URL) as conn:
        # mtime=0: the same data gives the same file, so git sees no change after a re-run.
        with (
            open(path, "wb") as raw,
            gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz,
        ):
            return dump(conn, gz)


def load_snapshot(path: Path = SNAPSHOT) -> None:
    from memory_system.core.config import DATABASE_URL

    if shutil.which("psql") is None:
        sys.exit("psql is needed to load the snapshot (it comes with Postgres).")
    with gzip.open(path, "rb") as sql:
        subprocess.run(
            ["psql", DATABASE_URL, "-q", "-v", "ON_ERROR_STOP=1"],
            stdin=sql,
            check=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--load", action="store_true", help="load it instead of writing"
    )
    args = parser.parse_args()
    if args.load:
        if not SNAPSHOT.exists():
            sys.exit(
                f"No snapshot at {SNAPSHOT.relative_to(ROOT)}: run make snapshot first."
            )
        load_snapshot()
        print(f"Loaded {SNAPSHOT.relative_to(ROOT)}.")
    else:
        users = write_snapshot()
        size = SNAPSHOT.stat().st_size / 1e6
        print(f"Wrote {SNAPSHOT.relative_to(ROOT)}: {users} users, {size:.1f} MB.")


if __name__ == "__main__":
    main()
