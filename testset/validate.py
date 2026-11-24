#!/usr/bin/env python3
"""Validate search test suites. Usage: python3 validate.py suites/*.json

A suite holds a corpus (clients, documents), queries with their correct answers and,
optionally, HTTP contract checks. The format is described in README.md.
"""
import collections
import json
import sys

LEVELS = {"required", "expected", "nice"}
SCOPES = {"all", "clients", "documents"}
OTHERS = {"wrong", "ignore"}
METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


def validate(path: str) -> list[str]:
    errors: list[str] = []
    err = errors.append
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:  # noqa: BLE001
        return [f"cannot parse: {exc}"]
    for key in ("suite", "author", "corpus", "queries"):
        if key not in data:
            err(f"missing top-level key: {key}")
    corpus = data.get("corpus") or {}
    kinds: dict[str, str] = {}
    for c in corpus.get("clients") or []:
        cid = c.get("id")
        if not isinstance(cid, str) or not cid.startswith("c") or cid in kinds:
            err(f"bad or duplicate client id: {cid!r}")
        kinds[cid] = "client"
        for f in ("first_name", "last_name", "email"):
            if not isinstance(c.get(f), str) or not c[f].strip():
                err(f"client {cid}: {f} must be a non-empty string")
        if not isinstance(c.get("description", ""), str):
            err(f"client {cid}: description must be a string")
        links = c.get("social_links", [])
        if not isinstance(links, list) or not all(isinstance(x, str) for x in links):
            err(f"client {cid}: social_links must be a list of strings")
    for d in corpus.get("documents") or []:
        did = d.get("id")
        if not isinstance(did, str) or not did.startswith("d") or did in kinds:
            err(f"bad or duplicate document id: {did!r}")
        kinds[did] = "document"
        if kinds.get(d.get("client_id")) != "client":
            err(f"document {did}: client_id {d.get('client_id')!r} is not a client id")
        for f in ("title", "content"):
            if not isinstance(d.get(f), str) or not d[f].strip():
                err(f"document {did}: {f} must be a non-empty string")
    qids: set[str] = set()
    for q in data.get("queries") or []:
        qid = q.get("id")
        if not isinstance(qid, str) or not qid or qid in qids:
            err(f"bad or duplicate query id: {qid!r}")
        qids.add(qid)
        if not isinstance(q.get("q"), str):
            err(f"query {qid}: q must be a string")
        if q.get("level") not in LEVELS:
            err(f"query {qid}: level must be one of {sorted(LEVELS)}")
        if not isinstance(q.get("category"), str) or not q.get("category"):
            err(f"query {qid}: category must be a non-empty string")
        if q.get("scope", "all") not in SCOPES:
            err(f"query {qid}: scope must be one of {sorted(SCOPES)}")
        if q.get("others", "wrong") not in OTHERS:
            err(f"query {qid}: others must be one of {sorted(OTHERS)}")
        lists = {name: q.get(name, []) for name in ("relevant", "acceptable", "first", "must_not", "top_set")}
        for name, lst in lists.items():
            if not isinstance(lst, list):
                err(f"query {qid}: {name} must be a list")
                continue
            for x in lst:
                if x not in kinds:
                    err(f"query {qid}: {name} id {x!r} is not in the corpus")
        rel, acc = set(lists["relevant"] or []), set(lists["acceptable"] or [])
        if rel & acc:
            err(f"query {qid}: ids in both relevant and acceptable: {sorted(rel & acc)}")
        if set(lists["must_not"] or []) & (rel | acc):
            err(f"query {qid}: must_not overlaps relevant or acceptable")
        if lists["first"] and not set(lists["first"]) <= rel | acc:
            err(f"query {qid}: every id in first must also be in relevant or acceptable")
        for pair in q.get("before", []):
            if not (isinstance(pair, list) and len(pair) == 2 and all(x in kinds for x in pair)):
                err(f"query {qid}: before must be a list of [id, id] pairs from the corpus")
        for name in ("min_results", "within_top"):
            if name in q and (not isinstance(q[name], int) or q[name] < (1 if name == "within_top" else 0)):
                err(f"query {qid}: {name} must be a positive integer")
        empty = q.get("empty", False)
        if not isinstance(empty, bool):
            err(f"query {qid}: empty must be true or false")
        elif empty and (rel or acc or lists["first"]):
            err(f"query {qid}: empty is true, so relevant, acceptable and first must be empty")
        checkable = empty or rel or lists["must_not"] or lists["top_set"] or q.get("before") or "min_results" in q
        if not checkable:
            err(f"query {qid}: nothing to check (no relevant, empty, must_not, top_set, before or min_results)")
        if not isinstance(q.get("why"), str) or not q["why"].strip():
            err(f"query {qid}: why must be a non-empty string")
    hids: set[str] = set()
    for h in data.get("http_cases") or []:
        hid = h.get("id")
        if not isinstance(hid, str) or not hid or hid in hids:
            err(f"http case id missing or duplicated: {hid!r}")
        hids.add(hid)
        if h.get("method") not in METHODS:
            err(f"http case {hid}: method must be one of {sorted(METHODS)}")
        if not isinstance(h.get("path"), str) or not h["path"].startswith("/"):
            err(f"http case {hid}: path must start with /")
        st = h.get("expected_status")
        if not isinstance(st, list) or not st or not all(isinstance(s, int) and 100 <= s <= 599 for s in st):
            err(f"http case {hid}: expected_status must be a non-empty list of HTTP status codes")
        if not isinstance(h.get("why"), str) or not h["why"].strip():
            err(f"http case {hid}: why must be a non-empty string")
    return errors


def summary(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    qs = data.get("queries") or []
    levels = collections.Counter(q.get("level") for q in qs)
    c = data.get("corpus") or {}
    return (f"{len(c.get('clients') or [])} clients, {len(c.get('documents') or [])} documents, {len(qs)} queries "
            f"({', '.join(f'{k} {v}' for k, v in sorted(levels.items()))}), {len(data.get('http_cases') or [])} http cases")


def main(paths: list[str]) -> int:
    failed = 0
    for path in paths:
        errors = validate(path)
        if errors:
            failed += 1
            print(f"FAIL {path}")
            print("\n".join("  " + e for e in errors[:50]))
        else:
            print(f"OK   {path}: {summary(path)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["suite.json"]))
