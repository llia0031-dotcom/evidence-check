"""v6, run 4: v5 Part 2's tool arm again, with the current evcheck as the tool (see PREREGISTRATION.md).

The same 8 tasks, prompts, model, effort and Batch API rounds as v5 (it reuses eval/v5/run_agents.py); only the
tool arm, 2 runs per task, 16 conversations. The plain arm is not run again.

    python eval/v6/run_tool_arm.py estimate | run | score

The API key is read as in v5: from EVAL_ENV_FILE (relative to eval/; default eval/.env), never from the environment.
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
V6 = Path(__file__).resolve().parent
ROOT = V6.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval" / "v5"))

import run_agents as ra  # noqa: E402
from evcheck import __version__  # noqa: E402
from evcheck.check import check_draft  # noqa: E402
from evcheck.readers import Doc, read_sources  # noqa: E402

ra.OUT = V6 / "results" / "tool-arm"
ra.STATE = ra.OUT / "state.json"
_all = ra.conversations
ra.conversations = lambda: [c for c in _all() if c["arm"] == "tool"]


def score():
    state = json.loads(ra.STATE.read_text(encoding="utf-8"))
    v5 = json.loads((ROOT / "eval" / "v5" / "results" / "tool-use.json").read_text(encoding="utf-8"))["conversations"]
    arms = {"v5 plain (no tool)": [c for c in v5 if c["arm"] == "plain"],
            "v5 tool (evcheck 0.5.0)": [c for c in v5 if c["arm"] == "tool"]}
    rows, out = [], []
    for conv in state["conversations"]:
        docs = read_sources([ra.source_dir(conv["set"])])
        final = conv.get("final", "")
        lines = final.splitlines()
        report = check_draft(Doc(id="answer", path=Path("answer"), lines=lines, places=[f"line {i}" for i in range(1, len(lines) + 1)]), docs)
        calls = sum(1 for m in conv["params"]["messages"] if m["role"] == "assistant" for b in m["content"] if b["type"] == "tool_use")
        seen = sum(json.loads(b["content"])["summary"]["flagged"] for m in conv["params"]["messages"] if m["role"] == "user"
                   and isinstance(m["content"], list) for b in m["content"] if b.get("type") == "tool_result")
        item = {"id": conv["id"], "task": conv["task"], "run": conv["run"], "rounds": conv["rounds"], "tool_calls": calls,
                "flags_seen_by_the_assistant": seen, "stop_reason": conv.get("stop_reason"), "error": conv.get("error"),
                "numbers_stated": sorted(ra.ce.numbers_in(final)), "numbers_not_in_sources": ra.numbers_not_in_sources(final, docs),
                "evcheck_flagged": report["summary"]["flagged"], "usage": conv["usage"], "answer": final}
        out.append(item)
        rows.append(f"| {conv['task']} | {conv['run']} | {calls} | {seen} | {len(item['numbers_stated'])} | "
                    f"{', '.join(item['numbers_not_in_sources']) or '—'} | {item['evcheck_flagged']} |")
    arms[f"v6 tool (evcheck {__version__})"] = out

    summary = ["| Arm | Answers | Numbers stated | Numbers not in any source | evcheck flags on the answer (0.6.0) | Tool calls |",
               "|---|---|---|---|---|---|"]
    for name, convs in arms.items():
        flags = 0
        for c in convs:
            lines = c["answer"].splitlines()
            set_id = c["task"][1]
            flags += check_draft(Doc(id="a", path=Path("a"), lines=lines, places=[f"line {i}" for i in range(1, len(lines) + 1)]),
                                 read_sources([ra.source_dir(set_id)]))["summary"]["flagged"]
        summary.append(f"| {name} | {len(convs)} | {sum(len(c['numbers_stated']) for c in convs)} | "
                       f"{sum(len(c['numbers_not_in_sources']) for c in convs)} | {flags} | "
                       f"{sum(c['tool_calls'] for c in convs) if 'plain' not in name else '—'} |")
    seen_now = sum(c["flags_seen_by_the_assistant"] for c in out)
    v5_state = ROOT / "eval" / "v5" / "results" / "agents" / "state.json"  # the v5 conversations, kept locally
    seen_v5 = None
    if v5_state.is_file():
        seen_v5 = sum(json.loads(b["content"])["summary"]["flagged"]
                      for c in json.loads(v5_state.read_text(encoding="utf-8"))["conversations"] if c["arm"] == "tool"
                      for m in c["params"]["messages"] if m["role"] == "user" and isinstance(m["content"], list)
                      for b in m["content"] if b.get("type") == "tool_result")
    lines = [f"# v6, run 4: the v5 tool arm again, with evcheck {__version__} as the tool", "",
             f"claude-haiku-5-5, effort medium, 2 runs per task, Message Batches API ({len(state['batches'])} batches). "
             f"Cost: US${state['spent']:.4f}. The v5 arms are the saved v5 answers; every answer is re-checked here with "
             f"evcheck {__version__}, so the flag column uses one version for all three.", ""] + summary + [
             "", f"Flags the assistant saw in its tool calls, summed over the 16 conversations: {seen_now} with evcheck "
             f"{__version__}" + (f", {seen_v5} in v5 with evcheck 0.5.0." if seen_v5 is not None else "."), "",
             "## Every answer", "", "| Task | Run | Tool calls | Flags seen | Numbers stated | Not in any source | evcheck flags |",
             "|---|---|---|---|---|---|---|"] + rows
    (V6 / "results" / "tool-arm.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    (V6 / "results" / "tool-arm.json").write_text(json.dumps({"model": ra.MODEL, "effort": ra.EFFORT, "evcheck": __version__,
        "spent_usd": round(state["spent"], 4), "batches": [{"requests": b["requests"], "created": b["created"]} for b in state["batches"]],
        "conversations": out}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines[:9]))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "estimate":
        ra.estimate()
    elif cmd == "run":
        sys.exit(ra.run())
    elif cmd == "score":
        score()
    else:
        sys.exit(__doc__)
