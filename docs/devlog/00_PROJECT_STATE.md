# 项目状态快照

> 更新时间：2026-10-27（第三阶段第 6 步完成）
> 当前阶段：**第三阶段（代码实现）第 6 步：FastAPI + Streamlit 已可用**
> 项目目录：`d:\A项目\Agent_Alex外贸合同智审助手`
> Git：提交 `cf0fd63`、`71e8a9d`、`750cca3`、`625e9bd`（第 3 步）、`e41d235`（第 4 步），第 5/6 步提交见 `git log`
> 范围变更：2026-10-27 用户明确「可以做 rag 和多 agent」→ **ADR-007**；第 5 步按 **ADR-008** 落地 RAG MVP；第 6 步按 **ADR-009** 落地 API/UI 与 pending 持久化（RAG 仍默认 `RAG_ENABLED=false`，只增强解释、不判级）

## 一句话了解项目

面向“国际货物销售合同”的 AI 预审智能体：上传 PDF/DOCX/TXT → 条款切分 → LLM 抽取关键要素 → **Python 规则引擎判定红/黄/绿风险**（唯一等级来源）→ 红色风险经 **LangGraph `interrupt()` 真人工确认** → LLM 依据规则结果、合同原文与知识片段生成解释 → Python 质量门校验后输出可追溯报告。交付：Streamlit + 命令行 + FastAPI，10 天完成。

## 当前完成度

| 模块 | 状态 | 说明 |
|---|---|---|
| 第一阶段：GitHub 调研 | ✅ 100% | 8 个仓库源码级分析；用户已确认 |
| 第二阶段：架构设计 | ✅ 100% | ADR-001 ~ ADR-008 全部**已接受**（ADR-007 范围变更、ADR-008 RAG 实现） |
| 第三阶段第 1 步：环境 + 最小图 | ✅ 100% | `.venv`/依赖/最小图/规则引擎/测试/git |
| 第三阶段第 2 步：解析 + 切分 | ✅ 100% | TXT/MD/文本型 PDF/DOCX；标题切分/合并/超长拆分/上限 |
| 第三阶段第 3 步：LLM 抽取 + 校验 | ✅ 100% | 17 字段抽取/引文核验/降级/字段规则 skipped；Fake LLM 测试 |
| 第三阶段第 4 步：HITL 真中断 | ✅ 100% | 条件边/`interrupt()`/审批载荷/checkpointer/幂等/惰性超时；15 个 HITL 测试 |
| 第三阶段第 5 步：解释 + 质量门 + RAG MVP | ✅ 100% | `explain_risks` 节点/越权拦截/引用定位/BM25 检索/引用白名单；28 个新测试 |
| 第三阶段第 6 步：FastAPI + Streamlit | ✅ 100% | 上传/审查/人工决定/下载 JSON+Markdown；pending 落盘；37 个新测试 |
| 第四阶段：测试与评测 | ⏳ 10% | 单元/图/HITL/解释测试齐；尚无评测集与 gold |
| 第五阶段：文档与交付 | ⏳ 35% | README/状态/交接/ADR/资料清单已同步；评测结果与答辩材料未做 |

## 最近一次产出（2026-10-27 第三阶段第 6 步：FastAPI + Streamlit + 真实语料接入）

- `app/services/pending_store.py`（新建）
  - `FilePendingStore`：`.data/pending/<review_id>.json`，`tempfile` + `os.replace` 原子写；`MemoryPendingStore` 供测试；
  - `validate_review_id` 正则白名单防路径穿越；损坏/缺失文件按“未记录”处理，**绝不据此判超时**。
- `app/review_service.py`
  - 注入 `PendingStore`：首次观察到暂停写时间戳（不覆盖已有值），`resume` / 超时后清理；
  - `start / get / resume` 按 `review_id` 持 `threading.RLock`（可重入），并发不重复跑图；
  - `ReviewStateError(missing=True)` 区分“不存在”（API 404）与“状态冲突”（409）。
- `app/api.py`（新建）
  - `create_app(service=None, upload_dir=..., pending_dir=..., max_upload_mb=...)`；不传 service 时 lifespan 内开 SQLite checkpointer + 文件 pending store；
  - `GET /health`、`POST /api/reviews`、`GET /api/reviews/{id}`、`POST /api/reviews/{id}/decisions`、`GET /api/reviews/{id}/report?format=json|markdown`；
  - 上传：basename 净化（同时处理 `\`/`/`）、后缀白名单、`.doc` 提示转换、分块读取 + 413、空文件 400、失败清理目录；落 `.data/uploads/<review_id>/`；
  - 错误码 400/404/409/413/422；响应模型 `ReviewSummary` 不回传合同原文。
- `app/report_markdown.py`（新建）：`render_report_markdown`，含摘要/风险清单/抽取要素/待核对/人工复核/限制/版本；表格 `|` 转义、换行折叠；解释缺失写“未提供”。
- `app/ui.py`（新建）：Streamlit 中文界面；`st.cache_resource` 持有 SQLite + 文件 pending store；上传→审查→展示审批载荷→批准/要求修改/拒绝/标记超时→报告与下载；**不拼 `Command(resume=)`**。
- `app/services/rag.py`（扩展，真实语料接入）
  - `ALLOWED_SUFFIXES` 增加 `.docx`；`.doc` 明确报错提示转换；
  - DOCX 按 `第X条` 切分（编/章/节作上下文，目录丢弃），section 直接用条文号（如 `第五百七十七条`）；
  - Markdown 识别 `***Article N***` 与结构性加粗标题；
  - 超长片段按段落/句末标点二次切分（上限 1600 字符），同一标题依次 `s2`、`s2-2`；
  - `load_knowledge_base` 按 `(目录, manifest+文件 mtime/size)` 缓存，语料变更自动重建。
- `data/knowledge/manifest.yaml`：登记 14 篇真实语料（CISG 中英/重点条款、Incoterms 2020、民法典、涉外民事关系法律适用法、6 份司法解释、UCP600/仲裁、内部红线）；`100问题.md` 不入库（评测 query 集），旧版 `.doc` 需转换。`data/knowledge/examples/` 保留 3 份自拟示例专供测试。
- 测试新增 37 个（`test_api.py` 15、`test_pending_store.py` 11、`test_rag.py` +7、`test_report_markdown.py` 3、`test_ui.py` 1），全量 **197 passed**；`ruff` 通过。
- 实测：真实语料 14 篇 / 1834 段，最长 1599 字符；`根本违约`、`FOB 风险转移`、`仲裁 管辖`、`不可抗力` 命中合理 `source_id#section`；SQLite 模式 API 上传→暂停→approve→Markdown 报告全通。

## 上一次产出（2026-10-27 第三阶段第 5 步：解释 + 质量门 + RAG）

- `app/nodes/explain.py`
  - `explain_risks`：只对 red/yellow 解释；`rejected / changes_requested / unreviewed_red_risk / failed` 直接 `skipped`，不调用 LLM；
  - LLM schema `RiskExplanation` **无 `risk_level`**；prompt 里把合同与知识标为 `<untrusted_*>` 并转义分隔符，防提示注入；
  - **质量门**（纯 Python）：`rule_id` 必须匹配、`clause_id` 必须在规则命中的条款内、`summary` 非空、越权表述黑名单（合同无效/有效/已批准/已签署/无风险/建议直接签署/等级判定…）、`quote` 必须能在原文定位；
  - 知识引用只接受**本条风险实际检索到**的 `source_id#section`，编造引用丢弃 + warning；
  - 单条失败隔离：模型未配置/抛错/质量门失败 → 该条回退规则理由，整体标 `fallback`，报告仍生成。
- `app/services/rag.py`
  - 本地 BM25（`k1=1.5, b=0.75`）+ 中文“单字 + 二元组”切分，零网络依赖、零新库；
  - 相对阈值（≥ 最高分 25%）+ `RAG_TOP_K` / `RAG_MIN_SCORE`；
  - `manifest.yaml` 强校验：9 个必填字段、`source_id` 命名、`effective_date` 格式、UTF-8、仅 md/txt、禁止 `..`/绝对路径、重复 ID/未知字段报错；
  - 按 Markdown 标题切段并生成 `source_id#sN` 引用。
- `data/knowledge/`：`manifest.yaml` + 3 份**项目自拟**示例摘要（Incoterms / CISG / 民法典合同编），仅用于跑通检索与引用链；文件内显著标注“不是官方文本”。
- `app/schemas.py`：新增 `RiskExplanation`、`ExplanationResult`；`ReportFinding` 增加解释摘要/引文/引用；`ReviewReport` 增加 `explanation_status / explanation_model / explanation_prompt_version`。
- `app/graph.py`：8 节点 + 两条条件边：`evaluate_rules → human_review | explain_risks | build_report`，`human_review → explain_risks | build_report`。
- `app/nodes/hitl.py`：新增 `route_after_human_review`（只有 `approved` 才解释）。
- `app/nodes/report.py`：`explanation_status` 进摘要与 limitation（`fallback` / “未使用知识库”）。
- `app/config.py` / `.env.example`：新增 `RAG_ENABLED / RAG_KNOWLEDGE_DIR / RAG_TOP_K / RAG_MIN_SCORE`，默认关闭。
- `tests/test_rag.py`（15 个）、`tests/test_explain.py`（13 个）；`tests/test_hitl.py` 增补 `route_after_human_review`。
- `docs/devlog/02_ARCHITECTURE_DECISIONS/ADR-008-RAG检索与解释质量门.md`：记录选项、决策、质量门、后果。
- 验证：**160 passed**；`ruff` 通过；CLI 实测（无 Key）解释 `fallback`、报告仍完整；Fake LLM + RAG 实测引用命中 `EX-INCOTERMS#s3`、`EX-CN-CONTRACT#s3` 等。

## 上一次产出（2026-10-27 第三阶段第 4 步：HITL）

- `app/nodes/hitl.py`
  - `build_approval_payload()`：只读 + 纯计算，**在 `interrupt()` 之前**完成（resume 会重跑节点顶部）；
  - 审批载荷 `ApprovalPayload` 不含 LLM 解释、不含时间戳、不含“建议通过/拒绝”；红色风险最多展示 20 条，超出给 `truncated` 计数；每条最多 3 段原文、每段截断 300 字符；
  - `interrupt(payload)` → `Command(resume=...)` 的决策经 Pydantic 校验；**决策缺失/非法一律 fail-closed** → `unreviewed_red_risk`，绝不当成 approve；
  - `route_by_risk()`：`failed` 直接走报告；有任一红色（含系统级 red）→ `human_review`，否则快速通道。
- `app/services/checkpointer.py`
  - `memory_checkpointer()`（测试）/ `sqlite_checkpointer()`（运行，`SqliteSaver`）/ `open_checkpointer()`（按 `CHECKPOINT_BACKEND` 选择）；
  - 自建 `JsonPlusSerializer(allowed_msgpack_modules=[...])` 登记 `app.schemas` 下全部 Pydantic 类型，消除 SQLite 反序列化“未登记类型”的未来阻断告警。
- `app/review_service.py`
  - API/UI/CLI 共用薄封装：`start()` / `get()` / `resume()`；
  - `get()` 做**惰性超时**：`now - requested_at >= HITL_TIMEOUT_MINUTES` → 自动 `resume(TIMEOUT_DECISION)` → `unreviewed_red_risk`；
  - 幂等：已是终态时再次 `resume` 直接返回现有结果，不重跑图、不重复生成报告；未知 `review_id` 抛 `ReviewStateError`。
- `app/graph.py`
  - 7 节点：`ingest → segment → extract → validate → rules → [条件边] → human_review → build_report`；
  - **未注入 checkpointer 时编译直接 `ValueError`**，不允许静默退化为假 HITL。
- `app/nodes/report.py`
  - 报告状态跟随人工终态（`approved / rejected / changes_requested / unreviewed_red_risk`）；
  - 摘要与 limitation 显式写“人工确认 / 已拒绝 / 要求修改 / 超时未确认，不得作为通过结论”；
  - 人工意见只进 `hitl`，**不改写规则等级**。
- `app/schemas.py`：新增 `ApprovalFinding` / `ApprovalPayload`（`extra="forbid"`）。
- `app/graph_demo.py`：CLI 支持 `--review-id` / `--decision {approve,reject,changes,timeout}` / `--reviewer` / `--comment` / `--memory`；默认 SQLite，跨进程可恢复。
- `tests/test_hitl.py`：14 个 HITL 测试（暂停、审批前零写入、快速通道、批准只写一次、拒绝不解释、要求修改、超时不通过、惰性超时、非法决策 fail-closed、幂等、未知 ID、载荷截断、未知 override 告警）。
- 文档：`ADR-007`（范围变更）、`06_RAG与多智能体资料清单.md`、`02_ARCHITECTURE_DECISIONS/README.md` 索引、开发日志 2026-10-26 追加 2026-10-27 章节。

## 上一次产出（2026-10-26 第三阶段第 3 步）

- `app/services/llm.py`
  - `StructuredLLM` 协议（节点只依赖它，测试用 Fake LLM）；`OpenAICompatibleLLM` 优先 `json_schema`，不支持时回退 `function_calling`；
  - `call_structured()` 统一做类型校验 + 1 次修复重试；`LLMNotConfigured` / `StructuredOutputError` 供节点降级；
  - `get_llm()` 无 Key 时显式抛错，不静默返回空结果。
- `app/services/evidence.py`
  - `locate_quote`：精确匹配优先；失败后只允许“NFC 整簇规范化 + 连续空白折叠”；找不到返回 None，绝不模糊匹配。
- `app/nodes/extract.py`
  - 17 字段显式 schema（无 `risk_level`）；按条款串行抽取；单条款失败隔离 + `to_verify`；
  - 条款选择优先前言/相关类型，上限 `MAX_EXTRACT_CLAUSES=40`；
  - `extraction_status` 仅在全量条款成功时为 `ok`，部分覆盖/失败一律 `degraded`；
  - 合同文本包在 `<untrusted_contract>` 并转义分隔符。
- `app/nodes/validate.py`
  - 引文核验（缺失/无法定位 → 丢弃字段 + `to_verify`）；数值去千分位并归一为 float；
  - 多条款同名字段冲突保留首个 + `to_verify`；金额/币种、单价/总价、Incoterms 版本、非 ISO 日期 → `to_verify`，不自动换算。
- `app/rules/engine.py` / `definitions.yaml`
  - 新增 `requires_extraction`；抽取不可用时字段规则 `skipped=True`（不算 pass 也不误报 yellow）；
  - 规则 5 → 7 条（新增 `R-DLV-001` 交付期限缺失、`R-INP-001` 检验标准缺失），`version: 2`。
- `app/graph.py`：6 节点 `ingest → segment → extract → validate → rules → report`。
- `app/nodes/report.py`：填 `extracted_fields / prompt_version / model_id`；抽取降级/跳过时追加 limitation，摘要写明跳过条数。
- 测试：新增 `tests/fakes.py` 与 5 个测试文件（evidence/llm/extract/validate/图端到端），总数 **115 个全部通过**。

## 核心设计（ADR-001~009，已接受）

```text
START → ingest → segment → extract(LLM) → validate → rules(Python)
   → [有 red?] → human_review(interrupt)
   │                ├─ approve → explain(LLM [+RAG]) → report → END
   │                └─ reject / request_changes / timeout → report → END
   └─ 无 red → explain(LLM [+RAG]) → report → END
```

- 当前已实现全部 8 个节点：`ingest → segment → extract → validate → rules → [条件边] → human_review → explain → report`；
  三种交付入口均可用：CLI（`graph_demo.py`）、FastAPI（`api.py`）、Streamlit（`ui.py`），全部只依赖 `ReviewService`。
- 等级只来自 Python 规则；LLM 的抽取/解释/专家候选 schema 中都没有 `risk_level`；
- HITL 用 `interrupt()`，不是状态字段；`thread_id=review_id`；SQLite 持久化已接入；
- 审批前零业务写入；超时 → `unreviewed_red_risk`，绝不自动通过；重复 resume 幂等；
- pending 时间戳落盘 `.data/pending/<review_id>.json`（原子写），重启后惰性超时仍有效；同 `review_id` 加进程内可重入锁；
- 解释必须通过 Python 质量门；知识引用只能是本条风险实际检索到的 `source_id#section`；
- 证据 `文件名:p页:start-end`；报告固定包含 limitation；
- 输入/解析/规则异常都有明确降级，不崩溃、不静默 pass；
- 抽取降级（无 Key/失败/超上限）时字段规则标记 `skipped`，不把“没抽到”说成“合同缺条款”；
- RAG/多智能体（ADR-007/008）：**允许但默认关闭**（`RAG_ENABLED=false`、`AGENTS_ENABLED=false`），只用于解释/建议/条款比对，不参与判级。

## 验证方式（可复现）

```powershell
.\.venv\Scripts\python.exe -m pytest
# 197 passed

.\.venv\Scripts\python.exe -m ruff check .
# All checks passed!

# HITL：含风险样例会停在人工确认（退出码 0，状态 running，等待审批）
.\.venv\Scripts\python.exe -m app.graph_demo --memory
# 条款数量 8；总体等级 red；3 红 1 黄；extraction_status=degraded（无 Key）
# 风险解释：skipped（尚未批准）；输出审批载荷与“恢复命令”

# 同一 review_id 恢复（SQLite 跨进程）
.\.venv\Scripts\python.exe -m app.graph_demo --review-id <id> --decision approve --reviewer zhangsan --comment "已核对"
# status=approved；解释 status=fallback（无 Key，回退规则理由）
# 摘要含“红色风险已经人工确认”；timings 含 human_review_ms / explain_risks_ms
# 已批准后再次 --decision reject → 仍 approved（幂等，不重跑图）

.\.venv\Scripts\python.exe -m app.graph_demo --review-id <id> --decision timeout
# status=unreviewed_red_risk；解释 skipped；摘要“未获人工确认（审批超时），报告不得作为通过结论”

# 干净合同：无 red → 快速通道 → 解释 skipped（不调用 LLM）→ completed
.\.venv\Scripts\python.exe -m app.graph_demo data\samples\sample_clean_contract.txt

# FastAPI（默认 SQLite + .data/pending）
.\.venv\Scripts\python.exe -m uvicorn app.api:create_app --factory --port 8000
# POST /api/reviews（上传）→ awaiting_human=true → POST .../decisions（approve）
# → GET /api/reviews/{id}/report?format=json|markdown

# Streamlit
.\.venv\Scripts\python.exe -m streamlit run app/ui.py
```

Fake LLM 端到端（`tests/test_graph_extraction.py`）：`extraction_status=ok`、`facts.total_amount=3100000.0`、字段规则正常 pass、报告 `extracted_fields` 与 `facts` 一致；单条款超时 → 降级且字段规则 skipped，报告状态 `approved`（测试显式批准）。

HITL 端到端（`tests/test_hitl.py`，17 个）：`__interrupt__` 暂停、审批前零报告、无 red 快速通道、approve 只写一次、reject 不解释、request_changes、timeout 不通过、惰性超时、非法决策 fail-closed、重复 resume 幂等、未知 ID 报错、载荷截断、未知 override 告警、`build_graph()` 无 checkpointer 报错、两条条件边。

API/UI（`tests/test_api.py` 15 个 + `tests/test_pending_store.py` 11 个 + `tests/test_report_markdown.py` 3 个 + `tests/test_ui.py` 1 个）：上传暂停、审批后下载 JSON/Markdown、报告 409、快速通道幂等、404/422/413、文件名净化、跨 service 超时、损坏 pending、Markdown 章节与转义、Streamlit 首屏。

解释/RAG 端到端（`tests/test_explain.py` 13 个 + `tests/test_rag.py` 22 个）：正常解释与引文定位、越权表述拦截、引文不可定位、rule_id/clause_id 不匹配、schema 禁 `risk_level`、无 Key 回退、拒绝/干净合同不调用 LLM、引用白名单（编造引用丢弃）、知识库配置错误降级、无命中告警、manifest 9 字段/路径穿越/重复 ID/编码校验、DOCX 条文切分、`***Article N***` 标题、超长片段二次切分、缓存重建、真实语料冒烟。

## 下一步（按顺序，不跳步）

1. ~~**第 2 步：文档解析与条款切分**~~ ✅ 已完成（2026-10-26）。
2. ~~**第 3 步：LLM 抽取 + Python 校验**~~ ✅ 已完成（2026-10-26）。
3. ~~**第 4 步：条件边 + HITL**~~ ✅ 已完成（2026-10-27）。
4. ~~**第 5 步：LLM 解释 + Quality Gate + 报告合并 + RAG MVP**~~ ✅ 已完成（2026-10-27，160 个测试）。
5. ~~**第 6 步：FastAPI + Streamlit**~~ ✅ 已完成（2026-10-27，197 个测试）
   - 上传（大小/类型/文件名净化）、运行、展示审批载荷、确认/拒绝/超时、下载报告 JSON/Markdown；
   - pending 时间戳落盘 `.data/pending`（ISSUE-017 已关闭）；按 `review_id` 的 `RLock` 防并发 resume；
   - UI/API 均不拼 `Command(resume=...)`，一律走 `ReviewService`。
6. 规则从 7 条扩到 10–12 条（ISSUE-009），再建 20–30 条 gold 评测集（ISSUE-005）；RAG 检索评测映射与 50 条 query（ISSUE-015/018）与阶段 B 多智能体专家节点（ISSUE-016）。

## 当前阻塞 / 需要你拍板

| 事项 | 状态 | 需要你做什么 | 默认 |
|---|---|---|---|
| LLM API Key / 模型名 | 待提供 | 全链路演示前提供 OpenAI 兼容 Key/模型 | 代码开发不阻塞（Fake LLM 覆盖）；真实抽取/解释效果需 Key |
| RAG 知识库授权（ISSUE-015） | 语料已提供，授权待确认 | 确认真实语料可否在演示/答辩中展示原文、可否再分发 | 语料已入库 14 篇；`RAG_ENABLED=false` 默认关闭 |
| RAG 检索评测（ISSUE-015/018） | 待映射 | 把 `100问题.md` 的 source_id/section 映射到 manifest 引用 | 映射完成前不宣称召回率 |
| 多智能体角色与编排（ISSUE-016） | 待确认 | 确认是否需要专家节点（付款/交付/争议）及其资料 | 阶段 B 再做；Supervisor 仅路由 |
| 规则集范围（ISSUE-009） | 部分解决 | 确认是否按现有 7 条继续扩到 10–12 条 | 按国际销售高频风险扩 |
| 评测 gold | 待创建 | 是否接受自拟 20–30 条条款级 gold | 阶段 4 创建 |
| 首批真实 PDF/DOCX 样例 | 待提供 | 有真实脱敏合同时优先用真实件 | 已有程序化 PDF/DOCX fixture，不阻塞 |
| 长合同抽取覆盖 | 已知限制 | 是否接受 > 40 条条款时字段规则跳过 | 先保持保守（宁可跳过不误报） |
| 多进程部署 | 已知限制 | 是否需要多 worker（当前锁仅进程内） | 单机单 worker 演示（ISSUE-019） |

## 3 分钟了解项目（给新接手的人）

1. 读根目录 `README.md` 的“设计底线 / 已知限制 / 快速开始”。
2. 读 `02_ARCHITECTURE_DECISIONS/README.md` 的“关键设计一句话”，再按需读 ADR-001~009。
3. 代码入口：`app/graph.py`（图组装）→ `app/review_service.py`（启动/查询/恢复）→ `app/graph_demo.py` / `app/api.py` / `app/ui.py`（三种入口）→ `app/nodes/explain.py`（解释与质量门）。
4. 当前已实现 ingest/segment/extract/validate/rules/human_review/explain/report、RAG 检索、FastAPI 与 Streamlit；未配置 Key 时抽取降级、解释回退规则理由。
5. 未解决事项看 `05_OPEN_ISSUES.md`（ISSUE-015/018/019 与本轮直接相关）；RAG/多智能体资料要求看 `06_RAG与多智能体资料清单.md`；RAG 设计看 `ADR-008`，API/UI 与 pending 落盘看 `ADR-009`。

## 文件地图

```text
开发提示词.md                          # 需求与约束（RAG/多智能体部分以 ADR-007 为准）
README.md                              # 项目介绍、启动、设计底线、限制
requirements.txt / requirements-dev.txt# 锁定依赖（Python 3.12）
pyproject.toml                         # ruff / pytest 配置
.env.example                           # 环境变量模板（无真实 Key）
app/
  config.py                            # 环境变量与上限（MAX_* / CHECKPOINT_* / HITL_TIMEOUT_MINUTES / PENDING_DIR / UPLOAD_DIR / RAG_*）
  schemas.py                           # Pydantic 契约（抽取 schema / RuleEvaluation / Report / ApprovalPayload / Explanation）
  graph.py                             # LangGraph 组装（8 节点 + 两条条件边 + 强制 checkpointer）
  review_service.py                    # start/get/resume（幂等 + 惰性超时 + pending 持久化 + review_id 锁）
  graph_demo.py                        # CLI 演示（SQLite 跨进程；--decision 恢复）
  api.py                               # FastAPI（上传/查询/决定/下载；错误码 400/404/409/413/422）
  ui.py                                # Streamlit 中文界面（上传/审批/报告/下载）
  report_markdown.py                   # ReviewReport → Markdown（纯渲染，不重算等级）
  nodes/ingest.py                      # TXT/MD/PDF/DOCX → canonical text + 页偏移
  nodes/segment.py                     # 标题切分/合并/超长拆分/段落 fallback
  nodes/extract.py                     # LLM 17 字段抽取（唯一 LLM 抽取节点）
  nodes/validate.py                    # 引文核验/数值归一/一致性 → facts + to_verify
  nodes/rules.py                       # 规则节点（等级唯一来源）
  nodes/hitl.py                        # 审批载荷 + interrupt() + 决策校验 + 条件边
  nodes/report.py                      # 报告汇总（跟随人工终态 + limitation）
  services/llm.py                      # 结构化输出 + 1 次修复重试 + 异常类型
  services/evidence.py                 # locate_quote（精确 → NFC/空白规范化）
  services/checkpointer.py             # memory/sqlite 工厂 + JsonPlusSerializer 类型登记
  services/pending_store.py            # pending 时间戳落盘（原子写 + review_id 白名单）
  services/rag.py                      # 本地 BM25 + 中文二元组 + MD/DOCX 切分 + manifest 校验 + 缓存
  rules/definitions.yaml               # 7 条规则（5 文本 + 2 字段）
  rules/dsl.py                         # 条件 DSL
  rules/engine.py                      # 规则加载/求值/证据/fail-closed/skipped
data/samples/                          # 2 份自拟脱敏样例
data/knowledge/                        # 真实语料 14 篇 + manifest；examples/ 为测试专用自拟语料
tests/                                 # 197 个测试（API 15 / pending 11 / RAG 22 / 解释 13 / HITL 17）
tests/fakes.py                         # Fake LLM（无需 Key）
tests/fixtures/pdf_builder.py          # 纯标准库构造最小 PDF（测试用）
docs/devlog/
  00_PROJECT_STATE.md                  # 本文件
  01_RESEARCH_LOG.md                   # 第一阶段调研
  02_ARCHITECTURE_DECISIONS/           # ADR-001~009（均已接受）
  03_DEV_LOGS/2026-10-26.md            # 调研 + ADR + 第 1/2/3/4/5/6 步日志
  04_HANDOVER.md                       # 交接说明
  05_OPEN_ISSUES.md                    # 待决事项
  06_RAG与多智能体资料清单.md          # RAG/多智能体需要准备的资料与目录格式
```

