"""The HTTP application: app factory, lifespan, routes, error handlers and the access log."""

import logging
import time
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from http import HTTPStatus
from typing import Annotated, Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import DEFAULT_LIMIT, MAX_BODY_BYTES, MAX_LIMIT, MAX_Q_CHARS, Services, Settings
from app.db import DatabaseUnavailable, create_schema, open_pool
from app.schemas import FieldError, Problem

log = logging.getLogger(__name__)
access_log = logging.getLogger("app.access")
router = APIRouter()

PROBLEM_JSON = "application/problem+json"
UNAVAILABLE_DETAIL = {  # DatabaseUnavailable.reason -> `detail` of the 503 (spec 13.2 B5)
    "unreachable": "The database is unreachable; retry shortly.",
    "busy": "The service is busy; retry shortly.",
    "timeout": "The database did not answer within 5 seconds; retry shortly.",
}


# ------------------------------------------------------------------------------ errors (RFC 9457)
def problem(
    status: int,
    detail: str | None = None,
    headers: Mapping[str, str] | None = None,
    errors: list[FieldError] | None = None,
) -> JSONResponse:
    """An application/problem+json response. `title` is the status phrase, `type` stays about:blank."""
    body = Problem(title=HTTPStatus(status).phrase, status=status, detail=detail, errors=errors)
    return JSONResponse(
        body.model_dump(exclude_none=True), status_code=status, headers=headers, media_type=PROBLEM_JSON
    )


def problem_doc(description: str, example_detail: str, status: int, **extra: Any) -> dict[str, Any]:
    """OpenAPI entry for one problem+json status of an operation, for `responses=` (used from step 2)."""
    example = Problem(title=HTTPStatus(status).phrase, status=status, detail=example_detail, **extra)
    return {
        "description": description,
        "content": {
            PROBLEM_JSON: {
                "schema": {"$ref": "#/components/schemas/Problem"},
                "example": example.model_dump(exclude_none=True),
            }
        },
    }


async def on_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Raised by the framework (unknown path 404, wrong method 405, chunked body over the cap 413) and by
    the routes (404 for an unknown id, 415 from require_json)."""
    phrase = HTTPStatus(exc.status_code).phrase
    return problem(exc.status_code, None if exc.detail == phrase else str(exc.detail), exc.headers)


async def on_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    invalid_json = next((e for e in errors if e["type"] == "json_invalid"), None)
    if invalid_json is not None:  # RFC 9110: 422 presumes syntactically correct content, so this is a 400
        reason, position = invalid_json["ctx"]["error"], invalid_json["loc"][-1]
        return problem(400, f"Request body is not valid JSON: {reason} (character {position}).")
    # `input` and `ctx` are left out on purpose: they hold the submitted value (a whole document, personal
    # data), and FastAPI's default handler fails with a 500 when that value is NaN or a lone surrogate.
    fields = [FieldError(loc=list(e["loc"]), msg=e["msg"], type=e["type"]) for e in errors]
    return problem(422, f"{len(fields)} validation error(s).", errors=fields)


async def on_database_unavailable(request: Request, exc: DatabaseUnavailable) -> JSONResponse:
    log.warning("database unavailable (%s) on %s %s", exc.reason, request.method, request.url.path)
    return problem(503, UNAVAILABLE_DETAIL[exc.reason], {"Retry-After": "5"})


async def on_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    # One line here; uvicorn logs the traceback, because Starlette re-raises after sending this response.
    log.error("unexpected %s on %s %s", type(exc).__name__, request.method, request.url.path)
    return problem(500, "Unexpected server error.")


# ----------------------------------------------------------------------- checks on every request
async def require_json(request: Request) -> None:
    """A POST body must be declared as JSON: `curl -d` without a header sends a form. `async`: no thread."""
    if request.method != "POST":
        return
    media_type = request.headers.get("content-type", "").partition(";")[0].strip().lower()
    if media_type != "application/json":
        raise HTTPException(415, "Send the body as application/json.", headers={"Accept": "application/json"})


class AccessLogMiddleware:
    """One line per request: method, path WITHOUT the query string, status, duration (spec section 9).
    The query string is left out because search terms are names and e-mail addresses."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = time.perf_counter()
        status = 500  # what the client gets when the application raises instead of answering

        async def send_and_note_status(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_and_note_status)
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            # quote(): the path arrives decoded, and a line break in it must not start a forged log line
            access_log.info("%s %s %d %.1f ms", scope["method"], quote(scope["path"]), status, elapsed_ms)


class FastAPIWithAccessLog(FastAPI):
    """FastAPI with the access log as the outermost layer, so that it logs the status the client receives.
    The framework's body limit sits outside every middleware passed to FastAPI and may replace a route's
    answer by 413 (a body over 2 MiB that the route never reads)."""

    def build_middleware_stack(self) -> ASGIApp:
        return AccessLogMiddleware(super().build_middleware_stack())


# --------------------------------------------------------------------------------------- routes
@router.get("/health", tags=["ops"], summary="Liveness check; does not touch the database")
async def health() -> dict[str, str]:
    """`async def` without I/O: answered on the event loop even when every worker thread is busy (B4)."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------------- application
def build_services(settings: Settings) -> Services:
    """Open what request handling needs. The schema must exist already (`app.db.create_schema`).

    Step 3 adds the embedder and the concept map; until then both are None.
    """
    return Services(settings=settings, pool=open_pool(settings.database_url), embedder=None, concepts=None)


def close_services(services: Services) -> None:
    services.pool.close()


async def get_services(request: Request) -> Services:
    """Dependency for the routes of later steps. `async`: reading app.state needs no worker thread."""
    services: Services = request.app.state.services
    return services


ServicesDep = Annotated[Services, Depends(get_services)]  # in a route: `def route(services: ServicesDep)`


def _configure_logging(level: str) -> None:
    """The application's loggers at `level`; uvicorn, psycopg and every other library at WARNING."""
    logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger().setLevel(logging.WARNING)
    for name in ("uvicorn", "uvicorn.error"):  # uvicorn sets these two to INFO itself
        logging.getLogger(name).setLevel(logging.WARNING)
    logging.getLogger("app").setLevel(level)


def create_app(settings: Settings | None = None) -> FastAPI:
    """The application. Without `settings`, they are read from NEVIS_* variables when it starts (in the
    lifespan), never at import or here: importing and creating the app needs no configuration."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        active = settings if settings is not None else Settings()
        _configure_logging(active.log_level)
        created = create_schema(active.database_url)  # before the pool, which needs the `vector` type
        services = build_services(active)
        try:
            app.state.services = services
            log.info(
                "started: schema: %s | concepts: not loaded | model: not loaded | limits:"
                " request body %d bytes, content %d characters, q %d characters, limit 1-%d (default %d)",
                "created" if created else "present",
                MAX_BODY_BYTES,
                active.max_content_chars,
                MAX_Q_CHARS,
                MAX_LIMIT,
                DEFAULT_LIMIT,
            )
            yield
        finally:
            close_services(services)

    app = FastAPIWithAccessLog(
        title="Nevis Search API",
        version="0.1.0",
        lifespan=lifespan,
        max_body_size=MAX_BODY_BYTES,  # 413 above 2 MiB (B3: text/plain when Content-Length says so)
        dependencies=[Depends(require_json)],
        exception_handlers={
            StarletteHTTPException: on_http_error,
            RequestValidationError: on_validation_error,
            DatabaseUnavailable: on_database_unavailable,
            Exception: on_unexpected_error,
        },
    )
    app.include_router(router)
    return app
