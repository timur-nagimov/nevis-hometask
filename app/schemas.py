from typing import Annotated, Any
from uuid import UUID

import email_validator
from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints

# email-validator rejects special-use domains (.test, .local, .invalid, ...) by default; this API accepts
# them. The list is part of the library's public API and is cleared when this module is imported.
email_validator.SPECIAL_USE_DOMAIN_NAMES.clear()

# "Control characters" are Unicode category Cc: U+0000-U+001F and U+007F-U+009F. Category Cf (zero-width
# space, soft hyphen, ...) is allowed. tests/unit/test_client_schemas.py checks the ranges against Cc.
NO_CONTROL = r'^[^\x00-\x1f\x7f-\x9f]+$'  # single-line text
NO_CONTROL_EXCEPT_TAB_LF = r'^[^\x00-\x08\x0b-\x1f\x7f-\x9f]*$'  # description: tab and newline allowed


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
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100, pattern=NO_CONTROL)
]
Email = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=254),
    AfterValidator(_check_email),
    Field(json_schema_extra={'format': 'email'}),
]
Description = Annotated[
    str,
    StringConstraints(max_length=2000, pattern=NO_CONTROL_EXCEPT_TAB_LF),
    BeforeValidator(_none_to_empty_str),
]
SocialLink = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2048, pattern=NO_CONTROL)
]
SocialLinks = Annotated[list[SocialLink], Field(max_length=20), BeforeValidator(_none_to_empty_list)]


class ClientCreate(BaseModel):
    """Body of POST /clients. Unknown members are ignored; a client-sent `id` is not honoured."""

    model_config = ConfigDict(
        json_schema_extra={
            'examples': [
                {
                    'first_name': 'John',
                    'last_name': 'Doe',
                    'email': 'john.doe@neviswealth.com',
                    'description': 'Founder of a logistics company, prefers ESG funds',
                    'social_links': ['https://www.linkedin.com/in/johndoe'],
                }
            ]
        }
    )

    first_name: Name = Field(description='Trimmed; 1-100 characters; no control characters')
    last_name: Name = Field(description='Trimmed; 1-100 characters; no control characters')
    email: Email = Field(description='Trimmed; at most 254 characters; syntax check only; stored as sent')
    description: Description = Field(
        default='',
        description='At most 2,000 characters, verbatim; tab and newline allowed; null or absent: empty',
    )
    social_links: SocialLinks = Field(
        default_factory=list,
        description='At most 20 strings, each trimmed, 1-2,048 characters, not validated as URLs; null: none',
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
