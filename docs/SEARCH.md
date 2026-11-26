# How search decides

**Clients.** Query and record use Unicode NFKC, accent removal and case folding. `exact` requires every query word
in name, e-mail or description: `neviswealth`, `wealth`, `john.doe`, `Doe John` find John Doe. With no matches and
at least 5 letters/digits, trigrams handle typos (`NevisWelth`, `Jon Doe` → `fuzzy`).

**Documents.** Documents are cut into fragments of up to 200 words, each with a vector; a document's cosine is its
best fragment's. One SQL statement, four ways in:

1. *literal*: every query word (English stemming) is in the title, the text or the tags → `lexical`, or `concept`
   when the tags were needed;
2. *typo*, only if the literal way found nothing: the title resembles the query, or the query is a misspelt concept
   phrase (`adress proof`) → `fuzzy`;
3. *meaning*: the document's cosine is at least 0.40 and within 0.08 of the best document's → `semantic`;
4. *weak guess*, only if nothing above matched: up to three nearest documents with a cosine of at least 0.32 →
   `semantic`.

Both kinds are fetched with `limit` each, merged, sorted by score, type and id, and cut to `limit` (1-50, default 10).

| Score | Meaning | `match_type` |
|---|---|---|
| 0.5 and above | the query's words are in the record, or in the document's tags | `exact`, `lexical`, `concept` |
| 0.2 to 0.5 | a strong semantic match, or a typo | `semantic`, `fuzzy` |
| below 0.2 | a weak semantic guess, or a client typo found only in the description (at most 0.245) | `semantic`, `fuzzy` |

For confident results, drop `semantic` items below 0.2.

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

`app/data/concepts.yaml` lists 30 concepts, query phrasings (`triggers`) and accepted documents (`expands_to`).
Concept names and `expands_to` phrases matched at upload become tags. Tags/triggers enter literal matching and,
for title matches or documents up to 200 words, an embedded fragment. Bills thus return as `concept` with
`proof of address` tags. Claude can add concepts and phrases when enabled.

An LLM drafted 120 entries from UK wealth-management knowledge, cut to 30 relations by dropping single documents,
topics and identifiers. Four cite official lists (GOV.UK, Bona Vacantia, DBS, JMLSG). Other relations include
`proof of income` → payslip and `photo ID` → passport.

## The demo queries

`NevisWealth` finds the client with the e-mail john.doe@neviswealth.com. `exact`: every query word is part of the
client's name, e-mail or description.

`address proof` finds the utility bills. `concept`: the query's words are in the tags the documents got at upload
(`proof of address`), not in their text. "Scan 0042" mentions "utility bill" only once, inside a 123-word text.

A query with no answer gets an empty list. The [main README](../README.md#the-two-examples-from-the-assignment)
shows captured output for all three queries.
