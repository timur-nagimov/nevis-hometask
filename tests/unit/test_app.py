"""Health check, access log, logging levels, settings timing and the entry point; no database needed
(the lifespan is not started, except in the test that shows it fails without settings)."""

import inspect
import logging
import re
from typing import Any

import pytest
import uvicorn
from fastapi.testclient import TestClient
from pydantic import ValidationError

import app.__main__ as entry_point
from app.config import MAX_BODY_BYTES
from app.main import _configure_logging, create_app, health


@pytest.fixture
def client() -> TestClient:
    app = create_app()

    @app.get("/broken")
    def broken() -> None:
        raise RuntimeError("boom")

    return TestClient(app, raise_server_exceptions=False)


def access_lines(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [record.getMessage() for record in caplog.records if record.name == "app.access"]


def test_health_answers_without_a_database(client: TestClient) -> None:
    response = client.get("/health")  # the lifespan never ran: no settings, no pool, no database

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"status": "ok"}


def test_health_is_async_so_it_never_waits_for_a_worker_thread() -> None:
    assert inspect.iscoroutinefunction(health)  # spec 13.2 B4


def test_access_log_has_method_path_status_and_duration_but_no_query_string(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="app")

    client.get("/health?q=john.doe%40neviswealth.com&token=secret-value")

    [line] = access_lines(caplog)
    assert re.fullmatch(r"GET /health 200 \d+\.\d ms", line)


def test_access_log_stays_one_line_whatever_the_path_contains(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="app")

    client.get("/nope%0A2026-11-20 INFO app.access: GET /forged 200 0.1 ms")

    [line] = access_lines(caplog)
    assert line.startswith(
        "GET /nope%0A2026-11-20%20INFO%20app.access%3A%20GET%20/forged%20200%200.1%20ms 404 "
    )


def test_access_log_records_errors_too(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="app")

    client.get("/nope?q=john")
    client.post("/health", content=b"{}", headers={"content-type": "application/json"})
    client.get("/broken")

    assert [re.sub(r" \d+\.\d ms$", "", line) for line in access_lines(caplog)] == [
        "GET /nope 404",
        "POST /health 405",
        "GET /broken 500",
    ]


def test_access_log_has_the_413_the_client_gets_for_a_body_over_the_cap(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="app")
    oversized = b"x" * (MAX_BODY_BYTES + 1)

    # No route reads this body: the framework's body limit answers 413 itself (B3), not the route (405, 200)
    responses = [
        client.post("/health", content=oversized, headers={"content-type": "application/json"}),
        client.request("GET", "/health", content=oversized),
    ]

    assert [response.status_code for response in responses] == [413, 413]
    assert [re.sub(r" \d+\.\d ms$", "", line) for line in access_lines(caplog)] == [
        "POST /health 413",
        "GET /health 413",
    ]


def test_libraries_log_at_warning_and_the_application_at_its_level() -> None:
    names = ("", "uvicorn", "uvicorn.error", "app")
    saved = {name: logging.getLogger(name).level for name in names}
    try:
        _configure_logging("DEBUG")

        assert logging.getLogger().level == logging.WARNING
        assert logging.getLogger("uvicorn").level == logging.WARNING
        assert logging.getLogger("uvicorn.error").level == logging.WARNING
        assert logging.getLogger("psycopg.pool").getEffectiveLevel() == logging.WARNING
        assert logging.getLogger("app").level == logging.DEBUG
    finally:
        for name, level in saved.items():
            logging.getLogger(name).setLevel(level)


def test_settings_are_read_when_the_app_starts_not_when_it_is_created(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NEVIS_DATABASE_URL", raising=False)

    app = create_app()  # importing and creating the application needs no configuration

    with pytest.raises(ValidationError, match="database_url"), TestClient(app):
        pass  # entering the client runs the lifespan, which reads the settings


def test_entry_point_runs_the_factory_with_one_worker_and_no_uvicorn_access_log(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[Any, dict[str, Any]]] = []
    monkeypatch.setattr(uvicorn, "run", lambda app, **options: calls.append((app, options)))

    entry_point.main()

    assert calls == [
        (
            "app.main:create_app",
            {"factory": True, "host": "0.0.0.0", "port": 8000, "workers": 1, "access_log": False},
        )
    ]
