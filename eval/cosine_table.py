"""Cosine of three queries against three one-sentence documents: the shipped model, no concept map.

For `address proof` the embeddings alone rank the utility bill last: this is the README's argument for the
concept map. It needs the model, not the database, so it runs in the tests container. To refresh the committed
table, redirect its output to eval/results/cosines.md:

    docker compose --profile test run --rm --no-deps -T tests python -m eval.cosine_table
"""

from collections.abc import Sequence

from app.config import Settings
from app.embedding import Embedder

# Embedded the way ingest embeds a short document: title, newline, text. The first query and the first
# document are the pair the image build checks (python -m app.embedding --selfcheck).
DOCUMENTS = (
    (
        'Utility bill',
        'British Gas utility bill for March 2025. Account holder John Doe, 14 Larkspur Close, Harrogate. '
        'Amount due £84.20.',
    ),
    (
        'Passport',
        'Copy of the passport of John Doe, United Kingdom. Passport number 533401372, expires 12 May 2031.',
    ),
    (
        'Tax return',
        'Self Assessment tax return for the tax year 2023-24, submitted to HMRC on 14 January 2025. '
        'Total income £86,400, tax due £21,930.',
    ),
)
QUERIES = ('address proof', 'proof of address', 'utility bill')


def render(rows: Sequence[tuple[str, Sequence[tuple[str, float]]]]) -> str:
    """One row per query; the documents ordered by cosine, best first, each as `title cosine`."""
    lines = ['| Query | 1st | 2nd | 3rd |', '|---|---|---|---|']
    for query, scored in rows:
        ranked = sorted(scored, key=lambda pair: pair[1], reverse=True)
        cells = ' | '.join(f'{title} {cosine:.2f}' for title, cosine in ranked)
        lines.append(f'| `{query}` | {cells} |')
    return '\n'.join(lines)


def main() -> None:
    settings = Settings()
    embedder = Embedder(settings.model_dir, settings.embed_threads)
    titles = [title for title, _ in DOCUMENTS]
    passages = embedder.embed_documents([f'{title}\n{text}' for title, text in DOCUMENTS])
    rows = []
    for query in QUERIES:
        vector = embedder.embed_query(query)
        cosines = [float(vector @ passage) for passage in passages]
        rows.append((query, list(zip(titles, cosines, strict=True))))
    print(render(rows))


if __name__ == '__main__':
    main()
