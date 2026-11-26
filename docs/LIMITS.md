# Limits

- **What a document is for** (`proof of income`, `photo ID`) is the weakest kind of query: the map is a closed list,
  so phrasings it lacks ("Council Tax demand notice") get no tag, and documents that merely mention the words, or carry
  a neighbouring tag, come back too.
- **`address proof`** with Claude off also returns "Proof of delivery … home address" and letters asking for proof
  of address. With Claude, still 0/10.
- **Client substrings inside words:** `Chester` finds Manchester, `Ng` finds England. Test authors disagree;
  whole-word matching for up to three letters is the first alternative to measure.
- **Similar names:** `Sergey Menshikov` finds Sergey Melikov; removing typo matching loses more typos and nicknames.
- **Typos inside a document's text** are not corrected, only in titles and concept phrases; swapped letters in a short
  name (`Jhon`) defeat trigrams.
- **Names in another script:** Cyrillic or Arabic spellings of Latin names are not found.
- **Queries without answers:** up to three weak guesses below 0.2 (`marriage certificate`); wrong semantic matches
  above 0.2 (`tenancy agreement`). Relative semantic cutoff can omit "Electricity bill" for `utility bill`.
- **Long and empty queries** get 422 (over 200 characters, or only spaces); one test suite expects 200 and `[]` for
  the empty one.

## What is not verified

- **Real data.** All corpora are synthetic or public; the thresholds were chosen on synthetic documents and should be
  re-tuned on real ones ([eval/README.md](../eval/README.md)).
- **Scale.** There is no vector index and no candidate cap. Design-time measurements put document search above 0.1 s
  at about 10,000 fragments, and very common client substrings (`gmail`, `com`) at 0.35-1.9 s per query with 100,000
  clients.
- **Whole API process memory.** Unmeasured; the model alone took about 180 MB, peaking at 415 MB
  while loading (design-time).
- **Platforms.** Built and tested with podman on Apple Silicon (arm64) and with Docker on x86_64 in
  [GitHub Actions](https://github.com/timur-nagimov/nevis-hometask/actions/workflows/ci.yml); Docker Desktop on
  Windows was not tried.
- **Deployed copy.** Reachability from outside Russia was not verified.
