"""PostgreSQL: the migrations runner, the connection pool, and (from step 2) every SQL call.

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

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
MIGRATIONS_LOCK = 0x4E45564953  # "NEVIS": every starting process takes this advisory lock before migrating
EXTENSIONS = ("vector", "pg_trgm", "unaccent")  # created by migrations/001_init.sql

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


class UnknownSchemaVersion(RuntimeError):
    """The database records a migration this build does not have: older code on a newer database."""


class MissingPrivilege(RuntimeError):
    """The database role may not create what the migrations need (in practice: the extensions)."""


def migrate(database_url: str, migrations_dir: Path = MIGRATIONS_DIR) -> list[int]:
    """Apply every NNN_*.sql in `migrations_dir` whose number is not recorded yet; return the numbers applied.

    One transaction under an advisory lock: processes that start together queue on the lock, the first one
    applies everything and the others find nothing left to do. A failing migration leaves nothing behind.
    """
    known = {int(path.name[:3]): path for path in migrations_dir.glob("[0-9][0-9][0-9]_*.sql")}
    applied: list[int] = []
    with psycopg.connect(database_url, connect_timeout=3) as conn:  # commit on success, rollback on error
        try:
            conn.execute("SELECT pg_advisory_xact_lock(%s)", (MIGRATIONS_LOCK,))
            # created under the lock too: concurrent CREATE TABLE IF NOT EXISTS statements collide
            conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations"
                " (version int PRIMARY KEY, applied_at timestamptz DEFAULT now())"
            )
            recorded = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
            if unknown := sorted(recorded - known.keys()):
                raise UnknownSchemaVersion(
                    f"the database has migration(s) {unknown} that this build does not know (older code"
                    " on a newer database). Deploy the matching build, or, for local data only:"
                    " docker compose down -v"
                )
            for version in sorted(known.keys() - recorded):
                conn.execute(known[version].read_bytes())  # several statements, no parameters
                conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
                applied.append(version)
        except psycopg.errors.InsufficientPrivilege as exc:
            raise MissingPrivilege(_privilege_message(conn, exc)) from exc
    return applied


def _privilege_message(conn: psycopg.Connection[TupleRow], exc: psycopg.Error) -> str:
    error = str(exc).partition("\n")[0]
    statements = " ".join(f"CREATE EXTENSION IF NOT EXISTS {name};" for name in EXTENSIONS)
    return (
        f"database role {conn.info.user!r} may not run the migrations ({error})."
        f" They need the extensions {', '.join(EXTENSIONS)}, and only a superuser may create `vector`."
        f" Run once as a superuser in database {conn.info.dbname!r}: {statements}"
        " The role must also own the database (or have CREATE on schema public)."
    )


def open_pool(database_url: str) -> Pool:
    """The connection pool of spec section 4 with the options of 13.2 B5.

    Call `migrate` first: every new connection registers the `vector` type, which migration 001 creates.
    """
    return ConnectionPool(
        database_url,
        kwargs=POOL_CONNECTION_OPTIONS,
        configure=register_vector,  # numpy arrays <-> the `vector` type
        min_size=0,  # no connection kept in reserve: nothing stale to trip over after a database restart
        max_size=8,
        max_idle=60,  # close connections idle for a minute
        timeout=5,  # wait at most 5 s for a free connection, then PoolTimeout
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
