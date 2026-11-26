# Nevis Search API

A REST service that stores wealth-management clients and their documents and searches both through one endpoint.
It uses FastAPI and PostgreSQL 18 (pgvector, pg_trgm, unaccent). The image includes local embeddings: offline after
the first build, without a key; Claude is optional at upload.

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
- **Port.** The API answers on http://127.0.0.1:8000 only. For another port:
  `docker compose down && API_PORT=8001 docker compose up -d` and `API_PORT=8001 scripts/demo.sh`, or set `API_PORT`
  in `.env` (see `.env.example`) and export it for the scripts. The database publishes no port.
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

No answer → an empty list.

<!-- transcript:start -->
```console
$ curl -s 'http://127.0.0.1:8000/search?q=chocolate%20cake%20recipe' | python3 -m json.tool --no-ensure-ascii
[]
```
<!-- transcript:end -->

## How it works

Clients: substrings in name/e-mail/description, then a typo tier.
Documents: one SQL statement with literal, typo and semantic legs; scores in bands.
At upload, the concept map gives utility bills `proof of address` tags: embeddings alone rank the bill last
for `address proof` (passport 0.25, tax return 0.19, bill 0.14).
Summaries are extractive; Claude is optional.
[Search rules](docs/SEARCH.md) · [Design](docs/DESIGN.md).

## Measured quality

With the map, Claude off: strict pass **1,323/1,887 (70%)**; required by the assignment **544/621 (88%)**;
first-10 precision/recall/F1 **0.80/0.74/0.766**.
Strict pass requires all expected results, no wrong results and correct ordering.
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

No runtime LLM by default: local `mdbr-leaf-ir` (Apache-2.0), nothing leaves the machine.
Optional Claude Haiku receives titles/text, adds summaries/tags at upload (86 documents: p50 2.1 s, p95 3.6 s,
$0.0003/document); [enable it](docs/ENRICHMENT.md).
I used AI agents throughout development. Claude Code researched, designed and wrote most code test-first;
Codex wrote enrichment parts and final review fixes (18 commits), and reviewed code.
Separate agents reviewed the design.
Agents wrote 10 suites (6 blind, Codex/Claude), built 8 from open datasets and drafted the map.
Scripts reproduce quality/cosine tables. CI docs tests compare quality cells and the cosine table with stored
`eval/results/`, without recomputing relevance, compare transcripts with captured output, and check links and run
instructions. Image builds require a model self-check. Design-time numbers predate the code.

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
