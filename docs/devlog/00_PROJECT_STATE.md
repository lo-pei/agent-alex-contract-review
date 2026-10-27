# 项目状态快照

> 更新时间：2026-10-27（第三阶段第 4 步完成）
> 当前阶段：**第三阶段（代码实现）第 4 步：条件边 + HITL `interrupt()` 真暂停/恢复 + checkpointer 已可用**
> 项目目录：`d:\A项目\Agent_Alex外贸合同智审助手`
> Git：提交 `cf0fd63`、`71e8a9d`、`750cca3`、`625e9bd`（第 3 步），以及第 4 步的 `feat: 接入HITL真中断与恢复`（完整哈希见 `git log`）
> 范围变更：2026-10-27 用户明确「可以做 rag 和多 agent」→ **ADR-007**（能力放开，判级/HITL/证据边界不变；RAG 与多智能体默认关闭，尚未实现）

## 一句话了解项目

面向“国际货物销售合同”的 AI 预审智能体：上传 PDF/DOCX/TXT → 条款切分 → LLM 抽取关键要素 → **Python 规则引擎判定红/黄/绿风险**（唯一等级来源）→ 红色风险经 **LangGraph `interrupt()` 真人工确认** → LLM 依据规则结果和原文生成解释与建议 → 输出可追溯报告。交付：Streamlit + 命令行 + FastAPI，10 天完成。

## 当前完成度

| 模块 | 状态 | 说明 |
|---|---|---|
| 第一阶段：GitHub 调研 | ✅ 100% | 8 个仓库源码级分析；用户已确认 |
| 第二阶段：架构设计 | ✅ 100% | ADR-001 ~ ADR-007 全部**已接受**（ADR-007 为 2026-10-27 范围变更） |
| 第三阶段第 1 步：环境 + 最小图 | ✅ 100% | `.venv`/依赖/最小图/规则引擎/测试/git |
| 第三阶段第 2 步：解析 + 切分 | ✅ 100% | TXT/MD/文本型 PDF/DOCX；标题切分/合并/超长拆分/上限 |
| 第三阶段第 3 步：LLM 抽取 + 校验 | ✅ 100% | 17 字段抽取/引文核验/降级/字段规则 skipped；Fake LLM 测试 |
| 第三阶段第 4 步：HITL 真中断 | ✅ 100% | 条件边/`interrupt()`/审批载荷/checkpointer/幂等/惰性超时；14 个 HITL 测试 |
| 第三阶段第 5 步：解释 + Quality Gate + RAG MVP | ⏳ 0% | 下一步 |
| 第三阶段第 6 步：FastAPI + Streamlit | ⏳ 0% | 依赖第 5 步 |
| 第四阶段：测试与评测 | ⏳ 0% | 只有单元/图/HITL 测试，尚无评测集与 gold |
| 第五阶段：文档与交付 | ⏳ 25% | README/状态/交接已同步；评测结果与答辩材料未做 |

## 最近一次产出（2026-10-27 第三阶段第 4 步：HITL）

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

## 核心设计（ADR-001~007，已接受）

```text
START → ingest → segment → extract(LLM) → validate → rules(Python)
   → [有 red?] → human_review(interrupt)
   │                ├─ approve → explain(LLM [+RAG]) → report → END
   │                └─ reject / request_changes / timeout → report → END
   └─ 无 red → explain(LLM [+RAG]) → report → END
```

- 当前已实现：`ingest → segment → extract → validate → rules → [条件边] → human_review → report`；
  **解释节点 `explain` 与 RAG 尚未实现**（第 5 步）。
- 等级只来自 Python 规则；LLM 的抽取/解释/专家候选 schema 中都没有 `risk_level`；
- HITL 用 `interrupt()`，不是状态字段；`thread_id=review_id`；SQLite 持久化已接入；
- 审批前零业务写入；超时 → `unreviewed_red_risk`，绝不自动通过；重复 resume 幂等；
- 证据 `文件名:p页:start-end`；报告固定包含 limitation；
- 输入/解析/规则异常都有明确降级，不崩溃、不静默 pass；
- 抽取降级（无 Key/失败/超上限）时字段规则标记 `skipped`，不把“没抽到”说成“合同缺条款”；
- RAG/多智能体（ADR-007）：**允许但默认关闭**（`RAG_ENABLED=false`、`AGENTS_ENABLED=false`），只用于解释/建议/条款比对，不参与判级。

## 验证方式（可复现）

```powershell
.\.venv\Scripts\python.exe -m pytest
# 131 passed

.\.venv\Scripts\python.exe -m ruff check .
# All checks passed!

# HITL：含风险样例会停在人工确认（退出码 0，状态 running，等待审批）
.\.venv\Scripts\python.exe -m app.graph_demo
# 条款数量 8；总体等级 red；3 红 1 黄；extraction_status=degraded（无 Key）
# 输出审批载荷（含 R-PAY-001 依据 p1:527-547 原文）与“恢复命令”
# 状态：running（待人工确认 review_id=...）

# 同一 review_id 恢复（SQLite 跨进程）
.\.venv\Scripts\python.exe -m app.graph_demo --review-id <id> --decision approve --reviewer zhangsan --comment "已核对"
# status=approved；报告摘要含“红色风险已经人工确认”；timings 含 human_review_ms
# 已批准后再次 --decision reject → 仍 approved（幂等，不重跑图）

.\.venv\Scripts\python.exe -m app.graph_demo --review-id <id> --decision timeout
# status=unreviewed_red_risk；摘要“未获人工确认（审批超时），报告不得作为通过结论”

# 干净合同：无 red → 快速通道，不触发人工确认
.\.venv\Scripts\python.exe -m app.graph_demo data\samples\sample_clean_contract.txt
# 条款数量 6；总体 pass；status=completed；无 human_review_ms
```

Fake LLM 端到端（`tests/test_graph_extraction.py`）：`extraction_status=ok`、`facts.total_amount=3100000.0`、字段规则正常 pass、报告 `extracted_fields` 与 `facts` 一致；单条款超时 → 降级且字段规则 skipped，报告状态 `approved`（测试显式批准）。

HITL 端到端（`tests/test_hitl.py`，14 个）：`__interrupt__` 暂停、审批前零报告、无 red 快速通道、approve 只写一次、reject 不解释、request_changes、timeout 不通过、惰性超时、非法决策 fail-closed、重复 resume 幂等、未知 ID 报错、载荷截断、未知 override 告警、`build_graph()` 无 checkpointer 报错。

## 下一步（按顺序，不跳步）

1. ~~**第 2 步：文档解析与条款切分**~~ ✅ 已完成（2026-10-26）。
2. ~~**第 3 步：LLM 抽取 + Python 校验**~~ ✅ 已完成（2026-10-26）。
3. ~~**第 4 步：条件边 + HITL**~~ ✅ 已完成（2026-10-27，131 个测试；SQLite 跨进程实测）。
4. **第 5 步：LLM 解释 + Quality Gate + 报告合并 + RAG MVP**
   - `nodes/explain.py`：只对 red/yellow 生成解释，必须在 `human_review` 之后（拒绝/要求修改不调用）；
   - Quality Gate：解释 schema 无 `risk_level`；拦截“合同无效/已批准/已签署”等越权表述；失败用规则 `reason` 兜底；
   - RAG MVP（ADR-007，默认 `RAG_ENABLED=false`）：本地 BM25/字符 n-gram，引用格式 `source_id#section`，无命中必须降级为纯规则解释。
5. **第 6 步：FastAPI + Streamlit**（上传、运行、展示/确认、下载；`asyncio.Lock` 防并发 resume）。
6. 规则从 7 条扩到 10–12 条（ISSUE-009），再建 20–30 条 gold 评测集（ISSUE-005）；阶段 B 再评估多智能体专家节点。

## 当前阻塞 / 需要你拍板

| 事项 | 状态 | 需要你做什么 | 默认 |
|---|---|---|---|
| LLM API Key / 模型名 | 待提供 | 全链路演示前提供 OpenAI 兼容 Key/模型 | 第 1–5 步代码开发不阻塞（Fake LLM 覆盖）；真实解释效果需 Key |
| RAG 知识库资料与授权（ISSUE-015） | 待提供 | 按 `06_RAG与多智能体资料清单.md` 的最小可开工集准备 6 项 | 先用内置极小示例语料跑通检索链路，`RAG_ENABLED=false` |
| 多智能体角色与编排（ISSUE-016） | 待确认 | 确认是否需要专家节点（付款/交付/争议）及其资料 | 阶段 B 再做；Supervisor 仅路由 |
| 规则集范围（ISSUE-009） | 部分解决 | 确认是否按现有 7 条继续扩到 10–12 条 | 按国际销售高频风险扩 |
| 评测 gold | 待创建 | 是否接受自拟 20–30 条条款级 gold | 阶段 4 创建 |
| 首批真实 PDF/DOCX 样例 | 待提供 | 有真实脱敏合同时优先用真实件 | 已有程序化 PDF/DOCX fixture，不阻塞 |
| 长合同抽取覆盖 | 已知限制 | 是否接受 > 40 条条款时字段规则跳过 | 先保持保守（宁可跳过不误报） |
| HITL pending 时间戳持久化 | 已知限制 | 是否接受重启后惰性超时失效 | 第 6 步随 FastAPI 落盘 `.data/pending` 解决（ISSUE-017） |

## 3 分钟了解项目（给新接手的人）

1. 读根目录 `README.md` 的“设计底线 / 已知限制 / 快速开始”。
2. 读 `02_ARCHITECTURE_DECISIONS/README.md` 的“关键设计一句话”，再按需读 ADR-001~007。
3. 代码入口：`app/graph.py`（图组装）→ `app/review_service.py`（启动/查询/恢复）→ `app/graph_demo.py`（可运行示例）。
4. 当前已实现 ingest/segment/extract/validate/rules/human_review/report；**解释 `explain`、RAG、FastAPI、Streamlit 尚不存在**。
5. 未解决事项看 `05_OPEN_ISSUES.md`；RAG/多智能体资料要求看 `06_RAG与多智能体资料清单.md`。

## 文件地图

```text
开发提示词.md                          # 需求与约束（RAG/多智能体部分以 ADR-007 为准）
README.md                              # 项目介绍、启动、设计底线、限制
requirements.txt / requirements-dev.txt# 锁定依赖（Python 3.12）
pyproject.toml                         # ruff / pytest 配置
.env.example                           # 环境变量模板（无真实 Key）
app/
  config.py                            # 环境变量与上限（MAX_PAGES / MAX_EXTRACT_CLAUSES / CHECKPOINT_* / HITL_TIMEOUT_MINUTES）
  schemas.py                           # Pydantic 契约（抽取 schema / RuleEvaluation / Report / ApprovalPayload）
  graph.py                             # LangGraph 组装（7 节点 + 条件边 + 强制 checkpointer）
  review_service.py                    # start/get/resume 薄封装（幂等 + 惰性超时）
  graph_demo.py                        # 演示入口（SQLite 跨进程；--decision 恢复）
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
  rules/definitions.yaml               # 7 条规则（5 文本 + 2 字段）
  rules/dsl.py                         # 条件 DSL
  rules/engine.py                      # 规则加载/求值/证据/fail-closed/skipped
data/samples/                          # 2 份自拟脱敏样例
tests/                                 # 131 个测试（含 14 个 HITL 测试）
tests/fakes.py                         # Fake LLM（无需 Key）
tests/fixtures/pdf_builder.py          # 纯标准库构造最小 PDF（测试用）
docs/devlog/
  00_PROJECT_STATE.md                  # 本文件
  01_RESEARCH_LOG.md                   # 第一阶段调研
  02_ARCHITECTURE_DECISIONS/           # ADR-001~007（均已接受）
  03_DEV_LOGS/2026-10-26.md            # 调研 + ADR + 第 1/2/3/4 步日志
  04_HANDOVER.md                       # 交接说明
  05_OPEN_ISSUES.md                    # 待决事项
  06_RAG与多智能体资料清单.md          # RAG/多智能体需要准备的资料与目录格式
```

