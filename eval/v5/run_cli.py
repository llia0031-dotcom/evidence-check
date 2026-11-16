"""Part 1 of v5: run evcheck on the four drafts and score it against the labels in cases.json (no model, no cost).

A labelled sentence counts as flagged when evcheck reports a problem for the sentence that contains its marker,
and as not checked when no checked sentence contains it. Writes results/cli.md and one JSON report per set.

Run from the project root (Word and Excel need `pip install "evcheck[docs]"`):  python eval/v5/run_cli.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
V5 = Path(__file__).resolve().parent
ROOT = V5.parents[1]
sys.path.insert(0, str(ROOT))

from evcheck import __version__  # noqa: E402
from evcheck.check import check_draft  # noqa: E402
from evcheck.readers import read, read_sources  # noqa: E402

EXPECT = {"correct": "pass", "error": "flagged", "meaning": "pass", "limit": "flagged", "skip": "not checked"}


def outcome(marker, report):
    hits = [s for s in report["sentences"] if marker in s["text"]]
    if not hits:
        return "not checked", None
    bad = [s for s in hits if s["status"] != "supported"]
    return ("flagged", bad[0]) if bad else ("pass", hits[0])


def main():
    cases = json.loads((V5 / "cases.json").read_text(encoding="utf-8"))
    out = V5 / "results"
    out.mkdir(exist_ok=True)
    tally, rows = Counter(), []
    for s in cases["sets"]:
        report = check_draft(read(V5 / s["draft"]), read_sources([V5 / s["sources"]]))
        (out / f"cli-{s['id']}.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        for x in s["sentences"]:
            got, item = outcome(x["marker"], report)
            tally[(x["kind"], got)] += 1
            tally[(x["kind"], "n")] += 1
            why = ""
            if item and item["status"] != "supported":
                why = item["status"] + (f" ({', '.join(item['missing_numbers'])})" if item["missing_numbers"] else "")
            rows.append(f"| {s['id']} | {x['kind']} | {x['text']} | {got} | {why or '—'} |")
    lines = [f"# v5 part 1: evcheck {__version__} on four drafts", "",
             "Each labelled sentence of `cases.json`, checked with no claims file and no model.", "",
             "| Kind | Sentences | Expected | Flagged | Passed | Not checked |", "|---|---|---|---|---|---|"]
    for kind in ("correct", "error", "meaning", "limit", "skip"):
        lines.append(f"| {kind} | {tally[(kind, 'n')]} | {EXPECT[kind]} | {tally[(kind, 'flagged')]} | "
                     f"{tally[(kind, 'pass')]} | {tally[(kind, 'not checked')]} |")
    lines += ["", f"- Planted errors flagged: **{tally[('error', 'flagged')]} of {tally[('error', 'n')]}**",
              f"- Correct sentences flagged (false alarms): **{tally[('correct', 'flagged')]} of {tally[('correct', 'n')]}**",
              "", "## Every sentence", "", "| Set | Kind | Sentence | Result | Why |", "|---|---|---|---|---|"] + rows
    (out / "cli.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines[6:14]))


if __name__ == "__main__":
    main()
