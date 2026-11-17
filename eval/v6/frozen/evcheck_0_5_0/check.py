"""Check a finished draft against its sources, with no claims file and no model.

1. Split the draft into sentences and keep the ones that state a number or a quotation.
2. For each one, find the source lines it shares the most words with (Chinese is compared by pairs of
   characters, other languages by words; numbers are left out of this step on purpose, so a changed number
   cannot pull in a line that happens to contain it).
3. Hand the sentence and those lines to evidence-check's rules: every quotation must be word for word in a
   source, and every number in the sentence must be in its lines.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from .readers import Doc
from .rules import ce

QUOTE_RE = re.compile(r"“([^“”\n]{2,})”|\"([^\"\n]{4,})\"|「([^「」\n]{2,})」|『([^『』\n]{2,})』")
CJK_RE = re.compile(r"[㐀-鿿豈-﫿]+")
WORD_RE = re.compile(r"[a-z][a-z'’-]*")
STOP = set("""a an and are as at be been but by for from had has have in into is it its of on or our that the
their them they this to was we were which will with would you your not no than then there these those""".split())
SENT_END = "。！？；!?;"
CLOSERS = "”’\"」』）)】]"
MIN_SHARE = 0.2      # a line must share at least this part of a sentence's words to count as its source
NEAR_BEST = 0.6      # ... and be at least this close to the best line
MAX_LINES = 3


def tokens(text: str) -> set:
    """Words cut to their first five letters (register, registration -> regis); Chinese as pairs of characters."""
    t = unicodedata.normalize("NFKC", text).lower()
    words = {w.strip("'’-") for w in WORD_RE.findall(t)} - STOP - {""}
    out = {w[:5] for w in words}
    for run in CJK_RE.findall(t):
        out |= {run} if len(run) == 1 else {run[i:i + 2] for i in range(len(run) - 1)}
    return out


def split_sentences(line: str) -> list:
    """Sentences of one line: cut after 。！？；!?; and after a full stop followed by a space."""
    out, start, i, n = [], 0, 0, len(line)
    while i < n:
        ch = line[i]
        # a full stop ends a sentence only before a space or the end of the line, so 4.2 and 1,234.5 stay whole
        end = ch in SENT_END or (ch == "." and (i + 1 == n or line[i + 1].isspace()))
        if end:
            j = i + 1
            while j < n and line[j] in CLOSERS:
                j += 1
            if line[start:j].strip():
                out.append(line[start:j].strip())
            start = i = j
            continue
        i += 1
    if line[start:].strip():
        out.append(line[start:].strip())
    return out


def quotations(sentence: str) -> list:
    return [next(g for g in m.groups() if g) for m in QUOTE_RE.finditer(sentence)]


def draft_sentences(doc: Doc) -> list:
    """(line number, sentence) for every sentence of the draft outside headings and code blocks."""
    out, fenced = [], False
    for no, raw in enumerate(doc.lines, 1):
        line = raw.strip()
        if line.startswith("```"):
            fenced = not fenced
            continue
        if fenced or not line or line.startswith("#") or set(line) <= set("-=*_|: "):
            continue
        line = re.sub(r"^(?:[-*+]|\d+[.)])\s+", "", line)  # list markers are not part of the sentence
        out += [(no, s) for s in split_sentences(line)]
    return out


def needs_check(sentence: str) -> bool:
    return bool(quotations(sentence)) or bool(ce.numbers_in(sentence))


@dataclass
class Line:
    doc: Doc
    no: int
    text: str
    toks: set = field(default_factory=set)


class Library:
    """The sources, line by line, ready to be searched."""

    def __init__(self, docs: list):
        self.docs = docs
        self.sources = {d.id: ce.Source(d.id, d.path, d.text) for d in docs}
        self.lines = [Line(d, i, t, tokens(t)) for d in docs for i, t in enumerate(d.lines, 1)
                      if t.strip() and i not in d.headers]

    def ranked(self, text: str) -> list:
        want = tokens(text)
        if not want:
            return []
        scored = [(len(want & ln.toks) / len(want), ln) for ln in self.lines if want & ln.toks]
        return sorted(scored, key=lambda s: -s[0])

    def best_lines(self, text: str) -> list:
        ranked = self.ranked(text)
        if not ranked or ranked[0][0] < MIN_SHARE:
            return []
        top = ranked[0][0]
        return [ln for score, ln in ranked if score >= max(MIN_SHARE, NEAR_BEST * top)][:MAX_LINES]

    def nearest(self, text: str):
        ranked = self.ranked(text)
        return ranked[0][1] if ranked else None

    def find(self, quote: str):
        """(doc, line number) of a word-for-word match of the quote in any source, or None."""
        for d in self.docs:
            match, line = self.sources[d.id].find(quote)
            if match:
                return d, line
        return None


def _where(ln) -> dict:
    return {"file": ln.doc.id, "place": ln.doc.place(ln.no), "line": ln.no, "text": ln.text}


def check_sentence(sentence: str, lib: Library) -> dict:
    result = {"status": "supported", "problems": [], "missing_numbers": [], "rounded": [], "evidence": [], "nearest": None}
    evidence = []
    for q in quotations(sentence):
        found = lib.find(q)
        if found is None:
            result["problems"].append({"kind": "quote_not_found", "quote": q})
            near = lib.nearest(q)
            if near is not None and result["nearest"] is None:
                result["nearest"] = _where(near)
        else:
            d, no = found
            evidence.append(Line(d, no, d.lines[no - 1]))
    numbers = ce.numbers_in(sentence)
    lines = lib.best_lines(sentence)
    seen = {(e.doc.id, e.no) for e in evidence}
    evidence += [ln for ln in lines if (ln.doc.id, ln.no) not in seen]
    if numbers:
        if not evidence:
            result["problems"].append({"kind": "no_source"})
            near = lib.nearest(sentence)
            if near is not None and result["nearest"] is None:
                result["nearest"] = _where(near)
        else:
            claim = {"id": "s", "text": sentence, "evidence": [{"source": e.doc.id, "quote": e.text} for e in evidence]}
            r = ce.check_claim(claim, lib.sources)
            result["rounded"] = r.get("rounded", [])
            if r["missing_numbers"]:
                result["problems"].append({"kind": "numbers_not_in_source"})
                result["missing_numbers"] = r["missing_numbers"]
                if result["nearest"] is None:
                    result["nearest"] = _where(evidence[0])
    result["evidence"] = [_where(e) for e in evidence]
    if result["problems"]:
        result["status"] = result["problems"][0]["kind"]
    return result


def check_draft(draft: Doc, sources: list) -> dict:
    lib = Library(sources)
    items, skipped = [], 0
    for no, sentence in draft_sentences(draft):
        if not needs_check(sentence):
            skipped += 1
            continue
        items.append({"line": no, "text": sentence, **check_sentence(sentence, lib)})
    flagged = sum(i["status"] != "supported" for i in items)
    return {
        "draft": draft.id,
        "sources": [d.id for d in sources],
        "summary": {"checked": len(items), "supported": len(items) - flagged, "flagged": flagged, "not_checked": skipped},
        "sentences": items,
    }
