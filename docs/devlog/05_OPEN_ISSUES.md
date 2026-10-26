# 待解决问题 / 风险登记

> 更新时间：2026-10-26 23:34
> 状态标记：`[OPEN]` 待处理 / `[CLOSED]` 已解决 / `[DEFERRED]` 本阶段不处理
> 规则：未决事项不写进代码；影响架构的必须先拍板，再进第二阶段。
> 本轮变化：用户回复“按建议继续”，ISSUE-003/004/005/006/007/008/010 已按默认建议关闭；ADR-001~006 已产出。
> 阅读提示：已关闭条目仍保留“决策前”的问题/选项/建议，最终以 **状态** 与 **决策** 段落为准。

---

## 汇总

| ID | 状态 | 优先级 | 问题 | 默认建议 |
|---|---|---|---|---|
| ISSUE-001 | CLOSED | — | 候选仓库 404 | 用 legal-tech-chat + graphrag 替代 |
| ISSUE-002 | CLOSED | — | GitHub clone 被重置 | codeload tar.gz 快照 |
| ISSUE-003 | CLOSED | P0 | LLM 供应商/模型/Key 未定 | OpenAI 兼容接口 + 环境变量，不绑定厂商（ADR-006） |
| ISSUE-004 | CLOSED | P0 | Python 3.9+ 与 2026 依赖冲突 | 改用 Python 3.12（ADR-006） |
| ISSUE-005 | CLOSED | P0 | 国际销售合同语料与 gold 未定 | 自拟 3 份样例 + 20–30 条条款级 gold（阶段 3 执行） |
| ISSUE-006 | CLOSED | P1 | HITL 超时策略 | 出“未审批”报告，绝不自动通过（ADR-002） |
| ISSUE-007 | CLOSED | P1 | PDF 解析库与扫描件范围 | pypdf 文本型 PDF；扫描件明确不支持（ADR-005） |
| ISSUE-008 | CLOSED | P1 | 无 LICENSE 仓库不能复用代码 | 只借鉴设计，重写实现（持续政策） |
| ISSUE-009 | OPEN | P1 | 国际销售合同规则集范围未定 | 先 10–12 条高置信规则，再按评测扩充 |
| ISSUE-010 | CLOSED | P2 | 指标口径与 baseline | 指标已写入 ADR-003 / ADR-005；实施时补结果文件 |
| ISSUE-011 | OPEN | P2 | Git 仓库未初始化 | 阶段 3 开始时 init + .gitignore + 首次提交 |

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

- **状态**：CLOSED（决策已定，实施待做）
- **决策**：先自拟 3 份脱敏样例（FOB/CIF、信用证付款、含质量检验与仲裁），再扩到 20–30 条“合同 × 条款”级 gold；gold 只标 `rule_id + red/yellow/pass + 原文 span`，不标“法律上是否有效”；评测集放 `data/eval/`；不直接使用 CUAD。阶段 3 创建样例时执行。
- **优先级**：P0（阻塞评测与规则设计）
- **问题**：调研中的 CUAD 是美国 SEC 商业合同，不覆盖国际货物销售的核心条款；没有语料就无法定义“红/黄/绿”的 gold，也无法证明规则有效。
- **需要决定**：
  1. 用真实脱敏合同、公开合同模板，还是自拟样例；
  2. 语言（中/英/双语）；
  3. 谁标注 gold（规则命中级别）；
  4. 样本量与条款覆盖范围。
- **默认建议**：
  - 先自拟 3 份脱敏样例（FOB/CIF、信用证付款、包含质量检验与仲裁条款），再扩到 20–30 条“合同 × 条款”级 gold；
  - gold 只标 `rule_id + red/yellow/pass + 原文 span`，不标“法律上是否有效”；
  - 评测集放 `data/eval/`，用例 JSON 可版本化；
  - 不把 CUAD 直接当本项目评测集。
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

- **状态**：OPEN
- **优先级**：P1（影响规则引擎与评测）
- **问题**：调研项目的规则多为中文采购/劳动/招投标，不能直接用于国际货物销售。需要确定首批规则，避免“什么都想查、每条都误报”。
- **候选规则（按国际货物销售高频风险）**：
  1. 贸易术语与风险转移（Incoterms 版本、地点、费用/风险是否匹配）；
  2. 付款方式与节点（T/T、L/C 开证时间、单据、软条款）；
  3. 交付时间与迟延责任（是否明确、是否与信用证/检验冲突）；
  4. 质量/数量检验（标准、期限、地点、第三方机构）；
  5. 所有权保留与风险转移；
  6. 违约责任/赔偿上限（是否过低、是否排除间接损失）；
  7. 不可抗力（范围、通知、证明、解除权）；
  8. 争议解决与管辖（仲裁机构/规则/地点，诉讼管辖）；
  9. 适用法律（是否缺失/矛盾）；
  10. 制裁/出口管制/反腐败合规；
  11. 知识产权/保密（如涉及）；
  12. 合同生效、变更、转让限制。
- **建议**：先做 10–12 条高置信、可用正则/关键词/数值判定的规则；每条规则写 `rule_id / severity / 条件 / reason / 建议 / test fixture`；语义型规则（如“赔偿上限是否过低”）如果无法确定性判定，先不做，避免把 LLM 判断伪装成规则。
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

- **状态**：OPEN
- **优先级**：P2（阶段 3 开始前）
- **现象**：当前目录 `git status` 返回 `fatal: not a git repository`。
- **建议**：阶段 3 第一步执行 `git init`，创建 `.gitignore`（至少忽略 `.venv/`、`.env`、`.data/`、`__pycache__/`、`.pytest_cache/`、`.ruff_cache/`、`*.pyc`），然后做首次提交（只提交文档与配置模板，不提交 Key/合同原件）。
- **注意**：初始化与提交属于写操作，执行前先向用户确认提交信息风格（项目未提供规范，可用 `docs: ...` / `feat: ...`）。

---

## 本阶段不处理（DEFERRED）

| 事项 | 原因 |
|---|---|
| OCR / 扫描件解析 | 超出 10 天 MVP；先用文本型 PDF/DOCX/TXT |
| 多语言 UI | Streamlit 中文界面即可 |
| 用户登录/权限/多租户 | 比赛演示不需要；不要引入 JWT/RBAC |
| 数据库/Redis/消息队列 | 规则与报告用本地文件 + SQLite checkpointer 足够 |
| 知识图谱/GraphRAG | 与指定技术栈不符，且不是本合同审查核心 |
| 微调模型 | 禁止训练模型；用规则 + 结构化输出 |
| Docker 部署 | 明确禁止；本地 Streamlit/FastAPI 演示 |
