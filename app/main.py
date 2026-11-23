"""The HTTP application: app factory, lifespan, routes, error handlers and the access log."""

import logging
from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import MAX_BODY_BYTES, Settings
from app.db import DatabaseUnavailable
from app.schemas import FieldError, Problem

log = logging.getLogger(__name__)

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


def create_app(settings: Settings | None = None) -> FastAPI:
    """The application. Without `settings`, they are read from NEVIS_* variables when it starts (in the
    lifespan, task 1.8), never at import or here: importing and creating the app needs no configuration."""
    app = FastAPI(
        title="Nevis Search API",
        version="0.1.0",
        max_body_size=MAX_BODY_BYTES,  # 413 above 2 MiB (B3: text/plain when Content-Length says so)
        dependencies=[Depends(require_json)],
        exception_handlers={
            StarletteHTTPException: on_http_error,
            RequestValidationError: on_validation_error,
            DatabaseUnavailable: on_database_unavailable,
            Exception: on_unexpected_error,
        },
    )
    return app
