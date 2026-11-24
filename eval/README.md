# Evaluation

`eval/run_testset.py` measures the shipped search code on 18 test suites: 1,887 queries whose correct answers were
written down before the code existed. It loads each suite and runs its queries through the service's own functions
(`app.db.insert_client`, `app.ingest.create_document`, `app.search.search` with the queries of `app/db.py`), so it
measures exactly what the API does, without the HTTP layer.

## Run it

Start the stack first (`docker compose up --build -d`, as in the [main README](../README.md)): the runner needs its
database, and `--no-deps` leaves the running containers alone.

```bash
docker compose --profile test run --rm --no-deps tests python -m eval.run_testset                 # shipped configuration
docker compose --profile test run --rm --no-deps tests python -m eval.run_testset --no-concepts   # without the concept map
```

One configuration takes about a minute to a minute and a half on an Apple M3 Pro (podman VM with 6 CPUs); the last
line of the output gives the run time. Every suite gets its own database (`nevis_ts_<suite>`), created, given the
schema with `app.db.create_schema` and dropped afterwards; the demo data is not touched. Records the API would
reject are skipped and logged, and a query the API would reject counts as an empty answer. Queries run with
`limit=50`; `type` is the query's `scope` (`clients` → `client`, `documents` → `document`, `all` → no type). Add
`--failures` to list every failing query with the reason, and suite names (`tools-mini-6`) to run only those
suites.

The outputs on the shipped code are committed: [results/with-concepts.txt](results/with-concepts.txt) and
[results/no-concepts.txt](results/no-concepts.txt). The README's quality table quotes only these files. This prints
nothing when a new run gives the same numbers:

```bash
diff <(grep '^|' eval/results/with-concepts.txt) \
     <(docker compose --profile test run --rm --no-deps -T tests python -m eval.run_testset | grep '^|')
```

`docker compose --profile test run --rm --no-deps tests python -m eval.cosine_table` prints the README's
three-document cosine table ([results/cosines.md](results/cosines.md)).

## The test set

[testset/](../testset/) holds the suites (`testset/suites/*.json`). Its [README](../testset/README.md) is in Russian;
this section summarises it.

- **Written blind** (6 suites, `codex-*` and `claude-*`): Codex (GPT-6) and Claude Opus 5.5 got the same brief, and
  each wrote a corpus, queries and answers without seeing the design or each other's work.
- **Open datasets** (8 suites, `ds-*`): Enron e-mails, FiQA, synthetic finance documents, the UK sanctions list,
  RVL-CDIP scans and name-matching sets. The answers come mechanically from the datasets' labels and, for questions
  about a document's purpose, from official UK lists (GOV.UK), with a quote.
- **Research** (4 suites, `existing-*` and `tools-mini-6`): the sets the design was measured on.
  `existing-documents-86` has a `dev` half (used to choose the thresholds) and a `test` half;
  `existing-clients-fixture-42` and `tools-mini-6` were written by the design's authors, so they are not independent.

Every query has a level: `required` (follows from the assignment's text), `expected` (a reasonable reviewer would
expect it) or `nice` (desirable; a miss is not a defect).

## What the tables mean

**Strict pass.** Results outside the query's scope are dropped first. A query passes only if every condition that
applies holds:

1. `empty`: the list is empty;
2. `relevant`: all listed results are present (with `within_top`, for typos and questions, at least one of them in the
   first k; when there are more than 50 relevant results, 50 suffice);
3. `others: wrong`, the default: nothing besides `relevant` and `acceptable`;
4. `must_not`: none of these;
5. `first`: the first result is one of these;
6. `top_set`: the first places hold exactly these;
7. `before`: for each pair both are present and the first ranks higher;
8. `min_results`: at least this many results.

One wrong result, even in last place, fails the query. In 532 queries of eight suites (`others: ignore`, for example
FiQA and Enron) extra results are not penalised.

**First 10.** Micro-averaged over (query, result) pairs in the first 10 results: a relevant result is a true
positive; an `acceptable` one is ignored; any other result is a false positive (for queries with `others: wrong`, and
every result of a query without an answer); a missed relevant result is a false negative (at most 10 per query).
`hit@10` is the share of answerable queries with a relevant result in the first 10; "no-answer clean" is the share of
the 230 queries without an answer that return nothing.

## Expected numbers

The reference implementation of the design (the same SQL, model and rules, without HTTP) scored this during design:

| | With the concept map | Without |
|---|---|---|
| Strict pass, all 1,887 | 1,325 (70 %) | 1,330 (70 %) |
| written blind, 400 | 255 | 259 |
| open datasets, 951 | 640 | 642 |
| research, independent, 391 | 298 | 298 |
| research, by the design's authors, 145 | 132 | 131 |
| required, 621 | 546 | 549 |
| First 10: precision / recall / F1 | 0.80 / 0.74 / 0.766 | 0.82 / 0.69 / 0.747 |
| hit@10 | 0.86 | 0.84 |
| no-answer clean (230) | 0.67 | 0.68 |

The shipped code scores 2 fewer strict passes in each configuration (1,323 and 1,328), and 2 fewer in the rows
"research, independent" and "required". The reference run loaded one client whose description exceeds the API's
2,000-character limit; without that client, queries B01 and B02 of `existing-clients-skeptic-44` (required,
research) always fail. Every other number above is the same in `results/`.

## Caveats

- The corpora are synthetic, except Enron, FiQA (forum posts), the sanctions list and RVL-CDIP; real documents need
  new thresholds.
- Two suites were written by the design's authors, and the thresholds were chosen on the `dev` half of a third suite;
  "written blind" and "open datasets" are the rows from outside the research.
- `codex-mixed` expects 200 and `[]` for an empty `q`, while the API answers 422: h23 and h24 of
  `tests/integration/test_http_cases.py` are expected failures (55 of the 57 HTTP checks pass).
- For future tuning, split the set by whole suites, not by query: otherwise spellings of one query land in both
  halves.
- Adding phrases from failed queries to the concept map would fit the map to this test set; new phrases come from
  official lists only.
