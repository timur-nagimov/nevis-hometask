"""Helpers for the integration tests.

Step 2 adds `post_client(client, **fields) -> dict`; step 3 adds `post_document(client, client_id, title,
content) -> dict` (DEVELOPMENT_PLAN.md section 4.3).
"""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo


@contextmanager
def new_database(admin_dsn: str, options: str = "") -> Iterator[str]:
    """An empty database `nevis_t_<hex>`, created with `CREATE DATABASE ... <options>` and dropped when the
    block ends. Yields its connection string."""
    name = f"nevis_t_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {} " + options).format(sql.Identifier(name)))
    try:
        yield make_conninfo(admin_dsn, dbname=name)
    finally:
        with psycopg.connect(admin_dsn, autocommit=True) as admin:
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
