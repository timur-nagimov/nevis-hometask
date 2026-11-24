#!/usr/bin/env python3
"""Score search results against a suite.

Usage:
  python3 score.py suites/X.json results.json   # results: {"<query id>": ["<corpus id>", ...] in ranked order}
  python3 score.py suites/X.json --oracle       # self-check: build ideal results from the expectations and score them
  ... --limit N                                 # results were collected with an API limit of N: a query whose
                                                # relevant set is larger than N needs N relevant results, not all

A query passes when every check that applies to it passes (see README.md, "Как засчитывается ответ").
"""
import collections
import json
import sys


def checks(q: dict, returned: list[str], kinds: dict[str, str], limit: int | None = None) -> list[str]:
    scope = q.get("scope", "all")
    got = [r for r in returned if scope == "all" or kinds.get(r) == scope[:-1]]
    rel, acc = q.get("relevant", []), q.get("acceptable", [])
    fails = []
    if q.get("empty"):
        if got:
            fails.append(f"expected nothing, got {got[:5]}")
        return fails
    if rel:
        k = q.get("within_top")
        if k and not set(rel) & set(got[:k]):
            fails.append(f"none of {rel} in the first {k}")
        need = len(rel) if limit is None else min(len(rel), limit)
        hits = len(set(rel) & set(got))
        if not k and hits < need:
            missing = sorted(set(rel) - set(got))
            fails.append(f"missing {missing}" if need == len(rel) else f"{hits} of {len(rel)} relevant returned, need {need}")
    if q.get("others", "wrong") == "wrong":
        extra = [r for r in got if r not in rel and r not in acc]
        if extra:
            fails.append(f"unexpected {extra[:5]}")
    bad = [r for r in got if r in set(q.get("must_not", []))]
    if bad:
        fails.append(f"must not return {bad}")
    if q.get("first") and (not got or got[0] not in q["first"]):
        fails.append(f"first is {got[0] if got else None}, expected one of {q['first']}")
    ts = q.get("top_set")
    if ts and set(got[: len(ts)]) != set(ts):
        fails.append(f"first {len(ts)} are {got[:len(ts)]}, expected {sorted(ts)}")
    for a, b in q.get("before", []):
        if a not in got or b not in got or got.index(a) > got.index(b):
            fails.append(f"{a} should be ranked above {b}")
    if len(got) < q.get("min_results", 0):
        fails.append(f"{len(got)} results, expected at least {q['min_results']}")
    return fails


def oracle(q: dict, kinds: dict[str, str]) -> list[str]:
    if q.get("empty"):
        return []
    pairs = [x for pair in q.get("before", []) for x in pair]  # both ids of a "before" pair must be present
    order = list(dict.fromkeys(q.get("first", [])[:1] + q.get("top_set", []) + q.get("relevant", []) + pairs))
    for _ in range(len(order)):  # satisfy "before" pairs by bubbling
        for a, b in q.get("before", []):
            if a in order and b in order and order.index(a) > order.index(b):
                order.remove(a)
                order.insert(order.index(b), a)
    if len(order) < q.get("min_results", 0):
        pool = [i for i in kinds if i not in order and i not in q.get("must_not", [])]
        order += pool[: q["min_results"] - len(order)]
    return order


def main(argv: list[str]) -> int:
    suite = json.load(open(argv[0], encoding="utf-8"))
    corpus = suite["corpus"]
    kinds = {c["id"]: "client" for c in corpus.get("clients") or []}
    kinds.update({d["id"]: "document" for d in corpus.get("documents") or []})
    limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else None
    if argv[1] == "--oracle":
        results = {q["id"]: oracle(q, kinds)[:limit] for q in suite["queries"]}
    else:
        results = json.load(open(argv[1], encoding="utf-8"))
    by_level: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])
    by_cat: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])
    failures = []
    for q in suite["queries"]:
        fails = checks(q, results.get(q["id"], []), kinds, limit)
        for table, key in ((by_level, q["level"]), (by_cat, q["category"])):
            table[key][0] += not fails
            table[key][1] += 1
        if fails:
            failures.append((q, fails))
    total = sum(v[1] for v in by_level.values())
    passed = sum(v[0] for v in by_level.values())
    print(f"{suite['suite']}: {passed}/{total} queries pass")
    for level in ("required", "expected", "nice"):
        if level in by_level:
            p, n = by_level[level]
            print(f"  {level:9} {p}/{n}")
    print("  by category: " + ", ".join(f"{k} {p}/{n}" for k, (p, n) in sorted(by_cat.items())))
    for q, fails in failures[:40]:
        print(f"  FAIL {q['id']} [{q['level']}] {q['q']!r}: {'; '.join(fails)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
