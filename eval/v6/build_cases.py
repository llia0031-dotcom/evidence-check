"""Write the v6 cases: two fictional "draft + sources" sets for the two problems v5 found, with their labels.

1. A sentence that joins facts from different lines of the sources (set E, Chinese; set F, English). evcheck 0.5.0
   picks at most three source lines for the whole sentence and can miss the line one of the facts comes from.
2. A number from the wrong row of a monthly table, when the sentence names the month in words (set F). evcheck 0.5.0
   matches every similar row, so another month's figure can pass.

Every label is fixed here, before evcheck is changed.

Run once from the project root:  python eval/v6/build_cases.py
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SETS = ROOT / "sets"

# kind: correct = true and stated by the sources; several facts from different lines in one sentence (should pass)
#       error   = one fact of the sentence changed or invented (should be flagged)
#       row     = a figure taken from another month's row of the table (should be flagged)
#       limit   = a number worked out from the sources (flagged on purpose)
#       skip    = no number and no quote (not checked)

E_RULES = """# 春季读书会说明

松间读书会是虚构的组织。

- 报名时间：2027 年 3 月 1 日至 3 月 15 日。
- 每期共 6 次活动，每次 90 分钟。
- 每位成员每期最多请假 2 次。
- 报名费 120 元，学生 60 元。
- 每组 5 到 8 人。

负责人在说明会上说：“读完比读快更重要。”
"""
E_CSV = [
    ["城市", "报名人数", "已分组", "候补人数"],
    ["杭州", "148", "136", "12"],
    ["苏州", "96", "90", "6"],
    ["宁波", "73", "73", "0"],
]
E_DRAFT = [
    ("# 春季读书会报名简报", "skip", None),
    ("报名时间为 2027 年 3 月 1 日至 3 月 15 日，每期共 6 次活动，每次 90 分钟。", "correct", "每次 90 分钟"),
    ("报名费 120 元，学生 60 元，每组 5 到 8 人。", "correct", "每组 5 到 8 人"),
    ("杭州报名 148 人，已分组 136 人，候补 12 人。", "correct", "候补 12 人"),
    ("苏州报名 96 人，宁波报名 73 人。", "correct", "宁波报名 73 人"),
    ("每位成员每期最多请假 2 次，负责人说：“读完比读快更重要。”", "correct", "读完比读快更重要"),
    ("报名时间为 3 月 1 日至 3 月 15 日，每次活动 120 分钟。", "error", "每次活动 120 分钟"),
    ("报名费 120 元，学生 50 元。", "error", "学生 50 元"),
    ("杭州报名 148 人，已分组 163 人。", "error", "已分组 163 人"),
    ("苏州候补 6 人，宁波候补 3 人。", "error", "宁波候补 3 人"),
    ("每组 5 到 10 人，每位成员每期最多请假 2 次。", "error", "5 到 10 人"),
    ("负责人说：“读快比读完更重要。”", "error", "读快比读完"),
    ("三个城市共报名 317 人。", "limit", "共报名 317 人"),
    ("读书会还会安排线上分享。", "skip", "线上分享"),
]

F_CSV = [
    ["month", "signups", "paid_conversions", "churn_rate"],
    ["2026-07", "5120", "384", "0.041"],
    ["2026-08", "5480", "421", "0.038"],
    ["2026-09", "6010", "467", "0.035"],
]
F_NOTES = """# Quarterly notes, Fernway

Fernway is a fictional app.

- The referral program launched on 4 August 2026.
- Annual plans were introduced on 15 September 2026 at $48 a year.
- The support team answers within 24 hours on weekdays.

The head of growth said: "Referrals did more than any ad campaign this quarter."
"""
F_DRAFT = [
    ("# Fernway, third quarter", "skip", None),
    ("Signups rose to 6,010 in September, and paid conversions reached 467.", "correct", "Signups rose to 6,010"),
    ("In August, signups were 5,480 and churn fell to 3.8%.", "correct", "fell to 3.8%"),
    ("The referral program launched on 4 August 2026, and annual plans followed on 15 September at $48 a year.",
     "correct", "$48 a year"),
    ('Support answers within 24 hours on weekdays, and the head of growth said: "Referrals did more than any ad '
     'campaign this quarter."', "correct", "within 24 hours"),
    ("July had 5,120 signups and 384 paid conversions.", "correct", "384 paid"),
    ("Churn was 4.1% in July and 3.5% in September.", "correct", "3.5% in September"),
    ("Signups reached 5,480 in September.", "row", "5,480 in September"),
    ("Churn was 3.8% in July.", "row", "3.8% in July"),
    ("Paid conversions reached 467 in August.", "row", "467 in August"),
    ("Annual plans were introduced on 15 September at $58 a year.", "error", "$58 a year"),
    ("The referral program launched on 4 August 2026, and support answers within 12 hours.", "error", "within 12 hours"),
    ("In September, signups were 6,010 and paid conversions 476.", "error", "paid conversions 476"),
    ('The head of growth said: "Referrals did more than every other channel."', "error", "every other channel"),
    ("Paid conversions grew by 83 from July to September.", "limit", "grew by 83"),
]


def write_csv(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        csv.writer(f, lineterminator="\n").writerows(rows)


def main():
    sets = {
        "E": {"lang": "zh", "draft": "简报.md", "rows": E_DRAFT},
        "F": {"lang": "en", "draft": "summary.md", "rows": F_DRAFT},
    }
    for name in sets:
        (SETS / name / "sources").mkdir(parents=True, exist_ok=True)
    (SETS / "E" / "sources" / "读书会说明.md").write_text(E_RULES, encoding="utf-8", newline="\n")
    write_csv(SETS / "E" / "sources" / "城市报名.csv", E_CSV)
    write_csv(SETS / "F" / "sources" / "metrics.csv", F_CSV)
    (SETS / "F" / "sources" / "notes.md").write_text(F_NOTES, encoding="utf-8", newline="\n")
    for name, s in sets.items():
        text = "\n".join(t for t, _, _ in s["rows"]) + "\n"
        (SETS / name / s["draft"]).write_text(text, encoding="utf-8", newline="\n")
        for _, _, marker in s["rows"]:
            if marker is not None:
                assert text.count(marker) == 1, f"marker not unique in set {name}: {marker}"

    cases = {
        "about": ("v6 cases for evcheck, written on 2026-11-17 before evcheck 0.6.0 was written; every label was fixed "
                  "when the case was written. kind: correct (true, joining facts from different source lines; should "
                  "pass), error (one fact changed or invented; should be flagged), row (a figure from another month's "
                  "row; should be flagged), limit (worked out from the sources; flagged on purpose), skip (no number "
                  "and no quote)."),
        "sets": [
            {"id": name, "lang": s["lang"], "draft": f"sets/{name}/{s['draft']}", "sources": f"sets/{name}/sources",
             "sentences": [{"marker": m, "kind": k, "text": t} for t, k, m in s["rows"] if m is not None]}
            for name, s in sets.items()
        ],
    }
    (ROOT / "cases.json").write_text(json.dumps(cases, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("wrote", sum(len(s["sentences"]) for s in cases["sets"]), "labelled sentences in", len(sets), "sets")


if __name__ == "__main__":
    main()
