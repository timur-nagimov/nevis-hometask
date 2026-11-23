"""Request and response models. Step 1: the error body, RFC 9457 problem details."""

from pydantic import BaseModel, Field


class FieldError(BaseModel):
    """One failed field of a 422 response. The submitted value is never echoed."""

    loc: list[str | int] = Field(
        description="Where: `body`/`query`/`path`, then the field path", examples=[["body", "email"]]
    )
    msg: str = Field(examples=["value is not a valid email address: An email address must have an @-sign."])
    type: str = Field(description="Stable machine-readable error code", examples=["value_error"])


class Problem(BaseModel):
    """RFC 9457 problem details. `type` is always `about:blank`: the HTTP status code carries the meaning."""

    type: str = "about:blank"
    title: str = Field(description="HTTP status phrase", examples=["Not Found"])
    status: int = Field(examples=[404])
    detail: str | None = Field(default=None, description="Human-readable explanation of this occurrence")
    errors: list[FieldError] | None = Field(default=None, description="Extension member, present on 422 only")
