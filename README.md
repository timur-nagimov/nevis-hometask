# Nevis Search API

A REST service that stores wealth-management clients and their documents and searches both through one endpoint.
FastAPI and PostgreSQL 18 (pgvector, pg_trgm, unaccent); a local embedding model is baked into the image, so after
the first build everything runs offline and without any API key.

## Run it

You need Docker with Compose v2 (or Podman with a compose provider), bash, curl and python3.

```bash
docker compose up --build -d                              # build and start PostgreSQL and the API
scripts/demo.sh                                           # create John Doe and five documents, run both examples
docker compose --profile test run --rm --no-deps tests    # unit and integration tests, on the running database
```

- **First build.** It downloads base images from docker.io and ghcr.io, Python packages from PyPI and the embedding
  model (92 MB, pinned revision, checked by sha256) from huggingface.co. It took 46 s on a fresh GitHub Actions
  runner (x86_64); allow longer on a slow connection. Later starts take seconds. If huggingface.co is slow or
  blocked: `docker compose build --build-arg HF_ENDPOINT=<mirror URL>`.
- **Port.** The API answers on http://127.0.0.1:8000 only. For another port:
  `docker compose down && API_PORT=8001 docker compose up -d` and `API_PORT=8001 scripts/demo.sh`, or set `API_PORT`
  in `.env` (see `.env.example`) and export it for the scripts. The database publishes no port.
- **API description.** Swagger UI at http://127.0.0.1:8000/docs loads its JavaScript and CSS from cdn.jsdelivr.net,
  so it stays blank offline; `docs/openapi.json` is the same description as a file.
- **Reset.** `docker compose down -v` stops everything and deletes the database volume. `scripts/demo.sh` creates
  nothing on a second run.
- **Tests.** After changing code, rebuild the test image first: `docker compose --profile test build`. The unit tests
  also run on the host: `uv sync && uv run pytest tests/unit` (Linux or Apple Silicon; onnxruntime has no wheels for
  Intel macOS).
- **Evaluation.** `docker compose --profile test run --rm --no-deps tests python -m eval.run_testset` scores this
  code on the 1,887-query test set in under a minute and a half; see [eval/README.md](eval/README.md).

## The two examples from the assignment

Captured with `scripts/demo.sh` on an empty database (full output: [docs/demo-transcript.txt](docs/demo-transcript.txt));
ids and timestamps differ on every machine.

**`NevisWealth` → the client with the e-mail john.doe@neviswealth.com.** `exact`: every query word is part of the
client's name, e-mail or description.

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

**`address proof` → the utility bills.** `concept`: the query's words are in the tags the documents got at upload
(`proof of address`), not in their text. "Scan 0042" mentions "utility bill" only once, inside a 123-word text.

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

**A query with no answer gets an empty list.**

<!-- transcript:start -->
```console
$ curl -s 'http://127.0.0.1:8000/search?q=chocolate%20cake%20recipe' | python3 -m json.tool --no-ensure-ascii
[]
```
<!-- transcript:end -->

## How search decides

**Clients.** Query and record are normalised alike (Unicode NFKC, no accents, case folded). A client matches `exact`
when every query word is a substring of its name, e-mail and description together: `neviswealth`, `wealth`,
`john.doe` and `Doe John` all find John Doe. Only when nothing matches and the query has at least 5 letters or digits
does a trigram typo tier run (`NevisWelth`, `Jon Doe` → `fuzzy`).

**Documents.** One SQL statement, four ways in:
1. *literal*: every query word (English stemming) is in the title, the text or the tags → `lexical`, or `concept`
   when the tags were needed;
2. *typo*, only if the literal way found nothing: the title resembles the query, or the query is a misspelt concept
   phrase (`adress proof`) → `fuzzy`;
3. *meaning*: the best fragment's cosine is at least 0.40 and within 0.08 of the best document → `semantic`;
4. *weak guess*, only if nothing above matched: up to three nearest documents with a cosine of at least 0.32 →
   `semantic`.

Documents are cut into fragments of up to 200 words, each with a vector; a document's cosine is its best fragment's.
Both kinds are fetched with `limit` each, merged, sorted by score, type and id, and cut to `limit` (1-50, default 10).

| Score | Meaning | `match_type` |
|---|---|---|
| 0.5 and above | the query's words are in the record, or in the document's tags | `exact`, `lexical`, `concept` |
| 0.2 to 0.5 | a strong semantic match, or a typo | `semantic`, `fuzzy` |
| below 0.2 | a weak semantic guess, or a client typo found only in the description | `semantic`, `fuzzy` |

A consumer that wants only confident results drops `semantic` items below 0.2.

## Why there is a concept map

Embeddings alone do not know that a utility bill is accepted as proof of address. With the shipped model, three
short documents and no concept map, `address proof` ranks the bill last
(`docker compose --profile test run --rm --no-deps tests python -m eval.cosine_table`; each document is embedded as
title and text):

<!-- cosines:start -->
| Query | 1st | 2nd | 3rd |
|---|---|---|---|
| `address proof` | Passport 0.25 | Tax return 0.19 | Utility bill 0.14 |
| `proof of address` | Passport 0.29 | Tax return 0.22 | Utility bill 0.17 |
| `utility bill` | Utility bill 0.52 | Tax return 0.21 | Passport 0.15 |
<!-- cosines:end -->

`app/data/concepts.yaml` lists 30 relations of this kind: a concept (`proof of address`), the ways people ask for it
(`triggers`) and the documents that satisfy it (`expands_to`: utility bill, council tax bill, bank statement …). At
upload a document gets as `tags` every concept whose name or document phrase occurs in it. The tags, with their
triggers, join the literal match and, for a title match or a document of up to 200 words, one extra embedded
fragment: that is why the bills come back as `concept`, with `proof of address` in their tags.

An LLM drafted the map once from general UK wealth-management knowledge (120 entries); it was cut by rule to 30 (keep
relations of this kind; drop single documents, topics and identifiers). Four entries cite an official list in
`sources` (GOV.UK, Bona Vacantia, DBS, JMLSG). The assignment's pair is there because it is the canonical case;
`proof of income` → payslip and `photo ID` → passport come from entries of the same kind. The map is a closed list:
phrasings it lacks get no tag (see Limits).

## Measured quality

`eval/run_testset.py` runs the 1,887 queries of `testset/` (18 suites) against this code, once with the concept map
and once without. Both columns are copied from its output in `eval/results/`.

<!-- quality:start -->
| | With the concept map (shipped) | Without the concept map |
|---|---|---|
| Strict pass, all 1,887 queries | 1323/1887 (70 %) | 1328/1887 (70 %) |
| … written blind by Codex and Claude (400) | 255/400 (64 %) | 259/400 (65 %) |
| … built from open datasets (951) | 640/951 (67 %) | 642/951 (68 %) |
| … level "required" (621) | 544/621 (88 %) | 547/621 (88 %) |
| First 10: precision | 0.80 | 0.82 |
| First 10: recall | 0.74 | 0.69 |
| First 10: F1 | 0.766 | 0.747 |
| Answerable queries with a relevant result in the first 10 | 0.86 | 0.84 |
| Queries without an answer that return nothing (230) | 0.67 (154/230) | 0.68 (156/230) |
| `NevisWealth`, strict, all its queries in the test set | 16/16 | 16/16 |
| `address proof`, strict, all its queries in the test set | 0/10 | 0/10 |
<!-- quality:end -->

Strict pass counts a query only if every expected result is found, nothing wrong is returned and the ordering
requirements hold ([eval/README.md](eval/README.md)). The thresholds were chosen on the dev half of one suite, and two
suites were written by the design's authors. The map costs a few strict passes and a little precision; it is what
makes `address proof` find the bills. On the test corpora `address proof` never passes strictly: some bills are
missed, and documents that merely mention proof or address come back with them (see Limits).

Under load: `/search` p95 21 ms and `/health` p95 5 ms while 16 parallel uploads send the 86 documents of the `existing-documents-86` suite (6 CPUs, `NEVIS_EMBED_THREADS=4`, podman on an Apple M3 Pro); idle `/search` p95 9 ms.

## API

| Operation | Success | Errors |
|---|---|---|
| `POST /clients` | 201, `Location`, the client | 400, 413, 415, 422 |
| `GET /clients/{id}` | 200, the client | 404 |
| `POST /clients/{id}/documents` | 201, `Location`, the document with `tags` and `summary` | 400, 404, 413, 415, 422 |
| `GET /clients/{id}/documents/{document_id}` | 200, the document | 404, also for another client's document |
| `GET /search?q=&type=&limit=` | 200, a list; `[]` when nothing matches | 400 (query string not UTF-8), 422 |
| `GET /health` | 200 `{"status": "ok"}`, without touching the database | none |

- Errors are `application/problem+json` (RFC 9457); a 422 adds `errors` (`loc`, `msg`, `type`) and never repeats the
  submitted value. Any call that uses the database may answer 500 without details, or 503 with `Retry-After: 5`
  (database unreachable, busy, or a query over 5 s). A body over 2 MiB gets 413, possibly as plain text.
- A search item is the client or document itself plus `type`, `score` and `match_type`, so `item["email"]` works.
  Documents carry `tags` (concepts matched at upload) and `summary` (the first sentences, up to 300 characters,
  `"method": "extractive"`).
- Limits: names up to 100 characters, description 2,000, 20 social links, title 300, text 50,000, `q` 1-200 after
  collapsing whitespace. Control characters are rejected, except tab and newline in a description or a document's
  text (and carriage return in the text). A path id that is not a UUID gets 404. An e-mail may repeat (spouses share
  addresses), so there is no 409.
- The 200-character cap on `q` bounds the substring patterns and the client typo tier; longer queries were not
  measured.
- Results carry whole documents, like the assignment's Document model: at most 50 documents of 50,000 characters,
  about 2.5 MB of Latin text and up to about 7.5 MB in other scripts; a few kilobytes on the demo data.
- Swagger UI offers both assignment queries as examples; `scripts/demo.sh` shows the create calls with curl.

## Limits

- **What a document is for** (`proof of income`, `photo ID`, `bank statement` as "anything that proves it") is the
  weakest kind of query: the map is a closed list, so phrasings it lacks ("Council Tax demand notice") get no tag, and
  documents that merely mention the words, or carry a neighbouring tag, come back too.
- **`address proof`** also returns "Proof of delivery … home address" and letters asking for proof of address (same
  tag as the bill); only a document-type label, say from an LLM at upload, could separate them.
- **Client substrings inside words:** `Chester` also finds a description that mentions Manchester. The test authors
  disagree on whether that is wrong; whole-word matching for words of up to three letters is the first variant to
  measure.
- **Similar names:** the typo tier can return another person with a similar name (`Sergey Menshikov` finds a
  different Menshikov); without the tier far more typos and nicknames fail.
- **Typos inside a document's text** are not corrected, only in titles and concept phrases; swapped letters in a short
  name (`Jhon`) defeat trigrams.
- **Names in another script:** Cyrillic or Arabic spellings of Latin names are not found.
- **Queries without an answer** can get up to three weak guesses below 0.2, sometimes a wrong semantic match above
  0.2 (`marriage certificate`).
- **Long and empty queries** get 422 (over 200 characters, or only spaces); one test suite expects 200 and `[]` for
  the empty one.

## What is not verified

- **Real data.** All corpora are synthetic or public; the thresholds were chosen on synthetic documents and should be
  re-tuned on real ones ([eval/README.md](eval/README.md)).
- **Scale.** There is no vector index and no candidate cap. Design-time measurements put document search above 0.1 s
  at about 10,000 fragments, and very common client substrings (`gmail`, `com`) at 0.35-1.9 s per query with 100,000
  clients.
- **Memory of the whole API process.** Not measured; the model alone took about 180 MB, and 415 MB at its peak while
  loading (design-time).
- **Platforms.** Built and tested with podman on Apple Silicon (arm64) and with Docker on x86_64 in GitHub Actions;
  Docker Desktop on Windows was not tried.
- **The Claude call at upload** was never run against the real API, so it is not included.
- **No deployed instance.**

## How LLMs were used

**At run time** the service calls no LLM: the vectors come from a local embedding model (`mdbr-leaf-ir`,
Apache-2.0) inside the image, and nothing leaves the machine. A Claude call at upload (summary and tags) was designed
but is not included: it was never run against the real API, and code that sends client documents to a third party
should not ship unexercised. **During development** I worked with AI agents throughout: Claude Code researched the
options, wrote the design and then this code, test-first; separate agent reviews attacked the design before any code
existed; LLM agents wrote 10 of the 18 test suites, Codex and Claude 6 of them blind. An LLM also drafted the
concept map (see above). **Checked, not trusted:** every number in the quality and cosine tables is printed by a
script in this repository (`tests/unit/test_docs.py` fails otherwise), numbers marked "design-time" come from the
research done before the code, the transcripts are captured from the running service, and the image build fails
unless the model passes a self-check. The code took about 25 hours of wall time up to this README; the research and
the test set came before.

## Repository map

```
app/                     the service: main.py (routes, errors), search.py, ingest.py, embedding.py, db.py, config.py, schemas.py
app/db.py                the tables as SQLAlchemy models and every query in SQLAlchemy Core: client search, document search, concept matching
app/data/concepts.yaml   the concept map (30 entries)
scripts/                 demo.sh, check_demo.py, export_openapi.py, fetch_model.py (model download at build time)
eval/                    evaluation runner and metrics, committed results, cosine table
testset/                 18 test suites with recorded answers (summary in eval/README.md)
tests/                   unit tests (host) and integration tests (compose)
docs/                    DESIGN.md, openapi.json, demo-transcript.txt
Dockerfile, docker-compose.yml, .github/workflows/ci.yml
```

Design decisions and their reasons: [docs/DESIGN.md](docs/DESIGN.md). Licences of the parts: the embedding model
`MongoDB/mdbr-leaf-ir` is Apache-2.0; psycopg is LGPL-3.0 and used unmodified as a library; each suite built from an
open dataset (`ds-*`) names its source and licence in its `about` and `source` fields.
