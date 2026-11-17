"""Read a draft or a source into numbered lines.

Plain text, Markdown, CSV and TSV need nothing beyond Python. Excel needs openpyxl; Word, PDF, PowerPoint
and web pages need markitdown (both come with `pip install "evcheck[docs]"`). A table becomes one line per
row, written as "header: value | header: value", so a quote can point at a row and its numbers.
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

TEXT = {".md", ".markdown", ".txt", ".rst", ".json", ".jsonl", ".yaml", ".yml", ".tex", ".log"}
TABLE = {".csv", ".tsv"}
SHEET = {".xlsx", ".xlsm"}
CONVERT = {".docx", ".pdf", ".pptx", ".html", ".htm"}
READABLE = TEXT | TABLE | SHEET | CONVERT
MAX_BYTES = 20_000_000


class ReadError(ValueError):
    """A file that cannot be read, with the reason in words."""


@dataclass
class Doc:
    id: str                   # the name used in reports: the path relative to the folder given
    path: Path
    lines: list = field(default_factory=list)   # the text the checks read, one entry per line
    places: list = field(default_factory=list)  # where each line is, in words ("line 4", "Monthly, row 4")
    headers: set = field(default_factory=set)   # table header lines: column names, never a source for a number

    @property
    def text(self) -> str:
        return "\n".join(self.lines)

    def place(self, line: int) -> str:
        return self.places[line - 1] if 0 < line <= len(self.places) else f"line {line}"


def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value).strip()


def _row_line(header: list, row: list) -> str:
    cells = [(h or "").strip() for h in header]
    parts = [f"{h}: {v}" if h else v for h, v in zip(cells, row) if v != ""]
    parts += [v for v in row[len(cells):] if v != ""]
    return " | ".join(parts)


def _table(rows: list) -> tuple:
    rows = [[_cell(c) for c in r] for r in rows]
    rows = [r for r in rows if any(c != "" for c in r)]
    if not rows:
        return [], []
    header, lines = rows[0], [" | ".join(c for c in rows[0] if c)]
    lines += [_row_line(header, r) for r in rows[1:]]
    return lines, [f"row {i}" for i in range(1, len(lines) + 1)]


class _HTMLText(HTMLParser):
    BLOCK = {"p", "div", "li", "tr", "br", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "table", "blockquote"}

    def __init__(self):
        super().__init__()
        self.parts, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")
        elif tag in ("td", "th"):
            self.parts.append(" | ")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def _convert(path: Path) -> str:
    try:
        from markitdown import MarkItDown
    except ImportError:
        MarkItDown = None
    if MarkItDown is not None:
        try:
            return MarkItDown().convert(str(path)).text_content
        except Exception as err:  # markitdown reports format-specific problems in many ways
            raise ReadError(f"could not convert {path.name}: {err}") from err
    if path.suffix.lower() in (".html", ".htm"):
        p = _HTMLText()
        p.feed(path.read_text(encoding="utf-8-sig", errors="replace"))
        return re.sub(r"[ \t]+", " ", "".join(p.parts))
    if path.suffix.lower() == ".docx":
        try:
            import docx
        except ImportError:
            docx = None
        if docx is not None:
            return "\n".join(par.text for par in docx.Document(str(path)).paragraphs)
    raise ReadError(f'{path.name}: reading {path.suffix} files needs `pip install "evcheck[docs]"`')


def read(path, name: str | None = None) -> Doc:
    path = Path(path)
    suffix = path.suffix.lower()
    if not path.is_file():
        raise ReadError(f"file not found: {path}")
    if path.stat().st_size > MAX_BYTES:
        raise ReadError(f"file too large (over 20 MB): {path}")
    doc = Doc(id=name or path.name, path=path)
    if suffix in TABLE:
        text = path.read_text(encoding="utf-8-sig")
        rows = list(csv.reader(io.StringIO(text), delimiter="\t" if suffix == ".tsv" else ","))
        doc.lines, doc.places = _table(rows)
        doc.headers = {1} if doc.lines else set()
    elif suffix in SHEET:
        try:
            import openpyxl
        except ImportError as err:
            raise ReadError(f'{path.name}: reading Excel files needs `pip install "evcheck[docs]"`') from err
        book = openpyxl.load_workbook(path, read_only=True, data_only=True)
        for sheet in book.worksheets:
            lines, places = _table(list(sheet.iter_rows(values_only=True)))
            if lines:
                doc.headers.add(len(doc.lines) + 1)
            doc.lines += lines
            doc.places += [f"{sheet.title}, {p}" for p in places]
        book.close()
    elif suffix in CONVERT:
        doc.lines = _convert(path).splitlines()
        doc.places = [f"line {i}" for i in range(1, len(doc.lines) + 1)]
    else:
        try:
            doc.lines = path.read_text(encoding="utf-8-sig").splitlines()
        except UnicodeDecodeError as err:
            raise ReadError(f"not UTF-8 text: {path}") from err
        doc.places = [f"line {i}" for i in range(1, len(doc.lines) + 1)]
    return doc


def from_text(name: str, text: str) -> Doc:
    """A source given as text rather than a file (for an assistant whose files are not on this machine).
    A name ending in .csv or .tsv is read as a table; anything else line by line."""
    suffix = Path(name).suffix.lower()
    doc = Doc(id=name, path=Path(name))
    if suffix in TABLE:
        rows = list(csv.reader(io.StringIO(text.lstrip("﻿")), delimiter="\t" if suffix == ".tsv" else ","))
        doc.lines, doc.places = _table(rows)
        doc.headers = {1} if doc.lines else set()
    else:
        doc.lines = text.splitlines()
        doc.places = [f"line {i}" for i in range(1, len(doc.lines) + 1)]
    return doc


def read_sources(paths) -> list:
    """Every readable file under the given files and folders, named by its path relative to the folder."""
    docs = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and f.suffix.lower() in READABLE and not f.name.startswith((".", "~$")):
                    docs.append(read(f, f.relative_to(p).as_posix()))
        elif p.is_file():
            docs.append(read(p))
        else:
            raise ReadError(f"source path not found: {raw}")
    if not docs:
        raise ReadError("no readable source files were given")
    return docs
