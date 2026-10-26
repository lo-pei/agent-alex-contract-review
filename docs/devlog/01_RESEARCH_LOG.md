# 01 GitHub 调研与借鉴决策文档

> 调研日期：2026-10-26
> 调研人：Trae AI 开发搭档
> 项目：面向“国际货物销售合同”的 AI 预审智能体（AI 创新应用大赛·智能体构建赛道）
> 验证级别：**实时验证**。GitHub REST API 可访问（HTTP 200），通过 `codeload.github.com` 拉取各仓库默认分支快照并阅读源码；不是仅凭训练记忆描述。
> Star / 更新时间均为 2026-10-26 的快照值，会随时间变化。
> 后续：用户于 2026-10-26 回复“按建议继续”，本调研的架构建议已落为 `02_ARCHITECTURE_DECISIONS/ADR-001~006`（ADR-006 已接受，其余待确认）。

---

## 0. 调研方法与结论摘要

### 0.1 调研过程

1. 用 GitHub REST API 查询 7 个候选仓库的元数据（Star、Fork、语言、默认分支、最近 push 时间、许可证）。
2. 直接用 `git clone` 访问 `github.com:443` 时连接被重置；改用 `codeload.github.com/{owner}/{repo}/tar.gz/refs/heads/{branch}` 下载默认分支快照并解压，逐个项目阅读 README、图编排、规则引擎、HITL、结构化输出、测试与评测代码。
3. 候选项目 `Negbepierre/enterprise-doc-intelligence` 返回 **404 Not Found**（用户主页无公开仓库），按提示搜索替代项目，补充：
   - `tomasonjo-labs/legal-tech-chat`（CUAD + LangGraph + Neo4j）
   - `neo4j-product-examples/graphrag-contract-review`（GraphRAG 合同问答）
4. 所有“项目声称”与“代码实际实现”分开记录；对关键差异在正文中标注证据文件与行号。

**最终分析 8 个项目**：原候选 6 个 + 替代 2 个。

### 0.2 一句话结论

没有任何一个项目同时满足本项目的三条硬约束（规则决定风险等级、LLM 只做抽取与解释、`interrupt()` 真 HITL）。最值得借鉴的是 **aurelien-henrion 的“LLM 提议 + Python 复核 + 审批前重校验”**、**Harvey 的确定性 Quality Gate**、**laolaola 的页码/字符偏移证据引用**，以及 **zihan 的结构化输出修复重试与降级/ Badcase 回归**。同时必须避开 bcefghj 的“文档声称 interrupt、代码并未中断”和 zihan 的“让 LLM 也判定风险等级”。

### 0.3 候选仓库可用性

| 候选 | 结果 |
|---|---|
| bcefghj/multi-agent-contract-review | 存在，已分析 |
| zihan154896-jpg/intelligent-contract-review | 存在，已分析 |
| laolaola278-dev/enterprise-contract-review-agent | 存在，已分析 |
| aurelien-henrion/contract-agent | 存在，已分析 |
| Harvey-cream/Langchain_DG | 存在，已分析 |
| kashifumair125/ContractSentinel | 存在，已分析（仓库名实际大小写为 `Contractsentinel`） |
| Negbepierre/enterprise-doc-intelligence | **404，已失效**；用 legal-tech-chat + graphrag-contract-review 替代 |

---

## 1. 项目快照与许可证

| # | 仓库 | Star | Fork | 最近 push | 主语言 | 许可证 | 规模（tree 条目） |
|---|---|---:|---:|---|---|---|---:|
| 1 | [bcefghj/multi-agent-contract-review](https://github.com/bcefghj/multi-agent-contract-review) | 69 | 18 | 2026-04-05 | Python / Java / Go | Apache-2.0 | 117 |
| 2 | [zihan154896-jpg/intelligent-contract-review](https://github.com/zihan154896-jpg/intelligent-contract-review) | 1 | 0 | 2026-09-07 | Python / TypeScript | **无 LICENSE 文件** | 263 |
| 3 | [laolaola278-dev/enterprise-contract-review-agent](https://github.com/laolaola278-dev/enterprise-contract-review-agent) | 2 | 0 | 2026-09-21 | Python | Apache-2.0 | 61 |
| 4 | [aurelien-henrion/contract-agent](https://github.com/aurelien-henrion/contract-agent) | 0 | 0 | 2026-10-21 | Python | MIT | 136 |
| 5 | [Harvey-cream/Langchain_DG](https://github.com/Harvey-cream/Langchain_DG) | 29 | 0 | 2026-10-12 | Python / TypeScript | **无 LICENSE 文件** | 407 |
| 6 | [kashifumair125/ContractSentinel](https://github.com/kashifumair125/ContractSentinel) | 0 | 0 | 2026-05-26 | Python / HTML | **无 LICENSE 文件** | 50 |
| 7 | [tomasonjo-labs/legal-tech-chat](https://github.com/tomasonjo-labs/legal-tech-chat) | 163 | 36 | 2025-06-03 | Jupyter / Python | MIT | — |
| 8 | [neo4j-product-examples/graphrag-contract-review](https://github.com/neo4j-product-examples/graphrag-contract-review) | 122 | 28 | 2024-11-02 | Python | Apache-2.0 | — |

> 许可证结论：**zihan / Harvey / Sentinel 没有 LICENSE，默认保留全部权利，不能复制代码**，只能借鉴设计思想；bcefghj、laolaola、graphrag 为 Apache-2.0，aurelien、legal-tech-chat 为 MIT，若复用代码需保留版权与许可声明。

---

## 2. 逐项目结构化分析

### 2.1 bcefghj/multi-agent-contract-review

| 维度 | 事实 |
|---|---|
| 仓库 / 更新时间 | 69 Star / 18 Fork，2026-04-05 创建并更新 |
| 技术栈 | Python 主实现：LangGraph ≥0.2、LangChain ≥0.3、FastAPI、Pydantic；另有 Java Spring、Go、Next.js 三套实现 |
| 工作流节点拆分 | 严格顺序：`clause_extraction → risk_identification → compliance_check → suggestion → 条件路由 → human_review → process_feedback → complete`；无并行、无 Supervisor（`python/src/pipeline/graph.py:107-140`） |
| 规则 / LLM 分工 | Python `RuleEngine` 内置 8 条规则（R001–R008），`contains / not_contains / matches / gt / lt / eq / in / and / or`，severity = critical/warning/info，按 priority 排序（`python/src/rules/engine.py:198-354`）。风险识别 Agent 先跑规则，再调用 LLM，取更高等级合并（`python/src/agents/risk_identification.py:135-155`）——**LLM 也参与等级判定** |
| HITL 实现 | **并非真实 interrupt**。`human_review_node` 只返回 `AWAITING_HUMAN` 状态（`graph.py:42-52`）；`create_review_pipeline` 虽可注入 `MemorySaver`，但 API 调用时固定 `with_checkpointing=False`（`python/src/api/main.py:112-115`、`:166-169`）；反馈接口只改内存 `review_store`，没有 `interrupt()`、`interrupt_before`、`Command(resume=...)`。README 与 `docs/interview/*.md` 宣称 interrupt/resume，但代码未实现 |
| 结构化输出 | 各 Agent 直接 `json.loads(content)`（`agents/risk_identification.py` 等），未使用 Pydantic validator、`with_structured_output` 或修复重试；失败时风险 Agent 回退到规则结果，其余 Agent 直接把异常抛给图 |
| 测试与评测 | 仅 3 个测试文件：`test_nlp.py`、`test_parser.py`、`test_rules_engine.py`；没有图、HITL、API、Agent 的自动化测试；README 声称“风险识别准确率 94%”“审查 8 分钟/份”，仓库内没有对应评测集、评测脚本或运行结果 |
| 明显短板 | ① 文档与实现不一致（HITL 是模拟的）；② 指标无法复现；③ 规则全部是中文关键词，缺少国际货物销售场景（Incoterms、信用证、检验、所有权/风险转移等）；④ 三语言实现对于 10 天 MVP 过重；⑤ 无证据偏移与引用校验 |

### 2.2 zihan154896-jpg/intelligent-contract-review

| 维度 | 事实 |
|---|---|
| 仓库 / 更新时间 | 1 Star，2026-09-07 创建并更新；**无 LICENSE** |
| 技术栈 | LangGraph ≥1.2、LangChain ≥1.3、FastAPI、React 19、PostgreSQL、Redis、FAISS、Celery（可选）、JWT/RBAC；39 个 `test_*.py` |
| 工作流节点拆分 | `clause_extraction → parallel_analysis → suggestion → 条件路由 → human_review → process_feedback → complete`。风险识别与合规检查在**同一个节点内**用 `asyncio.gather` 并发，各传一份 `model_copy(deep=True)`，汇合后合并结果与 errors（`python/src/pipeline/graph.py:156-245`）——不是 LangGraph 的并行分支 |
| 规则 / LLM 分工 | YAML 规则 10 条（R001–R008、R010、R011）+ Agent 风险规则 6 组关键词 + 合规规则 4 组 + 必备条款清单（`python/src/rules/definitions/risk_rules.yaml`）；关键词匹配器支持正则与否定语境（`keyword_matcher.py`）。LLM 同时输出 `risk_level`；合并时同一 `(clause_id, risk_type)` 取更高等级，等级分歧或“规则高风险但 LLM 未提”会触发人工复核（`agents/risk_identification.py:263-307`）——**边界是双引擎投票，不是规则单方决定** |
| HITL 实现 | **真实中断**：`create_review_pipeline` 在提供 checkpointer 时编译 `interrupt_before=["human_review"]`（`graph.py:383-418`）；`ReviewService` 用 `aget_state().next` 判断是否暂停，把状态置为 `AWAITING_HUMAN`；`submit_feedback` 通过 `aupdate_state(config, {"human_feedback": ...})` + `ainvoke(None)` 恢复（`services/review_service.py:288-289`）。checkpointer 支持 memory / sqlite / redis，初始化失败降级 memory 并告警（`pipeline/checkpointer.py:43-97`） |
| 结构化输出 | `structured_llm_call`：LLM → `parse_llm_json` → validator（Pydantic schema）→ 失败时把“错误 + 上次原始输出”回传模型，要求“只输出合法 JSON”重试；重试耗尽抛 `StructuredOutputError`，由 Agent 走规则回退（`agents/structured.py:34-89`）。状态里记录 `schema_failures`、`degraded_steps` |
| 测试与评测 | 10 条评测样本（`eval/dataset.json`）；`eval/run_eval.py` 支持 `rules` 与 `full` 两种模式，按 `(样本, risk_type)` 做 micro P/R/F1，并检查多次运行一致性；`eval/metrics.py` 纯函数；Badcase 检测（schema 失败≥2、降级≥2、高风险关键词但 LLM 判 low）、仓储、诊断、`convert_badcase_to_eval.py` 转评测；39 个测试文件覆盖认证、图、规则、报告、Badcase、RAG、追踪等 |
| 明显短板 | ① LLM 参与风险等级判定，不满足本项目“规则决定等级”的硬约束；② React/PostgreSQL/Redis/Celery/JWT/RBAC 对 10 天 MVP 过重；③ 无 LICENSE，不能复用代码；④ 默认 memory checkpointer 不跨进程，README 也承认“持久化取决于实际配置”；⑤ 在节点内改 `state.step_log` 再返回部分字典，进度回调与状态合并耦合较深；⑥ 规则以中文劳动合同/采购合同为主，无国际销售合同专用规则 |

### 2.3 laolaola278-dev/enterprise-contract-review-agent

| 维度 | 事实 |
|---|---|
| 仓库 / 更新时间 | 2 Star，2026-09-21 创建并更新；Apache-2.0 |
| 技术栈 | **纯 Python 标准库为主**，无 LangGraph、无 LangChain、无 LLM；PDF 用 PyMuPDF（可选 pdfplumber），DOCX 用 python-docx，XLSX 用 openpyxl；`ThreadingHTTPServer` 演示 |
| 工作流节点拆分 | 不是 LangGraph 状态图。服务流水线：`document_ingestion → chunk（保留页码/字符偏移）→ 6 类规则检查 → 本地检索/证据引用 → 报告 → human_review 状态 → 审计`；`ContractReviewWorkflow` 用 parser / review_engine / rag_retriever / report_builder 四个工具串起来并记录 `tool_trace`（`src/contract_agent/workflows/contract_review.py:61-141`） |
| 规则 / LLM 分工 | 100% 确定性：6 条规则（截止时间、付款条款、质保与服务、数据安全与隐私、违约与责任、供应商资质），`re.search` 命中即 `found`，未命中即 `missing`，severity 由规则写死；证据是命中位置前后约 90 字符的原文窗口（`src/contract_agent/review_engine.py:20-105`） |
| HITL 实现 | **不是阻塞式中断**：所有结果默认 `needs_human_review=true`，报告状态 `ready_for_human_review` / `needs_human_review`，`human_review.status="pending"`；人工复核发生在系统外部，代码不 resume 流程（`workflows/contract_review.py:100-118`、`service.py:59-63`） |
| 结构化输出 | 无 LLM。`Finding` dataclass + 稳定 dict schema，报告含 `summary`、`findings`、`workflow`、`tool_trace`、`access_policy`、`limitations` |
| 证据引用 | `DocumentChunk.citation` 形如 `文件名:第1页:字符0-342`（`document_ingestion.py:26-42`）；service 为每条命中的 finding 检索 top-2 证据并计算 `citation_coverage`（`service.py:37-51`）；报告可导出 JSON/Markdown/DOCX/XLSX |
| 测试与评测 | 7 个 `test_*.py` 文件，README 声称 24 项通过（未在本次调研中运行）；10 条 JSONL 评测用例（`examples/eval_cases.jsonl`）；`evaluation.py` 计算规则命中的 micro P/R/F1、citation coverage、平均延迟；CI |
| 明显短板 | ① 完全没有语义理解，无法识别“看似合规但实质不利”的条款；② 规则面向招投标/企业采购，不是国际货物销售合同；③ HITL 只是状态标记，没有暂停/恢复；④ 证据窗口是文本截取，规则 finding 与精确 clause span 还没有完全合一；⑤ 已实现功能与 README 中 50-Agent 演示等叙事相比，核心审查部分很薄 |
| 可复用价值 | **高**：文档分页/字符偏移模型、citation 格式、citation coverage 指标、append-only 哈希链审计、确定性评测脚本，均可按 Apache-2.0 复用/改写 |

### 2.4 aurelien-henrion/contract-agent

| 维度 | 事实 |
|---|---|
| 仓库 / 更新时间 | 0 Star，2026-10-21 创建并更新；MIT；Python ≥3.13 |
| 技术栈 | LangGraph ≥1.2.16、LangChain ≥1.6、Pydantic ≥2.14、Chroma、Streamlit、Azure OpenAI / Anthropic、pytest；60 份 CUAD 合同（`data/cuad_subset`）；11 个测试文件 |
| 工作流节点拆分 | ReAct 图：`START → agent →（无 tool call）END`；`agent → tools → agent` 处理只读工具；`agent → human_review`（检测到写工具 `save_contract_record`）→ `interrupt()` → `Command(resume=decision)` → 执行写入 → 回到 agent（`src/contract_agent/graph.py:76-165`）；`RECURSION_LIMIT=25` |
| 规则 / LLM 分工 | LLM 只输出 `ExtractedFields`（简单 JSON 类型；缺失为 null；每个非空字段给一条原文引文）；Python 负责：日期/期限解析（`calculations.py`）、引文是否真的出现在合同中、期限可解析性、自动续约与续约期限一致性、永久合同与到期日冲突、到期日早于生效日、当事人缺失 → 全部 doubtful 字段进 `to_verify`（`extraction.py:104-149`）。**LLM 不做日期算术，不做最终记录定型** |
| HITL 实现 | `human_review` 节点内 `interrupt({"type": "approval_request", "proposals": [...]}, response_schema=ReviewDecision)`；使用 checkpointer 持久化；resume 用 `Command(resume={"action": "approve|edit|reject", ...})`；关键安全设计：**interrupt 之前只做纯读取与 Python 重校验**（因为 resume 会从节点顶部重跑），所有写入都在 interrupt 之后；编辑由复核人作为最终权威，写入的记录就是复核人看到的已校验记录（`graph.py:108-148`、`207-250`） |
| 结构化输出 | 两层 schema：`ExtractedFields`（LLM 可约束的简单类型）→ Python 校验生成 `ContractRecord`（date/duration 已解析、evidence 已核验、`to_verify` 已标记）（`schema.py:1-130`）；`with_structured_output(method="json_schema")`（`llm.py`） |
| 测试与评测 | 11 个测试文件；`tests/test_graph.py` 用 `ScriptedChatModel` 脚本化 LLM，断言 `__interrupt__`、`state.next == ("human_review",)`、审批前 registry 与 audit 均为空、`Command(resume=approve)` 后只写一次且 actor 正确（`tests/test_graph.py:132-169`）。评测：30 份 CUAD 合同，**全字段准确率 88%**（空记录基线 46%）；当事人召回 95%；`to_verify` 标记率 8%；未标记字段准确率 91%，已标记 62%；抽取失败 0；成本 $0.2401；Agent 问答 14 题答案/工具选择均 100%（`evaluation/results/extraction.md`、`agent.md`） |
| 明显短板 | ① 聚焦“字段抽取 + 日期计算 + 写库审批”，没有风险规则分级；② CUAD 是美国 SEC 商业合同，不是国际货物销售合同；③ Python ≥3.13、Azure 部署脚本、Chroma 对 10 天 MVP 偏重；④ `effective_date` 69%、`expiration_date` 70%，说明日期字段仍不可靠；⑤ 不是“风险预审”产品形态 |
| 可复用价值 | **最高**：双 schema + Python 重校验、引文核验、HITL 安全写入门、脚本化 LLM 的 HITL 测试、CUAD 评测口径（gold / baseline / flag rate / cost） |

### 2.5 Harvey-cream/Langchain_DG

| 维度 | 事实 |
|---|---|
| 仓库 / 更新时间 | 29 Star，2026-10-12 更新；**无 LICENSE**；407 个 tree 条目，前后端 + Docker + 迁移 + 测试 |
| 技术栈 | LangGraph、FastAPI、PostgreSQL、pgvector、React、对象存储、MCP、SSE；Interview Agent 使用 PostgreSQL checkpointer；Contract 产品线有独立 Review Graph |
| 工作流节点拆分 | Contract Review Graph：`prepare_windows → retrieve_baseline → agent_decide（有界只读 Tool Calling）→ tools → agent_decide ... → generate_findings →（还有窗口？retrieve_baseline : quality_gate）→ END`（`products/contract/agents/review/graph.py:23-42`）。按条款窗口分批，控制上下文预算；`ReviewLimits` 限制工具轮数 0–4、调用数 0–8、超时、recursion_limit（`state.py:108-135`） |
| 规则 / LLM 分工 | LLM 生成风险建议；Python **Quality Gate** 做确定性校验：Pydantic schema、条款归属/版本、证据必须精确定位到原文（仅允许 Unicode 分解与空白规范化，禁止模糊相似/标点删除/数字转换）、RAG 引用必须来自本次召回片段、引用 policy 必须版本/归属/适用范围合法、**风险等级不得低于所引用企业规则的 severity**、禁止出现“已批准/已修改合同/最终合同已”等越权表述、禁止引用不存在的 ContractChange、保守去重、保留警告（`products/contract/quality.py:29-342`、`schemas/analysis.py:68-143`） |
| HITL 实现 | **Contract Review Graph 明确不启用 checkpoint / interrupt-resume**（README 第 15 行）；人工批准、Revision、Diff、谈判属于路线图，不是已交付能力。Interview Agent 有独立 checkpoint/HITL，但不属于合同审查链路 |
| 结构化输出 | `ReviewResult` / `RiskFinding`：`extra="forbid"`、非空校验、长度上限、`related_clause_ids` 最多 8、`policy_ids` 最多 12、`reference_citations` 最多 8；Quality Gate 再做真实原文定位与等级下限校验 |
| 测试与评测 | 15 个 `test_*.py`（contract 目录）；有质量门/回归测试与 trace/references；README 明确“来源校验和少量真实模型 smoke 不等于全面法律质量评估”，没有公开准确率数字 |
| 明显短板 | ① 平台级复杂度（Postgres、对象存储、MCP、前端、迁移）远超 10 天 MVP；② Contract Review 没有 HITL；③ 无 LICENSE，不能复制代码；④ 业务状态与 Agent checkpoint 分离、窗口化、预算控制等设计需要较大工程量；⑤ 质量门只验证“来源/协议/一致性”，不证明法律结论正确 |
| 可复用价值 | **高（仅设计）**：Workflow First / Agent Second、确定性 Quality Gate 的具体检查项、证据精确定位、等级下限、越权表述拦截、保守去重、引用快照与 trace |

### 2.6 kashifumair125/ContractSentinel

| 维度 | 事实 |
|---|---|
| 仓库 / 更新时间 | 0 Star，2026-05-26 更新；**无 LICENSE** |
| 技术栈 | 单文件 FastAPI（`backend/main.py` 约 19.5 KB）+ 静态 HTML；httpx；pdfplumber；Cerebras `llama3.1-8b`（Agent 1/2）、Groq `llama-3.3-70b-versatile`（Agent 3/4） |
| 工作流节点拆分 | 不是图/状态机：四个 prompt 顺序调用：条款抽取 → 企业政策检查 → 风险评分 → redline 生成；无状态持久化、无重试状态机 |
| 规则 / LLM 分工 | 企业政策标准直接写在 prompt 里（付款 Net-30、IP 归属、责任上限 2x、终止通知 30 天等），合规/严重级别完全由 LLM 判定；没有确定性规则引擎 |
| HITL 实现 | 无 |
| 结构化输出 | prompt 要求 JSON；`safe_json_parse` 用正则抓 `{...}` / `[...]`，硬编码替换 `"AS IS"` 等引号；失败打印原始输出并返回 `None`；无 Pydantic schema、无修复重试、无证据核验 |
| 测试与评测 | 无测试、无评测集、无 gold label |
| 明显短板 | ① 典型的“prompt 即规则”，不可回归、不可解释；② 模型/供应商分裂且有速率限制 sleep/递归重试；③ JSON 修复靠硬编码；④ 无 HITL、无审计；⑤ 无证据引用；⑥ 无 LICENSE |
| 可复用价值 | 基本没有可直接复用的代码；仅可参考其“条款 → 政策 → 风险 → redline”的产品叙事，但实现方式应作为反例 |

### 2.7 tomasonjo-labs/legal-tech-chat（替代项目）

| 维度 | 事实 |
|---|---|
| 仓库 / 更新时间 | 163 Star / 36 Fork，2025-06-03 更新；MIT |
| 技术栈 | LangGraph ≥0.3、LangChain、Neo4j（`langchain-neo4j`）、Gemini embeddings、FastAPI、React；研究目录含 CUAD 抽取 benchmark 与导入 notebook |
| 工作流节点拆分 | 最小 ReAct：`assistant → tools → assistant`，`tools_condition` 路由；只有一个 `ContractSearchTool`（`backend/agent.py:8-42`） |
| 规则 / LLM 分工 | LLM 决定调用工具与回答；工具参数用 Pydantic 建模（`MonetaryValue`、`Location`），检索层把日期/金额/当事人/合同类型等过滤翻译成 Cypher + 向量相似度（`backend/tools/contract_search_tool.py`）；没有规则引擎、没有风险分级 |
| HITL 实现 | 无 |
| 结构化输出 | 工具入参 Pydantic；最终回答是自然语言；无输出 schema、无引用校验 |
| 测试与评测 | `research/benchmark` 有抽取 benchmark notebook 与 `extraction_benchmark.csv`（511 行）；没有接入 CI 的自动化评测 |
| 明显短板 | ① Neo4j/图数据库依赖重；② 面向合同问答，不是审查工作流；③ 无 HITL、无规则边界、无引用核验；④ 数据导入与图模型需要额外工程 |
| 可复用价值 | Pydantic 工具参数建模、合同字段到 Cypher 过滤的映射思路；对 MVP 非必需 |

### 2.8 neo4j-product-examples/graphrag-contract-review（替代项目）

| 维度 | 事实 |
|---|---|
| 仓库 / 更新时间 | 122 Star / 28 Fork，2024-11-02 更新；Apache-2.0 |
| 技术栈 | **Semantic Kernel**（不是 LangGraph）、Neo4j、OpenAI、Streamlit；3 份 CUAD PDF |
| 工作流节点拆分 | 四阶段离线流水线：① LLM 按 40+ 问题抽取合同信息为 JSON；② 建 Neo4j 知识图谱；③ Python/Cypher 检索函数；④ Semantic Kernel Q&A Agent；不是带条件边/HITL 的图 |
| 规则 / LLM 分工 | LLM 做抽取与问答；Python/Cypher 做日期、金额、聚合等确定性查询；没有风险规则引擎 |
| HITL 实现 | 无 |
| 结构化输出 | `AgreementSchema.py` 定义合同图 schema；抽取 prompt 要求 JSON；无效 JSON 落 `data/debug`；无 schema 修复重试 |
| 测试与评测 | 仅 `test_agent.py` 基础脚本；无 gold 评测、无 CI |
| 明显短板 | ① GraphRAG + Neo4j + Semantic Kernel 与指定技术栈不符；② 只处理 3 份合同；③ 无风险规则、无 HITL、无评测；④ 2024 年后未更新 |
| 可复用价值 | “先结构化抽取，再用确定性查询/计算回答”的思路；合同图 schema 可参考，但不建议引入图数据库 |

---

## 3. 项目对比表（五个指定维度）

| 项目 | 节点拆分粒度 | 规则 / LLM 边界 | HITL 深度 | 评测方法 | 可复用代码模块（许可证） |
|---|---|---|---|---|---|
| bcefghj | 4 个 Agent 顺序流水线；条件边只决定是否进 human_review | 规则 8 条 + LLM 风险分析；**LLM 也判等级**，取高者 | **模拟**：节点只改状态，未真正中断；API 关闭 checkpoint | 3 个单元测试；94%/8 分钟无评测数据支撑 | 规则 DSL 框架、文档解析（Apache-2.0） |
| zihan | 4 Agent；风险与合规在一个节点内用 `asyncio.gather` 并行；条件边 + `interrupt_before` | YAML 规则 + LLM 双引擎；LLM 判等级，冲突取高并触发人工 | **真实**：checkpoint（memory/sqlite/redis）+ `interrupt_before` + update_state/ainvoke(None) | 10 条评测集，micro P/R/F1；rules/full 双模式；Badcase→评测；39 测试 | 结构化修复重试、checkpointer 工厂、降级标记、Badcase 管线（**无 LICENSE，仅思想**） |
| laolaola | 非 LangGraph；ingestion→chunk→6 规则→检索→报告→人工状态 | **100% 规则，无 LLM** | 状态标记，非阻塞、不可 resume | 10 条 JSONL；规则 P/R/F1 + citation coverage + 延迟；7 测试文件 | 分页/字符偏移、citation、审计、评测（Apache-2.0） |
| aurelien | ReAct：agent ↔ tools；写工具触发 human_review | LLM 只抽取；Python 解析日期、核验引文、一致性、`to_verify`；**无风险等级** | **真实** `interrupt()` + checkpointer + `Command(resume=...)`；审批前纯读取，审批后才写入；edit 以复核人为权威 | CUAD 30 份：全字段 88%（基线 46%）、flag 8%、成本；Agent 14/14；11 测试（含脚本化 LLM 的 HITL 测试） | 双 schema + `check_record`、HITL gate、测试 fake、评测口径（MIT） |
| Harvey | Review Graph 窗口化 + 有界 ReAct + quality_gate；无 HITL | LLM 生成风险；Python Quality Gate 校验证据/引用/等级下限/越权表述 | **Review 图无 checkpoint/interrupt**；人工批准是路线图 | 15 测试；质量门回归；无公开准确率 | Quality Gate 检查项、证据定位、等级下限、去重（**无 LICENSE，仅设计**） |
| Sentinel | 4 个 prompt 顺序调用，无图 | 政策写在 prompt；LLM 判合规/严重级别；无规则引擎 | 无 | 无 | 无可复用代码（无 LICENSE） |
| legal-tech-chat | 最小 ReAct（1 个检索工具） | LLM 决策 + Cypher/向量检索；无规则分级 | 无 | benchmark notebook / CSV，未入 CI | Pydantic 工具参数（MIT） |
| graphrag-contract-review | 四阶段离线 GraphRAG；非 LangGraph | LLM 抽取 + Python/Cypher 查询；无风险规则 | 无 | 1 个基础测试；无 gold | 合同图 schema 思路（Apache-2.0） |

---

## 4. 直接可借鉴的 5 个模式（具体到可落地）

### 模式 A：LLM 只产出“提议”，Python 负责把提议变成可信记录（来自 aurelien）

**做法**
- 定义两层模型：
  - `ExtractedFields`：只含 string / bool / list / null，供 LLM 的结构化输出模式约束；
  - `ContractRecord`：Python 解析后的强类型记录（date、duration、evidence、`to_verify`）。
- Python 复核项（`extraction.py:104-149`）：
  1. 每条 evidence 引文必须真的出现在合同文本中（先做小写 + 空白折叠，引文至少 8 字符）；
  2. 除 `document_name` / `parties` 外，每个非空字段必须有已核验引文；
  3. 期限必须能被 `parse_duration` 解析，否则进 `to_verify`；
  4. 自动续约必须有续约期限；永久合同不得同时有到期日/初始期限；到期日不得早于生效日；当事人不得为空；
  5. 所有 doubtful 字段只标记，不猜。
- **审批前用同一套 `check_record` 再校验一次**，因为 LLM 在工具调用里会重新“打字”记录，不能信任它仍是最初校验过的版本。

**对本项目的落地**
- 我们的 `ClauseExtraction` 同样分两层：`LLMExtraction`（null 友好）→ `ValidatedExtraction`（Python 解析金额/日期/期限、核验引文、生成 `to_verify`）。
- 规则引擎读取 `ValidatedExtraction`，但**规则判定也允许只依赖条款原文**，避免 LLM 抽取失败时规则失效。
- HITL 展示给复核人的必须是“已由 Python 复核过”的记录，而不是 LLM 原始 JSON。

### 模式 B：HITL 用 `interrupt()` + checkpointer + `Command(resume=...)`，并保证“审批前零写入”（来自 aurelien，zihan 提供另一种 resume 方式）

**做法**
- 在节点内 `interrupt(payload, response_schema=...)`，图暂停，状态由 checkpointer 保存；resume 用 `Command(resume=decision)`（aurelien `graph.py:131-140`）。
- 由于 LangGraph resume 会**从节点顶部重新执行**，`interrupt()` 之前只能做纯读取/纯校验，所有有副作用的写入放到 `interrupt()` 之后（aurelien `graph.py:108-148`）。
- 测试必须断言：
  - 暂停时 `__interrupt__` 存在、`state.next == ("human_review",)`；
  - 审批前 registry/audit 为空、LLM 没有被再次调用；
  - approve 后只写一次，actor 是复核人；
  - reject 不写，edit 以复核人版本为准（aurelien `tests/test_graph.py:132-169`）。
- zihan 的替代方式：`interrupt_before=["human_review"]` + `aupdate_state` + `ainvoke(None)`；也可以工作，但本项目按 md 要求使用节点内 `interrupt()`，语义更明确。

**对本项目的落地**
- `thread_id = review_id`；MVP 用 SQLite checkpointer（持久化到 `.data/checkpoints.sqlite`），测试用 `InMemorySaver`。
- HITL payload 包含：风险规则命中、等级、理由、原文引文与偏移、抽取字段、`to_verify` 列表。
- 审批动作：`approve` / `request_changes` / `reject` / `timeout`；复核人若覆盖等级，单独存 `hitl.overrides`，**不修改规则原始输出**，报告同时展示“规则等级”和“人工覆盖”。

### 模式 C：证据引用必须可定位到“文件:页码:字符偏移”，并单独度量 citation coverage（来自 laolaola + Harvey）

**做法**
- laolaola 的 `DocumentChunk` 在切片时同时保留 `source / page_number / start_offset / end_offset`，生成 `文件名:第N页:字符start-end` 的 citation（`document_ingestion.py:26-42`）；service 为每条命中 finding 检索 top-2 证据，计算 `citation_coverage = 有证据的 finding 数 / 总 finding 数`（`service.py:37-51`）。
- Harvey 的 `locate_excerpt` 更严格：先精确 `str.find`；失败后只允许 Unicode NFD 与空白规范化，**禁止模糊相似度、标点删除、数字转换、否定词删除**；定位不到就抛 `ReviewQualityError`（`quality.py:29-74`）。
- Harvey 还把“风险等级不得低于所引用 policy 的 severity”作为硬校验（`schemas/analysis.py:127-132`），并拦截“已批准/已修改合同”等越权表述（`quality.py:254-268`）。

**对本项目的落地**
- 文档解析阶段就建立 `pages[] + global text + char offsets`；条款切分记录 `start/end`；每条规则 finding 记录 `matched_text` 与 span。
- 报告每条风险输出 `citation = "{file}:p{page}:{start}-{end}"`，Streamlit 可点击/高亮原文。
- LLM 解释中的 `quote` 必须能在对应条款中精确定位；否则降级为规则 `reason`，并标记 `explanation_grounded=false`。
- 评测中单独报告 `citation_coverage` 与 `explanation_grounded_rate`，不把它们混进“准确率”。

### 模式 D：用确定性 Quality Gate 约束 LLM 输出，而不是靠 prompt 自觉（来自 Harvey）

**做法**
- Quality Gate 不是第二个 Agent，也不判断法律结论是否正确；它只检查：
  - schema 合法（`extra="forbid"`、非空、长度上限）；
  - 条款 ID 属于本版本、不得重复/自引用；
  - 证据必须定位到条款真实原文；
  - 引用必须来自本次召回的片段，且片段属于该条款；
  - 风险等级不得低于政策等级；
  - 禁止越权表述（已批准、已修改合同、最终合同已…）；
  - 同条款/同类型/同证据的重复项保守去重，不同判断保留并告警；
  - 报告里写明 limitation：“仅验证来源、协议和内部一致性，不证明风险判断或法律结论正确；建议未经人工批准。”
- 这套 gate 的成本很低，但能挡住大部分“看起来像真的”幻觉。

**对本项目的落地**
- 增加 `validate_explanation` 纯 Python 节点/函数：
  - `rule_id` 必须存在；
  - `risk_level` 必须等于规则引擎输出（LLM 无权改级）；
  - `quote` 必须属于该条款原文；
  - 禁止“合同无效/违法/已批准/已修改”等超出规则依据的断言；
  - 解释缺失或校验失败 → 用规则 `reason` 兜底，状态记 `degraded_steps`。
- 报告末尾固定输出“本报告为预审辅助，不构成法律意见；红色风险必须人工确认”。

### 模式 E：结构化输出“修复重试” + 明确降级 + Badcase 转回归（来自 zihan，laolaola/aurelien 提供评测口径）

**做法**
- zihan `structured_llm_call`：第一次解析/校验失败后，把错误信息与原始输出回传给模型，要求只输出合法 JSON；最多 1 次修复；仍失败则抛错，由 Agent 回退规则结果并记录 `schema_failures` / `degraded_steps`（`agents/structured.py:34-89`）。
- Badcase 检测不是靠人工翻日志：schema 失败≥2、降级步骤≥2、合同含高风险关键词但 LLM 判 low，都会产生信号（`services/bad_case_detector.py:16-56`）；Badcase 可转成评测用例（`scripts/convert_badcase_to_eval.py`）。
- 评测算 micro P/R/F1 与一致性（`eval/metrics.py`、`eval/run_eval.py`），规则模式无需 LLM Key，可作为 CI 回归门槛。
- aurelien 的评测口径值得照搬：报告准确率时同时给“空记录基线”，并单独给 `to_verify` 标记率、未标记/已标记准确率、失败数、token 与成本（`evaluation/results/extraction.md`）。

**对本项目的落地**
- LLM 抽取节点：`with_structured_output` + Pydantic 校验 + 1 次纠错重试；仍失败 → 所有字段置 null + `extraction_status="degraded"`，规则照常跑。
- 解释节点：失败 → 规则理由兜底，不阻塞报告。
- 评测：规则模式纯确定性，进 CI；全链路模式用固定 key 手动跑；每个 Badcase 落一条 JSON fixture，修复后必须回归。
- 禁止在 README/答辩里写“准确率 94%”这类无出处数字；所有指标必须能从 `eval/results/*.json` 复现。

---

## 5. 明确不借鉴的部分及理由

| 不借鉴内容 | 来源 | 理由 |
|---|---|---|
| “文档写 interrupt、代码只改状态”的伪 HITL | bcefghj | 无法真正暂停/恢复，评审现场演示会露馅；我们必须用 `interrupt()` + checkpointer，并用测试断言暂停态 |
| 无评测数据的 94% / 8 分钟指标 | bcefghj | 仓库内没有评测集与结果；本项目所有指标必须可复现，否则不写 |
| 三语言（Python/Java/Go）+ Next.js 前端 | bcefghj | 10 天 MVP 只需要 Python + FastAPI + Streamlit；多语言实现不增加评审价值 |
| LLM 参与风险等级判定、双引擎“取更高等级” | bcefghj、zihan | 与硬约束冲突；等级必须由可枚举、可回归的 Python 规则决定，否则无法解释“为什么是红/黄” |
| React + PostgreSQL + Redis + Celery + JWT/RBAC + 39 个测试的全栈应用层 | zihan | 对 10 天 MVP 过重；我们只需要上传、运行、展示报告三个功能 |
| 在单个节点里用 `asyncio.gather` 模拟并行分支 | zihan | 状态合并、错误合并、进度回调耦合；MVP 顺序执行足够，且 LangGraph 并行分支会增加 HITL/状态调试成本 |
| 无 LICENSE 仓库的代码复制 | zihan、Harvey、Sentinel | 默认保留全部权利；只能借鉴设计，不能复制源文件 |
| “规则引擎 100% + 零 LLM”的产品形态 | laolaola | 我们确实需要 LLM 做条款要素抽取与风险解释；纯规则无法覆盖语义条款，也无法生成可读解释 |
| 把人工复核做成一个 `pending` 状态字段 | laolaola | 不是阻塞门，无法保证红风险必须人工确认后才能出报告 |
| Azure OpenAI / Azure Container Apps / Python 3.13 / Chroma 的部署栈 | aurelien | 环境不支持 Azure 全链路；Python 3.13 也不是本地默认；MVP 用 OpenAI 兼容接口 + SQLite checkpointer + 本地文件即可 |
| CUAD 字段口径直接当成本项目需求 | aurelien、legal-tech-chat、graphrag | CUAD 是美国 SEC 商业合同；本项目是国际货物销售合同，需要 Incoterms、信用证、检验、所有权/风险转移等规则 |
| Postgres + 对象存储 + MCP + SSE + 50-Agent 平台 | Harvey | 工程量远超 10 天；Contract Review 本身还没有 HITL，照搬叙事会本末倒置 |
| 把企业政策写进 prompt、用正则抠 JSON、无 schema/无测试 | Sentinel | 不可回归、不可解释、无法审计；应作为反例 |
| Neo4j / GraphRAG / Semantic Kernel / 知识图谱 | legal-tech-chat、graphrag | 与指定技术栈不符，增加数据导入与运维成本；MVP 不需要图数据库 |
| “为了多 Agent 而多 Agent”的 Supervisor 架构 | 多个项目 | 本任务是确定性流水线 + 两个 LLM 节点 + 一个 HITL 门；Supervisor 只会增加不可控性 |
| 无来源的“业界领先/很强大”式描述 | 多个 README | 评审需要可验证技术事实；文档只写代码里能指到的行为与指标 |

---

## 6. 对本项目架构的建议（已落为 ADR-001~006）

> 以下是**调研后的建议草案**。它已在第二阶段落为 ADR-001 ~ ADR-006：图结构、HITL、规则/LLM 边界、持久化、文档解析、环境依赖；其中 ADR-001~005 仍待用户确认，确认后才开始代码。

### 6.1 设计原则

1. **规则先行，LLM 后置**：风险等级只由 Python 规则产生；LLM 只做“条款要素抽取”和“风险解释”。
2. **每个结论可追溯**：规则输出 `rule_id + risk_level + reason + evidence span`；报告引用 `文件:页码:字符偏移`。
3. **失败不崩溃，失败要显式降级**：LLM 超时/非 JSON、空合同、规则异常、HITL 超时都有明确路径与状态标记。
4. **HITL 是门，不是状态字段**：红色风险必须经过 `interrupt()` 暂停与人工 resume；未审批不得标记为“已通过”。
5. **Workflow First**：图节点是确定性流水线；不引入 Supervisor、不让 Agent 自由决定流程。

### 6.2 高层图草案

```text
                         ┌──────────────────────────────┐
                         │            START             │
                         └──────────────┬───────────────┘
                                        ▼
                         ingest_document（纯 Python）
                    解析 PDF/DOCX/TXT → 规范文本 + pages + 字符偏移
                                        ▼
                         segment_clauses（纯 Python）
                    条款切分 → clause_id/title/text/page/start/end
                                        ▼
                         extract_fields（LLM，结构化输出）
                    金额/日期/期限/交付/付款/检验/违约/管辖… 缺失=null
                                        ▼
                         validate_extraction（纯 Python）
                    引文核验/日期期限解析/一致性 → to_verify
                                        ▼
                         evaluate_rules（纯 Python）
                    rule_id / red|yellow|pass / reason / evidence span
                                        ▼
                         route_by_risk（条件边）
                    ┌───────────────┴────────────────┐
              存在 red 风险                     无 red 风险
                    ▼                                │
        human_review（interrupt + checkpointer）    │
        payload：red findings + 证据 + 抽取字段      │
        resume：Command(resume=HitlDecision)        │
                    └───────────────┬────────────────┘
                                    ▼
                         explain_risks（LLM）
              只解释 + 引用原文；等级由规则固定，LLM 不得改级
                                    ▼
                         build_report（纯 Python）
              Pydantic Report → JSON / Markdown / Streamlit 展示
                                    ▼
                                   END
```

**异常边（建议实现为节点内降级 + 状态标记，而不是额外主路径）**

| 异常 | 处理 |
|---|---|
| 合同为空 / 格式不支持 / 超过大小上限 | 进入图前直接 4xx，不创建 review |
| 文档解析失败 | 返回明确错误；若仅部分页失败，标记 `degraded_steps` 并继续 |
| LLM 超时 / 非 JSON / schema 不符 | 1 次修复重试；仍失败 → 抽取字段全 null + `extraction_status=degraded`，规则仍跑 |
| 规则执行异常 | **Fail-closed**：该条款标记 `yellow` + “规则执行异常，需人工确认”，绝不静默 `pass` |
| 解释生成失败/引文核验失败 | 用规则 `reason` 作为解释，`explanation_grounded=false`，报告仍生成 |
| HITL 超时 | 以 `timeout` 决策恢复；报告状态 `unreviewed_red_risk`，绝不自动 approve |
| checkpointer 不可用 | 开发环境降级 MemorySaver 并告警；生产/演示要求 SQLite，否则 HITL 重启即丢 |

### 6.3 状态 schema 草案（字段级别）

```python
# 设计草案，不是最终代码
class Page(BaseModel):
    page_number: int
    text: str
    start_offset: int  # 全文全局偏移


class Clause(BaseModel):
    clause_id: str
    title: str
    text: str
    page: int | None
    start: int  # 全文全局偏移
    end: int
    clause_type: str | None


class Evidence(BaseModel):
    quote: str
    start: int | None
    end: int | None
    grounded: bool


class FieldExtraction(BaseModel):
    clause_id: str
    fields: dict[str, str | float | bool | None]  # 未提及=null
    evidence: list[Evidence]
    uncertain_fields: list[str]


class RuleFinding(BaseModel):
    rule_id: str
    clause_id: str
    risk_level: Literal["red", "yellow", "pass"]
    reason: str
    matched_text: str | None
    evidence_start: int | None
    evidence_end: int | None


class HitlDecision(BaseModel):
    action: Literal["approve", "request_changes", "reject", "timeout"]
    reviewer: str
    comment: str | None
    overrides: dict[str, str]  # 人工覆盖单独记录，不修改规则原始等级


class RiskExplanation(BaseModel):
    clause_id: str
    rule_id: str
    summary: str
    quote: str | None
    recommendation: str | None
    grounded: bool


class ContractReviewState(BaseModel):
    review_id: str
    thread_id: str
    status: Literal[
        "running",
        "awaiting_human",
        "approved",
        "rejected",
        "completed",
        "degraded",
        "unreviewed_red_risk",
        "failed",
    ]
    source_filename: str
    raw_text: str
    pages: list[Page]
    clauses: list[Clause]
    extractions: list[FieldExtraction]
    findings: list[RuleFinding]
    hitl: HitlDecision | None
    explanations: list[RiskExplanation]
    degraded_steps: set[str]
    errors: list[str]
    report: Report | None
    model_id: str | None
    prompt_version: str
    timings: dict[str, float]
```

### 6.4 HITL 具体契约

- `thread_id = review_id`；图编译时注入持久 checkpointer（MVP：`AsyncSqliteSaver`）。
- 仅当 `any(f.risk_level == "red" for f in findings)` 时进入 `human_review`。
- `interrupt()` 之前：只读取 state / 纯函数重校验，**不写数据库、不发外部请求**。
- `interrupt()` 之后：按 `HitlDecision` 更新报告状态并落库；`approve` 才能把报告标为“已人工确认”；`reject` 记录拒绝理由；`request_changes` 保留草稿并等待新的输入（MVP 可先只记录，不自动重跑）。
- 超时：`hitl.requested_at` + 配置的超时时间；由后台 sweeper 或 `GET /review/{id}` 的惰性检查触发 `Command(resume={"action":"timeout"})`。超时报告标 `unreviewed_red_risk`，绝不当成通过。
- 幂等：resume 前检查状态，已处理过的 review 不再重复应用决策。

### 6.5 规则 / LLM 边界（硬约束）

| 能力 | Python 规则 | LLM |
|---|---|---|
| 风险等级 red/yellow/pass | ✅ 唯一来源 | ❌ 禁止输出等级 |
| rule_id / reason / evidence span | ✅ 规则产生 | ❌ 不参与 |
| 条款要素抽取（金额、日期、期限、Incoterms、付款方式等） | ❌ | ✅ 输出 JSON，缺失 null |
| 引文核验、日期/期限解析、一致性检查 | ✅ | ❌ |
| 风险解释、修改建议 | ❌ | ✅ 必须引用原文，经 Python 校验 |
| 最终报告结论 | ✅ 汇总规则 + 人工决策 | ❌ 不得宣称“合同有效/无效/已批准” |

**补充**：规则匹配应优先基于条款原文与标准化字段；LLM 抽取失败时，规则仍应能对原文做关键词/正则/数值检查，保证核心风险不漏。

### 6.6 评测与测试建议（10 天可执行版）

| 层次 | 内容 | 是否进 CI |
|---|---|---|
| 单元测试 | 文档解析、条款切分、规则命中/未命中/边界、日期期限解析、引文定位 | ✅ 无 LLM |
| 图测试 | 用 `FakeChatModel` 脚本化 LLM 输出，断言节点顺序、条件边、降级路径 | ✅ 无真实 LLM |
| HITL 测试 | 断言 `__interrupt__`、`state.next`、审批前无写入、approve 只写一次、reject 不写、timeout 不自动通过 | ✅ 无真实 LLM |
| 规则评测 | 20–30 份合同，条款级 gold `rule_id`；micro P/R/F1；零容忍误报的规则单独看 | ✅ 确定性 |
| 全链路评测 | 抽取字段准确率（含 null）、引文支撑率、citation coverage、解释改级率、降级率、p95 延迟、token 成本 | 手动/有 Key |
| Badcase 回归 | 每个失败样本转 JSON fixture，修复后必须回归 | ✅ |

**报告口径**：同时给 baseline（空抽取/全 pass），不要只报一个好看的准确率；所有数字附命令、模型名、样本数、日期。

---

## 7. 对后续阶段的直接影响

1. **ADR-001 图结构选型**：采用“确定性主干 + 一个条件边 + 一个 HITL 节点”，不采用 Supervisor；需要说明为什么顺序执行而非并行。
2. **ADR-002 HITL 实现方式**：采用节点内 `interrupt()` + checkpointer + `Command(resume=...)`；需要写清“resume 会重跑节点顶部”“审批前零写入”“超时不自动通过”。
3. **ADR-003 规则/LLM 边界**：规则唯一决定等级；LLM 只抽取与解释；需要写清引文校验、失败降级、禁止改级。
4. **ADR-004（候选）状态持久化与超时**：SQLite checkpointer、thread_id、pending 状态、sweeper。
5. **ADR-005（候选）文档解析与证据模型**：page/char offset、条款 span、citation 格式。

---

## 8. 复现与证据索引

### 8.1 本次使用的实时查询方式

```powershell
# 元数据
curl.exe -s "https://api.github.com/repos/{owner}/{repo}"

# 仓库文件树
curl.exe -s "https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"

# 默认分支快照（git clone 被网络重置时的替代）
curl.exe -sL "https://codeload.github.com/{owner}/{repo}/tar.gz/refs/heads/{branch}" -o repo.tar.gz
tar.exe -xzf repo.tar.gz -C <temp-dir>
```

> 快照仅用于调研阅读，未将任何第三方代码复制进本项目。

### 8.2 关键证据文件

| 结论 | 证据文件 / 行号 |
|---|---|
| bcefghj 的 human_review 不调用 interrupt | `python/src/pipeline/graph.py:42-52`；`python/src/api/main.py:112-115`、`:166-169` |
| bcefghj 无评测数据、仅 3 个测试 | `python/tests/` 目录；README 中的 94% 声明 |
| zihan 真实 interrupt_before 与 resume | `python/src/pipeline/graph.py:383-418`；`python/src/services/review_service.py:288-289` |
| zihan 结构化修复重试 | `python/src/agents/structured.py:34-89` |
| zihan LLM 参与风险等级 | `python/src/agents/risk_identification.py:157-173`、`:263-307` |
| laolaola 页码/字符偏移 citation | `src/contract_agent/document_ingestion.py:26-42` |
| laolaola citation coverage / 人工状态 | `src/contract_agent/service.py:37-51`、`:59-63` |
| aurelien LLM 提议 + Python 复核 | `src/contract_agent/extraction.py:104-149`；`schema.py:41-130` |
| aurelien interrupt + 审批前纯读取 | `src/contract_agent/graph.py:108-148` |
| aurelien HITL 测试断言 | `tests/test_graph.py:132-169` |
| aurelien CUAD 评测数字 | `evaluation/results/extraction.md`、`evaluation/results/agent.md` |
| Harvey 明确 Review Graph 无 checkpoint/interrupt | `README.md:15` |
| Harvey Quality Gate 证据精确定位/等级下限/越权拦截/去重 | `products/contract/quality.py:29-342`；`schemas/analysis.py:68-143` |
| Harvey Review Graph 窗口化 + 有界 ReAct | `products/contract/agents/review/graph.py:23-42`；`state.py:108-135` |
| Sentinel 正则抠 JSON、无 schema | `backend/main.py:18-54` |
| Sentinel prompt 内政策与 LLM 判级 | `backend/main.py:207-249` |
| legal-tech-chat 最小 ReAct + 单检索工具 | `backend/agent.py:8-42` |
| graphrag 四阶段非 LangGraph | `README.md:15-19` |

### 8.3 调研限制

- Star 数不能代表质量，仅用于说明项目量级；部分仓库 Star 可能被人为推广。
- 未逐个运行所有仓库的测试（依赖、API Key、数据库条件不具备）；测试相关描述以仓库文件与 README 为准，已明确区分“文件存在”与“已运行验证”。
- 未对 zihan/Harvey/Sentinel 的无许可证代码做任何复制；后续如复用 Apache-2.0/MIT 项目的代码，会在文件头与 `04_HANDOVER.md` 中保留来源与许可证说明。
- LLM 抽取/风险规则的法律正确性无法由开源仓库证明；本项目必须用自己的评测集验证。
