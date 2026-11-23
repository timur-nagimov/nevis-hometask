"""PostgreSQL: the schema, the connection pool, and (from step 2) every SQL call.

Every public function that touches the database owns its transaction and has committed before it returns,
so the API never answers before the row it reports is visible to other connections (spec section 4).
"""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import TupleRow
from psycopg_pool import ConnectionPool, PoolTimeout

SCHEMA_FILE = Path(__file__).parent / "sql" / "schema.sql"

# libpq options of every pooled connection (spec 13.2 B5)
POOL_CONNECTION_OPTIONS: dict[str, str | int] = {
    "connect_timeout": 3,  # seconds to open a connection
    "options": "-c statement_timeout=5000",  # the server cancels a statement after 5 s: QueryCanceled
    "keepalives": 1,  # TCP keepalives notice a server or a network that went away
    "keepalives_idle": 30,
    "keepalives_interval": 10,
    "keepalives_count": 3,
}

Pool = ConnectionPool[psycopg.Connection[TupleRow]]

Reason = Literal["unreachable", "busy", "timeout"]


class DatabaseUnavailable(Exception):
    """The database cannot serve this request now; the API answers 503 with `Retry-After: 5`."""

    def __init__(self, reason: Reason) -> None:
        super().__init__(reason)
        self.reason: Reason = reason


def create_schema(database_url: str) -> bool:
    """Create the extensions, functions and tables of app/sql/schema.sql if the database has none yet.

    Returns True when it created them, False when they were there already. One transaction: a failure
    leaves nothing behind. There are no migrations: after a change to schema.sql, start from an empty
    database (`docker compose down -v`).
    """
    with psycopg.connect(database_url, connect_timeout=3) as conn:  # commit on success, rollback on error
        if conn.execute("SELECT to_regclass('public.clients') IS NOT NULL").fetchone() == (True,):
            return False
        conn.execute(SCHEMA_FILE.read_bytes())  # several statements, no parameters
    return True


def open_pool(database_url: str) -> Pool:
    """The connection pool of spec section 4 with the options of 13.2 B5.

    Call `create_schema` first: every new connection registers the `vector` type, which the schema creates.
    """
    return ConnectionPool(
        database_url,
        kwargs=POOL_CONNECTION_OPTIONS,
        configure=register_vector,  # numpy arrays <-> the `vector` type
        min_size=0,  # no connection kept in reserve: nothing stale to trip over after a database restart
        max_size=8,
        max_idle=60,  # close connections idle for a minute
        timeout=5,  # wait at most 5 s for a free connection, then PoolTimeout
        # give up a failed reconnect after 5 s, so the next request tries at once; the default 300 s backs off
        # to 64 s and more between attempts, and requests stay at 503 long after the database is back
        reconnect_timeout=5,
        check=ConnectionPool.check_connection,  # test a connection before handing it out
        open=True,
        name="nevis",
    )


@contextmanager
def _connection(pool: Pool) -> Iterator[psycopg.Connection[TupleRow]]:
    """One transaction on a pooled connection: committed when the block ends, rolled back if it raises.

    Every SQL function of later steps runs inside it, so a database failure always reaches the API as
    DatabaseUnavailable, never as a 500.
    """
    try:
        with pool.connection() as conn:
            yield conn
    except PoolTimeout as exc:
        raise DatabaseUnavailable(_why_no_connection(pool)) from exc
    except psycopg.errors.QueryCanceled as exc:  # statement_timeout expired
        raise DatabaseUnavailable("timeout") from exc
    except psycopg.OperationalError as exc:  # connection refused, lost or reset
        raise DatabaseUnavailable("unreachable") from exc


def _why_no_connection(pool: Pool) -> Reason:
    """No pooled connection within 5 s: either all of them are in use (busy) or none can be opened
    (unreachable). The pool raises PoolTimeout in both cases; one direct connection attempt (at most
    3 s) tells them apart."""
    conninfo = pool.conninfo if isinstance(pool.conninfo, str) else pool.conninfo()
    try:
        psycopg.connect(conninfo, connect_timeout=3).close()
    except psycopg.OperationalError:
        return "unreachable"
    return "busy"
