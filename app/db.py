"""PostgreSQL: the migrations runner, the connection pool, and (from step 2) every SQL call.

Every public function that touches the database owns its transaction and has committed before it returns,
so the API never answers before the row it reports is visible to other connections (spec section 4).
"""

from typing import Literal

Reason = Literal["unreachable", "busy", "timeout"]


class DatabaseUnavailable(Exception):
    """The database cannot serve this request now; the API answers 503 with `Retry-After: 5`."""

    def __init__(self, reason: Reason) -> None:
        super().__init__(reason)
        self.reason: Reason = reason
