"""Show a check: in the terminal, as JSON, or as one HTML file that opens anywhere."""
from __future__ import annotations

import html
import json
import os
import re
import sys
from pathlib import Path

LABELS = {
    "en": {
        "supported": "found", "quote_not_found": "quote not in the sources", "no_source": "no source says this",
        "numbers_not_in_source": "numbers not in the source line", "missing": "not found", "nearest": "closest",
        "rounded": "rounded", "from": "from",
        "summary": "{checked} {sentences} checked: {supported} found in the sources, {flagged} not.",
        "skipped": " {skipped} {sentences} without a number or quotation {were} not checked.",
        "with_llm": " {k} of the found {sentences} {were} found through the passages chosen with --llm.",
        "title": "Draft check", "sources": "Sources", "problems": "Not found in the sources", "found": "Found in the sources",
        "none": "Every checked sentence was found in the sources.", "line": "line", "colon": ": ", "list": ", ",
        "k_checked": "sentences checked", "k_flagged": "not found", "k_supported": "found",
    },
    "zh": {
        "supported": "找到", "quote_not_found": "资料里没有这句引文", "no_source": "资料里找不到相关内容",
        "numbers_not_in_source": "数字和资料对不上", "missing": "找不到", "nearest": "最接近",
        "rounded": "四舍五入", "from": "出自",
        "summary": "核对了 {checked} 句：{supported} 句在资料里找到，{flagged} 句没有。",
        "skipped": "另有 {skipped} 句没有数字或引文，没有核对。",
        "with_llm": "找到的句子里有 {k} 句，原文是用 --llm 找出来的。",
        "title": "查稿结果", "sources": "资料", "problems": "和资料对不上的句子", "found": "在资料里找到的句子",
        "none": "核对的句子都在资料里找到了。", "line": "第 {n} 行", "colon": "：", "list": "、",
        "k_checked": "句核对", "k_flagged": "句对不上", "k_supported": "句找到",
    },
}


LIST_MARK = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")


def show(text: str) -> str:
    """A source line as a reader wants it: without its list marker and surrounding spaces."""
    return LIST_MARK.sub("", text).strip()


def guess_lang(text: str) -> str:
    cjk = sum("一" <= c <= "鿿" for c in text)
    return "zh" if cjk > len(text) * 0.15 else "en"


PLACE = re.compile(r"^(?:(?P<sheet>.+), )?(?:line|row) (?P<n>\d+)$")


def place(text: str, lang: str) -> str:
    """"line 7" / "Sheet1, row 4" in the report's language."""
    m = PLACE.match(text)
    if lang != "zh" or not m:
        return text
    return (f'{m["sheet"]} 表第 {m["n"]} 行' if m["sheet"] else f'第 {m["n"]} 行')


def line_text(e: dict, lang: str) -> str:
    """A source line for the report. A table row is evcheck's own "header: value | ..." rendering, so a Chinese
    report writes it with Chinese punctuation; any other line is shown as it is in the file."""
    text = show(e["text"])
    if lang == "zh" and re.search(r"(^|, )row \d+$", e["place"]):
        text = text.replace(": ", "：").replace(" | ", "；")
    return text


def where(e: dict, lang: str) -> str:
    """The file and the place in it: "survey.csv, row 4" or "门店周数据.csv 第 4 行"."""
    return f'{e["file"]}{" " if lang == "zh" else ", "}{place(e["place"], lang)}'


def summary(L, m: dict) -> str:
    def word(k):
        return {"sentences": "sentence" if k == 1 else "sentences", "were": "was" if k == 1 else "were"}
    out = L["summary"].format(checked=m["checked"], supported=m["supported"], flagged=m["flagged"], **word(m["checked"]))
    if m["not_checked"]:
        out += L["skipped"].format(skipped=m["not_checked"], **word(m["not_checked"]))
    if m.get("found_with_llm"):
        out += L["with_llm"].format(k=m["found_with_llm"], **word(m["found_with_llm"]))
    return out


def _line(L, n: int) -> str:
    return L["line"].format(n=n) if "{n}" in L["line"] else f'{L["line"]} {n}'


def _color(enabled: bool):
    if not enabled:
        return lambda s, _c: s
    codes = {"ok": "32", "bad": "31", "dim": "2", "bold": "1"}
    return lambda s, c: f"\033[{codes[c]}m{s}\033[0m"


def render_text(report: dict, lang: str, only_problems: bool = False, color: bool | None = None) -> str:
    L = LABELS[lang]
    if color is None:
        color = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
    paint = _color(color)
    out = [paint(f"evcheck  {report['draft']}  ←  {L['list'].join(report['sources'])}", "bold"), ""]
    for s in report["sentences"]:
        bad = s["status"] != "supported"
        if only_problems and not bad:
            continue
        mark = paint("✗", "bad") if bad else paint("✓", "ok")
        out.append(f" {mark}  {_line(L, s['line'])}  {s['text']}")
        if bad:
            out.append(f"      {paint(L[s['status']], 'bad')}")
            if s["missing_numbers"]:
                out.append(f"      {L['missing']}{L['colon']}{L['list'].join(s['missing_numbers'])}")
            for p in s["problems"]:
                if p["kind"] == "quote_not_found":
                    out.append(f"      “{p['quote']}”")
            if s["nearest"]:
                n = s["nearest"]
                out.append(paint(f"      {L['nearest']}{L['colon']}{where(n, lang)}{L['colon']}{line_text(n, lang)}", "dim"))
        else:
            for e in s["evidence"][:2]:
                out.append(paint(f"      {L['from']} {where(e, lang)}{L['colon']}{line_text(e, lang)}", "dim"))
            if s["rounded"]:
                out.append(paint(f"      {L['rounded']}{L['colon']}" + L["list"].join(f"{r['claim']} ← {r['quote']}" for r in s["rounded"]), "dim"))
    m = report["summary"]
    out += ["", summary(L, m)]
    return "\n".join(out)


def render_json(report: dict) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2)


def _esc(s) -> str:
    return html.escape(str(s), quote=True)


def render_html(report: dict, lang: str) -> str:
    L = LABELS[lang]
    css = (Path(__file__).parent / "assets" / "report.css").read_text(encoding="utf-8")
    m = report["summary"]
    bad = [s for s in report["sentences"] if s["status"] != "supported"]
    good = [s for s in report["sentences"] if s["status"] == "supported"]

    def at(e):
        return _esc(where(e, lang))

    rows_bad = []
    for s in bad:
        detail = []
        if s["missing_numbers"]:
            detail.append(f'<p class="r-miss">{_esc(L["missing"] + L["colon"])}<b class="k-num">{_esc(L["list"].join(s["missing_numbers"]))}</b></p>')
        for p in s["problems"]:
            if p["kind"] == "quote_not_found":
                detail.append(f'<p class="r-miss">“{_esc(p["quote"])}”</p>')
        if s["nearest"]:
            n = s["nearest"]
            detail.append(f'<blockquote class="k-quote"><span class="k-label">{_esc(L["nearest"])}</span><br>{_esc(line_text(n, lang))}<cite>{at(n)}</cite></blockquote>')
        rows_bad.append(
            f'<li class="k-card r-item"><div class="r-top"><span class="k-mark k-mark--stop">{_esc(L[s["status"]])}</span>'
            f'<span class="k-label">{_esc(_line(L, s["line"]))}</span></div><p class="r-sent k-read">{_esc(s["text"])}</p>{"".join(detail)}</li>')
    rows_good = []
    for s in good:
        ev = s["evidence"][0] if s["evidence"] else None
        src = f'<cite>{at(ev)}</cite>' if ev else ""
        extra = ""
        if s["rounded"]:
            extra = f'<span class="k-tag">{_esc(L["rounded"])} ' + _esc(L["list"].join(f"{r['claim']} ← {r['quote']}" for r in s["rounded"])) + "</span>"
        rows_good.append(f'<li class="r-good"><span class="k-mark k-mark--yes">{_esc(L["supported"])}</span>'
                         f'<span class="k-label">{_esc(_line(L, s["line"]))}</span><span class="r-gtext">{_esc(s["text"])}{src}</span>{extra}</li>')

    page_lang = "zh-CN" if lang == "zh" else "en"
    return f"""<!doctype html>
<html lang="{page_lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(L["title"] + L["colon"] + report["draft"])}</title>
<style>
{css}
.r-hero {{ padding-block: clamp(40px, 6vw, 72px) clamp(32px, 4vw, 48px); }}
.r-hero h1 {{ font-size: clamp(30px, 4vw, 48px); margin: 12px 0 16px; overflow-wrap: anywhere; }}
.r-src {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }}
.r-list {{ display: grid; gap: 16px; padding: 0; margin: 0 0 48px; list-style: none; }}
.r-top {{ display: flex; gap: 12px; align-items: center; margin-bottom: 8px; }}
.r-sent {{ font-size: 18px; margin-bottom: 12px; }}
.r-miss {{ font-size: 15px; margin-bottom: 12px; color: var(--stop); }}
.r-good {{ display: grid; grid-template-columns: auto 6em 1fr; gap: 12px; align-items: baseline; padding: 12px 0; border-top: 1px solid var(--rule-2); font-size: 15px; }}
.r-gtext cite {{ display: block; font-style: normal; font-size: 13px; color: var(--muted); }}
.r-good .k-tag {{ grid-column: 3; justify-self: start; }}
.r-sec h2 {{ font-size: 24px; margin-bottom: 16px; }}
.r-foot {{ padding-bottom: 48px; }}
.r-sec.k-sec {{ padding-block: clamp(40px, 5vw, 64px) 0; }}
.r-item .k-quote {{ margin: 0; }}
.k-night .k-keys li {{ background: var(--night-2); box-shadow: inset 0 0 0 1px var(--night-rule); }}
.k-night .k-keys .k-keys-l {{ color: var(--on-night-2); }}
.k-night .k-big.r-badnum {{ color: oklch(0.78 0.14 35); }}
@media (max-width: 640px) {{ .r-good {{ grid-template-columns: auto 1fr; }} .r-good .k-label {{ display: none; }} .r-good .k-tag {{ grid-column: 2; }} }}
</style>
</head>
<body>
<header class="k-night"><div class="k-wrap r-hero">
<p class="k-label">evcheck · {_esc(L["title"])}</p>
<h1>{_esc(report["draft"])}</h1>
<ul class="k-keys">
<li><b class="k-big k-num">{m["checked"]}</b><span class="k-keys-l">{_esc(L["k_checked"])}</span></li>
<li><b class="k-big k-num{' r-badnum' if m['flagged'] else ''}">{m["flagged"]}</b><span class="k-keys-l">{_esc(L["k_flagged"])}</span></li>
<li><b class="k-big k-num">{m["supported"]}</b><span class="k-keys-l">{_esc(L["k_supported"])}</span></li>
</ul>
<div class="r-src"><span class="k-label">{_esc(L["sources"])}</span>{"".join(f'<span class="k-tag">{_esc(s)}</span>' for s in report["sources"])}</div>
</div></header>
<main class="k-wrap">
<section class="r-sec k-sec"><h2>{_esc(L["problems"])}</h2>
{f'<ul class="r-list">{"".join(rows_bad)}</ul>' if rows_bad else f'<p class="k-read">{_esc(L["none"])}</p>'}
</section>
<section class="r-sec"><h2>{_esc(L["found"])}</h2><ul class="r-list" style="gap:0">{"".join(rows_good)}</ul></section>
<p class="k-label r-foot">{_esc(summary(L, m))}</p>
</main>
</body>
</html>
"""
