# API details

- Errors are `application/problem+json` (RFC 9457); a 422 adds `errors` (`loc`, `msg`, `type`) and never repeats the
  submitted value. Any call that uses the database may answer 500 without details, or 503 with `Retry-After: 5`
  (database unreachable, busy, or a query over 5 s). A body over 2 MiB gets 413, possibly as plain text.
- A search item is the client or document itself plus `type`, `score` and `match_type`, so `item["email"]` works.
  Documents carry `tags` (matched or Claude-added concepts) and `summary` (first sentences, up to
  300 characters, plus '…' when cut, `"method": "extractive"`; with Claude enabled, up to
  600 characters, `"method": "llm"`).
- Validation: names up to 100 characters, description 2,000, 20 social links, title 300, text 50,000, `q` 1-200 after
  collapsing whitespace. Control characters are rejected, except tab and newline in a description or a document's
  text (and carriage return in the text). Non-UUID path ids get 404. E-mails may repeat (spouses share
  addresses), so no 409.
- The 200-character cap on `q` bounds the substring patterns and the client typo tier; longer queries were not
  measured.
- Results carry whole documents, like the assignment's Document model: at most 50 documents of 50,000 characters,
  about 2.5 MB of Latin text and up to about 7.5 MB in other scripts; a few kilobytes on the demo data.
- Swagger UI offers both assignment queries as examples.
