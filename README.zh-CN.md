# evidence-check（有据可查）

交稿之前，核对稿子里的每个数字、每句引文是不是真的在你自己的资料里。

- **evcheck**：命令行工具，也是 MCP 服务。给它一篇写好的稿子和写稿用的资料文件夹，它列出数字或引文在资料里找不到的每一句，并给出最接近的原文。不联网，不用模型，不用注册账号。
- **一个 [Agent Skill](https://agentskills.io)**：让 AI 写的每一句事实都附上资料里的逐字原文，并用同一套规则核对这些原文。

[English](README.md)

## 一行命令查稿

安装（Python 3.10 或以上，用 [uv](https://docs.astral.sh/uv/)）：

```bash
uv tool install "evcheck[docs] @ git+https://github.com/llia0031-dotcom/evidence-check"
```

运行：

```bash
evcheck 周报.md --sources 原始数据/
```

结果（例子在 [`eval/v5/sets/A`](eval/v5/sets/A)，核对了 11 句，这里列出 6 处问题中的 3 处）：

```
 ✗  第 4 行  南京新街口店本周订单 1,978 单。
      数字和资料对不上
      找不到：1978
      最接近：门店周数据.csv 第 4 行：门店：南京新街口店；周：2026-W46；订单数：1987；GMV（元）：69545；客单价（元）：35.0；退款率：0.018
 ✗  第 8 行  每位顾客每天最多使用 3 张优惠券。
      数字和资料对不上
      找不到：3
      最接近：活动说明.md 第 7 行：每位顾客每天最多使用 2 张优惠券。
 ✗  第 10 行  区域经理强调：“复购比单量更重要，所有门店都要冲刺。”
      资料里没有这句引文
      “复购比单量更重要，所有门店都要冲刺。”
      最接近：活动说明.md 第 10 行：区域经理在启动会上说：“这次活动先看复购，不追求单量。”

核对了 11 句：5 句在资料里找到，6 句没有。另有 2 句没有数字或引文，没有核对。
```

加上 `--html 报告.html`，同样的结果会写成一个可以发给别人看的网页：

![例子的网页报告：核对 11 句，6 句对不上，每句附最接近的原文](images/report-zh.png)

- **稿子**可以是 Markdown、纯文本、Word、PDF、网页；**资料**可以是这些格式的文件或文件夹，也可以是 CSV 和 Excel，表格每一行连同列名一起读。
- **退出码**：有对不上的句子时是 1，全部找到是 0，文件读不了是 2，所以可以放进脚本或 CI 里拦住有问题的稿子。`--json -` 输出完整结果，`--problems-only` 只列有问题的句子，`--lang en` 换成英文标签（默认按稿子的语言）。
- **不装 `[docs]`** 也能读 Markdown、纯文本和 CSV，不需要别的包（Python 3.9 或以上）：`pip install "evcheck @ git+https://github.com/llia0031-dotcom/evidence-check"`。
- **`--llm`（可选）**：对没找到的句子，由 Claude Haiku 5.5 指出资料里说这件事的原文，不限语言；脚本再像核对其他原文一样核对它，所以只有资料里真有、而且含有句中数字的原文，才能让这句通过。发出请求前会先显示 token 数和费用（一篇 4 句的中文稿对英文资料，0.0004 美元）。需要装 `evcheck[llm]`，并设置 `ANTHROPIC_API_KEY`。
- **原理**：带数字、日期、金额或引号的每一句，先按字词在资料里找最接近的几行，再由 Skill 的脚本逐字核对引文、逐个核对数字。一句话里合并了几件事时，还会按逗号分成几段分别去找；用文字写的月份（9 月、September）会找表格里那个月的一行。它不判断意思，没有数字或引文的句子不核对。不加 `--llm` 时，稿子和资料要是同一种语言。

## 让 AI 助手自己查（MCP）

```bash
claude mcp add evcheck -- uvx --from "evcheck[mcp] @ git+https://github.com/llia0031-dotcom/evidence-check" evcheck-mcp
```

助手会多出三个工具：`check_draft` 核对整篇稿子，`check_claim` 核对一句话和它所引的原文，`find_quote` 查一段话在资料里逐字出现在哪里（找不到就给最接近的几行）。资料在助手自己的沙箱里、不在运行这个服务的电脑上时，助手直接传资料原文，不传路径。任何 MCP 客户端都可以启动同一条命令；已经在 Claude Code 和 DeerFlow 里跑过。

## Agent Skill

根据资料写的回答和草稿，常常错在不起眼又要命的地方：截止日期差了一天，时长是自己算的而不是照抄的，多出一个哪份资料都没写的细节。evidence-check 让 Agent 给每个事实注明出处，然后由脚本确认：

1. **引文确实在所引的文件里**（大小写、空格、弯引号、标点的差别不算）；
2. **说法里的每个日期、时间、金额、数量都出现在引文里**，中英文可以互相对照：`下午2点` 对得上 `14:00`，`五位` 对得上 `Five`，`4.3万` 对得上 `43,000`，引文写的是 `13:00` 时，`13:30` 过不了。

脚本看不懂意思：一句真实存在的原文，可能被拿来支持相反的说法。所以 Skill 还要求 Agent 把每条通过脚本的说法和引文对照着读一遍。

### 两种用法

- **只依据资料回答。** “只根据 handbook.md 和 faq.md 回答，每句给出处。”过不了脚本的说法会先被改正或删掉，你看到的回答里每句都有原文。
- **核对一份草稿。** “用规章文件夹核对这份通知。”Agent 把草稿拆成一条条说法，给每条找原文，跑脚本，再逐条报告问题：资料原话是什么，建议怎么改。它不会替你改草稿。

### 安装 Skill

Claude Code，作为插件安装：

```
/plugin marketplace add llia0031-dotcom/evidence-check
/plugin install evidence-check@evidence-check
```

其他支持 Agent Skills 的工具：把 `skills/evidence-check/` 复制到它的 Skill 文件夹（不用插件的 Claude Code 是 `~/.claude/skills/evidence-check/`）。

脚本只需要 Python 3.9 或以上，不用装别的包。

版本号：给 Agent 的说明（`SKILL.md`）是 v0.2，只有和新的模型评测一起才会改；脚本和插件是 0.5.0；evcheck 是 0.6.0。各自单独编号。

### 自己跑脚本

claims 文件列出每条说法和支持它的原文：

```json
{"claims": [
  {"id": "2", "text": "Projects must be submitted by 13:30 on Sunday.",
   "evidence": [{"source": "B02-update-notice-1.md",
                 "quote": "Project submission now closes on Sunday 17 January 2027 at 14:00 MYT instead of 13:00."}]}
]}
```

```bash
python skills/evidence-check/scripts/check_evidence.py claims.json --sources eval/v2/sources --format markdown --lang zh
```

用 `eval/v2/sources` 里的示例资料核对四条说法，结果是：第 1 条（报名 2027 年 1 月 3 日 23:59 截止）有依据；第 2 条（13:30 前提交）数字在引文里找不到，缺 `13:30`；第 3 条（押金是50令吉）对上了英文原文 “refundable deposit of RM 50”；第 4 条（每人送一件 T 恤）没有给出依据。完整表格见 [英文说明](README.md#run-the-script-yourself)。

退出码 0 表示全部通过，1 表示至少一条没通过，2 表示输入读不了。`--format json` 输出完整报告。字段和匹配规则见 [`references/claims-format.md`](skills/evidence-check/references/claims-format.md)。

## 能抓到什么

evcheck 用的就是脚本的规则，所以它和“脚本”一栏相同，另外多一条限制，在表格最后一行。

| | 脚本 | Agent 读意思 | 处理不了 |
|---|---|---|---|
| 引文被改过、拼接过或编造 | ✓ | | |
| 日期、时间、金额、数量被改 | ✓ | | |
| 数字是自己算出来的（把 19:00 到 20:30 说成“两小时”） | ✓ | | |
| 说法没有出处 | ✓ | | |
| 用真实原文支持相反的意思、漏掉条件、说大了范围 | | ✓ | |
| 旧值已被新文件替换，但旧文件还在资料里 | | v2 题目里都抓到了 | |
| 保留两位以上有效数字的四舍五入（`0.31` 对 `0.314`）：认，并在报告里列出 | ✓ | | |
| 加总、换算和更粗的四舍五入（`约 4 万` 对 `43,000`）、罗马数字：会标出来，由你核对 | | | ✓ |
| 仅 evcheck：句子没写明是表格哪一行，或者别的词几行都对得上时，取错行的数字（v6 里 3 处取错月份的数字标出 2 处） | | | ✓ |

## 谁在用它

下面这些项目都出自同一作者，在自己的产出上运行这个脚本：

- **[有据审核（广告审核 Agent）](https://github.com/llia0031-dotcom/grounded-review)。** 它的 `check_quotes` 工具把每一句广告原话和所引条款的原文交给脚本核对，不是逐字出现在广告或条款里的引文，在有人读到答案之前就会被拦下。
- **[有据标注流水线](https://github.com/llia0031-dotcom/grounded-labelling-pipeline)。** 围绕有据审核搭的审核工作流：引文核对没过的判断进复核队列，政策库问答里的每一句引文也对照它所引的条款核对。
- **[卖点体检](https://github.com/llia0031-dotcom/sellpoint-check)。** 从商品评价里摘出的每一句引文，都和它出自的那条评价逐字核对。
- **[有据可查的简历初筛](https://github.com/llia0031-dotcom/evidence-screening)。** 用冻结的 0.2.0 脚本核对每个“符合要求”判断背后的引文，来源只有那份简历。
- **[实时语音 Agent 体验评测](https://github.com/llia0031-dotcom/voice-agent-eval)。** 助手说出口的确认里的日期、时间和数字，对照工具调用记录核对，脚本原样使用。
- **[有据经营分析](https://github.com/llia0031-dotcom/grounded-business-review)。** 周报里每一段写了数字的话，都要逐字引用查询结果里它出自的那几行，并通过这个脚本；没通过的周报不发出。

## 相关工具

- **Claude API 的 [Citations](https://platform.claude.com/docs/en/build-with-claude/citations)（引用功能）** 直接从你的文档里截取引文，引文一定在原文里。在这个 API 上做产品，就用它。它是在 Messages API 里给 Claude 正在写的回答附出处：不检查说法里的数字是否在引文里；用工具读文件的 Agent 和其他模型用不到它；也不会把别人写好的草稿拆成一条条说法来核对。evidence-check 管的是这几块。
- **云平台的依据检查**（Vertex AI check grounding、Azure AI Content Safety groundedness detection、Amazon Bedrock Guardrails contextual grounding check）和**开源检测模型**（LettuceDetect、MiniCheck、HHEM）用模型判断一段话有没有依据。evidence-check 给每条说法附上原文和行号，比对数字不用模型、不用云账号，也不用装别的包。
- **用模型或上网核查说法的工具**（RefChecker，以及 groundcheck、Factiverse 等 MCP 服务）问的是一句话“在世界上真不真”或“模型认为有没有依据”。evcheck 只回答一个更窄的问题：这个数字、这句引文在不在你给的文件里，并给出那一行。**[andon](https://github.com/gulmezeren2-byte/andon)** 按你写好的断言核对表格和报告里的数，两者可以一起用。
- **评测框架**（RAGAS、DeepEval、TruLens、promptfoo）事后给一批测试题打分。这个项目的评测用的是 promptfoo。

## 评测

都在虚构资料上做；用到模型的几轮都是 Claude Haiku 5.5，每道题跑两遍：

- **v1，84 句已拆好的句子。** 普通提示词 168 个判断已经对了 167 个；漏掉的那一句是算错的时长（把 19:00 到 20:30 说成“两小时”），脚本抓住了。
- **v2，留出题：16 道自由作答、8 篇没拆好的草稿。** 三种做法都抓到了全部 30 处埋好的错误。唯一编出来的数字是自己算的“32 小时”（普通提示词 32 个回答里有 4 个，SKILL.md v0.2 一个也没有），脚本每次都能标出来。如果事后才对普通提示词的输出跑脚本，它会把 150 处正确事实里的 12 处也判成不通过，因为引文不完整；装了 Skill，Agent 会自己补齐引文，只剩 2 到 3 处误报。代价是每个任务的费用约为普通提示词的 3 倍。
- **脚本 0.3.0，来自上面这些项目里的使用。** 针对在这些项目的文件上出现的误报加了 9 条比对规则（`December 2025`、`三分之一`、`4.3万`、`99.6%` 对 `0.996`、带版本号的模型名）。在改动之前定好的 36 道新题上，正确说法的通过数从 16 条里 3 条变成 16 条全过，17 处改过的数字仍然全部标出；v1、v2 的结果一处没变。
- **脚本 0.4.0。** 保留两位以上有效数字的四舍五入算对上，并在报告里列出；引文附近的中文序数、引号里的组名、`a third`、带秒的时间和 `SigLIP 2` 这类名字不再误报。在改动之前定好的 28 道新题上，正确说法的通过数从 11 条里 0 条变成 11 条全过，13 处改过的数字或名字仍然全部标出。

- **v5，evcheck 核对整篇稿子。** 4 篇 Markdown 和 Word 稿子，资料有 Markdown、CSV、Excel：埋的 16 处错全部标出，25 句正确的一句也没误报。32 次写作任务里，能调用它的助手写出的数字全都能在资料里找到，不能调用的有 6 个找不到；这 6 个都不是错数（列表编号、数出来的个数、算对了的增长率），所以它在这里的作用是让每个数字都能对回原文。它在助手的回答里也有 10 处误报，都是一句话里合并了资料里不同行的几件事，这是下一步要改的。32 段对话走批量接口，一共 0.0092 美元。
- **v6，evcheck 0.6.0。** 一句话合并了几件事时分段去找原文，用文字写的月份会找表格里那个月的一行。在改动前定好的 27 道新题上，11 句合并句全部通过，10 处改错的仍全部标出；3 处取错月份的数字标出 2 处（改前 0 处）。在 v5 助手写的 32 个回答上，误报从 10 处降到 2 处。用 0.6.0 的助手保留的数字更多（161 对 152），资料里找不到的数字仍是 0 个。

完整报告（英文）：[`eval/EVALUATION.md`](eval/EVALUATION.md)。测试用的资料和草稿是虚构的，和 Skill 出自同一作者。

## 开发

```bash
python -m unittest discover -s tests -v     # 离线测试，不调用模型
python eval/script_only.py                  # 只用脚本核对 v1 题目
python eval/v2/score.py --check             # 检查 v2 题目本身
python eval/v3/run.py                       # 比对规则：脚本 0.2.0 和当前版本对照
python eval/v4/run.py                       # 四舍五入和名字规则：脚本 0.3.0 和当前版本对照
python eval/v5/run_cli.py                   # 用 evcheck 核对 v5 的稿子（Word 和 Excel 要装 evcheck[docs]）
python eval/v6/run.py                       # 在 v6 新题上对照 evcheck 0.5.0 和当前版本
```

模型对比评测用 [promptfoo](https://www.promptfoo.dev)，需要 Node.js，并在 `eval/.env` 里放 Anthropic API 密钥（`ANTHROPIC_API_KEY=...`）；运行命令写在每个 `promptfooconfig.yaml` 的开头。v5 第二部分用 `python eval/v5/run_agents.py estimate | run | score` 跑（要装 `anthropic`）。

## 许可证

MIT，见 [LICENSE](LICENSE)。
