from pgvector.psycopg import register_vector
from psycopg_pool import ConnectionPool

from memory_system.config import DATABASE_URL

_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    """Lazily create one shared connection pool with pgvector registered."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            DATABASE_URL,
            min_size=1,
            max_size=5,
            configure=register_vector,
            open=True,
        )
    return _pool
