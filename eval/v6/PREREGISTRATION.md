# v6 preregistration: evcheck 0.6.0

Written 17 Nov 2026, 17:25 MYT, after the cases below were written and before evcheck was changed or run on them.

## Why v6

v5 Part 2 showed two weaknesses of evcheck 0.5.0 on writing it had not seen:

1. **A sentence that joins facts from different source lines** ("报名时间为 3 月 1 日至 3 月 15 日，每期共 6 次活动，每次 90 分钟。"). evcheck picks at most three lines for the whole sentence by its words, can miss the line one fact comes from, and then reports that fact's number as not found. In the 32 answers of v5 Part 2 this caused 10 false alarms.
2. **A figure from the wrong row of a table**, when the sentence names the row in words that the table writes differently ("in September" against `2026-09`). Every similar row is used, so another month's figure can pass.

## The change, fixed in advance

- **Lines for each part of a sentence.** A sentence is also split at Chinese commas and semicolons and at English commas and semicolons followed by a space (never inside a number such as `1,978`). For each part that states a number, the source lines that best match that part are added to the lines the sentence is checked against.
- **Month names.** When lines are picked, `September`, `Sep`, `9 月` and `2026-09` count as the same word, so a sentence that names a month prefers that month's row.
- The script's matching rules do not change. evcheck becomes 0.6.0.

## Cases

[`cases.json`](cases.json), built by [`build_cases.py`](build_cases.py): two fictional sets, 27 labelled sentences.

| Kind | E (Chinese) | F (English) | Should be |
|---|---|---|---|
| correct: true, facts from different lines in one sentence | 5 | 6 | passed |
| error: one fact changed or invented | 6 | 4 | flagged |
| row: a figure from another month's row | 0 | 3 | flagged |
| limit: worked out from the sources (a sum, a difference) | 1 | 1 | flagged |
| skip: no number and no quote | 1 | 0 | not checked |

## Runs

1. **v6 cases:** evcheck 0.5.0 (the frozen copy in [`frozen/evcheck_0_5_0`](frozen/evcheck_0_5_0)) against evcheck 0.6.0, no model.
2. **v5 Part 1, regression:** evcheck 0.6.0 on the four v5 drafts.
3. **The 32 final answers of v5 Part 2:** the sentences evcheck flags, 0.5.0 against 0.6.0, no model. These answers are not held out: their false alarms are what the change is for.
4. **v5 Part 2's tool arm again, with 0.6.0 as the tool:** the 8 tasks, 2 runs each, 16 conversations, Claude Haiku 5.5 at effort medium, the same prompts and the same Batch API rounds as v5. Measured as in v5: numbers in no line of any source, numbers stated, evcheck flags on the final answer, tool calls. The tasks are not new and the plain arm is not run again; the comparison with v5's arms is reported as a re-run, not a held-out result. Cost estimate: under US$0.01.

## Expectations

- v6 cases with 0.5.0: at least 4 of the 11 correct sentences flagged; at most 1 of the 3 wrong-row figures flagged.
- v6 cases with 0.6.0: at least 10 of 11 correct sentences passed; all 10 errors, all 3 wrong-row figures and both limits flagged.
- v5 Part 1 with 0.6.0: unchanged, 16 of 16 errors flagged and 0 of 25 correct sentences flagged; the meaning, limit and skip sentences as before.
- v5 Part 2 answers with 0.6.0: the 10 false alarms fall to 3 or fewer; the 8 flags on worked-out numbers stay.
- Run 4: fewer flags seen by the assistant than in v5's tool arm, and at least as many numbers stated (152 in v5's tool arm).

If an expectation fails, the result is reported as it is.

## Limits fixed in advance

The cases were written by the same author as evcheck, after seeing the v5 false alarms, to test this change. Run 4 repeats tasks the change was designed around.

## Frozen files

| File | sha256 (first 12) |
|---|---|
| `build_cases.py` | `d40c6f950a26` |
| `cases.json` | `b4c21fe34ba4` |
| `sets/E/sources/城市报名.csv` | `68ea72b815a4` |
| `sets/E/sources/读书会说明.md` | `5b099c9e60c5` |
| `sets/E/简报.md` | `34ba32273be8` |
| `sets/F/sources/metrics.csv` | `5505e9c02526` |
| `sets/F/sources/notes.md` | `d5f2eff6bcef` |
| `sets/F/summary.md` | `51edaec87729` |
| `frozen/evcheck_0_5_0/check.py` | `049db1c9340c` |
| `frozen/evcheck_0_5_0/readers.py` | `4683dab9aa8f` |
| `frozen/evcheck_0_5_0/_rules.py` (script 0.5.0) | `b6e3b4b2fad6` |

## Changes after the run

- `run.py` (runs 1 to 3) and `run_tool_arm.py` (run 4) were written after this file, with the change; they only run and count, as described above.
- Runs 1 to 3 ran first. Then a sentence-splitting error, found while writing a test, was fixed: a full stop followed by a closing quote mid-line (`said: "Bring a laptop." Next`) now ends the sentence. Runs 1 to 3 were repeated with the fix and every result was the same. Run 4 started before the fix; one of the flags its assistants saw (TB1, run 1) came from that error.
- Run 4 ran on 17 Nov 2026 from 17:29 to 17:37 MYT, 3 batches, US$0.0061. After it, `run_tool_arm.py` changed only in how `score` prints the arm without the tool.
