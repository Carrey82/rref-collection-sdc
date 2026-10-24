# Wang Zhilin — research and documentation revision

## 修改范围

根据导师反馈，本次仅完善研究论证和文档表述。修改 `docs/deck.md` 中的执行摘要、
问题与方案匹配、AI 作用、商业价值及证据边界；不修改应用代码、界面、测试、
现场演示章节、其他成员的演示脚本、PPTX、PDF 或提交材料生成程序。

本文件为研究与答辩文字补充，不表示已经完成前端、安全或部署整改。

## 1. 可直接使用的英文执行摘要

### 一句话定位

**中文：** 把客户的付款承诺纳入催收判断：该等的时候等，该跟进的时候准备草稿，再由人审核。

**English:** CollectLoop makes the customer's payment promise part of the next follow-up decision.

### 约 45–60 秒英文介绍（建议时长，需排练）

> CollectLoop helps small suppliers decide when to follow up an overdue invoice and when
> to wait. A due date alone does not tell you whether the customer has made a payment
> promise that is still valid.
>
> We record that promise and use rules to decide whether to hold or prepare a reminder.
> AI helps write the wording from recorded facts; a person checks the result. If the model
> is unavailable, a template takes over.
>
> Our prototype uses synthetic data and records approvals without sending messages.
> The next step is to test whether this workflow reduces preparation time and unnecessary
> follow-up, and whether AI adds value beyond templates. Those benefits are hypotheses,
> not results we have already measured.

### 书面补充，不必全部念出

当前为手动录入、JSON 本地存储及样例导出数据适配；尚未证实实时 Orbyte 集成。
竞争优势、回款改善和付费意愿需要独立证据。正文先讲用户、问题和方法；
上述限制作为明确备注保留，回答相关问题时展开。

### 三种证据状态

| 状态 | 当前可以如何说 | 不应替换成 |
|---|---|---|
| 代码中已有，演示前仍需核验 | 有手动录入、承诺规则、草稿和审核记录的实现 | 已通过真实客户验证 |
| 待测假设 | 希望减少准备时间和不必要的跟进 | 已减少成本或提高回款率 |
| 未来工作 | 实时集成和实际发送尚未完成 | 已接入平台或已发送提醒 |

## 2. 问题与方案为什么匹配

| 待验证的用户问题 | 当前方案如何回应 | 能展示的证据 | 不能据此推断 |
|---|---|---|---|
| 付款承诺分散在电话或聊天中 | 人工记录日期、渠道和原话 | 承诺记录及状态 | 已自动读取 WhatsApp |
| 只按到期日催收可能忽略仍有效的承诺 | 规则对有效承诺暂停起草 | 保留中的发票没有新草稿 | 已证明客户满意度提高 |
| 失约与无承诺需要不同提醒 | 账龄与失约记录影响语气和优先级 | 规则及对应草稿上下文 | AI 在预测客户信用或违约概率 |
| 每次从头写提醒耗时 | 模型或模板先提供草稿，再由人审核 | 草稿来源、编辑和审批记录 | 已测得 12 分钟降至 1 分钟 |

差异化应表述为“以付款承诺驱动跟进”，不要写“所有竞品都没有此功能”。
目前没有附带可验证的竞品调查，不能宣称市场唯一性。

## 3. 回答老师：“AI 到底做什么？”

**英文答辩版本：**

> The AI writes the reminder paragraph from invoice details and recorded promise context.
> Rules, not the model, decide eligibility and tone. The intended benefit is reducing manual
> writing while keeping the message relevant to the customer's situation. The model can
> still make mistakes, so a person checks the facts. Without a working model call, we use a
> template and identify it as such. Approval only logs a decision in this prototype.

**需要避免的表述：**
- “AI 不可能编造日期”：提示词限制不是准确性保证。
- “不配置模型也证明 AI 有效”：这只能说明模板回退可用。
- “审批后自动发送”：当前没有实际发送能力。
- “AI 决定谁该付款、谁会违约”：当前是确定性规则，不是预测模型。

## 4. 商业价值与数字口径

所有下列数字均为**假设算例**，不是用户研究结论：

- 时间：20 次提醒 ×（手工 12 分钟 − 审核草稿 1 分钟）= 220 分钟，约 3.7 小时。
- 现金流：每月赊销 RM30,000 ÷ 30 天 × 提前 7 天回款 = RM7,000。
- RM7,000 表示简化假设下减少占用的应收资金，不是新增销售收入或利润。
- 尚未证明本产品能缩短 7 天账期；不要把目标效果写成实际效果。
- 按发票量收费只是待验证选项，不代表已有付费客户或正式平台合作。

## 5. 最小研究验证方案（尚未执行）

1. 访谈少量目标供应商，记录当前承诺如何保存、由谁跟进、最近一次遗漏的具体情形。
   先验证问题是否存在，不用引导式问题要求对方认同产品。
2. 在同一组脱敏或虚构案例上比较手工写提醒与审核草稿；记录总用时、修改次数、
   事实错误和不必要催收情况。轮换操作顺序，避免仅测熟悉程度。
3. 分别记录模型输出和模板输出，不能合并后全部称作 AI 效果。
4. 报告样本量、任务条件、计时方式、中位数及范围；保留原始匿名记录。
5. 真正的回款改善需要更长期的观察，并考虑客户结构、季节等因素，不能由一次演示推断。

这些是研究建议，不是本轮已经实施的用户访谈或测试。

### 更明确的比较方法

| 比较条件 | 保持不变 | 记录什么 |
|---|---|---|
| A：手工编写 | 相同难度的发票与承诺案例、相同审核要求 | 从阅读资料到完成可用提醒的总时间 |
| B：规则 + 模板 | 相同事实与规则决定的语气 | 总时间、事实修正数、仍未修正的错误 |
| C：规则 + AI | 与 B 相同的事实、语气和审核要求 | 同样指标，另记模型调用失败及回退 |

用匹配但不完全相同的案例，轮换 A/B/C 顺序，避免背熟同一张发票造成虚假提速。
无承诺、承诺仍有效、承诺已失效的案例应分别记录。模型失败后产生的模板结果应
保留在 C 条件的整体耗时和失败率统计中，同时单列来源，不当作成功的 AI 输出。

**区分两个问题：** B 与 C 比较的是 AI 是否优于模板；A 与 B/C 的比较反映整个流程
的效果，不能把全部节省都归功于 AI。是否更少出现不必要跟进，还需单独比较
参与者在现行流程与承诺感知流程中的“等待／跟进”判断。

**结果判读规则：** 只在本次样本中，若总耗时下降且残留事实错误没有增加，才能称为
“初步支持效率假设”；若结果混合或样本太小，应如实报告不确定性。不得据此推断
真实回款改善，也不得隐去失败案例。正式实验前确定样本与评价规则，不看完结果再改标准。

**空白记录格式（不是测试结果）：**

| 匿名参与者编号 | 案例编号／承诺状态 | A/B/C | 顺序 | 总耗时（秒） | 实际草稿来源／回退原因 | 事实修正数 | 残留错误数 | 等待／跟进判断是否合适 |
|---|---|---|---|---|---|---|---|---|
| 待采集 | 待采集 | 待采集 | 待采集 | 待采集 | 待采集 | 待采集 | 待采集 | 待采集 |

## 6. 导师建议中的职责边界

| 建议 | 本轮研究文档处理 | 其他负责人的工作，本轮不改 |
|---|---|---|
| 导航难找、字体偏小、WCAG | 记录为待验证的可用性要求，不声称合规 | 前端与 UX |
| 展示发票输入 | 解释现有 Upload invoice 是手填表单，Run today's scan 是检查账款而非相机 | 前端、后端和演示操作 |
| 说明 AI 创新性 | 补充输入、输出、价值、限制及对照评估方法 | 模型接入和运行状态 |
| 执行摘要式提案 | 精简问题、方案、证据和价值表述 | PPT 排版、视频与录制 |
| Observatory B+ | 标注为目标，不能写成已实测达标 | 安全修复和发布后检查 |
| 解释前后端及存储 | 如实说明 HTML/CSS、Python、JSON 和原型边界 | 技术实现与部署 |

导师截图提到提案清晰度和问题—方案匹配的评分权重，但本次未拿到正式评分表；
答辩前应以主办方正式版本为准，不自行补全其他权重。

## 7. 使用说明与证据清单

- 导师建议来源：用户上传的 11 张会议翻译截图；转写可能有误，关键评分项应复核。
- 产品能力依据：当前仓库的发票录入、规则、文案、适配器和存储实现；本轮只读核对，
  未运行或验证其他成员的功能。
- 部署状态：2026-10-24 查询显示本导入项目尚未发布；旧 README 中的网址不能证明
  当前版本已发布。未生成 Observatory 分数。
- 原有演示章节、`docs/pitch.md` 和提交文件本轮保持原样，其中固定计数、日期、
  实际集成及效果表述仍需各负责人确认。本文件不宣称整个项目材料已全部一致。
- 团队合稿时，可采用本次执行摘要和 AI 回答；不要把研究计划描述成已完成研究。

## 8. 评委追问：简短回答

以下是研究部分的口头回答，不替换其他成员的现场演示脚本。

**“Why not just use templates?”**
> Templates are a valid baseline. AI may help adapt the wording to different promise
> histories, but we have not proved it is better. We will compare review time and errors.
> If it adds no value, the rule-and-template workflow still works.

**“What is your innovation?”**
> Our focus is making a recorded payment promise affect the next follow-up decision:
> hold, draft, or refer to a missed commitment. That explains our design focus; it is
> not a claim that no competitor has similar features.

**“Have you proved that businesses need this?”**
> Not yet. We have a working concept and a research hypothesis. We need supplier interviews
> and task-based comparisons to establish how frequent the problem is and whether our
> approach improves their current process.

**“How much money does it save?”**
> We do not have measured savings yet. The RM7,000 figure is a working-capital illustration
> under stated assumptions, not product revenue, profit or a verified customer result.

**“What would make you change the proposal?”**
> If suppliers already capture promises reliably, we would revise the problem definition.
> If AI takes longer to review or introduces more errors than templates, we would not
> claim an AI advantage.

## 9. Wang Zhilin 部分的交稿检查

- 开头能否用一句话说清目标用户和产品作用，而不是先报技术名称？
- 正文是否只保留核心论点，详细假设与来源放在备注，并且仍可查阅？
- 每个“提高、减少、节省”是否明确是目标、算例还是实际测量？
- 是否把规则的价值与 AI 的增量价值分开，而不是笼统称为 AI 自动化？
- 时间数字是否包括人工检查和修正，而不是只算生成速度？
- 竞品、评分表和真实用户研究如另有材料，是否先核实来源再合入，而非自行补结论？
- 是否避免修改其他成员的演示、实现和提交文件？若发现不一致，只标注交接事项。
