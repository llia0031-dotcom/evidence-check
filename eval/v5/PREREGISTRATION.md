# v5 plan: the evcheck command line, checked before it is written

Written 17 November 2026, 06:44 MYT. The drafts, sources, labels and writing tasks below were fixed before the evcheck command line existed, and their hashes are recorded here. Hashes are of the files as stored in the repository (text files with LF line endings).

## What evcheck must do

Given one finished draft and a folder of sources, with no claims file and no model: find the sentences that state a number or a quotation, find the source line each one rests on, and flag a sentence whose number is not in that line (after the script's rules: Chinese numerals, 万, percentages and decimals, rounding to two significant digits, clock times), or whose quotation is not word for word in any source. Sources include Markdown, CSV and Excel; one draft is a Word file.

## Part 1: catching planted errors

`cases.json` labels 48 sentences in four drafts (two Chinese, two English), built by `build_cases.py`:

| Kind | Count | What it is | Expected |
|---|---|---|---|
| correct | 25 | stated by the sources, some as a rounded figure, a Chinese numeral, a percentage of a decimal, a table cell or a quotation | pass |
| error | 16 | a changed or invented number, an invented or altered quotation | flagged |
| meaning | 4 | wrong, but its numbers and quotations are in the sources (or it has none) | pass: a reader has to catch these |
| limit | 2 | a number worked out from the sources (a sum, a span of days) | flagged on purpose |
| skip | 1 | no number and no quotation | not checked |

A labelled sentence counts as flagged when evcheck reports a problem for the sentence that contains its marker. Scored: errors flagged (of 16), correct sentences flagged (false alarms, of 25), meaning sentences passed, limit sentences flagged.

Expectations: at least 14 of 16 errors flagged; at most 3 of 25 correct sentences flagged; all 4 meaning sentences pass.

## Part 2: an assistant that can call evcheck, against one that cannot

Eight writing tasks (`tasks` in `cases.json`, two per set, half Chinese) ask for a short brief, notice or summary from the set's sources. Two arms, same model (`claude-haiku-5-5`, effort `medium`), same sources in the prompt, same instructions to use only the sources:

- **plain**: writes the answer.
- **tool**: may call a `check_draft` tool that runs evcheck on its draft against the set's sources and returns the flagged sentences, then gives its final answer.

Each task runs twice per arm: 32 conversations. Requests go through the Message Batches API, one batch per round of the tool loop.

Scored on the final answer, the same way in both arms:

- **numbers not in any source**: a number the answer states that is in no line of any source of its set, read with the script's rules (no rounding allowance, so a rounded figure counts as not found). This is the main measure.
- answers with at least one such number;
- numbers stated per answer, so that an arm cannot look better by stating fewer numbers;
- evcheck's own flags on the answer, reported but not used as the measure, since the tool arm sees them.

Expectation: fewer numbers not in any source with the tool than without; a similar count of numbers per answer. Cost estimate: under US$0.10. Over US$0.50, the run stops and the owner is asked first.

## Limits fixed in advance

The drafts, sources and tasks are fictional and were written by the same author as evcheck, who knows the rules it uses; the errors are the kinds evcheck is built to find. Part 1 shows whether evcheck finds them in whole files of several formats, not how often such errors occur. Part 2 uses one model and two runs per task.

## Frozen files

| File | sha256 (first 12) |
|---|---|
| `build_cases.py` | `ece36bc6f500` |
| `cases.json` | `9b1f39577ad6` |
| `sets/A/sources/活动说明.md` | `250ccafa4817` |
| `sets/A/sources/门店周数据.csv` | `c956fcfd702a` |
| `sets/A/周报.md` | `fe6753b72e4b` |
| `sets/B/sources/metrics.xlsx` | `7d20fffd764a` |
| `sets/B/sources/release-notes.md` | `54312e926bcb` |
| `sets/B/update.docx` | `d05b85c1b4c8` |
| `sets/C/sources/招募规则.md` | `b4d4cf0d3f12` |
| `sets/C/公告.md` | `ec930a9e37cf` |
| `sets/D/sources/interviews.md` | `914cde41a1cc` |
| `sets/D/sources/survey.csv` | `8dbfcebda4c9` |
| `sets/D/summary.md` | `2cc501f9680c` |

## Part 2 details fixed before its run (17 Nov 2026, 07:06 MYT)

Written after Part 1 had run and before any Part 2 request was sent. `run_agents.py` (sha256 `968743222216`) holds them:

- Both arms get the same system prompt: use only the files, write in the language of the request, reply with the document only. The tool arm also gets the instructions the evcheck MCP server gives an assistant, and a `check_draft` tool that takes the whole draft.
- The files go into the first message as text; the Excel sheet is shown as CSV. The tool checks the draft against the files themselves.
- `max_tokens` 8,000; a tool-arm conversation stops after 6 rounds at most.
- Cost estimate from a token count: about US$0.02.

## Changes after the run

- Part 1: none. Re-run after the report wording changed (17 Nov 2026), the results are the same.
- Part 2 ran on 17 Nov 2026 between 07:06 and 07:20 MYT, 6 batches, US$0.0092. After the run, `run_agents.py` changed only in what `score` writes: the result files are named `tool-use.md` and `tool-use.json`, and batch IDs are left out of them. The answers, the run and the measure did not change.
- The measure was applied as fixed. The six numbers it counts in the arm without the tool were then read one by one, and the report says what each one is (list numbers, counts, worked-out growth rates; none a wrong figure). The sentences evcheck flags in the final answers were read the same way.
