"""evcheck as an MCP server, so an AI assistant can check its own writing against the user's files.

Three tools, all offline, with the same rules as the command line:
  check_draft  - every sentence with a number or quotation in a draft, against the sources
  check_claim  - one sentence and the quotes the assistant chose for it
  find_quote   - where a sentence appears word for word in the sources, or the closest lines

Start it with `evcheck-mcp` (needs `pip install "evcheck[mcp]"`), for example:
  claude mcp add evcheck -- evcheck-mcp
"""
from __future__ import annotations

from pathlib import Path

from .check import Library, check_draft as _check_draft, check_sentence
from .readers import Doc, ReadError, from_text, read, read_sources
from .rules import ce

try:  # mcp 2.x
    from mcp.server import MCPServer as _Server
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server

INSTRUCTIONS = (
    "Use these tools before you hand over anything written from the user's files: a summary, a report, an answer "
    "with figures or quotations. check_draft lists every sentence whose number or quotation is not in the files; fix "
    "or remove those sentences and check again. The tools match words and numbers; they do not judge meaning, so "
    "still read each sentence against the source line they return. If the files are not on this machine (for example "
    "they are in a sandbox), pass their full text in source_texts instead of paths."
)

server = _Server("evcheck", instructions=INSTRUCTIONS)


def _sources(paths, texts=None):
    docs = read_sources([Path(p).expanduser() for p in paths]) if paths else []
    docs += [from_text(name, text) for name, text in (texts or {}).items()]
    if not docs:
        raise ReadError("give at least one source: a path in sources or a text in source_texts")
    return docs


def _error(err) -> dict:
    msg = str(err)
    if "not found" in msg:  # most often a path inside the assistant's own sandbox
        msg += (". This tool runs outside your sandbox and cannot open that path: read the files yourself and call "
                "again with their full text in source_texts, and the draft in text.")
    return {"error": msg}


@server.tool()
def check_draft(sources: list[str] | None = None, text: str = "", path: str = "",
                source_texts: dict[str, str] | None = None) -> dict:
    """Check every sentence with a number or a quotation in a draft against the source files.

    Args:
        sources: source files or folders on this machine (Markdown, text, CSV, Excel, Word, PDF, web pages).
        text: the draft itself. Give either text or path.
        path: a draft file instead of text.
        source_texts: sources given as text instead, {"file name": "full text"}, when the files are not on
            this machine (a name ending in .csv is read as a table).

    Returns the sentences that were checked; each has a status ("supported", "numbers_not_in_source",
    "quote_not_found" or "no_source"), the numbers that were not found, and the source lines used or the
    closest line.
    """
    try:
        docs = _sources(sources, source_texts)
        if path:
            draft = read(Path(path).expanduser())
        else:
            lines = text.splitlines()
            draft = Doc(id="draft", path=Path("draft"), lines=lines, places=[f"line {i}" for i in range(1, len(lines) + 1)])
    except (ReadError, OSError) as err:
        return _error(err)
    return _check_draft(draft, docs)


@server.tool()
def check_claim(claim: str, sources: list[str] | None = None, quotes: list[dict] | None = None,
                source_texts: dict[str, str] | None = None) -> dict:
    """Check one sentence. With quotes, its numbers must be in those quotes and each quote word for word in its file;
    without quotes, the closest lines of the sources are used.

    Args:
        claim: one sentence, one fact.
        sources: source files or folders.
        quotes: optional list of {"source": file name, "quote": text copied from that file}.
        source_texts: sources given as text, {"file name": "full text"}, instead of or as well as paths.
    """
    try:
        docs = _sources(sources, source_texts)
    except (ReadError, OSError) as err:
        return _error(err)
    if not quotes:
        return check_sentence(claim, Library(docs))
    lib = Library(docs)
    return ce.check_claim({"id": "1", "text": claim, "evidence": quotes}, lib.sources)


@server.tool()
def find_quote(text: str, sources: list[str] | None = None, source_texts: dict[str, str] | None = None) -> dict:
    """Find where a passage appears word for word in the sources (spacing, case and curly quotes are forgiven).
    If it does not appear, return the three closest lines instead.

    Args:
        text: the passage to look for.
        sources: source files or folders.
        source_texts: sources given as text, {"file name": "full text"}, instead of or as well as paths.
    """
    try:
        lib = Library(_sources(sources, source_texts))
    except (ReadError, OSError) as err:
        return _error(err)
    found = lib.find(text)
    if found:
        doc, line = found
        return {"found": True, "file": doc.id, "place": doc.place(line), "line": line, "text": doc.lines[line - 1]}
    near = [{"file": ln.doc.id, "place": ln.doc.place(ln.no), "line": ln.no, "text": ln.text, "share": round(score, 2)}
            for score, ln in lib.ranked(text)[:3]]
    return {"found": False, "closest": near}


def main() -> None:
    server.run()


if __name__ == "__main__":
    main()
