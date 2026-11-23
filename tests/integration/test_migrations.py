"""The migrations runner (spec section 4, 13.2 B5): a fresh database, a restart, eight simultaneous starts,
later migrations, a database newer than the build, and a role that may not create the extensions."""

import threading
import uuid
from pathlib import Path

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo

from app.db import MIGRATIONS_DIR, MissingPrivilege, UnknownSchemaVersion, migrate
from tests.integration.helpers import new_database

# The numbers of the migration files of this build ([1] in step 1). The tests compare against this list,
# never against a literal, so a new migration file (option A adds 002) needs no test change.
ALL_MIGRATIONS = sorted(int(path.name[:3]) for path in MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql"))
NEWER = max(ALL_MIGRATIONS) + 1  # a migration only a newer build has


def column(dsn: str, query: str) -> list[object]:
    with psycopg.connect(dsn) as conn:
        return [row[0] for row in conn.execute(query)]


def test_fresh_database_gets_the_whole_schema(admin_dsn: str) -> None:
    with new_database(admin_dsn) as dsn:
        assert migrate(dsn) == ALL_MIGRATIONS

        assert column(dsn, "SELECT version FROM schema_migrations ORDER BY 1") == ALL_MIGRATIONS
        assert column(dsn, "SELECT extname FROM pg_extension WHERE extname <> 'plpgsql' ORDER BY 1") == [
            "pg_trgm",
            "unaccent",
            "vector",
        ]
        assert column(dsn, "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY 1") == [
            "app_meta",
            "clients",
            "document_chunks",
            "documents",
            "schema_migrations",
        ]


def test_second_start_applies_nothing(fresh_dsn: str) -> None:
    assert migrate(fresh_dsn) == []
    assert migrate(fresh_dsn) == []
    assert column(fresh_dsn, "SELECT version FROM schema_migrations ORDER BY 1") == ALL_MIGRATIONS


@pytest.mark.parametrize("attempt", range(3))
def test_eight_simultaneous_starts_apply_the_migration_once(admin_dsn: str, attempt: int) -> None:
    with new_database(admin_dsn) as dsn:
        start = threading.Barrier(8)
        applied: list[list[int]] = []
        errors: list[BaseException] = []

        def starter() -> None:
            start.wait()  # all eight call migrate() at the same moment
            try:
                applied.append(migrate(dsn))
            except BaseException as error:
                errors.append(error)

        threads = [threading.Thread(target=starter) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert errors == []
        assert sorted(applied) == [[], [], [], [], [], [], [], ALL_MIGRATIONS]
        assert column(dsn, "SELECT version FROM schema_migrations ORDER BY 1") == ALL_MIGRATIONS


def test_later_migrations_are_applied_in_order_and_keep_the_data(admin_dsn: str, tmp_path: Path) -> None:
    (tmp_path / "001_notes.sql").write_text(
        "CREATE TABLE notes (body text); INSERT INTO notes VALUES ('kept');"
    )
    (tmp_path / "README.md").write_text("not a migration")
    with new_database(admin_dsn) as dsn:
        assert migrate(dsn, tmp_path) == [1]

        (tmp_path / "003_index.sql").write_text("CREATE INDEX notes_author_idx ON notes (author);")
        (tmp_path / "002_author.sql").write_text("ALTER TABLE notes ADD COLUMN author text DEFAULT 'nobody';")

        assert migrate(dsn, tmp_path) == [2, 3]
        assert migrate(dsn, tmp_path) == []
        assert column(dsn, "SELECT body || ' by ' || author FROM notes") == ["kept by nobody"]


def test_database_newer_than_the_build_is_refused(fresh_dsn: str) -> None:
    with psycopg.connect(fresh_dsn) as conn:
        conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (NEWER,))

    with pytest.raises(UnknownSchemaVersion, match=rf"migration\(s\) \[{NEWER}\]"):
        migrate(fresh_dsn)


@pytest.mark.parametrize("owns_database", [True, False], ids=["database owner", "no rights"])
def test_role_that_may_not_create_the_extensions_gets_a_clear_error(
    admin_dsn: str, owns_database: bool
) -> None:
    role = f"nevis_t_role_{uuid.uuid4().hex[:8]}"  # LOGIN, not a superuser: may not create `vector`
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD 'secret'").format(sql.Identifier(role)))
    try:
        with new_database(admin_dsn, f"OWNER {role}" if owns_database else "") as dsn:
            with pytest.raises(MissingPrivilege) as error:
                migrate(make_conninfo(dsn, user=role, password="secret"))

            message = str(error.value)
            for word in (role, "vector", "pg_trgm", "unaccent"):
                assert word in message
            assert column(dsn, "SELECT count(*) FROM pg_extension WHERE extname = 'vector'") == [0]
    finally:
        with psycopg.connect(admin_dsn, autocommit=True) as admin:
            admin.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(role)))
