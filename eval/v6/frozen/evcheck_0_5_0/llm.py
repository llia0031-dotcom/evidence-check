"""Optional model mode (`evcheck --llm`).

For each sentence evcheck could not find, a model looks through the sources for the passages that state its facts,
in any language. The script then checks those passages exactly as it checks everything else: each passage must be
word for word in its file, and the sentence's numbers must be in the passages. So the model can turn "not found"
into "found" only by pointing at a real passage; it never decides on its own that a sentence is right.

Needs `pip install "evcheck[llm]"` and an Anthropic API key in ANTHROPIC_API_KEY.
"""
from __future__ import annotations

import json

from .check import Library
from .rules import ce

MODEL = "claude-haiku-5-5"
PRICES = {"claude-haiku-5-5": (0.10, 0.50)}  # US$ per million input and output tokens
OUTPUT_PER_SENTENCE = 250  # output tokens assumed per sentence for the estimate, thinking included

SYSTEM = (
    "You find evidence in the user's files. For each numbered sentence, copy the passages of the files that state its "
    "facts. Copy each passage exactly, character for character, from a single line of a single file, and give that "
    "file's name. A passage may be part of a line. The files and the sentences may be in different languages. If no "
    "passage states the sentence's facts, copy the one passage on the same subject instead, so the reader can compare; "
    "if the files do not cover the subject at all, give no passages. Do not correct or judge the sentences."
)
SCHEMA = {
    "type": "object",
    "properties": {"sentences": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "n": {"type": "integer"},
            "passages": {"type": "array", "items": {
                "type": "object",
                "properties": {"file": {"type": "string"}, "passage": {"type": "string"}},
                "required": ["file", "passage"], "additionalProperties": False}},
        },
        "required": ["n", "passages"], "additionalProperties": False}}},
    "required": ["sentences"], "additionalProperties": False,
}


class LLMError(RuntimeError):
    pass


def client():
    try:
        import anthropic
    except ImportError as err:
        raise LLMError('--llm needs `pip install "evcheck[llm]"`') from err
    try:
        return anthropic.Anthropic()
    except anthropic.AnthropicError as err:
        raise LLMError(f"--llm needs an Anthropic API key in ANTHROPIC_API_KEY ({err})") from err


def request(report: dict, sources: list, model: str = MODEL) -> tuple:
    """The request for the sentences that were not found, and their numbers in it."""
    todo = [s for s in report["sentences"] if s["status"] != "supported"]
    files = "\n\n".join(f'<file name="{d.id}">\n' + "\n".join(d.lines) + "\n</file>" for d in sources)
    listed = "\n".join(f"{n}. {s['text']}" for n, s in enumerate(todo, 1))
    params = {
        "model": model, "max_tokens": 16000, "system": SYSTEM,
        "messages": [{"role": "user", "content": f"<files>\n{files}\n</files>\n\nSentences:\n{listed}"}],
    }
    return params, todo


def estimate(api, params: dict, sentences: int) -> tuple:
    """(input tokens, estimated US$) from a free token count."""
    tokens = api.messages.count_tokens(model=params["model"], system=params["system"], messages=params["messages"]).input_tokens
    price_in, price_out = PRICES.get(params["model"], PRICES[MODEL])
    return tokens, (tokens * price_in + sentences * OUTPUT_PER_SENTENCE * price_out) / 1e6


def ask(api, params: dict) -> tuple:
    """The passages the model chose, by sentence number, and the cost of the call in US$."""
    msg = api.messages.create(**params, output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}})
    if msg.stop_reason not in ("end_turn", "stop_sequence"):
        raise LLMError(f"the model stopped early ({msg.stop_reason})")
    text = next(b.text for b in msg.content if b.type == "text")
    price_in, price_out = PRICES.get(params["model"], PRICES[MODEL])
    spent = (msg.usage.input_tokens * price_in + msg.usage.output_tokens * price_out) / 1e6
    return {item["n"]: item["passages"] for item in json.loads(text)["sentences"]}, spent


def apply(report: dict, todo: list, chosen: dict, sources: list) -> int:
    """Check the chosen passages with the script; returns how many sentences they turned into "found"."""
    lib = Library(sources)
    docs = {d.id: d for d in sources}
    turned = 0
    for n, s in enumerate(todo, 1):
        passages = chosen.get(n) or []
        if not passages:
            continue
        claim = {"id": str(n), "text": s["text"], "evidence": [{"source": p["file"], "quote": p["passage"]} for p in passages]}
        r = ce.check_claim(claim, lib.sources)
        found = [e for e in r["evidence"] if e["found"] and e["source"] in docs]
        where = [{"file": e["source"], "place": docs[e["source"]].place(e["line"]), "line": e["line"],
                  "text": docs[e["source"]].lines[e["line"] - 1]} for e in found]
        if r["status"] == "supported" and where:
            s.update(status="supported", problems=[], missing_numbers=[], rounded=r.get("rounded", []),
                     evidence=where, nearest=None, found_by="llm")
            turned += 1
        elif where and r["missing_numbers"]:  # a real passage on the subject, without the sentence's numbers
            s.update(status="numbers_not_in_source", problems=[{"kind": "numbers_not_in_source"}],
                     missing_numbers=r["missing_numbers"], evidence=where, nearest=where[0])
    flagged = sum(s["status"] != "supported" for s in report["sentences"])
    report["summary"].update(supported=report["summary"]["checked"] - flagged, flagged=flagged, found_with_llm=turned)
    return turned
