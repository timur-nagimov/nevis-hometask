"""What migrations/001_init.sql promises (spec section 4, 13.2 B5): text functions that ignore the database
locale, the generated search columns, uuid v7 ids, and an app_meta table that holds at most one row."""

from collections.abc import Iterator

import psycopg
import pytest

from app.db import migrate
from tests.integration.helpers import new_database


@pytest.fixture(
    scope="module", params=["", "TEMPLATE template0 LOCALE 'C'"], ids=["default locale", "LOCALE C"]
)
def locale_dsn(request: pytest.FixtureRequest, admin_dsn: str) -> Iterator[str]:
    with new_database(admin_dsn, request.param) as dsn:
        migrate(dsn)
        yield dsn


def value(dsn: str, query: str, *params: object) -> object:
    with psycopg.connect(dsn) as conn:
        row = conn.execute(query, params).fetchone()
    assert row is not None
    return row[0]


def test_text_functions_do_not_depend_on_the_database_locale(locale_dsn: str) -> None:
    # spec section 4: in a LOCALE 'C' database [[:alnum:]] alone would turn "ü" into a space
    text = "Zürich Versicherung: Łódź (LV-7734-0921-KX)"
    assert (
        value(locale_dsn, "SELECT public.strip_punct(%s)", text)
        == "Zürich Versicherung Łódź LV 7734 0921 KX "
    )
    assert value(locale_dsn, "SELECT public.search_normalize(%s)", "José MÜLLER-Østergård") == (
        "jose muller-ostergard"
    )
    assert value(locale_dsn, "SELECT public.search_normalize(%s)", "Straße") == "strasse"


def test_generated_columns_and_uuid7_ids(fresh_dsn: str) -> None:
    with psycopg.connect(fresh_dsn) as conn:
        row = conn.execute(
            "INSERT INTO clients (first_name, last_name, email)"
            " VALUES ('José', 'Müller', 'Jose.Mueller@NevisWealth.com')"
            " RETURNING id, search_text, uuid_extract_version(id)"
        ).fetchone()
        assert row is not None
        client_id, search_text, version = row
        conn.execute(
            "INSERT INTO documents (client_id, title, content, tags_text, summary, summary_method)"
            " VALUES (%s, 'Zürich Versicherung', 'Police LV-7734-0921-KX', 'proof of address, utility bill.',"
            " 'Police LV-7734-0921-KX', 'extractive')",
            (client_id,),
        )

        def matches(column: str, query: str) -> bool:
            hit = conn.execute(
                f"SELECT {column} @@ plainto_tsquery('english', public.strip_punct(%s)) FROM documents",
                (query,),
            ).fetchone()
            assert hit is not None
            return bool(hit[0])

        assert search_text == "jose muller jose.mueller@neviswealth.com "
        assert version == 7
        assert matches("fts_text", "zürich")
        assert matches("fts_text", "7734")
        assert not matches("fts_text", "utility bill")  # tags are searched through `fts` only
        assert matches("fts", "utility bill")


def test_app_meta_holds_at_most_one_row(fresh_dsn: str) -> None:
    with psycopg.connect(fresh_dsn, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO app_meta (model_revision, tokenizer_settings, concepts_sha256)"
            " VALUES ('r1', '{}', NULL)"
        )
        with pytest.raises(psycopg.errors.UniqueViolation):
            conn.execute("INSERT INTO app_meta (model_revision, tokenizer_settings) VALUES ('r2', '{}')")
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(
                "INSERT INTO app_meta (id, model_revision, tokenizer_settings) VALUES (2, 'r2', '{}')"
            )
