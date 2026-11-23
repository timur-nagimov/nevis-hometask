import logging
import time
import traceback
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from http import HTTPStatus
from typing import Annotated, Any
from urllib.parse import quote, unquote_to_bytes
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import StatementError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app import __version__, db
from app.config import (
    DEFAULT_LIMIT,
    EXACT_SCORE_MIN,
    MAX_BODY_BYTES,
    MAX_ECHOED_ID_CHARS,
    MAX_LIMIT,
    MAX_Q_CHARS,
    RETRY_AFTER_SECONDS,
    SCORE_DECIMALS,
    Services,
    Settings,
)
from app.db import DatabaseUnavailable, Reason, create_schema, open_engine
from app.schemas import Client, ClientCreate, FieldError, Problem, QueryText, SearchItem
from app.search import ResultType
from app.search import search as run_search

log = logging.getLogger(__name__)
access_log = logging.getLogger('app.access')
router = APIRouter()

PROBLEM_JSON = 'application/problem+json'
INTERNAL_ERROR_DETAIL = 'Unexpected server error.'
UNAVAILABLE_DETAIL: dict[Reason, str] = {  # DatabaseUnavailable.reason -> `detail` of the 503
    'unreachable': 'The database is unreachable; retry shortly.',
    'busy': 'The service is busy; retry shortly.',
    'timeout': 'The database did not answer in time; retry shortly.',
}


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


def problem_doc(
    description: str, example_detail: str, status: int, errors: list[FieldError] | None = None
) -> dict[str, Any]:
    """OpenAPI entry for one problem+json status of an operation."""
    example = Problem(title=HTTPStatus(status).phrase, status=status, detail=example_detail, errors=errors)
    return {
        'description': description,
        'content': {
            PROBLEM_JSON: {
                'schema': {'$ref': '#/components/schemas/Problem'},
                'example': example.model_dump(exclude_none=True),
            }
        },
    }


async def on_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Raised by the framework and by the routes."""
    phrase = HTTPStatus(exc.status_code).phrase
    return problem(exc.status_code, None if exc.detail == phrase else str(exc.detail), exc.headers)


async def on_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    invalid_json = next((e for e in errors if e['type'] == 'json_invalid'), None)
    if invalid_json is not None:  # RFC 9110: 422 presumes syntactically correct content, so this is a 400
        reason, position = invalid_json['ctx']['error'], invalid_json['loc'][-1]
        return problem(400, f'Request body is not valid JSON: {reason} (character {position}).')
    # `input` and `ctx` are left out on purpose: they hold the submitted value (a whole document, personal
    # data), and FastAPI's default handler fails with a 500 when that value is NaN or a lone surrogate.
    fields = [FieldError(loc=list(e['loc']), msg=e['msg'], type=e['type']) for e in errors]
    return problem(422, f'{len(fields)} validation error(s).', errors=fields)


async def on_database_unavailable(request: Request, exc: DatabaseUnavailable) -> JSONResponse:
    log.warning(
        'database unavailable (%s) on %s %s: %s',
        exc.reason,
        request.method,
        quote(request.scope['path']),
        exc.cause or '-',
    )
    return problem(503, UNAVAILABLE_DETAIL[exc.reason], {'Retry-After': str(RETRY_AFTER_SECONDS)})


async def on_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    # One line here; uvicorn logs the traceback, because Starlette re-raises after sending this response.
    log.error('unexpected %s on %s %s', type(exc).__name__, request.method, quote(request.scope['path']))
    return problem(500, INTERNAL_ERROR_DETAIL)


async def on_database_error(request: Request, exc: StatementError) -> JSONResponse:
    """A database error's message can quote row values (PostgreSQL's DETAIL): log names and frames only."""
    diag = getattr(exc.orig, 'diag', None)
    log.error(
        'database error %s (SQLSTATE %s, table %s, column %s, constraint %s) on %s %s\n%s',
        type(exc).__name__,
        getattr(exc.orig, 'sqlstate', None),
        getattr(diag, 'table_name', None),
        getattr(diag, 'column_name', None),
        getattr(diag, 'constraint_name', None),
        request.method,
        quote(request.scope['path']),
        ''.join(traceback.format_tb(exc.__traceback__)),  # now: Starlette drops the traceback afterwards
    )
    return problem(500, INTERNAL_ERROR_DETAIL)


async def on_response_validation_error(request: Request, exc: ResponseValidationError) -> JSONResponse:
    """Its text would print the invalid response, a client's data: log locations and types only."""
    errors = [(e['loc'], e['type']) for e in exc.errors()]
    log.error('invalid response %s on %s %s', errors, request.method, quote(request.scope['path']))
    return problem(500, INTERNAL_ERROR_DETAIL)


async def require_json(request: Request) -> None:
    """A POST body must be declared as JSON: `curl -d` without a header sends a form. `async`: no thread."""
    if request.method != 'POST':
        return
    media_type = request.headers.get('content-type', '').partition(';')[0].strip().lower()
    if media_type != 'application/json':
        raise HTTPException(415, 'Send the body as application/json.', headers={'Accept': 'application/json'})


class AccessLogMiddleware:
    """One line per request: method, path WITHOUT the query string, status, duration.
    The query string is left out because search terms are names and e-mail addresses."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return
        started = time.perf_counter()
        status = 500  # what the client gets when the application raises instead of answering

        async def send_and_note_status(message: Message) -> None:
            nonlocal status
            if message['type'] == 'http.response.start':
                status = message['status']
            await send(message)

        try:
            await self.app(scope, receive, send_and_note_status)
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            # quote(): the path arrives decoded, and a line break in it must not start a forged log line
            access_log.info('%s %s %d %.1f ms', scope['method'], quote(scope['path']), status, elapsed_ms)


class SearchAPI(FastAPI):
    """FastAPI with the access log as the outermost layer, so that it logs the status the client receives,
    and an OpenAPI document whose errors are problem+json."""

    def build_middleware_stack(self) -> ASGIApp:
        return AccessLogMiddleware(super().build_middleware_stack())

    def openapi(self) -> dict[str, Any]:
        previous = self.openapi_schema
        spec = super().openapi()
        if spec is not previous:  # built anew; FastAPI rebuilds it after a route is added
            _problem_json_only(spec)
        return spec


def _problem_json_only(spec: dict[str, Any]) -> None:
    """Errors of this API are problem+json: declare Problem and FieldError, and drop FastAPI's own 422
    (application/json); routes that can answer 422 declare the problem+json one themselves."""
    schemas = spec['components']['schemas']
    schemas['Problem'] = Problem.model_json_schema(ref_template='#/components/schemas/{model}')
    schemas['FieldError'] = schemas['Problem'].pop('$defs')['FieldError']
    for operations in spec['paths'].values():
        for operation in operations.values():
            if 'application/json' in operation['responses'].get('422', {}).get('content', {}):
                del operation['responses']['422']
    for name in ('HTTPValidationError', 'ValidationError'):
        schemas.pop(name, None)


@router.get('/health', tags=['ops'], summary='Liveness check; does not touch the database')
async def health() -> dict[str, str]:
    """`async def` without I/O: answered on the event loop even when every worker thread is busy."""
    return {'status': 'ok'}


def build_services(settings: Settings) -> Services:
    """Open what request handling needs."""
    return Services(settings=settings, engine=open_engine(settings), embedder=None, concepts=None)


def close_services(services: Services) -> None:
    services.engine.dispose()


async def get_services(request: Request) -> Services:
    """The services the lifespan built. `async`: reading app.state needs no worker thread."""
    services: Services = request.app.state.services
    return services


ServicesDep = Annotated[Services, Depends(get_services)]  # in a route: `def route(services: ServicesDep)`

# OpenAPI documentation shared by the routes
_R422: dict[int | str, dict[str, Any]] = {
    422: problem_doc(
        'A field or parameter failed validation',
        '1 validation error(s).',
        422,
        errors=[
            FieldError(
                loc=['body', 'email'],
                msg='value is not a valid email address: An email address must have an @-sign.',
                type='value_error',
            )
        ],
    )
}
_WRITE_ERRORS: dict[int | str, dict[str, Any]] = {
    400: problem_doc(
        'Body is not parseable JSON',
        "Request body is not valid JSON: Expecting ',' delimiter (character 41).",
        400,
    ),
    413: {
        'description': f'Body larger than {MAX_BODY_BYTES:,} bytes (rejected before parsing)',
        'content': {
            'text/plain': {'schema': {'type': 'string'}, 'example': 'Content Too Large'},
            PROBLEM_JSON: {'schema': {'$ref': '#/components/schemas/Problem'}},
        },
    },
    415: problem_doc('`Content-Type` is not `application/json`', 'Send the body as application/json.', 415),
    **_R422,
}


def _created(what: str, example_location: str) -> dict[int | str, dict[str, Any]]:
    location = {
        'description': f'URI reference of the new {what.lower()}',
        'schema': {'type': 'string', 'format': 'uri-reference', 'example': example_location},
    }
    return {201: {'description': f'{what} created', 'headers': {'Location': location}}}


def _not_found(what: str) -> dict[int | str, dict[str, Any]]:
    return {
        404: problem_doc(
            f'{what} does not exist (unknown or malformed id)', f"{what} '123' does not exist.", 404
        )
    }


def parse_id(raw: str) -> UUID | None:
    """Ids are opaque strings for API clients: anything that is not a canonical UUID does not exist."""
    try:
        value = UUID(raw)
    except ValueError:
        return None
    return value if str(value) == raw.lower() else None


@router.post(
    '/clients',
    status_code=201,
    response_model=Client,
    tags=['clients'],
    summary='Create a client',
    responses={**_created('Client', '/clients/019aa0c5-6d6e-7c7b-9d55-2f1c3b0a4e11'), **_WRITE_ERRORS},
)
def create_client(body: ClientCreate, response: Response, services: ServicesDep) -> dict[str, Any]:
    """Creates a new client on every call: e-mail addresses are not unique, and POST is not idempotent."""
    client = db.insert_client(
        services.engine,
        first_name=body.first_name,
        last_name=body.last_name,
        email=body.email,
        description=body.description,
        social_links=body.social_links,
    )
    response.headers['Location'] = router.url_path_for('get_client', client_id=str(client['id']))
    return client


@router.get(
    '/clients/{client_id}',
    response_model=Client,
    tags=['clients'],
    summary='Get a client',
    responses=_not_found('Client'),
)
def get_client(client_id: str, services: ServicesDep) -> dict[str, Any]:
    """A client by id. An id that is not a UUID is answered like an unknown one: 404."""
    parsed = parse_id(client_id)
    client = db.get_client(services.engine, parsed) if parsed is not None else None
    if client is None:
        raise HTTPException(404, f"Client '{client_id[:MAX_ECHOED_ID_CHARS]}' does not exist.")
    return client


async def require_utf8_query(request: Request) -> None:
    """400 when the percent-decoded query string is not UTF-8. `async`: no worker thread.

    Starlette would quietly turn such bytes into U+FFFD. As a route dependency this runs before FastAPI
    validates q, type and limit, so `?q=%FF&limit=abc` is a 400, not a 422.
    """
    try:
        unquote_to_bytes(request.scope['query_string']).decode('utf-8', errors='strict')
    except UnicodeDecodeError:
        raise HTTPException(400, 'The query string is not valid UTF-8.') from None


@router.get(
    '/search',
    response_model=list[SearchItem],
    tags=['search'],
    summary='Search clients and documents',
    description=(
        f'Results matching `q`, best first. Order: `score` descending ({SCORE_DECIMALS} decimals), '
        'then `type`, then `id`. '
        f'`score` >= {EXACT_SCORE_MIN}: every query word occurs in the record (`exact`); '
        f'below {EXACT_SCORE_MIN}: a typo match (`fuzzy`).'
    ),
    dependencies=[Depends(require_utf8_query)],
    responses={
        200: {'description': 'Matches, best first; an empty array when nothing matches'},
        400: problem_doc('The query string is not valid UTF-8', 'The query string is not valid UTF-8.', 400),
        422: problem_doc(
            'A parameter failed validation',
            '1 validation error(s).',
            422,
            errors=[
                FieldError(
                    loc=['query', 'q'], msg='String should have at least 1 character', type='string_too_short'
                )
            ],
        ),
    },
)
def search(
    services: ServicesDep,
    q: Annotated[
        QueryText,
        Query(
            description='Search text. Whitespace runs collapse to one space and the ends are trimmed; '
            f'then 1-{MAX_Q_CHARS} characters, no control characters.',
            openapi_examples={
                'client': {'summary': 'Client by part of an e-mail domain', 'value': 'NevisWealth'},
                'document': {'summary': 'Document by meaning', 'value': 'address proof'},
            },
        ),
    ],
    type_: Annotated[
        ResultType | None,
        Query(alias='type', description='Return only this kind of result'),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=MAX_LIMIT, description='Maximum number of results, clients and documents together'),
    ] = DEFAULT_LIMIT,
) -> list[dict[str, Any]]:
    return run_search(services, q, type_, limit)


def _configure_logging(level: str) -> None:
    """The application's loggers at `level`; uvicorn, psycopg and every other library at WARNING."""
    logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    logging.getLogger().setLevel(logging.WARNING)
    for name in ('uvicorn', 'uvicorn.error'):  # uvicorn sets these two to INFO itself
        logging.getLogger(name).setLevel(logging.WARNING)
    logging.getLogger('app').setLevel(level)


def create_app(settings: Settings | None = None) -> FastAPI:
    """The application. Without `settings`, they are read from NEVIS_* variables when it starts (in the
    lifespan), never at import or here: importing and creating the app needs no configuration."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        active = settings if settings is not None else Settings()
        _configure_logging(active.log_level)
        created = create_schema(active)
        services = build_services(active)
        try:
            app.state.services = services
            log.info(
                'started: schema: %s | concepts: not loaded | model: not loaded | limits:'
                ' request body %d bytes, content %d characters, q %d characters, limit 1-%d (default %d)'
                ' | database: pool %d, wait %g s, connect timeout %d s, statement timeout %d ms | version %s',
                'created' if created else 'present',
                MAX_BODY_BYTES,
                active.max_content_chars,
                MAX_Q_CHARS,
                MAX_LIMIT,
                DEFAULT_LIMIT,
                active.db_pool_size,
                active.db_pool_timeout_seconds,
                active.db_connect_timeout_seconds,
                active.db_statement_timeout_ms,
                __version__,
            )
            yield
        finally:
            close_services(services)
            log.info('stopped')

    app = SearchAPI(
        title='Nevis Search API',
        version=__version__,
        lifespan=lifespan,
        max_body_size=MAX_BODY_BYTES,
        dependencies=[Depends(require_json)],
        exception_handlers={
            StarletteHTTPException: on_http_error,
            RequestValidationError: on_validation_error,
            DatabaseUnavailable: on_database_unavailable,
            StatementError: on_database_error,
            ResponseValidationError: on_response_validation_error,
            Exception: on_unexpected_error,
        },
    )
    app.include_router(router)
    return app
