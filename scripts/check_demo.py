"""Check the demo data and both assignment examples against a running API.

Run it after scripts/demo.sh on a database that holds only the demo data (in CI, or after
`docker compose down -v && docker compose up -d && scripts/demo.sh`):

    python3 scripts/check_demo.py        # http://127.0.0.1:8000; API_PORT and NEVIS_API work as in demo.sh

Prints one line per check and exits with status 1 at the first failed check. Standard library only.
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from typing import Any

API = os.environ.get('NEVIS_API') or f'http://127.0.0.1:{os.environ.get("API_PORT", "8000")}'
EMAIL = 'john.doe@neviswealth.com'
BILLS = ['Electricity bill', 'Scan 0042', 'Utility bill']
EXACT_SCORE_MIN = 0.5  # as in app/config.py: from this score on, the query words or the concept tags matched
TIMEOUT_SECONDS = 30  # per request


def search(q: str, **params: str) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode({'q': q, **params}, quote_via=urllib.parse.quote)
    with urllib.request.urlopen(f'{API}/search?{query}', timeout=TIMEOUT_SECONDS) as response:
        items: list[dict[str, Any]] = json.load(response)
    return items


def check(ok: bool, what: str, evidence: object) -> None:
    if not ok:
        print(f'FAIL  {what}\n{json.dumps(evidence, indent=2, ensure_ascii=False)}', file=sys.stderr)
        sys.exit(1)
    print(f'ok    {what}')


def main() -> None:
    clients = [item for item in search(EMAIL, type='client') if item['email'] == EMAIL]
    check(len(clients) == 1, f'one client with the e-mail {EMAIL}', clients)

    items = search('NevisWealth')
    first = items[0] if items else {}
    found_first = first.get('email') == EMAIL and first.get('match_type') == 'exact'
    check(found_first, 'NevisWealth: John Doe first, exact', items)

    strong = [item for item in search('address proof') if item['score'] >= EXACT_SCORE_MIN]
    titles = sorted(item['title'] for item in strong)
    all_concept = all(item['match_type'] == 'concept' for item in strong)
    check(
        titles == BILLS and all_concept,
        f'address proof: each bill once, as concept with score >= {EXACT_SCORE_MIN}, '
        f'and nothing else >= {EXACT_SCORE_MIN}',
        strong,
    )

    for title in ('Passport', 'Tax return'):
        same = [item for item in search(title, type='document') if item['title'] == title]
        check(len(same) == 1, f'one document titled {title!r}', same)

    check(search('chocolate cake recipe') == [], 'chocolate cake recipe: []', None)


if __name__ == '__main__':
    main()
