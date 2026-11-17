"""v6, runs 1 to 3 (no model, no cost): evcheck 0.5.0 (frozen copy) against the current evcheck.

1. the v6 cases;
2. v5 Part 1 with the current evcheck (regression);
3. the 32 final answers saved from v5 Part 2: which sentences each version flags.

Writes results/script-only.md and results/v5-answers.md. Run from the project root:  python eval/v6/run.py
"""
import importlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
V6 = Path(__file__).resolve().parent
ROOT = V6.parents[1]
V5 = ROOT / "eval" / "v5"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(V6 / "frozen"))

VERSIONS = {"0.5.0": "evcheck_0_5_0", "current": "evcheck"}
EXPECT = {"correct": "pass", "error": "flagged", "row": "flagged", "meaning": "pass", "limit": "flagged", "skip": "not checked"}


def load(pkg):
    check = importlib.import_module(f"{pkg}.check")
    readers = importlib.import_module(f"{pkg}.readers")
    version = importlib.import_module(pkg).__version__
    return version, check, readers


def outcome(marker, report):
    hits = [s for s in report["sentences"] if marker in s["text"]]
    if not hits:
        return "not checked"
    return "flagged" if any(s["status"] != "supported" for s in hits) else "pass"


def run_cases(folder, check, readers):
    cases = json.loads((folder / "cases.json").read_text(encoding="utf-8"))
    got = {}
    for s in cases["sets"]:
        report = check.check_draft(readers.read(folder / s["draft"]), readers.read_sources([folder / s["sources"]]))
        for x in s["sentences"]:
            got[(s["id"], x["marker"])] = (x["kind"], x["text"], outcome(x["marker"], report))
    return got


def tally(got):
    t = Counter()
    for kind, _, result in got.values():
        t[(kind, result)] += 1
        t[(kind, "n")] += 1
    return t


def table(title, results, kinds):
    lines = [f"## {title}", "", "| Kind | Sentences | Expected | " + " | ".join(f"{v}: flagged / passed / not checked" for v in results) + " |",
             "|---|---|---|" + "---|" * len(results)]
    for kind in kinds:
        tallies = [tally(g) for g in results.values()]
        n = tallies[0][(kind, "n")]
        if not n:
            continue
        cells = [f"{t[(kind, 'flagged')]} / {t[(kind, 'pass')]} / {t[(kind, 'not checked')]}" for t in tallies]
        lines.append(f"| {kind} | {n} | {EXPECT[kind]} | " + " | ".join(cells) + " |")
    return lines


def answers_flags(check, readers, answers, sets):
    out = {}
    for c in answers:
        lines = c["answer"].splitlines()
        doc = readers.Doc(id="answer", path=Path("answer"), lines=lines, places=[f"line {i}" for i in range(1, len(lines) + 1)])
        report = check.check_draft(doc, readers.read_sources([V5 / "sets" / sets[c["task"]] / "sources"]))
        out[c["id"]] = [(s["text"], s["missing_numbers"]) for s in report["sentences"] if s["status"] != "supported"]
    return out


def main():
    loaded = {name: load(pkg) for name, pkg in VERSIONS.items()}
    label = {name: f"evcheck {v[0]}" for name, v in loaded.items()}
    out_dir = V6 / "results"
    out_dir.mkdir(exist_ok=True)

    v6 = {label[n]: run_cases(V6, ch, rd) for n, (_, ch, rd) in loaded.items()}
    v5 = {label[n]: run_cases(V5, ch, rd) for n, (_, ch, rd) in loaded.items()}
    lines = ["# v6: evcheck 0.5.0 against the current version, no model", ""]
    lines += table("1. v6 cases (27 sentences)", v6, ["correct", "error", "row", "limit", "skip"]) + [""]
    lines += table("2. v5 Part 1, regression (48 sentences)", v5, ["correct", "error", "meaning", "limit", "skip"]) + [""]
    lines += ["## Every v6 sentence", "", "| Set | Kind | Sentence | " + " | ".join(v6) + " |", "|---|---|---|" + "---|" * len(v6)]
    first = next(iter(v6.values()))
    for key, (kind, text, _) in first.items():
        lines.append(f"| {key[0]} | {kind} | {text} | " + " | ".join(g[key][2] for g in v6.values()) + " |")
    changed = [(k, [g[k][2] for g in v5.values()]) for k in next(iter(v5.values())) if len({g[k][2] for g in v5.values()}) > 1]
    lines += ["", "## v5 Part 1 sentences whose result changed", ""]
    lines += [f"- {k[0]} {v5[label['current']][k][0]}: {v5[label['current']][k][1]} ({' → '.join(r)})" for k, r in changed] or ["None."]
    (out_dir / "script-only.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    saved = json.loads((V5 / "results" / "tool-use.json").read_text(encoding="utf-8"))["conversations"]
    sets = {t["id"]: t["set"] for t in json.loads((V5 / "cases.json").read_text(encoding="utf-8"))["tasks"]}
    flags = {label[n]: answers_flags(ch, rd, saved, sets) for n, (_, ch, rd) in loaded.items()}
    old, new = flags[label["0.5.0"]], flags[label["current"]]
    rows = ["# v6, run 3: the 32 final answers of v5 Part 2, flagged sentences", "",
            "Not held out: these answers' false alarms are what the change is for.", "",
            "| | " + " | ".join(flags) + " |", "|---|---|---|",
            "| Sentences flagged | " + " | ".join(str(sum(len(v) for v in f.values())) for f in flags.values()) + " |", "",
            "## Each flagged sentence", "", "| Answer | Sentence | Numbers not found | " + " | ".join(flags) + " |", "|---|---|---|---|---|"]
    for cid in old:
        seen = {t for t, _ in old[cid]} | {t for t, _ in new[cid]}
        for text in sorted(seen):
            miss = next((m for t, m in old[cid] + new[cid] if t == text), [])
            rows.append(f"| {cid} | {text} | {', '.join(miss)} | " + " | ".join("flagged" if any(t == text for t, _ in f[cid]) else "—" for f in flags.values()) + " |")
    (out_dir / "v5-answers.md").write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines[:22]))
    print("\n".join(rows[4:7]))


if __name__ == "__main__":
    main()
