"""Offline tests for the evcheck command line (no network, no model calls).

Run from the project root:  python -m unittest discover -s tests -v
Word, PDF and Excel tests need the optional packages (`pip install "evcheck[docs]"`) and are skipped without them.
"""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evcheck import cli  # noqa: E402
from evcheck.check import check_draft, draft_sentences, month_tokens, parts, split_sentences  # noqa: E402
from evcheck.readers import ReadError, from_text, read, read_sources  # noqa: E402
from evcheck.report import render_html, render_text  # noqa: E402

RULES = """# Workshop rules

- The workshop takes place on Saturday 14 March 2027 from 10:00 to 16:00 MYT.
- Registration closes on 7 March 2027 at 23:59 MYT.
- Each team has 2 to 4 members.

The organiser said: "Bring your own laptop."
"""
SALES = "门店,订单数,GMV（元）,退款率\n杭州湖滨店,3412,128406.5,0.023\n上海静安店,2890,121380,0.031\n"


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        try:
            code = cli.main(argv)
        except SystemExit as e:  # argparse
            code = e.code
    return code, out.getvalue(), err.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "src").mkdir()
        (self.dir / "src" / "rules.md").write_text(RULES, encoding="utf-8")
        (self.dir / "src" / "sales.csv").write_text(SALES, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def draft(self, text, name="draft.md"):
        p = self.dir / name
        p.write_text(text, encoding="utf-8")
        return p

    def check(self, text):
        return check_draft(read(self.draft(text)), read_sources([self.dir / "src"]))

    def status(self, text):
        return [(s["text"], s["status"]) for s in self.check(text)["sentences"]]


class Sentences(Base):
    def test_split_keeps_decimals_and_quotes_whole(self):
        self.assertEqual(split_sentences("Version 4.2 shipped. Revenue was 1,234.5 today!"),
                         ["Version 4.2 shipped.", "Revenue was 1,234.5 today!"])
        self.assertEqual(split_sentences("他说：“先看复购。”然后散会。"), ["他说：“先看复购。”", "然后散会。"])
        self.assertEqual(split_sentences("Register by 8 March 2027. The fee is RM 30."),
                         ["Register by 8 March 2027.", "The fee is RM 30."])

    def test_headings_lists_and_code_blocks(self):
        doc = read(self.draft("# Title 2027\n\n- Teams have 2 to 4 members.\n```\nx = 5\n```\n"))
        self.assertEqual([s for _, s in draft_sentences(doc)], ["Teams have 2 to 4 members."])

    def test_sentences_without_numbers_or_quotes_are_not_checked(self):
        r = self.check("Lunch is provided.\nTeams have 2 to 4 members.\n")
        self.assertEqual(r["summary"]["checked"], 1)
        self.assertEqual(r["summary"]["not_checked"], 1)


class Checks(Base):
    def test_right_number_passes_with_its_source_line(self):
        r = self.check("Registration closes on 7 March 2027.\n")
        s = r["sentences"][0]
        self.assertEqual(s["status"], "supported")
        self.assertEqual((s["evidence"][0]["file"], s["evidence"][0]["line"]), ("rules.md", 4))

    def test_changed_number_is_flagged_with_the_closest_line(self):
        s = self.check("Register by 8 March 2027.\n")["sentences"][0]
        self.assertEqual(s["status"], "numbers_not_in_source")
        self.assertEqual(s["missing_numbers"], ["8"])
        self.assertIn("Registration closes", s["nearest"]["text"])

    def test_invented_number_with_no_matching_line(self):
        s = self.check("新客占比达到 38%。\n")["sentences"][0]
        self.assertEqual(s["status"], "no_source")

    def test_quotes_must_be_word_for_word(self):
        self.assertEqual(self.status('The organiser said: "Bring your own laptop."\n')[0][1], "supported")
        s = self.check('The organiser said: "Bring two laptops."\n')["sentences"][0]
        self.assertEqual(s["status"], "quote_not_found")
        self.assertIn("Bring your own laptop", s["nearest"]["text"])

    def test_table_rows_with_rounding_percent_and_wan(self):
        r = self.check("杭州湖滨店订单 3,412 单，GMV 约 12.8 万元，退款率 2.3%。\n")
        s = r["sentences"][0]
        self.assertEqual(s["status"], "supported")
        self.assertEqual(s["evidence"][0]["place"], "row 2")
        self.assertEqual(s["rounded"], [{"claim": "128000", "quote": "128406.5"}])
        self.assertEqual(self.status("上海静安店订单 2,980 单。\n")[0][1], "numbers_not_in_source")

    def test_worked_out_number_is_flagged(self):
        self.assertEqual(self.status("The workshop runs for 6 hours, from 10:00 to 16:00 MYT.\n")[0][1], "numbers_not_in_source")


class CommandLine(Base):
    def test_exit_codes_and_outputs(self):
        good = self.draft("Each team has 2 to 4 members.\n", "good.md")
        bad = self.draft("Each team has 2 to 5 members.\n", "bad.md")
        code, out, _ = run([str(good), "--sources", str(self.dir / "src"), "--no-color"])
        self.assertEqual(code, 0)
        self.assertIn("rules.md, line 5", out)
        html_path, json_path = self.dir / "r.html", self.dir / "r.json"
        code, out, _ = run([str(bad), "--sources", str(self.dir / "src"), "--no-color", "--html", str(html_path), "--json", str(json_path)])
        self.assertEqual(code, 1)
        self.assertIn("not found: 5", out)
        self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["summary"]["flagged"], 1)
        self.assertIn("<html lang=\"en\">", html_path.read_text(encoding="utf-8"))
        code, _, err = run([str(self.dir / "missing.md"), "--sources", str(self.dir / "src")])
        self.assertEqual(code, 2)
        self.assertIn("file not found", err)

    def test_json_to_standard_output(self):
        p = self.draft("Each team has 2 to 4 members.\n")
        code, out, _ = run([str(p), "--sources", str(self.dir / "src"), "--json", "-"])
        self.assertEqual(json.loads(out)["summary"]["supported"], 1)

    def test_chinese_labels_follow_the_draft(self):
        r = self.check("上海静安店订单 2,980 单。\n")
        self.assertIn("数字和资料对不上", render_text(r, "zh", color=False))
        self.assertIn('lang="zh-CN"', render_html(r, "zh"))


class SourcesAsText(Base):
    DRAFT = "Registration closes on 7 March 2027 at 23:59 MYT. 杭州湖滨店的退款率是 2.3%。Each team has 2 to 5 members.\n"

    def test_text_sources_match_file_sources(self):
        draft = read(self.draft(self.DRAFT))
        from_files = check_draft(draft, read_sources([self.dir / "src"]))
        from_texts = check_draft(draft, [from_text("rules.md", RULES), from_text("sales.csv", SALES)])
        self.assertEqual(from_files["summary"], from_texts["summary"])
        self.assertEqual(from_texts["summary"]["flagged"], 1)

    def test_mcp_tools_take_text_sources(self):
        try:
            from evcheck import mcp_server
        except ImportError:
            self.skipTest("mcp is not installed")
        texts = {"rules.md": RULES, "sales.csv": SALES}
        got = mcp_server.check_draft(text=self.DRAFT, source_texts=texts)
        self.assertEqual(got["summary"]["flagged"], 1)
        self.assertTrue(mcp_server.find_quote("Each team has 2 to 4 members.", source_texts=texts)["found"])
        self.assertIn("error", mcp_server.check_draft(text=self.DRAFT))


class JoinedSentencesAndMonths(Base):
    """0.6.0: a sentence that joins facts from different lines, and a month named in words against a table."""

    MONTHLY = "month,signups,churn_rate\n2026-08,5480,0.038\n2026-09,6010,0.035\n"

    def test_month_written_four_ways_is_one_word(self):
        want = {"month:09"}
        for text in ("September", "Sep 2026", "9 月", "2026-09", "2026/09/14"):
            self.assertEqual(month_tokens(text), want, text)
        self.assertEqual(month_tokens("We may march on."), set())  # ordinary words, not months
        self.assertEqual(month_tokens("2026-W46"), set())

    def test_parts_of_a_joined_sentence(self):
        self.assertEqual(parts("报名时间为 3 月 1 日，每次 90 分钟。"), ["报名时间为 3 月 1 日", "每次 90 分钟。"])
        self.assertEqual(parts("Signups were 5,480, and churn fell."), ["Signups were 5,480", "and churn fell."])
        self.assertEqual(parts("南京新街口店本周订单 1,978 单。"), [])
        self.assertEqual(len(split_sentences('He said: "Bring a laptop." Teams have 2 to 4 members.')), 2)

    def test_each_fact_of_a_joined_sentence_finds_its_line(self):
        got = self.check("Registration closes on 7 March 2027 at 23:59 MYT, and the organiser said: \"Bring your own laptop.\" "
                         "Registration closes on 7 March 2027 at 23:59 MYT, and each team has 2 to 4 members. "
                         "Registration closes on 7 March 2027 at 23:59 MYT, and each team has 2 to 5 members.\n")
        statuses = [s["status"] for s in got["sentences"]]
        self.assertEqual(statuses, ["supported", "supported", "numbers_not_in_source"])

    def test_a_named_month_picks_its_row(self):
        (self.dir / "src" / "monthly.csv").write_text(self.MONTHLY, encoding="utf-8")
        got = dict(self.status("Signups reached 6,010 in September. Signups reached 5,480 in September.\n"))
        self.assertEqual(got["Signups reached 6,010 in September."], "supported")
        self.assertEqual(got["Signups reached 5,480 in September."], "numbers_not_in_source")


class ModelMode(Base):
    """--llm without a network: the passages a model would choose are given directly to llm.apply."""

    def setUp(self):
        super().setUp()
        from evcheck import llm
        self.llm = llm
        self.sources = read_sources([self.dir / "src"])

    def run_apply(self, draft_text, chosen):
        report = check_draft(read(self.draft(draft_text)), self.sources)
        params, todo = self.llm.request(report, self.sources)
        return report, todo, self.llm.apply(report, todo, chosen, self.sources)

    def test_a_real_passage_turns_not_found_into_found(self):
        # Chinese sentence, English source: the words do not match, so evcheck alone cannot find the line.
        report, todo, turned = self.run_apply("报名截止时间是 2027 年 3 月 7 日 23:59。\n",
                                              {1: [{"file": "rules.md", "passage": "Registration closes on 7 March 2027 at 23:59 MYT."}]})
        self.assertEqual(len(todo), 1)
        self.assertEqual(turned, 1)
        self.assertEqual(report["summary"]["flagged"], 0)
        self.assertEqual(report["sentences"][0]["found_by"], "llm")

    def test_an_invented_or_wrong_passage_changes_nothing(self):
        draft = "每队 2 到 5 人。\n"
        report, _, turned = self.run_apply(draft, {1: [{"file": "rules.md", "passage": "Each team has 2 to 5 members."}]})
        self.assertEqual((turned, report["summary"]["flagged"]), (0, 1))  # not in the file
        report, _, turned = self.run_apply(draft, {1: [{"file": "rules.md", "passage": "Each team has 2 to 4 members."}]})
        self.assertEqual((turned, report["summary"]["flagged"]), (0, 1))  # in the file, but 5 is not
        self.assertEqual(report["sentences"][0]["nearest"]["text"], "- Each team has 2 to 4 members.")
        self.assertEqual(report["sentences"][0]["missing_numbers"], ["5"])

    def test_request_lists_only_sentences_not_found(self):
        report = check_draft(read(self.draft("Registration closes on 7 March 2027 at 23:59 MYT. Each team has 2 to 5 members.\n")), self.sources)
        params, todo = self.llm.request(report, self.sources)
        self.assertEqual([s["text"] for s in todo], ["Each team has 2 to 5 members."])
        self.assertIn("1. Each team has 2 to 5 members.", params["messages"][0]["content"])


class Formats(Base):
    def test_unknown_format_needs_the_extra(self):
        try:
            import markitdown  # noqa: F401
            self.skipTest("markitdown is installed")
        except ImportError:
            p = self.dir / "x.pdf"
            p.write_bytes(b"%PDF-1.4")
            with self.assertRaises(ReadError):
                read(p)

    def test_word_draft_and_excel_source(self):
        try:
            import docx
            import openpyxl
        except ImportError:
            self.skipTest("python-docx and openpyxl are not installed")
        d = docx.Document()
        d.add_paragraph("Active users reached 47,310 in October.")
        d.add_paragraph("Retention was 31% in October.")
        d.save(self.dir / "update.docx")
        wb = openpyxl.Workbook()
        wb.active.title = "Monthly"
        for row in (["month", "active_users", "retention"], ["2026-10", 47310, 0.305]):
            wb.active.append(row)
        wb.save(self.dir / "src" / "metrics.xlsx")
        r = check_draft(read(self.dir / "update.docx"), read_sources([self.dir / "src"]))
        got = {s["text"]: s for s in r["sentences"]}
        first = got["Active users reached 47,310 in October."]
        self.assertEqual(first["status"], "supported")
        self.assertEqual(first["evidence"][0]["place"], "Monthly, row 2")
        self.assertEqual(got["Retention was 31% in October."]["status"], "supported")  # 31% is 0.305 rounded


if __name__ == "__main__":
    unittest.main()
