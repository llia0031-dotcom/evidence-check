"""evcheck: check a finished draft against your own sources before you send it.

  evcheck 周报.md --sources 原始数据/
  evcheck report.docx --sources data.xlsx notes.md --html check.html --json check.json

Exit code 0: every checked sentence was found in the sources; 1: at least one was not; 2: a file could not be read
or --llm could not run.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .check import check_draft
from .readers import ReadError, read, read_sources
from .report import guess_lang, render_html, render_json, render_text


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="evcheck", description="Check every number and quotation in a draft against your sources.")
    p.add_argument("draft", help="the draft: .md, .txt, .docx, .pdf, .html")
    p.add_argument("--sources", "-s", nargs="+", required=True, help="source files or folders (documents, .csv, .xlsx)")
    p.add_argument("--json", metavar="FILE", help="also write the full result as JSON (- for standard output)")
    p.add_argument("--html", metavar="FILE", help="also write a report you can open in a browser")
    p.add_argument("--lang", choices=["auto", "en", "zh"], default="auto", help="language of the labels (default: the draft's)")
    p.add_argument("--problems-only", action="store_true", help="list only the sentences that were not found")
    p.add_argument("--no-color", action="store_true")
    p.add_argument("--llm", action="store_true",
                   help="for sentences not found, let a model point at the passage that supports them (any language); "
                        "the passage is still checked word for word. Shows the cost first; needs ANTHROPIC_API_KEY")
    p.add_argument("--model", default="claude-haiku-5-5", help="the model for --llm (default: claude-haiku-5-5)")
    p.add_argument("--yes", "-y", action="store_true", help="with --llm: do not ask before spending")
    p.add_argument("--version", action="version", version=f"evcheck {__version__}")
    return p


def _write(text: str) -> None:
    out = getattr(sys.stdout, "buffer", None)
    if out is None:  # already a text stream (tests, some IDEs)
        sys.stdout.write(text + "\n")
    else:  # bytes, so Chinese prints on any Windows console code page
        out.write((text + "\n").encode("utf-8"))
    sys.stdout.flush()


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        draft = read(args.draft)
        sources = read_sources(args.sources)
    except (ReadError, OSError) as err:
        print(f"evcheck: {err}", file=sys.stderr)
        return 2
    report = check_draft(draft, sources)
    if args.llm and report["summary"]["flagged"]:
        code = _with_llm(report, sources, args)
        if code:
            return code
    lang = guess_lang(draft.text) if args.lang == "auto" else args.lang
    if args.json == "-":
        _write(render_json(report))
    else:
        _write(render_text(report, lang, args.problems_only, color=False if args.no_color else None))
        if args.json:
            Path(args.json).write_text(render_json(report) + "\n", encoding="utf-8")
    if args.html:
        Path(args.html).write_text(render_html(report, lang), encoding="utf-8")
    return 1 if report["summary"]["flagged"] else 0


def _with_llm(report: dict, sources: list, args) -> int:
    from . import llm
    try:
        api = llm.client()
        params, todo = llm.request(report, sources, args.model)
        tokens, cost = llm.estimate(api, params, len(todo))
        print(f"evcheck --llm: {len(todo)} sentences to {args.model}, {tokens} input tokens, about US${cost:.4f}", file=sys.stderr)
        if not args.yes:
            if not sys.stdin.isatty():
                print("evcheck: add --yes to spend without asking", file=sys.stderr)
                return 2
            if input("Continue? [y/N] ").strip().lower() not in ("y", "yes"):
                print("evcheck: --llm skipped", file=sys.stderr)
                return 0
        chosen, spent = llm.ask(api, params)
        turned = llm.apply(report, todo, chosen, sources)
        print(f"evcheck --llm: {turned} of {len(todo)} found through the passages the model chose; spent US${spent:.4f}", file=sys.stderr)
    except Exception as err:  # the API's own errors carry a readable message
        print(f"evcheck --llm: {err}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
