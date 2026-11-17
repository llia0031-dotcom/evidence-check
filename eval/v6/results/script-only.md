# v6: evcheck 0.5.0 against the current version, no model

## 1. v6 cases (27 sentences)

| Kind | Sentences | Expected | evcheck 0.5.0: flagged / passed / not checked | evcheck 0.6.0: flagged / passed / not checked |
|---|---|---|---|---|
| correct | 11 | pass | 1 / 10 / 0 | 0 / 11 / 0 |
| error | 10 | flagged | 10 / 0 / 0 | 10 / 0 / 0 |
| row | 3 | flagged | 0 / 3 / 0 | 2 / 1 / 0 |
| limit | 2 | flagged | 2 / 0 / 0 | 2 / 0 / 0 |
| skip | 1 | not checked | 0 / 0 / 1 | 0 / 0 / 1 |

## 2. v5 Part 1, regression (48 sentences)

| Kind | Sentences | Expected | evcheck 0.5.0: flagged / passed / not checked | evcheck 0.6.0: flagged / passed / not checked |
|---|---|---|---|---|
| correct | 25 | pass | 0 / 25 / 0 | 0 / 25 / 0 |
| error | 16 | flagged | 16 / 0 / 0 | 16 / 0 / 0 |
| meaning | 4 | pass | 0 / 2 / 2 | 0 / 2 / 2 |
| limit | 2 | flagged | 2 / 0 / 0 | 2 / 0 / 0 |
| skip | 1 | not checked | 0 / 0 / 1 | 0 / 0 / 1 |

## Every v6 sentence

| Set | Kind | Sentence | evcheck 0.5.0 | evcheck 0.6.0 |
|---|---|---|---|---|
| E | correct | 报名时间为 2027 年 3 月 1 日至 3 月 15 日，每期共 6 次活动，每次 90 分钟。 | pass | pass |
| E | correct | 报名费 120 元，学生 60 元，每组 5 到 8 人。 | pass | pass |
| E | correct | 杭州报名 148 人，已分组 136 人，候补 12 人。 | pass | pass |
| E | correct | 苏州报名 96 人，宁波报名 73 人。 | pass | pass |
| E | correct | 每位成员每期最多请假 2 次，负责人说：“读完比读快更重要。” | pass | pass |
| E | error | 报名时间为 3 月 1 日至 3 月 15 日，每次活动 120 分钟。 | flagged | flagged |
| E | error | 报名费 120 元，学生 50 元。 | flagged | flagged |
| E | error | 杭州报名 148 人，已分组 163 人。 | flagged | flagged |
| E | error | 苏州候补 6 人，宁波候补 3 人。 | flagged | flagged |
| E | error | 每组 5 到 10 人，每位成员每期最多请假 2 次。 | flagged | flagged |
| E | error | 负责人说：“读快比读完更重要。” | flagged | flagged |
| E | limit | 三个城市共报名 317 人。 | flagged | flagged |
| E | skip | 读书会还会安排线上分享。 | not checked | not checked |
| F | correct | Signups rose to 6,010 in September, and paid conversions reached 467. | pass | pass |
| F | correct | In August, signups were 5,480 and churn fell to 3.8%. | pass | pass |
| F | correct | The referral program launched on 4 August 2026, and annual plans followed on 15 September at $48 a year. | pass | pass |
| F | correct | Support answers within 24 hours on weekdays, and the head of growth said: "Referrals did more than any ad campaign this quarter." | flagged | pass |
| F | correct | July had 5,120 signups and 384 paid conversions. | pass | pass |
| F | correct | Churn was 4.1% in July and 3.5% in September. | pass | pass |
| F | row | Signups reached 5,480 in September. | pass | flagged |
| F | row | Churn was 3.8% in July. | pass | flagged |
| F | row | Paid conversions reached 467 in August. | pass | pass |
| F | error | Annual plans were introduced on 15 September at $58 a year. | flagged | flagged |
| F | error | The referral program launched on 4 August 2026, and support answers within 12 hours. | flagged | flagged |
| F | error | In September, signups were 6,010 and paid conversions 476. | flagged | flagged |
| F | error | The head of growth said: "Referrals did more than every other channel." | flagged | flagged |
| F | limit | Paid conversions grew by 83 from July to September. | flagged | flagged |

## v5 Part 1 sentences whose result changed

None.
