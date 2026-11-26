# Nevis Search API

A REST service that stores wealth-management clients and their documents and searches both through one endpoint.
FastAPI and PostgreSQL 18 (pgvector, pg_trgm, unaccent); a local embedding model is baked into the image, so after
the first build everything runs offline and without any API key. Claude enrichment at upload is optional.

## Run it

You need Docker with Compose v2 (or Podman with a compose provider), bash, curl and python3.

```bash
docker compose up --build -d                              # build and start PostgreSQL and the API
scripts/demo.sh                                           # create John Doe and five documents, run both examples
docker compose --profile test run --rm --no-deps tests    # unit and integration tests, on the running database
```

- **First build.** Downloads: images from docker.io and ghcr.io, packages from PyPI, the embedding model (92 MB,
  pinned revision and sha256) from huggingface.co. Measured: 46 s on fresh GitHub Actions x86_64; later starts take
  seconds. For a model mirror: `docker compose build --build-arg HF_ENDPOINT=<mirror URL>`.
- **Port.** The API answers on http://127.0.0.1:8000 only; for another, set `API_PORT`
  (`docker compose down && API_PORT=8001 docker compose up -d`, then `API_PORT=8001 scripts/demo.sh`, or `.env`).
  The database publishes no port.
- **API description.** http://127.0.0.1:8000/docs requires cdn.jsdelivr.net;
  [docs/openapi.json](docs/openapi.json) works offline.
- **Reset.** `docker compose down -v` stops everything and deletes the database volume. `scripts/demo.sh` creates
  nothing on a second run.
- **Tests.** Rebuild after code changes: `docker compose --profile test build`. Host unit tests:
  `uv sync && uv run pytest tests/unit` (Linux or Apple Silicon; no onnxruntime wheels for Intel macOS).
- **Evaluation.** `docker compose --profile test run --rm --no-deps tests python -m eval.run_testset` scores this
  code on the 1,887-query test set in under a minute and a half; see [eval/README.md](eval/README.md).

## Try the deployed copy

A copy of `main` with the demo data runs in Yandex Cloud: Claude off, HTTP basic auth on everything but
`/health` (credentials sent separately). In a browser, open `/docs`.

```bash
API=https://d5db1cnp9cksolkc8ki5.fovt0b64.apigw.yandexcloud.net
AUTH='<login>:<password>'
curl -s "$API/health"
curl -s -u "$AUTH" "$API/search?q=NevisWealth" | python3 -m json.tool
CLIENT=$(curl -s -u "$AUTH" -H 'Content-Type: application/json' "$API/clients" \
  -d '{"first_name": "Anna", "last_name": "Schmidt", "email": "anna.schmidt@example.com"}' \
  | python3 -c 'import json, sys; print(json.load(sys.stdin)["id"])')
curl -s -u "$AUTH" -H 'Content-Type: application/json' "$API/clients/$CLIENT/documents" \
  -d '{"title": "Council tax bill", "content": "Council tax bill for 2025, 3 Lake Road, Zurich. Amount due CHF 1,240."}'
curl -s -u "$AUTH" "$API/search?q=address%20proof" | python3 -m json.tool
```

## The two examples from the assignment

Captured by `scripts/demo.sh` on an empty database; [full output](docs/demo-transcript.txt). IDs and timestamps vary.

`NevisWealth` → the client with e-mail john.doe@neviswealth.com.

<!-- transcript:start -->
```console
$ curl -s 'http://127.0.0.1:8000/search?q=NevisWealth' | python3 -m json.tool --no-ensure-ascii
[
    {
        "type": "client",
        "score": 0.85,
        "match_type": "exact",
        "id": "01a20d78-9dc6-7176-80d5-c653059a60a9",
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@neviswealth.com",
        "description": "Founder of a logistics company; prefers ESG funds.",
        "social_links": [
            "https://www.linkedin.com/in/johndoe"
        ]
    }
]
```
<!-- transcript:end -->

`address proof` → utility bills, through upload-time tags.

<!-- transcript:start -->
```console
$ curl -s 'http://127.0.0.1:8000/search?q=address%20proof' | python3 -m json.tool --no-ensure-ascii
[
    {
        "type": "document",
        "score": 0.7531,
        "match_type": "concept",
        "id": "01a20d78-a241-7823-9839-67457e69335f",
        "client_id": "01a20d78-9dc6-7176-80d5-c653059a60a9",
        "title": "Electricity bill",
        "content": "Electricity bill from EDF Energy for January 2025, 7 Mill Lane, Leeds. Amount due £96.10.",
        "created_at": "2026-11-24T12:12:19.393278Z",
        "tags": [
            "proof of address"
        ],
        "summary": {
            "text": "Electricity bill from EDF Energy for January 2025, 7 Mill Lane, Leeds. Amount due £96.10.",
            "method": "extractive"
        }
    },
    {
        "type": "document",
        "score": 0.7396,
        "match_type": "concept",
        "id": "01a20d78-a17e-7410-82f7-0e000102bcc2",
        "client_id": "01a20d78-9dc6-7176-80d5-c653059a60a9",
        "title": "Scan 0042",
        "content": "Scan: utility bill (electricity), 2 pages.\n\nNORTHMOOR ENERGY\nMr Tobias Hallworth\n14 Larkspur Close, Harrogate HG2 7QD\nCustomer number 8830 5512 07. Bill date 14 March 2025.\n\nYour electricity bill for 11 December 2024 to 10 March 2025 (90 days).\nMeter 21E4470913: previous reading 41,208, latest reading 42,371 (smart meter). Electricity used: 1,163 kWh.\nUnit charges 1,163 kWh at 24.86p: £289.12\nStanding charge 90 days at 60.97p: £54.87\nVAT at 5%: £17.20\nTotal charges this period: £361.19\nPayments received, thank you (3 direct debits of £95.47): £286.41\nBalance carried forward: £74.78 debit\n\nYour monthly direct debit stays at £95.47 and is collected on the 3rd of each month. Tariff: Fixed Saver 18, ends 30 September 2025. Estimated annual cost on this tariff: £1,210.",
        "created_at": "2026-11-24T12:12:19.198030Z",
        "tags": [
            "proof of address",
            "customer due diligence"
        ],
        "summary": {
            "text": "Scan: utility bill (electricity), 2 pages. NORTHMOOR ENERGY Mr Tobias Hallworth 14 Larkspur Close, Harrogate HG2 7QD Customer number 8830 5512 07. Bill date 14 March 2025. Your electricity bill for 11 December 2024 to 10 March 2025 (90 days).",
            "method": "extractive"
        }
    },
    {
        "type": "document",
        "score": 0.7382,
        "match_type": "concept",
        "id": "01a20d78-9ec5-7c74-acdd-4ab3baa2a17e",
        "client_id": "01a20d78-9dc6-7176-80d5-c653059a60a9",
        "title": "Utility bill",
        "content": "British Gas utility bill for March 2025. Account holder John Doe, 14 Larkspur Close, Harrogate. Amount due £84.20.",
        "created_at": "2026-11-24T12:12:18.501407Z",
        "tags": [
            "proof of address",
            "customer due diligence"
        ],
        "summary": {
            "text": "British Gas utility bill for March 2025. Account holder John Doe, 14 Larkspur Close, Harrogate. Amount due £84.20.",
            "method": "extractive"
        }
    }
]
```
<!-- transcript:end -->

`chocolate cake recipe` → an empty list.

<!-- transcript:start -->
```console
$ curl -s 'http://127.0.0.1:8000/search?q=chocolate%20cake%20recipe' | python3 -m json.tool --no-ensure-ascii
[]
```
<!-- transcript:end -->

## How it works

- **Clients:** every query word is a substring of the name, e-mail or description (`exact`); if no client matches,
  typo matches by trigrams (`fuzzy`).
- **Documents:** one SQL statement: literal full-text matches, typo matches on titles and concept phrases, and the
  meaning of embedded fragments. Score bands: 0.5 and above, words found; 0.2 to 0.5, meaning or a typo; below 0.2,
  a weak guess.
- **Concept map:** at upload, 30 concepts tag documents, so a utility bill carries `proof of address`. Embeddings
  alone rank the bill last for `address proof` (passport 0.25, tax return 0.19, bill 0.14).
- **Summary:** the document's first sentences, up to 300 characters; Claude can write it instead.

Details: [search rules](docs/SEARCH.md) and [design decisions](docs/DESIGN.md).

## Measured quality

On the 1,887 queries of `testset/`, Claude off:

<!-- quality:start -->
| | With the concept map (shipped) | Without the concept map |
|---|---|---|
| Strict pass, all 1,887 queries | 1323/1887 (70 %) | 1328/1887 (70 %) |
| … required by the assignment's text (621) | 544/621 (88 %) | 547/621 (88 %) |
| First 10: precision | 0.80 | 0.82 |
| First 10: recall | 0.74 | 0.69 |
| First 10: F1 | 0.766 | 0.747 |
| `NevisWealth`, strict, all its queries in the test set | 16/16 | 16/16 |
| `address proof`, strict, all its queries in the test set | 0/10 | 0/10 |
<!-- quality:end -->

Strict pass: every expectation of the query holds (results, no wrong ones, order). `address proof` finds the bills
but passes none of its ten queries strictly.
[Full results and qualifications](eval/README.md#measured-quality).

## API

| Operation | Success | Errors |
|---|---|---|
| `POST /clients` | 201, `Location`, the client | 400, 413, 415, 422 |
| `GET /clients/{id}` | 200, the client | 404 |
| `POST /clients/{id}/documents` | 201, `Location`, the document with `tags` and `summary` | 400, 404, 413, 415, 422 |
| `GET /clients/{id}/documents/{document_id}` | 200, the document | 404, also for another client's document |
| `GET /search?q=&type=&limit=` | 200, a list; `[]` when nothing matches | 400 (query string not UTF-8), 422 |
| `GET /health` | 200 `{"status": "ok"}`, without touching the database | none |

Errors: `application/problem+json` (RFC 9457); 503 with `Retry-After`.
[Details](docs/API.md) · [OpenAPI](docs/openapi.json).

## Limits

- Closed concept map: missing phrasings and false positives.
- Client substrings match inside words; similar names collide.
- Scale and real-data quality are unverified.
- Deployed-copy reachability outside Russia is unverified.

[All limits](docs/LIMITS.md).

## How LLMs were used

**At run time** no LLM is called by default: vectors come from the local `mdbr-leaf-ir` model (Apache-2.0), and nothing
leaves the machine. Claude Haiku is optional: at upload it reads each title and text and writes the summary and tags
(86 documents: p50 2.1 s, p95 3.6 s, $0.0003 per document); [how to enable it](docs/ENRICHMENT.md).

**During development** I used AI agents throughout. Claude Code researched, designed and wrote most of the code
test-first; Codex wrote parts of the Claude enrichment and the review fixes (18 commits) and reviewed the code;
separate agents reviewed the design. Agents wrote 10 test suites (Codex and Claude wrote 6 of them blind), built 8
from open datasets and drafted the concept map.
Scripts reproduce the quality and cosine tables; CI keeps every quoted cell and transcript equal to the stored
outputs, without recomputing relevance. Image builds require a model self-check. Design-time numbers predate the code.

## Repository map

```
app/                     the service: main.py (routes, errors), search.py, ingest.py, embedding.py, db.py, config.py, schemas.py
app/db.py                the tables as SQLAlchemy models and every query in SQLAlchemy Core: client search, document search, concept matching
app/data/concepts.yaml   the concept map (30 entries)
scripts/                 demo.sh, check_demo.py, export_openapi.py, fetch_model.py (model download at build time)
eval/                    evaluation runner and metrics, committed results, cosine table
testset/                 18 test suites with recorded answers (summary in eval/README.md)
tests/                   unit tests (host) and integration tests (compose)
docs/                    DESIGN.md, SEARCH.md, API.md, ENRICHMENT.md, LIMITS.md, openapi.json, demo-transcript.txt
Dockerfile, docker-compose.yml, .github/workflows/ci.yml
```

Design decisions and reasons: [docs/DESIGN.md](docs/DESIGN.md). Licences of the parts: the embedding model
`MongoDB/mdbr-leaf-ir` is Apache-2.0; psycopg is LGPL-3.0 and used unmodified as a library; each suite built from an
open dataset (`ds-*`) names its source and licence in its `about` and `source` fields.
