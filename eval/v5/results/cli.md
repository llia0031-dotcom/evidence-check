# v5 part 1: evcheck 0.5.0 on four drafts

Each labelled sentence of `cases.json`, checked with no claims file and no model.

| Kind | Sentences | Expected | Flagged | Passed | Not checked |
|---|---|---|---|---|---|
| correct | 25 | pass | 0 | 25 | 0 |
| error | 16 | flagged | 16 | 0 | 0 |
| meaning | 4 | pass | 0 | 2 | 2 |
| limit | 2 | flagged | 2 | 0 | 0 |
| skip | 1 | not checked | 0 | 0 | 1 |

- Planted errors flagged: **16 of 16**
- Correct sentences flagged (false alarms): **0 of 25**

## Every sentence

| Set | Kind | Sentence | Result | Why |
|---|---|---|---|---|
| A | correct | 杭州湖滨店本周订单 3,412 单，GMV 约 12.8 万元。 | pass | — |
| A | correct | 上海静安店客单价 42 元，退款率 3.1%。 | pass | — |
| A | error | 南京新街口店本周订单 1,978 单。 | flagged | numbers_not_in_source (1978) |
| A | error | 三家店的退款率都低于 3%。 | flagged | numbers_not_in_source (3) |
| A | correct | 活动时间是 11 月 11 日至 11 月 13 日。 | pass | — |
| A | correct | 会员第二杯半价，非会员第二杯八折。 | pass | — |
| A | error | 每位顾客每天最多使用 3 张优惠券。 | flagged | numbers_not_in_source (3) |
| A | correct | 区域经理在启动会上说：“这次活动先看复购，不追求单量。” | pass | — |
| A | error | 区域经理强调：“复购比单量更重要，所有门店都要冲刺。” | flagged | quote_not_found |
| A | meaning | 活动期间积分加倍。 | not checked | — |
| A | error | 新客占比达到 38%。 | flagged | no_source |
| A | skip | 下周计划在南京新街口店试点外卖满减。 | not checked | — |
| A | limit | 三家店本周合计订单 8,289 单。 | flagged | no_source |
| B | correct | Active users reached 47,310 in October, up from 43,950 in September. | pass | — |
| B | correct | Thirty-day retention rose to 30.5% in October. | pass | — |
| B | correct | Revenue was $110,240 in October. | pass | — |
| B | error | Revenue grew 12% from August to October. | flagged | numbers_not_in_source (12) |
| B | correct | Version 4.2 shipped on 14 October 2026. | pass | — |
| B | error | Offline mode keeps the last 60 days of notes on the device. | flagged | numbers_not_in_source (60) |
| B | correct | The new onboarding flow has 3 steps instead of 5. | pass | — |
| B | meaning | Dark mode shipped in version 4.2. | pass | — |
| B | correct | Mira Osei said: "Offline mode was the most requested feature for two years." | pass | — |
| B | error | As Mira Osei put it, "offline mode changed how people use the app." | flagged | quote_not_found |
| B | correct | September revenue was $101,800. | pass | — |
| B | error | We now have over 50,000 active users. | flagged | numbers_not_in_source (50000) |
| C | correct | 报名从 2 月 1 日开始，到 2 月 20 日截止。 | pass | — |
| C | correct | 每位志愿者每月至少服务八小时。 | pass | — |
| C | error | 报名条件是年满 16 周岁。 | flagged | numbers_not_in_source (16) |
| C | correct | 需要参加 3 次线下培训。 | pass | — |
| C | correct | 每次服务补贴交通费 20 元。 | pass | — |
| C | error | 志愿者每月还有 200 元餐补。 | flagged | numbers_not_in_source (200) |
| C | correct | 首批招募四十人。 | pass | — |
| C | meaning | 首批招募 40 人，满额后不再接受报名。 | pass | — |
| C | correct | 负责人表示：“我们更看重稳定的时间投入，而不是经验。” | pass | — |
| C | error | 负责人表示：“有经验的志愿者会优先录取。” | flagged | quote_not_found |
| C | limit | 报名时间共三周。 | flagged | numbers_not_in_source (3) |
| D | correct | The survey had 214 responses. | pass | — |
| D | correct | 62% of readers find the weekly digest useful. | pass | — |
| D | correct | 71% read the digest on mobile. | pass | — |
| D | error | Only 28% think the digest is too long. | flagged | numbers_not_in_source (28) |
| D | correct | We interviewed eight readers in October 2026. | pass | — |
| D | correct | One reader said: "I skim the headlines on the train and save the long pieces for Sunday." | pass | — |
| D | error | Another said: "The charts are the only thing I look at." | flagged | quote_not_found |
| D | correct | Six of the eight readers read the digest on a phone. | pass | — |
| D | meaning | Most readers want a daily edition. | not checked | — |
| D | error | A reader told us: "I would pay for a longer version." | flagged | quote_not_found |
| D | correct | Neutral answers ranged from 12% to 30%. | pass | — |
| D | error | 45% of readers disagree that the digest is useful. | flagged | numbers_not_in_source (45) |
