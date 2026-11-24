from app.config import SELFCHECK_PASSAGE, SELFCHECK_QUERY
from eval.cosine_table import DOCUMENTS, QUERIES, render


def test_documents_are_ordered_by_cosine_best_first() -> None:
    table = render({'address proof': {'Utility bill': 0.14, 'Passport': 0.25, 'Tax return': 0.19}})
    assert table.splitlines() == [
        '| Query | 1st | 2nd | 3rd |',
        '|---|---|---|---|',
        '| `address proof` | Passport 0.25 | Tax return 0.19 | Utility bill 0.14 |',
    ]


def test_the_utility_bill_cell_is_what_the_build_checks() -> None:
    title, text = DOCUMENTS[0]
    assert f'{title}\n{text}' == SELFCHECK_PASSAGE
    assert QUERIES[0] == SELFCHECK_QUERY
