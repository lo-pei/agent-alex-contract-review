# 待解决问题 / 风险登记

> 更新时间：2026-10-27（第四阶段第 1 轮：规则扩充 + 合同级评测基线）
> 状态标记：`[OPEN]` 待处理 / `[CLOSED]` 已解决 / `[DEFERRED]` 本阶段不处理
> 规则：未决事项不写进代码；影响架构的必须先拍板，再进第二阶段。
> 本轮变化：规则 7 → 13 条（ISSUE-009 第 1 轮完成，仍 OPEN）；新增合同级评测链路与 50 份模拟合同（ADR-010）；发现模拟合同实际 **50 份而非 60 份**、规则级 gold 与留出验证缺失 → 新增 **ISSUE-020**。ISSUE-005 的“gold 只标 rule_id + span”仍未执行，保持在 ISSUE-020 跟踪。ISSUE-015/018/019 状态不变。
> 阅读提示：已关闭条目仍保留“决策前”的问题/选项/建议，最终以 **状态** 与 **决策** 段落为准。

---

## 汇总

| ID | 状态 | 优先级 | 问题 | 默认建议 |
|---|---|---|---|---|
| ISSUE-001 | CLOSED | — | 候选仓库 404 | 用 legal-tech-chat + graphrag 替代 |
| ISSUE-002 | CLOSED | — | GitHub clone 被重置 | codeload tar.gz 快照 |
| ISSUE-003 | CLOSED | P0 | LLM 供应商/模型/Key 未定 | OpenAI 兼容接口 + 环境变量，不绑定厂商（ADR-006） |
| ISSUE-004 | CLOSED | P0 | Python 3.9+ 与 2026 依赖冲突 | 改用 Python 3.12（ADR-006） |
| ISSUE-005 | CLOSED | P0 | 国际销售合同语料与 gold 未定 | 决策已定：50 份模拟合同 + 检索期望 gold 已就位；**规则级 gold 由 ISSUE-020 跟踪** |
| ISSUE-006 | CLOSED | P1 | HITL 超时策略 | 出“未审批”报告，绝不自动通过（ADR-002） |
| ISSUE-007 | CLOSED | P1 | PDF 解析库与扫描件范围 | pypdf 文本型 PDF；扫描件明确不支持（ADR-005） |
| ISSUE-008 | CLOSED | P1 | 无 LICENSE 仓库不能复用代码 | 只借鉴设计，重写实现（持续政策） |
| ISSUE-009 | OPEN | P1 | 国际销售合同规则集范围未定 | 已扩到 **13 条**（11 文本 + 2 字段）；39/50 合同仍无命中，继续补主题 |
| ISSUE-010 | CLOSED | P2 | 指标口径与 baseline | 指标已写入 ADR-003 / ADR-005；实施时补结果文件 |
| ISSUE-011 | CLOSED | P2 | Git 仓库未初始化 | 已 `git init` + `.gitignore` + 首次提交 `cf0fd63` |
| ISSUE-012 | OPEN | P2 | 中文/复杂版式 PDF 未验证 | 补 CJK 字体 PDF fixture；用真实中文合同手测并记录 |
| ISSUE-013 | OPEN | P1 | 真实 LLM 未联调 | 待用户提供 Key/模型名；先用 Fake LLM 覆盖降级路径 |
| ISSUE-014 | OPEN | P2 | 长合同抽取覆盖不足（>40 条款跳过字段规则） | 先保守跳过；后续评估分块/提高上限并补评测 |
| ISSUE-015 | OPEN | P1 | RAG 知识库授权与检索评测未确认 | 真实语料已入库（14 篇，含 DOCX 条文切分）；下一步确认对外引用授权并做检索评测 |
| ISSUE-016 | OPEN | P2 | 多智能体专家角色与编排范围未定 | 阶段 B 再做；只做专家节点 + 路由，Supervisor 不得判级 |
| ISSUE-017 | CLOSED | P2 | HITL pending 时间戳只在进程内存 | 已落盘 `.data/pending/<review_id>.json`，跨进程超时判定有测试 |
| ISSUE-018 | OPEN | P1 | 检索评测问题集的 source_id 与 manifest 不一致 | 建立 `100问题.md` → manifest `source_id#section` 映射后再报召回率 |
| ISSUE-019 | OPEN | P2 | 并发锁仅进程内、上传/报告文件无清理策略 | 单机演示可接受；多进程部署前需换文件锁/数据库并加保留期 |
| ISSUE-020 | OPEN | P1 | 规则级 gold、留出合同集与模拟合同数量不符 | 用户称 60 份、实际 50 份（C01–C50）；标注 `合同 × rule_id → red/yellow/pass + span` 并另找独立合同做泛化验证 |

---

## ISSUE-001 · 候选仓库 404

- **状态**：CLOSED
- **现象**：`Negbepierre/enterprise-doc-intelligence` 的 GitHub API 返回 `404 Not Found`；用户主页无公开仓库。
- **影响**：原定 7 个候选少 1 个，调研样本不足。
- **解决**：按提示检索替代项目，补充 `tomasonjo-labs/legal-tech-chat`（CUAD + LangGraph + Neo4j）与 `neo4j-product-examples/graphrag-contract-review`（GraphRAG），最终分析 8 个。
- **证据**：`01_RESEARCH_LOG.md` 0.1、0.3、2.7、2.8。

---

## ISSUE-002 · GitHub `git clone` 被重置

- **状态**：CLOSED
- **现象**：`git clone https://github.com/...` 在 `github.com:443` 连接被重置；REST API 与 `raw.githubusercontent.com` 可用。
- **影响**：无法用 git 历史/分支调研。
- **解决**：用 `https://codeload.github.com/{owner}/{repo}/tar.gz/refs/heads/{branch}` 下载默认分支快照，`tar.exe` 解压后阅读源码。
- **限制**：只看到默认分支最新快照，看不到提交历史与其他分支；文档已注明。
- **证据**：`01_RESEARCH_LOG.md` 8.1。

---

## ISSUE-003 · LLM 供应商、模型与 Key 未定

- **状态**：CLOSED（接口决策已定；实际 Key/模型名待提供）
- **决策**：采用 OpenAI 兼容接口；`.env` 配置 `LLM_BASE_URL / LLM_API_KEY / LLM_MODEL / LLM_TIMEOUT_SECONDS / LLM_MAX_REPAIR_RETRIES`；代码不写死厂商；结构化输出优先 `json_schema`，不支持时回退 `function_calling`；测试用 Fake LLM。详见 `ADR-006-运行环境与依赖策略.md`。
- **仍待用户提供**：实际 API Key 与可用模型名（不阻塞规则/图/测试开发，只影响全链路演示）。
- **优先级**：P0（阻塞第三阶段 LLM 节点）
- **需要决定**：
  1. 用哪家 API（OpenAI / Azure OpenAI / 国内兼容接口 / 本地模型）；
  2. 模型名与上下文上限；
  3. 谁提供 Key，比赛环境是否允许联网；
  4. 超时、重试、成本上限。
- **默认建议**：抽象成 OpenAI 兼容接口，用 `.env` 配置 `LLM_BASE_URL / LLM_API_KEY / LLM_MODEL`；代码不写死厂商；结构化输出优先 `with_structured_output(method="json_schema")`，不支持时回退 `function_calling`；单次调用超时 60s，最多 1 次修复重试。
- **影响**：影响抽取/解释节点、评测成本、演示稳定性；不影响规则引擎与 HITL 测试（测试用 Fake LLM）。

---

## ISSUE-004 · Python 版本约束冲突

- **状态**：CLOSED（2026-10-26）
- **决策**：采用 **Python 3.12**；本机 `py -3.12` 可用。原 `开发提示词.md` 的“3.9+”因 2026 年 LangGraph/Streamlit 依赖要求而调整；README 必须写明原因。详见 `ADR-006-运行环境与依赖策略.md`。
- **优先级**：P0（阻塞环境初始化）
- **现象**：`开发提示词.md` 写“Python 3.9+”；但 2026-10-26 最新依赖要求：
  - LangGraph 1.2.17 / LangChain 1.4.7 / FastAPI 0.162.0 / Pydantic 2.14.1：≥3.10；
  - Streamlit 1.66.1：**≥3.11**。
- **本机**：默认 `python` 是 3.14；已装 `py -3.12`（`C:\Users\lenovo\AppData\Local\Python\pythoncore-3.12-64`）。
- **选项**：
  - A. 用 Python 3.12（推荐）：享受当前 LangGraph HITL/checkpointer、Streamlit 新特性；需在 README 说明“实际 3.12，3.9 无法满足 2026 依赖”。
  - B. 严格 3.9：锁 LangGraph 0.2.x、Streamlit 旧版、Pydantic 2 低版本；HITL API 与文档能力受限，需要额外兼容测试，风险高。
  - C. 3.11：也可以，但本机未装；需额外安装。
- **建议**：A（3.12）。请用户确认；确认后写入 ADR-001/环境说明。
- **证据**：`04_HANDOVER.md` 3.2；PyPI requires-python 查询。

---

## ISSUE-005 · 国际销售合同语料与 gold 未定

- **状态**：CLOSED（决策已定；语料与检索期望 gold 已就位，规则级 gold 转 ISSUE-020）
- **进展（2026-10-27）**：用户提供 50 份模拟合同（`data/knowledge/模拟合同1..6.md`），已拆分到 `data/contracts/C01..C50.md`，并解析出自带映射摘要 → `data/eval/gold_contracts.json`（50 份 / 105 条“条款 → Q 编号 → 期望召回 → 干扰项”）。该 gold 是**检索期望**，不含 `red/yellow/pass`，因此不能直接用于规则准率。
- **决策**（保持不变）：gold 只标 `rule_id + red/yellow/pass + 原文 span`，不标“法律上是否有效”；评测集放 `data/eval/`；不直接使用 CUAD。
- **剩余工作**：见 ISSUE-020（规则级 gold 标注、留出合同集、模拟合同数量 50 ≠ 60 的口径确认）。
- **影响**：规则阈值、HITL 触发率、报告可信度、答辩演示。

---

## ISSUE-006 · HITL 超时策略

- **状态**：CLOSED（2026-10-26）
- **决策**：采用 C：超时后恢复并标记 `unreviewed_red_risk`，报告可下载但明确“红色风险未获人工确认”；惰性检查（GET /review/{id} 或 Streamlit 轮询）触发 `Command(resume={"action":"timeout"})`；绝不自动 approve。详见 `ADR-002-HITL实现方式.md`。
- **优先级**：P1（影响 HITL 契约）
- **问题**：红色风险暂停后，如果 30 分钟无人确认，系统该怎么办？
- **选项**：
  - A. 一直等待，不自动处理（演示可能卡住）；
  - B. 超时后自动 approve（**禁止**，违背硬约束）；
  - C. 超时后恢复并标记 `unreviewed_red_risk`，报告写明“红色风险未获人工确认”（推荐）；
  - D. 超时后取消本次 review，不生成报告。
- **建议**：C；由后台 sweeper 或 `GET /review/{id}` 惰性检查触发 `Command(resume={"action":"timeout"})`；报告可下载但状态明确未审批；Streamlit 显示黄色警示条。
- **影响**：API/UI 状态机、checkpointer 线程、报告字段 `hitl.status`。

---

## ISSUE-007 · PDF 解析库与扫描件范围

- **状态**：CLOSED（2026-10-26）
- **决策**：MVP 用 `pypdf`（BSD）+ `python-docx` + TXT/Markdown；扫描件/OCR 明确不支持；不默认引入 PyMuPDF（AGPL/商业许可）；表格/复杂版式只 warning + 人工核对。详见 `ADR-005-文档解析与证据模型.md`。
- **优先级**：P1（影响 ingest 节点）
- **问题**：
  - `pypdf` BSD，能取文本型 PDF，但对复杂版式/表格/扫描件弱；
  - `PyMuPDF` 能力更强，但 AGPL/商业双许可，不适合默认引入；
  - `pdfplumber` MIT，表格强但速度慢。
- **建议**：
  - MVP 用 `pypdf` + `python-docx` + TXT；
  - 明确“不支持扫描件/OCR”；上传扫描件时返回可读错误；
  - 若后续需要表格/复杂版式，再评估 `pdfplumber`（MIT）；
  - 不引入 PyMuPDF 作为默认依赖，除非用户确认许可证。
- **影响**：文档解析质量、证据偏移是否可靠、演示合同选择。

---

## ISSUE-008 · 无 LICENSE 仓库不能复用代码

- **状态**：CLOSED（政策已定，持续执行）
- **优先级**：P1（法律/合规风险）
- **事实**：zihan、Harvey、Sentinel 仓库没有 LICENSE 文件，默认保留全部权利。
- **处理**：
  - 只借鉴设计思想与架构模式，不复制源文件、不复制大段代码；
  - 可复用代码仅限 Apache-2.0（bcefghj、laolaola、graphrag）与 MIT（aurelien、legal-tech-chat），且保留版权/许可声明；
  - 所有引用记入 `README.md` 的“第三方代码与许可”。
- **证据**：`01_RESEARCH_LOG.md` 第 1 节、8.3。

---

## ISSUE-009 · 国际销售合同规则集范围未定

- **状态**：OPEN（2026-10-27 第 1 轮已扩到 13 条；覆盖仍不足）
- **优先级**：P1（影响规则引擎与评测）
- **当前进度**：`app/rules/definitions.yaml`（`version: 3`）已实现 **13 条**：
  | rule_id | 主题 | 等级 | 依赖 | 50 份语料命中 |
  |---|---|---|---|---|
  | R-TRD-001 | 使用贸易术语但未约定 Incoterms 版本 | yellow | 文本 | 0（修正 `®` 后） |
  | R-PAY-001 | 要求买方全额预付 | red | 文本 | 0 |
  | R-PAY-002 | 未约定付款方式/节点 | yellow | 文本 | 5 |
  | R-DIS-001 | 未约定适用法律 | red | 文本 | 0 |
  | R-DIS-002 | 未约定争议解决方式 | red | 文本 | 0 |
  | R-DLV-001 | 未抽取到交付期限 | yellow | 字段（`delivery_date`） | skipped（无 Key） |
  | R-INP-001 | 未抽取到检验标准/机构 | yellow | 字段（`inspection_standard`） | skipped（无 Key） |
  | R-DIS-003 | 仲裁与诉讼并列（“或裁或审”） | red | 文本 | 1（C47） |
  | R-DIS-004 | 仲裁裁决后仍可向法院起诉（“先裁后审”） | red | 文本 | 1（C48） |
  | R-INS-001 | CIF/CIP 约定投保但未写保额/比例 | yellow | 文本 | 1（C04） |
  | R-INC-001 | 贸易术语与运费承担矛盾 | yellow | 文本 | 1（C11） |
  | R-INC-002 | FOB/EXW 用于整箱集装箱货物 | yellow | 文本 | 1（C23） |
  | R-INP-002 | 检验或通知期限以小时计（极短） | yellow | 文本 | 1（C09） |
- **新规则准入四关**（ADR-010）：DSL 可确定性判定 → 正反 fixture + 证据 span 回填 → 50 份语料命中集合固化为回归测试 → 两份样例合同零误报。
- **抽取降级语义**：`requires_extraction: true` 的规则在抽取不可用（无 Key/失败/超上限）时标记 `skipped`，不落入 yellow，避免系统降级被误读为合同缺陷。
- **仍缺的主题（下一轮候选，要求可确定性判定）**：
  1. 不可抗力条款缺失（文本级，可判定）；
  2. 责任上限缺失/过低（字段 `liability_cap` 为空 → yellow；“过低”需阈值，暂不做）；
  3. 质保期缺失（字段 `warranty_period` 为空 → yellow）；
  4. 所有权保留/风险转移条款缺失（文本级）；
  5. 制裁/出口管制/反腐败条款缺失（文本级，中国出口场景）。
- **现状判断**：50 份合同中 39 份未命中任何规则，说明上述主题确实缺口明显；但模拟合同大量使用 `[C] 天`、`[X]` 占位符，数值/期限类规则需要容忍占位符，否则会误报。
- **建议**：下一轮每条新规则同样走准入四关；语义型规则（如“赔偿上限是否过低”）如果无法确定性判定，先不做，避免把 LLM 判断伪装成规则。
- **影响**：产品定位、评测 gold、答辩演示的风险列表。

---

## ISSUE-010 · 指标口径与 baseline

- **状态**：CLOSED（2026-10-26，口径已定；结果待补）
- **决策**：规则评测 micro P/R/F1 + 混淆矩阵；抽取字段 accuracy（含 null）+ 引文支撑率；解释 `explanation_grounded_rate`、改级率（应为 0）、越权表述率、兜底率；系统 HITL 触发 precision/recall、降级率、p95、token 成本。所有结果附样本数/模型/prompt 版本/日期/命令，并给 baseline。详见 `ADR-003-规则与LLM边界.md` 3.10。
- **优先级**：P2（影响评测与汇报）
- **要求**：
  - 规则评测：micro P/R/F1（按 `合同 × rule_id`），附混淆矩阵；
  - 抽取评测：字段级 accuracy（含 null）、引文支撑率；
  - 解释评测：`explanation_grounded_rate`、是否出现改级/越权表述；
  - 系统评测：HITL 触发 precision/recall、降级率、p95 延迟、token 成本；
  - 所有报告附：样本数、模型名、prompt 版本、日期、命令；
  - **必须给 baseline**（空抽取 / 全 pass 规则）作为对照。
- **禁止**：无评测集支撑的“94%”“8 分钟”“业界领先”。
- **影响**：README、答辩材料、评委追问。

---

## ISSUE-011 · Git 仓库未初始化

- **状态**：CLOSED（2026-10-26）
- **解决方式**：已执行 `git init`；提交 `.gitignore`（忽略 `.venv/`、`.env`、`.data/`、`*.sqlite*`、`__pycache__/`、`.pytest_cache/`、`.ruff_cache/`）；首次提交 `cf0fd63 chore: 初始化仓库并提交阶段1-3第1步成果`。
- **未提交**：`.venv/`、`.env`（尚不存在）、`.data/`、缓存；未提交任何真实合同或 Key。
- **备注**：提交前未单独确认提交信息风格，采用 `chore:` 前缀；如需调整可 `git commit --amend`（尚未 push）。

---

## ISSUE-012 · 中文 / 复杂版式 PDF 未验证

- **状态**：OPEN
- **优先级**：P2（影响真实合同可用性与演示选择）
- **现象**：
  - `tests/fixtures/pdf_builder.py` 只构造 ASCII（Helvetica/WinAnsi）单栏 PDF，**不能证明中文 PDF 可解析**；
  - 页眉/页脚/水印会被 pypdf 提取进正文；表格/多栏可能打乱列顺序（只在 `warnings` 提示）；
  - 尚未用真实中文合同（含 CJK 字体、盖章页、扫描混合页）做手测。
- **复现步骤**：用一份真实中文 PDF 执行
  `.\.venv\Scripts\python.exe -m app.graph_demo 合同.pdf`，检查 `clauses` 的标题/顺序/页码与 `report.findings` 引用是否可定位。
- **建议方向**：
  1. 手测 2–3 份中文 PDF（文本型），记录解析结果到开发日志；
  2. 如需自动化，构造嵌入 CJK 子集字体的 PDF fixture（不引入 reportlab，可用 pypdf 附件/字体子集方案）；
  3. 页眉/页脚过滤放到后续迭代，先靠规则关键词窄化 + 人工核对；
  4. 复杂版式明确不支持时，在 UI 提示转 DOCX。
- **影响**：演示合同选择、证据页码可信度、中文条款切分质量。

---

## ISSUE-013 · 真实 LLM 尚未联调

- **状态**：OPEN
- **优先级**：P1（影响全链路演示与抽取效果评估）
- **现象**：
  - 目前所有抽取测试都基于 `tests/fakes.py` 的 `FakeLLM`，`json_schema` → `function_calling` 的真实回退路径未在真实供应商上验证；
  - 未测真实模型对 17 字段 schema 的遵循度、超时行为、非 JSON 输出的实际频率；
  - 没有 Key/模型名，无法给出任何抽取准确率或延迟数字。
- **需要**：用户提供 OpenAI 兼容的 `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL`（写进本地 `.env`，不入库）。
- **联调步骤**：
  1. `.\.venv\Scripts\python.exe -m app.graph_demo`（不带 Key 走降级 → 带 Key 应显示 `要素抽取：ok`）；
  2. 检查 `facts`、`fact_evidence`、`to_verify` 是否合理；
  3. 记录模型名、prompt 版本、耗时到开发日志；
  4. 若供应商不支持 `json_schema`，确认回退 `function_calling` 成功（日志里应只有一次 `StructuredOutputError` 级别的重试）。
- **禁止**：在没有真实运行记录前写“抽取准确率 X%”。

---

## ISSUE-014 · 长合同抽取覆盖不足

- **状态**：OPEN
- **优先级**：P2（影响长合同可用性）
- **现象**：`MAX_EXTRACT_CLAUSES=40`，超过上限时只抽取“前言 + 相关类型优先”的前 40 条；由于 `extraction_status` 只有全量成功才算 `ok`，此时字段规则全部 `skipped`，报告只能靠文本规则。
- **风险**：长合同（>40 条款）的字段类风险（交付期限、检验标准、责任上限）会静默不判。
- **建议方向**：
  1. 短期：报告 limitation 已写明；UI 明确提示“条款过多，字段规则未执行”；
  2. 中期：按 `clause_type` 分批抽取（每批独立 `extract_fields` 调用）+ 明确批次状态；
  3. 长期：结合成本上限做“重要性排序 + 覆盖统计”，并在评测集里加入长合同样本。
- **不可接受**：为了“跑完”把部分覆盖当 `ok`，会直接产生误报。

---

## ISSUE-015 · RAG 知识库授权与检索评测未确认

- **状态**：OPEN（2026-10-27 语料已提供，链路已跑通；授权与评测待确认）
- **优先级**：P1（影响“知识引用能否对外展示”与检索质量结论）
- **已解决**：
  - 用户已将真实语料放入 `data/knowledge/`（CISG 中英、Incoterms 2020、民法典、涉外民事关系法律适用法、6 份最高法司法解释、UCP600/仲裁要点、内部红线清单）；
  - `manifest.yaml` 已登记 14 篇，含 `source_id/title/publisher/version/jurisdiction/effective_date/language/file/license`；
  - `app/services/rag.py` 已支持 `.docx` 按“第X条”切分（民法典 1260 条 → 1261 段）、英文 CISG `***Article N***` 标题、超长片段二次切分，并显式拒绝旧版 `.doc`；
  - 实测加载 14 篇 / 1834 段，最长 1599 字符；`根本违约`、`FOB 风险转移`、`仲裁 管辖`、`不可抗力` 均能命中合理引用。
- **仍未解决**：
  1. **授权边界**：`license` 字段只是当前标注（如 `ICC-copyright-internal-use-only`、`official-text-verify-reuse`），是否允许在演示/答辩中展示原文、是否允许再分发，仍需业务/法务确认；
  2. **effective_date 复核**：日期取文件标题/文件名标注，对外引用前需按官方文本核对；
  3. **旧版 `.doc`**（`最高人民法院关于涉外民商事案件诉讼管辖若干问题的规定_20201229.doc`）未入库，需转换为 `.docx` 或 `.md`；
  4. **检索评测**：尚未跑 `100问题.md` 的 100 条 query，且其 `source_id` 命名与 manifest 不一致（ISSUE-018）。
- **默认**：`RAG_ENABLED=false`；开启后只增强解释，不参与判级；知识引用必须能在 `source_id#section` 定位。
- **禁止**：把无授权文本、抓取的付费标准全文、或模型记忆当成知识库引用。

---

## ISSUE-016 · 多智能体专家角色与编排范围未定

- **状态**：OPEN
- **优先级**：P2（阶段 B 才做，不阻塞第 5/6 步）
- **背景**：ADR-007 允许专家节点与 Supervisor 路由。但“哪些专家、谁触发、如何合并”会直接影响延迟、成本与可测试性，必须先定范围。
- **候选角色**：
  | 角色 | 输入 | 输出（禁止 `risk_level`） |
  |---|---|---|
  | 付款专家 | 付款条款 + 规则结果 | 付款节点风险解释、改写建议 |
  | 交付/物流专家 | 交付、贸易术语、检验条款 | 交付与风险转移说明 |
  | 争议解决专家 | 适用法律、仲裁/管辖条款 | 争议路径说明 |
- **约束（不可变）**：专家只能依据既有规则结果补充解释与建议；不得改级、不得新增 red/yellow；Supervisor 只做白名单路由，不做判级；专家失败必须回退到单节点解释。
- **需要用户确认**：是否需要专家节点、专家资料（30–50 组“问题条款→改写”对照、让步顺序、品类模板）、是否接受额外 LLM 调用成本。
- **默认建议**：阶段 B 先做 2 个专家（付款、争议解决），用开关 `AGENTS_ENABLED=false` 默认关闭；先补 `test_agents_cannot_override_rule_level` 与 `test_supervisor_whitelist`。

---

## ISSUE-017 · HITL pending 时间戳只在进程内存

- **状态**：CLOSED（2026-10-27 第 6 步）
- **优先级**：P2（影响重启后的超时判定）
- **原现象**：`ReviewService._requested_at` 是进程内 `dict[review_id, datetime]`；进程重启后该表为空，`get()` 无法判断是否已超过 `HITL_TIMEOUT_MINUTES`，惰性超时失效。
- **解决方式**：
  1. 新增 `app/services/pending_store.py`：`FilePendingStore` 落盘 `.data/pending/<review_id>.json`（临时文件 + `os.replace` 原子写），`MemoryPendingStore` 供测试；
  2. `ReviewService` 注入 `PendingStore`：首次观察到暂停写时间戳（不覆盖已有值），恢复/超时后清理；
  3. `review_id` 用正则白名单校验，防路径穿越；损坏文件按“未记录”处理，**绝不据此判超时**；
  4. 同一 `review_id` 的 `get` / `resume` 加 `threading.RLock`（可重入），防止并发恢复把图跑两次。
- **证据**：`tests/test_pending_store.py`
  - `test_lazy_timeout_survives_service_restart`：换新 service + 新 store 实例后仍触发 `unreviewed_red_risk`；
  - `test_pending_removed_after_decision`、`test_file_store_ignores_corrupted_file`、非法 ID 参数化测试。
- **残余风险**：锁只在单进程内有效（ISSUE-019）。

---

## ISSUE-018 · 检索评测问题集的 source_id 与 manifest 不一致

- **状态**：OPEN
- **优先级**：P1（影响 RAG 检索评测与任何“召回率”数字）
- **现象**：`data/knowledge/100问题.md` 的 100 条 query 使用 `CISG-25`、`CISG-39(2)`、`INC`、`LAW`、`CC`、`JI`、`RISK` 等命名，而 manifest 的 `source_id` 是 `CISG-ZH / CISG-EN / CISG-KEY / INCOTERMS-2020 / CN-CIVIL-CODE / CN-LAW-APPLICATION / SPC-* / RISK-REDLINE`；section 也是自然语言描述而非 `sN` / `第X条`。
- **影响**：直接跑评测会把“正确命中”误判为“未命中”，无法给出可信召回率。
- **建议方向**：
  1. 建立映射表（query # → `expected_source_ids` + `expected_sections`），人工确认 20–30 条高置信样本先跑；
  2. 检索结果允许“多命中”，评测按 `source_id` 与条文号（docx）或章节语义（md）匹配；
  3. 评测结果写入 `eval/results/*.json`，含 `RAG_TOP_K` / `RAG_MIN_SCORE` / 语料版本。
- **禁止**：在映射完成前宣称“RAG 召回率 X%”。

---

## ISSUE-019 · 并发锁仅进程内、上传/报告文件无清理策略

- **状态**：OPEN
- **优先级**：P2（单机演示可接受）
- **现象**：
  - `ReviewService` 的锁是进程内 `threading.RLock`；多 worker（多进程 uvicorn）部署时仍可能并发 resume；
  - `.data/uploads/<review_id>/` 与 `.data/pending/<review_id>.json` 没有保留期/清理任务；
  - SQLite checkpointer 的 `check_same_thread=False` 只解决线程问题，不解决多进程写冲突。
- **建议方向**：
  1. 多进程前先改用文件锁（`filelock`）/SQLite 事务锁，或限制单 worker 部署并在 README 写明；
  2. 增加启动时清理 N 天前的 uploads/pending（先做脚本，不引入调度组件）；
  3. 评测/演示环境保留现状即可，但必须在文档中说明“单进程假设”。

---

## ISSUE-020 · 规则级 gold、留出合同集与模拟合同数量不符

- **状态**：OPEN
- **优先级**：P1（决定能否报 precision/recall，以及新规则是否有泛化能力）
- **事实（2026-10-27）**：
  1. 用户称新增“60 份模拟合同”，实际 `data/knowledge/` 只有 6 个文件、**50 份合同（C01–C50）**；逐份核对无 C51–C60；
  2. 每份合同自带「条款—问题映射摘要」，已解析为 `data/eval/gold_contracts.json`（50 份 / 105 条），但它是**检索期望**（条款 → Q 编号 → 期望召回 → 干扰项），**不含 red/yellow/pass 判级**；
  3. 6 条新规则是在这同一批 50 份合同上设计并验证命中集合的，属于同分布验证。
- **影响**：
  - 现在只能报“规则触发情况”（11/50 命中），**不能报 precision/recall/F1**；
  - 用同分布语料验证的规则，泛化能力未知；
  - 若答辩需要“60 份合同”的数字，需先补齐文件或更正口径。
- **建议方向**：
  1. 请用户确认另外 10 份合同是否还有文件未放入；若确实只有 50 份，文档与答辩统一按 50 份表述；
  2. 人工标注规则级 gold（`合同 × rule_id → red/yellow/pass + 原文 span`），先标 20–30 份高置信样本，再以 `eval/run_eval.py` 输出 micro P/R/F1 与混淆矩阵（ISSUE-010 口径）；
  3. 另找或另写一批**未参与规则设计**的合同（不同措辞、英文条款、真实脱敏合同）做留出验证；
  4. 检索评测映射仍由 ISSUE-018 跟踪，不要与规则 gold 混用。
- **禁止**：把 `gold_contracts.json` 的检索期望直接当规则判级 gold，或在此前宣称任何准确率。

---

## 本阶段不处理（DEFERRED）

| 事项 | 原因 |
|---|---|
| OCR / 扫描件解析 | 超出 10 天 MVP；先用文本型 PDF/DOCX/TXT |
| 多语言 UI | Streamlit 中文界面即可 |
| 用户登录/权限/多租户 | 比赛演示不需要；不要引入 JWT/RBAC |
| 数据库/Redis/消息队列 | 规则与报告用本地文件 + SQLite checkpointer 足够 |
| 知识图谱 / GraphRAG | RAG 已放开（ADR-007），但图数据库与实体关系抽取不在 MVP；先做 BM25/字符 n-gram 检索 |
| 向量数据库 / 外部 embedding 服务 | 增加依赖与成本；MVP 用本地词法检索即可 |
| Supervisor 判级 / 专家改级 | 违反“规则唯一判级”，永远不会做 |
| 微调模型 | 禁止训练模型；用规则 + 结构化输出 |
| Docker 部署 | 明确禁止；本地 Streamlit/FastAPI 演示 |
