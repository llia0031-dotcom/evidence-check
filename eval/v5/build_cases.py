"""Write the v5 cases: four fictional "draft + sources" sets and the writing tasks, with their answers.

v5 tests the evcheck command line on whole drafts it has not seen: it must find the sentences worth
checking by itself, find the source line each one comes from, and flag invented or changed numbers and
quotes. Every sentence's label is fixed here, before evcheck was written.

Run once from the project root (needs python-docx and openpyxl for set B's Word draft and Excel sheet):
  python eval/v5/build_cases.py
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SETS = ROOT / "sets"

# kind: correct = true and stated by the sources (should pass)
#       error   = a changed or invented number or quote (should be flagged)
#       meaning = wrong, but every number and quote is in the sources (expected to pass: a reader must catch it)
#       limit   = a number worked out from the sources (flagged on purpose)
#       skip    = no number and no quote (not checked)

A_CSV = [
    ["门店", "周", "订单数", "GMV（元）", "客单价（元）", "退款率"],
    ["杭州湖滨店", "2026-W46", "3412", "128406.5", "37.6", "0.023"],
    ["上海静安店", "2026-W46", "2890", "121380", "42.0", "0.031"],
    ["南京新街口店", "2026-W46", "1987", "69545", "35.0", "0.018"],
]
A_RULES = """# 双 11 门店活动说明

云杉咖啡是虚构的品牌。

- 活动时间：2026 年 11 月 11 日至 11 月 13 日。
- 会员第二杯半价，非会员第二杯八折。
- 每位顾客每天最多使用 2 张优惠券。
- 活动期间不参与积分加倍。

区域经理在启动会上说：“这次活动先看复购，不追求单量。”
"""
A_DRAFT = [
    ("# 华东门店第 46 周周报", "skip", None),
    ("杭州湖滨店本周订单 3,412 单，GMV 约 12.8 万元。", "correct", "12.8 万元"),
    ("上海静安店客单价 42 元，退款率 3.1%。", "correct", "退款率 3.1%"),
    ("南京新街口店本周订单 1,978 单。", "error", "1,978 单"),
    ("三家店的退款率都低于 3%。", "error", "都低于 3%"),
    ("活动时间是 11 月 11 日至 11 月 13 日。", "correct", "11 月 13 日"),
    ("会员第二杯半价，非会员第二杯八折。", "correct", "第二杯八折"),
    ("每位顾客每天最多使用 3 张优惠券。", "error", "3 张优惠券"),
    ("区域经理在启动会上说：“这次活动先看复购，不追求单量。”", "correct", "先看复购"),
    ("区域经理强调：“复购比单量更重要，所有门店都要冲刺。”", "error", "都要冲刺"),
    ("活动期间积分加倍。", "meaning", "积分加倍"),
    ("新客占比达到 38%。", "error", "38%"),
    ("下周计划在南京新街口店试点外卖满减。", "skip", "外卖满减"),
    ("三家店本周合计订单 8,289 单。", "limit", "8,289"),
]

B_XLSX = [
    ["month", "active_users", "d30_retention", "revenue_usd"],
    ["2026-08", 41200, 0.284, 96500],
    ["2026-09", 43950, 0.291, 101800],
    ["2026-10", 47310, 0.305, 110240],
]
B_NOTES = """# Larchwood release notes, October 2026

Larchwood is a fictional app.

- Version 4.2 shipped on 14 October 2026 with offline mode and a new onboarding flow.
- Offline mode keeps the last 30 days of notes on the device.
- The new onboarding flow has 3 steps instead of 5.
- Dark mode is planned for version 4.3, not 4.2.

Product lead Mira Osei said: "Offline mode was the most requested feature for two years."
"""
B_DRAFT = [
    ("Larchwood update for October", "skip", None),
    ("Active users reached 47,310 in October, up from 43,950 in September.", "correct", "47,310"),
    ("Thirty-day retention rose to 30.5% in October.", "correct", "30.5%"),
    ("Revenue was $110,240 in October.", "correct", "$110,240"),
    ("Revenue grew 12% from August to October.", "error", "grew 12%"),
    ("Version 4.2 shipped on 14 October 2026.", "correct", "shipped on 14 October"),
    ("Offline mode keeps the last 60 days of notes on the device.", "error", "60 days"),
    ("The new onboarding flow has 3 steps instead of 5.", "correct", "3 steps instead of 5"),
    ("Dark mode shipped in version 4.2.", "meaning", "Dark mode shipped"),
    ('Mira Osei said: "Offline mode was the most requested feature for two years."', "correct", "most requested feature"),
    ('As Mira Osei put it, "offline mode changed how people use the app."', "error", "changed how people use"),
    ("September revenue was $101,800.", "correct", "$101,800"),
    ("We now have over 50,000 active users.", "error", "50,000"),
]

C_RULES = """# 2027 春季读书会志愿者招募规则

读书会是虚构的组织。

- 报名时间：2027 年 2 月 1 日至 2 月 20 日。
- 每位志愿者每月至少服务 8 小时。
- 年满 18 周岁、能参加 3 次线下培训的人可以报名。
- 志愿者每次服务补贴交通费 20 元，不发放其他报酬。
- 首批招募 40 人，满额后进入候补名单。

负责人在说明会上表示：“我们更看重稳定的时间投入，而不是经验。”
"""
C_DRAFT = [
    ("# 春季读书会志愿者招募", "skip", None),
    ("报名从 2 月 1 日开始，到 2 月 20 日截止。", "correct", "2 月 20 日截止"),
    ("每位志愿者每月至少服务八小时。", "correct", "八小时"),
    ("报名条件是年满 16 周岁。", "error", "16 周岁"),
    ("需要参加 3 次线下培训。", "correct", "3 次线下培训"),
    ("每次服务补贴交通费 20 元。", "correct", "交通费 20 元"),
    ("志愿者每月还有 200 元餐补。", "error", "200 元餐补"),
    ("首批招募四十人。", "correct", "四十人"),
    ("首批招募 40 人，满额后不再接受报名。", "meaning", "不再接受报名"),
    ("负责人表示：“我们更看重稳定的时间投入，而不是经验。”", "correct", "稳定的时间投入"),
    ("负责人表示：“有经验的志愿者会优先录取。”", "error", "优先录取"),
    ("报名时间共三周。", "limit", "共三周"),
]

D_CSV = [
    ["question", "agree", "neutral", "disagree", "responses"],
    ["The weekly digest is useful", "0.62", "0.21", "0.17", "214"],
    ["I read the digest on mobile", "0.71", "0.12", "0.17", "214"],
    ["The digest is too long", "0.38", "0.30", "0.32", "214"],
]
D_NOTES = """# Reader interviews, Harbor Weekly

Harbor Weekly is a fictional newsletter. Eight readers were interviewed in October 2026.

- Reader 3: "I skim the headlines on the train and save the long pieces for Sunday."
- Reader 5: "The charts are the first thing I look at."
- Reader 7: "If it were shorter I would read it every week."

Six of the eight readers said they read the digest on a phone.
"""
D_DRAFT = [
    ("# What readers told us", "skip", None),
    ("The survey had 214 responses.", "correct", "214 responses"),
    ("62% of readers find the weekly digest useful.", "correct", "62% of readers"),
    ("71% read the digest on mobile.", "correct", "71% read"),
    ("Only 28% think the digest is too long.", "error", "Only 28%"),
    ("We interviewed eight readers in October 2026.", "correct", "interviewed eight readers"),
    ('One reader said: "I skim the headlines on the train and save the long pieces for Sunday."', "correct", "skim the headlines"),
    ('Another said: "The charts are the only thing I look at."', "error", "the only thing I look at"),
    ("Six of the eight readers read the digest on a phone.", "correct", "Six of the eight"),
    ("Most readers want a daily edition.", "meaning", "daily edition"),
    ('A reader told us: "I would pay for a longer version."', "error", "pay for a longer version"),
    ("Neutral answers ranged from 12% to 30%.", "correct", "from 12% to 30%"),
    ("45% of readers disagree that the digest is useful.", "error", "45% of readers"),
]

TASKS = [
    {"id": "TA1", "set": "A", "lang": "zh", "prompt": "根据资料，给区域经理写 4 句话的本周门店简报。"},
    {"id": "TA2", "set": "A", "lang": "zh", "prompt": "根据资料，用 3 句话向会员介绍双 11 活动规则。"},
    {"id": "TB1", "set": "B", "lang": "en", "prompt": "Using the files, write a short paragraph for the board on Larchwood's growth from August to October."},
    {"id": "TB2", "set": "B", "lang": "en", "prompt": "Using the files, summarise for users what shipped in version 4.2, in 3 sentences."},
    {"id": "TC1", "set": "C", "lang": "zh", "prompt": "根据资料，写一段 100 字左右的志愿者招募公告。"},
    {"id": "TC2", "set": "C", "lang": "zh", "prompt": "根据资料回答：报名需要满足哪些条件？有什么补贴？"},
    {"id": "TD1", "set": "D", "lang": "en", "prompt": "Using the files, summarise the survey and the interviews for the editor in 4 sentences."},
    {"id": "TD2", "set": "D", "lang": "en", "prompt": "Using the files, tell the editor in 3 sentences what readers say about the digest's length."},
]


def write_csv(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        csv.writer(f, lineterminator="\n").writerows(rows)


def write_md(path, lines):
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main():
    import docx
    import openpyxl

    sets = {
        "A": {"lang": "zh", "draft": "周报.md", "rows": A_DRAFT},
        "B": {"lang": "en", "draft": "update.docx", "rows": B_DRAFT},
        "C": {"lang": "zh", "draft": "公告.md", "rows": C_DRAFT},
        "D": {"lang": "en", "draft": "summary.md", "rows": D_DRAFT},
    }
    for name in sets:
        (SETS / name / "sources").mkdir(parents=True, exist_ok=True)
    write_csv(SETS / "A" / "sources" / "门店周数据.csv", A_CSV)
    (SETS / "A" / "sources" / "活动说明.md").write_text(A_RULES, encoding="utf-8", newline="\n")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Monthly"
    for row in B_XLSX:
        ws.append(row)
    wb.save(SETS / "B" / "sources" / "metrics.xlsx")
    (SETS / "B" / "sources" / "release-notes.md").write_text(B_NOTES, encoding="utf-8", newline="\n")
    (SETS / "C" / "sources" / "招募规则.md").write_text(C_RULES, encoding="utf-8", newline="\n")
    write_csv(SETS / "D" / "sources" / "survey.csv", D_CSV)
    (SETS / "D" / "sources" / "interviews.md").write_text(D_NOTES, encoding="utf-8", newline="\n")

    for name, s in sets.items():
        lines = [text for text, _, _ in s["rows"]]
        path = SETS / name / s["draft"]
        if path.suffix == ".docx":
            d = docx.Document()
            d.add_heading(lines[0], level=1)
            for line in lines[1:]:
                d.add_paragraph(line)
            d.save(path)
        else:
            write_md(path, lines)

    cases = {
        "about": ("v5 cases for the evcheck command line, written on 2026-11-17 before evcheck was written; every label was "
                  "fixed when the case was written. kind: correct (should pass), error (a changed or invented number or "
                  "quote; should be flagged), meaning (wrong, but its numbers and quotes are in the sources; expected to "
                  "pass), limit (a number worked out from the sources; flagged on purpose), skip (no number and no quote)."),
        "sets": [
            {"id": name, "lang": s["lang"], "draft": f"sets/{name}/{s['draft']}", "sources": f"sets/{name}/sources",
             "sentences": [{"marker": m, "kind": k, "text": t} for t, k, m in s["rows"] if m is not None]}
            for name, s in sets.items()
        ],
        "tasks": TASKS,
    }
    (ROOT / "cases.json").write_text(json.dumps(cases, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("wrote", sum(len(s["sentences"]) for s in cases["sets"]), "labelled sentences in 4 sets and", len(TASKS), "tasks")


if __name__ == "__main__":
    main()
