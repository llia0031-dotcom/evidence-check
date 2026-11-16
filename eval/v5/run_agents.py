"""Part 2 of v5: an assistant that can call evcheck, against one that cannot (see PREREGISTRATION.md).

Eight writing tasks x two arms x two runs = 32 conversations with claude-haiku-5-5 (effort medium). Every request
goes through the Message Batches API, one batch per round of the tool loop. The plain arm ends after round 1; a
tool-arm conversation goes on while the model calls check_draft, up to MAX_ROUNDS rounds.

    python eval/v5/run_agents.py estimate   # token count and cost estimate, free
    python eval/v5/run_agents.py run        # the batches; state is saved after every round, so it can resume
    python eval/v5/run_agents.py score      # results/tool-use.md and results/tool-use.json, no model calls

The API key is read from an .env file (EVAL_ENV_FILE, relative to eval/; default eval/.env), never from the
environment, and is never printed. Needs `pip install anthropic openpyxl` and evcheck's own folder on the path.
"""
import csv
import io
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
V5 = Path(__file__).resolve().parent
ROOT = V5.parents[1]
sys.path.insert(0, str(ROOT))

from evcheck.check import check_draft  # noqa: E402
from evcheck.readers import Doc, read_sources  # noqa: E402
from evcheck.rules import ce  # noqa: E402

MODEL = "claude-haiku-5-5"
EFFORT = "medium"
MAX_TOKENS = 8000
RUNS = 2
MAX_ROUNDS = 6
PRICE_IN, PRICE_OUT, BATCH = 0.10, 0.50, 0.5  # US$ per million tokens; batches cost half
STOP_AT = 0.50  # US$: stop and ask the owner first
OUT = V5 / "results" / "agents"
STATE = OUT / "state.json"

BASE = ("You write short documents from the user's files, which are below. Use only these files: every fact, number "
        "and quotation must come from them. Write in the language of the request and reply with the document only.")
# The tool arm also gets the instructions the evcheck MCP server gives an assistant (evcheck/mcp_server.py).
TOOL_NOTE = ("You have a check_draft tool. Use it before you hand over the document: it lists every sentence whose "
             "number or quotation is not in the files. Fix or remove those sentences and check again. The tool matches "
             "words and numbers; it does not judge meaning, so still read each sentence against the source line it "
             "returns.")
TOOL = {
    "name": "check_draft",
    "description": ("Check a draft against the user's files. Every sentence with a number or a quotation is matched "
                    "against the files; the sentences whose numbers or quotations are not there come back with the "
                    "closest line of the files."),
    "input_schema": {"type": "object", "properties": {"text": {"type": "string", "description": "the whole draft"}},
                     "required": ["text"], "additionalProperties": False},
}


# ---------------------------------------------------------------- inputs

def cases():
    return json.loads((V5 / "cases.json").read_text(encoding="utf-8"))


def source_dir(set_id):
    return V5 / "sets" / set_id / "sources"


def file_text(path: Path) -> str:
    """A source as the model sees it: text files as they are, an Excel sheet as CSV."""
    if path.suffix.lower() != ".xlsx":
        return path.read_text(encoding="utf-8-sig").strip()
    import openpyxl
    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    parts = []
    for sheet in book.worksheets:
        buf = io.StringIO()
        csv.writer(buf, lineterminator="\n").writerows([["" if v is None else v for v in row] for row in sheet.iter_rows(values_only=True)])
        parts.append(f"[sheet {sheet.title}]\n{buf.getvalue().strip()}")
    book.close()
    return "\n\n".join(parts)


def files_block(set_id) -> str:
    files = sorted(p for p in source_dir(set_id).iterdir() if p.is_file())
    return "\n\n".join(f'<file name="{p.name}">\n{file_text(p)}\n</file>' for p in files)


def first_params(task, arm):
    params = {
        "model": MODEL, "max_tokens": MAX_TOKENS, "output_config": {"effort": EFFORT},
        "system": BASE + ("\n\n" + TOOL_NOTE if arm == "tool" else ""),
        "messages": [{"role": "user", "content": f"<files>\n{files_block(task['set'])}\n</files>\n\n{task['prompt']}"}],
    }
    if arm == "tool":
        params["tools"] = [TOOL]
    return params


def run_tool(set_id, text) -> str:
    lines = text.splitlines()
    draft = Doc(id="draft", path=Path("draft"), lines=lines, places=[f"line {i}" for i in range(1, len(lines) + 1)])
    report = check_draft(draft, read_sources([source_dir(set_id)]))
    flagged = []
    for s in report["sentences"]:
        if s["status"] == "supported":
            continue
        item = {"sentence": s["text"], "problem": s["status"]}
        if s["missing_numbers"]:
            item["numbers_not_in_files"] = s["missing_numbers"]
        if s["nearest"]:
            item["closest_line"] = f'{s["nearest"]["file"]}, {s["nearest"]["place"]}: {s["nearest"]["text"]}'
        flagged.append(item)
    return json.dumps({"summary": report["summary"], "flagged": flagged}, ensure_ascii=False)


# ---------------------------------------------------------------- the API

def client():
    import anthropic
    # Claude Code's own ANTHROPIC_* / CLAUDE_* variables must not reach the SDK.
    for name in [k for k in os.environ if k.upper().startswith(("ANTHROPIC_", "CLAUDE_"))]:
        del os.environ[name]
    env_file = (ROOT / "eval" / os.environ.get("EVAL_ENV_FILE", ".env")).resolve()
    key = ""
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8-sig").splitlines():
            name, sep, value = line.partition("=")
            if sep and name.strip() == "ANTHROPIC_API_KEY":
                key = value.strip().strip('"').strip("'")
    if not key:
        sys.exit(f"NOT RUN: no ANTHROPIC_API_KEY in {env_file}")
    return anthropic.Anthropic(api_key=key, base_url="https://api.anthropic.com", max_retries=3)


def cost(usage) -> float:
    tokens_in = usage.get("input_tokens", 0) + usage.get("cache_read_input_tokens", 0) + usage.get("cache_creation_input_tokens", 0)
    return (tokens_in * PRICE_IN + usage.get("output_tokens", 0) * PRICE_OUT) / 1e6 * BATCH


def conversations():
    return [{"id": f"{t['id']}-{arm}-{r}", "task": t["id"], "set": t["set"], "lang": t["lang"], "arm": arm, "run": r,
             "params": first_params(t, arm), "rounds": 0, "done": False, "usage": {}}
            for t in cases()["tasks"] for arm in ("plain", "tool") for r in range(1, RUNS + 1)]


def estimate():
    c = client()
    seen, total_in = {}, 0
    for conv in conversations():
        key = (conv["task"], conv["arm"])
        if key not in seen:
            p = conv["params"]
            seen[key] = c.messages.count_tokens(model=p["model"], system=p["system"], messages=p["messages"],
                                                **({"tools": p["tools"]} if "tools" in p else {})).input_tokens
        total_in += seen[key]
    # Assume about 800 output tokens per answer, thinking included, and two extra tool rounds per tool-arm conversation.
    n = len(conversations())
    tool_convs = n // 2
    round1 = (total_in * PRICE_IN + n * 800 * PRICE_OUT) / 1e6 * BATCH
    extra = tool_convs * 2 * ((total_in / n + 1600) * PRICE_IN + 800 * PRICE_OUT) / 1e6 * BATCH
    print(f"{n} conversations; first-round input {total_in} tokens in all (per task and arm: {min(seen.values())}-{max(seen.values())})")
    print(f"estimate: round 1 about US${round1:.4f}, tool rounds about US${extra:.4f}, total about US${round1 + extra:.4f}")
    print(f"the run stops if the running total passes US${STOP_AT:.2f}")


def block_dict(b) -> dict:
    return b.model_dump(exclude_none=True)


def run():
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request
    OUT.mkdir(parents=True, exist_ok=True)
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.is_file() else {"conversations": conversations(), "batches": [], "spent": 0.0}
    c = client()
    while True:
        todo = [conv for conv in state["conversations"] if not conv["done"]]
        if not todo:
            break
        if state["spent"] > STOP_AT:
            print(f"STOPPED: spent US${state['spent']:.4f}, over US${STOP_AT}; ask the owner before going on")
            return 1
        batch = c.messages.batches.create(requests=[
            Request(custom_id=conv["id"], params=MessageCreateParamsNonStreaming(**conv["params"])) for conv in todo])
        state["batches"].append({"id": batch.id, "requests": len(todo), "created": time.strftime("%Y-%m-%d %H:%M:%S%z")})
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"round batch {batch.id}: {len(todo)} requests", flush=True)
        while c.messages.batches.retrieve(batch.id).processing_status != "ended":
            time.sleep(30)
        by_id, got = {conv["id"]: conv for conv in todo}, set()
        for res in c.messages.batches.results(batch.id):
            conv = by_id[res.custom_id]
            got.add(res.custom_id)
            conv["rounds"] += 1
            if res.result.type != "succeeded":
                conv["done"], conv["error"] = True, f"{res.result.type}: {getattr(res.result, 'error', '')}"
                continue
            msg = res.result.message
            usage = msg.usage.model_dump(exclude_none=True)
            for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
                conv["usage"][k] = conv["usage"].get(k, 0) + (usage.get(k) or 0)
            state["spent"] += cost({k: usage.get(k) or 0 for k in usage if isinstance(usage.get(k), int)})
            content = [block_dict(b) for b in msg.content]
            conv["params"]["messages"].append({"role": "assistant", "content": content})
            calls = [b for b in content if b["type"] == "tool_use"]
            if msg.stop_reason == "tool_use" and calls and conv["rounds"] < MAX_ROUNDS:
                conv["params"]["messages"].append({"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": b["id"], "content": run_tool(conv["set"], str(b["input"].get("text", "")))}
                    for b in calls]})
            else:
                conv["done"] = True
                conv["stop_reason"] = msg.stop_reason
                conv["final"] = "\n".join(b["text"] for b in content if b["type"] == "text").strip()
        for conv in todo:  # a request missing from the results
            if conv["id"] not in got:
                conv["done"], conv["error"] = True, "no result"
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  ended; spent so far US${state['spent']:.4f}; still open: {sum(not x['done'] for x in state['conversations'])}", flush=True)
    print(f"all done; spent US${state['spent']:.4f}")
    return 0


# ---------------------------------------------------------------- scoring

def numbers_not_in_sources(text, docs):
    """Numbers the text states that are in no line of any source, by the script's rules, with no rounding allowance."""
    lib_sources = {d.id: ce.Source(d.id, d.path, d.text) for d in docs}
    evidence = [{"source": d.id, "quote": line} for d in docs for line in d.lines if ce.quote_long_enough(line)]
    r = ce.check_claim({"id": "a", "text": text, "evidence": evidence}, lib_sources)
    return sorted(set(r["missing_numbers"]) | {x["claim"].rstrip("%") for x in r["rounded"]})


def score():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    rows, per_arm = [], {"plain": Counter(), "tool": Counter()}
    out = []
    for conv in state["conversations"]:
        docs = read_sources([source_dir(conv["set"])])
        final = conv.get("final", "")
        stated = sorted(ce.numbers_in(final))
        missing = numbers_not_in_sources(final, docs)
        lines = final.splitlines()
        report = check_draft(Doc(id="answer", path=Path("answer"), lines=lines, places=[f"line {i}" for i in range(1, len(lines) + 1)]), docs)
        calls = sum(1 for m in conv["params"]["messages"] if m["role"] == "assistant" for b in m["content"] if b["type"] == "tool_use")
        a = per_arm[conv["arm"]]
        a["answers"] += 1
        a["stated"] += len(stated)
        a["missing"] += len(missing)
        a["with_missing"] += bool(missing)
        a["flagged"] += report["summary"]["flagged"]
        a["calls"] += calls
        a["used_tool"] += calls > 0
        a["errors"] += "error" in conv
        out.append({"id": conv["id"], "task": conv["task"], "arm": conv["arm"], "run": conv["run"], "rounds": conv["rounds"],
                    "tool_calls": calls, "stop_reason": conv.get("stop_reason"), "error": conv.get("error"),
                    "numbers_stated": stated, "numbers_not_in_sources": missing,
                    "evcheck_flagged": report["summary"]["flagged"], "usage": conv["usage"], "answer": final})
        rows.append(f"| {conv['task']} | {conv['arm']} | {conv['run']} | {calls} | {len(stated)} | "
                    f"{', '.join(missing) or '—'} | {report['summary']['flagged']} |")
    (V5 / "results" / "tool-use.json").write_text(json.dumps({"model": MODEL, "effort": EFFORT, "spent_usd": round(state["spent"], 4),
                                                             "batches": [{"requests": b["requests"], "created": b["created"]} for b in state["batches"]],
                                                             "conversations": out},
                                                            ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    lines = ["# v5 part 2: an assistant that can call evcheck, against one that cannot", "",
             f"{MODEL}, effort {EFFORT}, {RUNS} runs per task and arm, Message Batches API "
             f"({len(state['batches'])} batches). Cost: US${state['spent']:.4f}.", "",
             "| Arm | Answers | Numbers stated | Numbers not in any source | Answers with one or more | evcheck flags on the answer | Used the tool | Tool calls |",
             "|---|---|---|---|---|---|---|---|"]
    for arm in ("plain", "tool"):
        a = per_arm[arm]
        lines.append(f"| {arm} | {a['answers']} | {a['stated']} | **{a['missing']}** | {a['with_missing']} | {a['flagged']} | "
                     f"{a['used_tool'] if arm == 'tool' else '—'} | {a['calls'] if arm == 'tool' else '—'} |")
    errors = sum(a["errors"] for a in per_arm.values())
    if errors:
        lines += ["", f"Conversations that ended in an error: {errors} (see tool-use.json)."]
    lines += ["", "Numbers are distinct numbers per answer, read with the script's rules; a rounded figure counts as not found.", "",
              "## Every answer", "", "| Task | Arm | Run | Tool calls | Numbers stated | Not in any source | evcheck flags |",
              "|---|---|---|---|---|---|---|"] + rows
    (V5 / "results" / "tool-use.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines[:9 + (2 if errors else 0)]))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "estimate":
        estimate()
    elif cmd == "run":
        sys.exit(run())
    elif cmd == "score":
        score()
    else:
        sys.exit(__doc__)
