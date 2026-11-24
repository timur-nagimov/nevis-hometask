#!/usr/bin/env python3
"""Render every suite as a readable markdown list: query -> correct answer.

Usage: python3 render.py suites/*.json   (writes lists/<suite>.md)
"""
import json
import os
import sys

LEVEL_RU = {"required": "обязательно", "expected": "ожидаемо", "nice": "желательно"}


def label(item: dict) -> str:
    if "first_name" in item:
        return f"{item['first_name']} {item['last_name']} <{item['email']}>"
    return f"«{item['title']}»"


def cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def show_query(q: str) -> str:
    if not q.strip() or any(ord(ch) < 32 or 0xD800 <= ord(ch) <= 0xDFFF or ord(ch) in (0x200B, 0xFEFF, 0xA0, 0xAD) for ch in q):
        return "`" + q.encode("unicode_escape").decode("ascii") + "`"
    return "`" + (q if len(q) <= 80 else q[:77] + "…") + "`"


def answer(q: dict, items: dict) -> str:
    if q.get("empty"):
        return "пустой список"
    parts = []
    rel = [label(items[i]) for i in q.get("relevant", [])]
    if rel:
        prefix = f"хотя бы один в первых {q['within_top']}: " if q.get("within_top") else ""
        parts.append(prefix + "; ".join(rel))
    if q.get("acceptable"):
        parts.append("допустимо: " + "; ".join(label(items[i]) for i in q["acceptable"]))
    if q.get("first"):
        parts.append("первым: " + " или ".join(label(items[i]) for i in q["first"]))
    if q.get("top_set"):
        parts.append("первые " + str(len(q["top_set"])) + ": " + "; ".join(label(items[i]) for i in q["top_set"]))
    for a, b in q.get("before", []):
        parts.append(f"{label(items[a])} выше, чем {label(items[b])}")
    if q.get("must_not"):
        parts.append("не должно быть: " + "; ".join(label(items[i]) for i in q["must_not"]))
    if q.get("min_results"):
        parts.append(f"не меньше {q['min_results']} результатов")
    if q.get("others") == "ignore":
        parts.append("прочие результаты не оцениваются")
    return "<br>".join(parts)


def render(path: str, out_dir: str) -> str:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    c = data["corpus"]
    items = {x["id"]: x for x in (c.get("clients") or []) + (c.get("documents") or [])}
    lines = [f"# {data['suite']}", "", f"Автор: {data['author']}.", ""]
    if data.get("about"):
        lines += [data["about"], ""]
    lines += [f"Корпус: {len(c.get('clients') or [])} клиентов, {len(c.get('documents') or [])} документов "
              f"(полный текст — в `suites/{os.path.basename(path)}`).", "",
              "| id | Запрос | Уровень | Категория | Правильный ответ | Почему |", "|---|---|---|---|---|---|"]
    for q in data["queries"]:
        scope = {"clients": " (только клиенты)", "documents": " (только документы)"}.get(q.get("scope", "all"), "")
        lines.append(f"| {q['id']} | {cell(show_query(q['q']))} | {LEVEL_RU[q['level']]} | {cell(q['category'])}{scope} | "
                     f"{cell(answer(q, items))} | {cell(q['why'])} |")
    if data.get("http_cases"):
        lines += ["", "## Проверки HTTP-контракта", "", "| id | Запрос | Ожидаемый код | Почему |", "|---|---|---|---|"]
        for h in data["http_cases"]:
            req = h["method"] + " " + h["path"]
            if h.get("query"):
                req += " ?" + "&".join(f"{k}={show_query(str(v)).strip('`')}" for k, v in h["query"].items())
            if h.get("body") is not None:
                req += " " + json.dumps(h["body"], ensure_ascii=False)[:120]
            lines.append(f"| {h['id']} | {cell('`' + req + '`')} | {' или '.join(map(str, h['expected_status']))} | {cell(h['why'])} |")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, data["suite"] + ".md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return out


NOT_INDEPENDENT = {"existing-clients-fixture-42": "нет: автор эталонного SQL", "tools-mini-6": "нет: автор плана"}
DATASETS = {"enron": "Enron + EnronQA", "fiqa": "FiQA-2018", "gretel": "Gretel synthetic finance",
            "opensanctions": "UK Sanctions List (FCDO)", "rvlcdip": "RVL-CDIP с OCR", "senzing": "Senzing + nicknames",
            "sinabis": "sinabis synthetic PDF", "splink": "Splink fake_1000"}


def origin(name: str) -> str:
    if name.startswith("codex-"):
        return "написан вслепую: Codex (GPT-6)"
    if name.startswith("claude-"):
        return "написан вслепую: Claude Opus 5.5"
    if name.startswith("ds-"):
        key = name.split("-")[1]
        return "датасет: " + DATASETS.get(key, key)
    return "из исследования"


def update_readme(here: str) -> None:
    """Regenerate the table of suites between the markers in README.md."""
    rows = ["| Набор | Происхождение | Корпус | Запросы: обязательно / ожидаемо / желательно | HTTP-проверки | Независим от плана |",
            "|---|---|---|---|---|---|"]
    total = [0, 0, 0, 0, 0]
    for name in sorted(os.listdir(os.path.join(here, "suites"))):
        with open(os.path.join(here, "suites", name), encoding="utf-8") as fh:
            data = json.load(fh)
        c, qs = data["corpus"], data["queries"]
        lv = [sum(q["level"] == x for q in qs) for x in ("required", "expected", "nice")]
        nh = len(data.get("http_cases") or [])
        total = [total[0] + len(qs), total[1] + lv[0], total[2] + lv[1], total[3] + lv[2], total[4] + nh]
        rows.append(f"| [{data['suite']}](lists/{data['suite']}.md) | {origin(data['suite'])} | "
                    f"{len(c.get('clients') or [])} клиентов, {len(c.get('documents') or [])} документов | "
                    f"{len(qs)}: {lv[0]} / {lv[1]} / {lv[2]} | {nh} | {NOT_INDEPENDENT.get(data['suite'], 'да')} |")
    rows.append(f"| **Всего** | | | **{total[0]}: {total[1]} / {total[2]} / {total[3]}** | **{total[4]}** | |")
    path = os.path.join(here, "README.md")
    text = open(path, encoding="utf-8").read()
    start, end = text.index("<!-- suites:start -->"), text.index("<!-- suites:end -->")
    text = text[: start + len("<!-- suites:start -->")] + "\n" + "\n".join(rows) + "\n" + text[end:]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    for p in sys.argv[1:]:
        print(render(p, os.path.join(here, "lists")))
    update_readme(here)
