from datetime import UTC, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

import email_validator
from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints

from app.config import (
    DEFAULT_MAX_CONTENT_CHARS,
    EXACT_SCORE_MIN,
    MAX_DESCRIPTION_CHARS,
    MAX_EMAIL_CHARS,
    MAX_NAME_CHARS,
    MAX_Q_CHARS,
    MAX_SOCIAL_LINK_CHARS,
    MAX_SOCIAL_LINKS,
    MAX_TITLE_CHARS,
    SCORE_DECIMALS,
    DocumentMatchType,
    SummaryMethod,
)
from app.search import prepare

# email-validator rejects special-use domains (.test, .local, .invalid, ...) by default; this API accepts
# them. The list is part of the library's public API and is cleared when this module is imported.
email_validator.SPECIAL_USE_DOMAIN_NAMES.clear()

# "Control characters" are Unicode category Cc: U+0000-U+001F and U+007F-U+009F. Category Cf (zero-width
# space, soft hyphen, ...) is allowed. tests/unit/test_client_schemas.py checks the ranges against Cc.
NO_CONTROL = r'^[^\x00-\x1f\x7f-\x9f]+$'  # single-line text
NO_CONTROL_EXCEPT_TAB_LF = r'^[^\x00-\x08\x0b-\x1f\x7f-\x9f]*$'  # description: tab and newline allowed
NO_CONTROL_EXCEPT_TAB_LF_CR = r'^[^\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]*$'  # document content: also CR


class FieldError(BaseModel):
    """One failed field of a 422 response. The submitted value is never echoed."""

    loc: list[str | int] = Field(
        description='Where: `body`/`query`/`path`, then the field path', examples=[['body', 'email']]
    )
    msg: str = Field(examples=['value is not a valid email address: An email address must have an @-sign.'])
    type: str = Field(description='Stable machine-readable error code', examples=['value_error'])


class Problem(BaseModel):
    """`type` is always `about:blank`: the HTTP status code carries the meaning."""

    type: str = 'about:blank'
    title: str = Field(description='HTTP status phrase', examples=['Not Found'])
    status: int = Field(examples=[404])
    detail: str | None = Field(default=None, description='Human-readable explanation of this occurrence')
    errors: list[FieldError] | None = Field(default=None, description='Extension member, present on 422 only')


def _none_to_empty_str(value: Any) -> Any:
    return '' if value is None else value


def _none_to_empty_list(value: Any) -> Any:
    return [] if value is None else value


def _check_email(value: str) -> str:
    """Syntax check only, no DNS. The address is kept exactly as sent: no case folding."""
    try:
        email_validator.validate_email(value, check_deliverability=False)
    except email_validator.EmailNotValidError as exc:
        raise ValueError(f'value is not a valid email address: {exc}') from None
    return value


# In every Annotated below the constraints come before BeforeValidator: in the other order pydantic drops
# `pattern` from the JSON schema. The BeforeValidator still runs first.
Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_NAME_CHARS, pattern=NO_CONTROL)
]
Email = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=MAX_EMAIL_CHARS),
    AfterValidator(_check_email),
    Field(json_schema_extra={'format': 'email'}),
]
Description = Annotated[
    str,
    StringConstraints(max_length=MAX_DESCRIPTION_CHARS, pattern=NO_CONTROL_EXCEPT_TAB_LF),
    BeforeValidator(_none_to_empty_str),
]
SocialLink = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=MAX_SOCIAL_LINK_CHARS, pattern=NO_CONTROL
    ),
]
SocialLinks = Annotated[
    list[SocialLink], Field(max_length=MAX_SOCIAL_LINKS), BeforeValidator(_none_to_empty_list)
]
_NAME_RULES = f'Trimmed; 1-{MAX_NAME_CHARS} characters; no control characters'


class ClientCreate(BaseModel):
    """Body of POST /clients. Unknown members are ignored; a client-sent `id` is not honoured."""

    model_config = ConfigDict(
        json_schema_extra={
            'examples': [
                {
                    'first_name': 'John',
                    'last_name': 'Doe',
                    'email': 'john.doe@neviswealth.com',
                    'description': 'Founder of a logistics company; prefers ESG funds.',
                    'social_links': ['https://www.linkedin.com/in/johndoe'],
                }
            ]
        }
    )

    first_name: Name = Field(description=_NAME_RULES)
    last_name: Name = Field(description=_NAME_RULES)
    email: Email = Field(
        description=f'Trimmed; at most {MAX_EMAIL_CHARS} characters; syntax check only; stored as sent'
    )
    description: Description = Field(
        default='',
        description=f'At most {MAX_DESCRIPTION_CHARS:,} characters, verbatim; tab and newline allowed; '
        'null or absent: empty',
    )
    social_links: SocialLinks = Field(
        default_factory=list,
        description=f'At most {MAX_SOCIAL_LINKS} strings, each trimmed, '
        f'1-{MAX_SOCIAL_LINK_CHARS:,} characters, not validated as URLs; null: none',
    )


class Client(BaseModel):
    """A client as the API returns it."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: UUID
    first_name: str
    last_name: str
    email: str
    description: str
    social_links: list[str]


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError('must not be blank')
    return value


DocumentTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_TITLE_CHARS, pattern=NO_CONTROL),
]
# The upper limit of the content is a setting, so the route checks it.
DocumentContent = Annotated[
    str, StringConstraints(min_length=1, pattern=NO_CONTROL_EXCEPT_TAB_LF_CR), AfterValidator(_not_blank)
]


class DocumentCreate(BaseModel):
    """Body of POST /clients/{client_id}/documents. Unknown members are ignored."""

    model_config = ConfigDict(
        json_schema_extra={
            'examples': [
                {
                    'title': 'Utility bill',
                    'content': 'British Gas utility bill for March 2025. '
                    'Account holder John Doe, 14 Larkspur Close, Harrogate. Amount due £84.20.',
                }
            ]
        }
    )

    title: DocumentTitle = Field(
        description=f'Trimmed; 1-{MAX_TITLE_CHARS} characters; no control characters'
    )
    content: DocumentContent = Field(
        description=f'Stored as sent; 1 to NEVIS_MAX_CONTENT_CHARS (default {DEFAULT_MAX_CONTENT_CHARS:,}) '
        'characters; not blank; control characters other than tab, line feed and carriage return are rejected'
    )


class Summary(BaseModel):
    text: str
    method: SummaryMethod


class Document(BaseModel):
    """A document as the API returns it."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: UUID
    client_id: UUID
    title: str
    content: str
    created_at: datetime = Field(description='RFC 3339, UTC')
    tags: list[str] = Field(description='Concepts the document matched at upload, in concept-map order')
    summary: Summary

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> Document:
        """From a row of `documents` as app.db returns it.
        `created_at` is returned in UTC, not in the database session's time zone."""
        return cls(
            id=row['id'],
            client_id=row['client_id'],
            title=row['title'],
            content=row['content'],
            created_at=row['created_at'].astimezone(UTC),
            tags=row['tags'],
            summary=Summary(text=row['summary'], method=row['summary_method']),
        )


def _prepare_query(value: Any) -> Any:
    return prepare(value) if isinstance(value, str) else value


# `q` of /search: whitespace collapsed and trimmed first (prepare), then 1 to MAX_Q_CHARS characters without
# category Cc.
QueryText = Annotated[
    str,
    StringConstraints(min_length=1, max_length=MAX_Q_CHARS, pattern=NO_CONTROL),
    BeforeValidator(_prepare_query),
]


class _ClientMatch(BaseModel):
    """Search metadata of a client hit. As the second base class below, its fields come first in the JSON."""

    type: Literal['client'] = 'client'
    score: float = Field(
        ge=0,
        le=1,
        description=f'Ordering key, {SCORE_DECIMALS} decimals, not a probability. '
        f'>= {EXACT_SCORE_MIN}: the query words occur in the record; below {EXACT_SCORE_MIN}: a typo match',
    )
    match_type: Literal['exact', 'fuzzy'] = Field(
        description='`exact`: every query word occurs in name, e-mail or description; `fuzzy`: a typo match'
    )


class ClientSearchItem(Client, _ClientMatch):
    """A Client plus search metadata, flat: `item['email']` works."""


class _DocumentMatch(BaseModel):
    """Search metadata of a document hit. As the second base class below, its fields come first in JSON."""

    type: Literal['document'] = 'document'
    score: float = Field(
        ge=0,
        le=1,
        description=f'Ordering key, {SCORE_DECIMALS} decimals, not a probability. '
        f'>= {EXACT_SCORE_MIN}: the query words occur in the title, the text or the concept tags; '
        f'below {EXACT_SCORE_MIN}: a typo match or closeness of meaning',
    )
    match_type: DocumentMatchType = Field(
        description='`lexical`: the words are in title or text; `concept`: only with the concept tags; '
        '`fuzzy`: a typo of the title or of a concept phrase; `semantic`: closeness of meaning'
    )


class DocumentSearchItem(Document, _DocumentMatch):
    """A Document plus search metadata, flat: `item['title']` works."""


SearchItem = Annotated[ClientSearchItem | DocumentSearchItem, Field(discriminator='type')]
