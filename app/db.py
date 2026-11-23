from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import TupleRow, dict_row
from psycopg_pool import ConnectionPool, PoolTimeout

SCHEMA_FILE = Path(__file__).parent / 'sql' / 'schema.sql'

# libpq options of every pooled connection
POOL_CONNECTION_OPTIONS: dict[str, str | int] = {
    'connect_timeout': 3,  # seconds to open a connection
    'options': '-c statement_timeout=5000',  # the server cancels a statement after 5 s: QueryCanceled
    'keepalives': 1,  # TCP keepalives notice a server or a network that went away
    'keepalives_idle': 30,
    'keepalives_interval': 10,
    'keepalives_count': 3,
}

Pool = ConnectionPool[psycopg.Connection[TupleRow]]

Reason = Literal['unreachable', 'busy', 'timeout']


class DatabaseUnavailable(Exception):
    def __init__(self, reason: Reason) -> None:
        super().__init__(reason)
        self.reason: Reason = reason


def create_schema(database_url: str) -> bool:
    """Create the extensions, functions and tables of app/sql/schema.sql if the database has none yet.

    Returns True when it created them, False when they were there already. One transaction: a failure
    leaves nothing behind. There are no migrations: after a change to schema.sql, start from an empty
    database.
    """
    with psycopg.connect(database_url, connect_timeout=3) as conn:  # commit on success, rollback on error
        if conn.execute("SELECT to_regclass('public.clients') IS NOT NULL").fetchone() == (True,):
            return False
        conn.execute(SCHEMA_FILE.read_bytes())  # several statements, no parameters
    return True


def open_pool(database_url: str) -> Pool:
    """The connection pool with the options."""
    return ConnectionPool(
        database_url,
        kwargs=POOL_CONNECTION_OPTIONS,
        configure=register_vector,  # numpy arrays <-> the `vector` type
        min_size=0,  # no connections kept in reserve: fewer stale ones to trip over after a database restart
        max_size=8,
        max_idle=60,  # close connections idle for a minute
        timeout=5,  # wait at most 5 s for a free connection, then PoolTimeout
        reconnect_timeout=5,
        check=ConnectionPool.check_connection,  # test a connection before handing it out
        open=True,
        name='nevis',
    )


@contextmanager
def _connection(pool: Pool) -> Iterator[psycopg.Connection[TupleRow]]:
    """One transaction on a pooled connection: committed when the block ends, rolled back if it raises."""
    try:
        with pool.connection() as conn:
            yield conn
    except PoolTimeout as exc:
        raise DatabaseUnavailable(_why_no_connection(pool)) from exc
    except psycopg.errors.QueryCanceled as exc:  # statement_timeout expired
        raise DatabaseUnavailable('timeout') from exc
    except psycopg.OperationalError as exc:  # connection refused, lost or reset
        raise DatabaseUnavailable('unreachable') from exc


def _why_no_connection(pool: Pool) -> Reason:
    """No pooled connection within 5 s: either all of them are in use (busy) or none can be opened."""
    conninfo = pool.conninfo if isinstance(pool.conninfo, str) else pool.conninfo()
    try:
        psycopg.connect(conninfo, connect_timeout=3).close()
    except psycopg.OperationalError:
        return 'unreachable'
    return 'busy'


def insert_client(
    pool: Pool,
    *,
    first_name: str,
    last_name: str,
    email: str,
    description: str,
    social_links: list[str],
) -> dict[str, Any]:
    """Insert one client and return it as the API shows it. Committed before it returns."""
    with _connection(pool) as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            'INSERT INTO clients (first_name, last_name, email, description, social_links)'
            ' VALUES (%s, %s, %s, %s, %s)'
            ' RETURNING id, first_name, last_name, email, description, social_links',
            (first_name, last_name, email, description, social_links),
        )
        row = cur.fetchone()
    if row is None:  # INSERT ... RETURNING always yields the row; the check is for mypy
        raise RuntimeError('INSERT ... RETURNING returned no row')
    return row


def get_client(pool: Pool, client_id: UUID) -> dict[str, Any] | None:
    """The client with this id as the API shows it, or None."""
    with _connection(pool) as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            'SELECT id, first_name, last_name, email, description, social_links FROM clients WHERE id = %s',
            (client_id,),
        )
        return cur.fetchone()
