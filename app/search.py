from typing import Any, Literal

from app import db
from app.config import Services

# app.schemas imports prepare() from this module, so this module must not import app.schemas: that would be
# an import cycle. The database is called through `db.<function>`, so unit tests can replace those functions.


def prepare(q: str) -> str:
    """Collapse every whitespace run to one space and trim; the API validates the result.

    str.split() also splits on U+001C-U+001F and U+0085, which are control characters: they are collapsed
    like spaces, not rejected.
    """
    return ' '.join(q.split())


def merge(items: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    """Round scores to 4 decimals, sort by (score desc, type asc, id asc), keep the first `limit`.

    Rounding comes first, so scores that round to the same value are ordered by type and id.
    """
    rounded = [{**item, 'score': round(float(item['score']), 4)} for item in items]
    rounded.sort(key=lambda item: (-item['score'], item['type'], str(item['id'])))
    return rounded[:limit]


ResultType = Literal['client', 'document']  # the type of a search item


def search(services: Services, q: str, type_: ResultType | None, limit: int) -> list[dict[str, Any]]:
    """Ask each engine for `limit` rows with unrounded scores, then merge.

    `q` is prepared and validated already (QueryText). Each result is a flat dict: the API fields plus
    `type`, `score` and `match_type`.
    """
    items: list[dict[str, Any]] = []
    if type_ != 'document':
        items += [{'type': 'client', **row} for row in db.search_clients(services.engine, q, limit)]
    return merge(items, limit)
