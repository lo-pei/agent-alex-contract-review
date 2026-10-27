# Agent Alex · 外贸合同智审助手

面向**国际货物销售合同**的 AI 预审智能体：上传合同 → 条款切分 → LLM 抽取关键要素 → **Python 规则引擎判定红/黄/绿风险**（唯一等级来源）→ 红色风险经 **LangGraph `interrupt()` 真人工确认** → LLM 依据规则结果与原文生成解释 → 输出可追溯报告。

> 当前处于**第三阶段（代码实现）第 4 步**：已跑通 `ingest → segment → extract → validate → rules → [条件边] → human_review → report`——支持 **TXT / Markdown / 文本型 PDF / DOCX** 解析、标题式条款切分、LLM 17 字段要素抽取与 Python 引文校验，7 条规则（5 条文本 + 2 条字段），红色风险触发 **LangGraph `interrupt()` 真暂停**，经 `Command(resume=...)` 恢复。**LLM 解释、RAG、FastAPI、Streamlit 尚未实现**；未配置 `LLM_API_KEY` 时抽取自动降级，字段规则标记跳过。详见 [`docs/devlog/00_PROJECT_STATE.md`](docs/devlog/00_PROJECT_STATE.md)。

## 当前完成度

| 阶段 | 状态 | 说明 |
|---|---|---|
| 1. GitHub 调研 | ✅ | 8 个开源项目源码级分析，产出借鉴/不借鉴清单 |
| 2. 架构设计 | ✅ | ADR-001 ~ ADR-007 全部已接受 |
| 3. 代码实现 | 🚧 第 4 步完成 | 环境、7 节点图、规则引擎（7 条规则）、PDF/DOCX/TXT 解析、标题切分、LLM 抽取 + 引文校验、HITL 真中断/恢复、131 个测试 |
| 4. 测试与评测 | ⏳ 未开始 | 尚无评测集，**不公布任何准确率** |
| 5. 文档与交付 | ⏳ 进行中 | 开发日志、ADR、交接文档与 RAG 资料清单已建立 |

## 技术栈

- Python **3.12**（`开发提示词.md` 原写 3.9+，但 Streamlit 1.66.1 要求 ≥3.11，LangGraph 1.2 要求 ≥3.10；决策见 [ADR-006](docs/devlog/02_ARCHITECTURE_DECISIONS/ADR-006-运行环境与依赖策略.md)）
- LangGraph 1.2.17 + LangChain 1.4.7（含 `langgraph-checkpoint-sqlite`）
- Pydantic 2.14（结构化输出与状态契约）
- FastAPI（计划）、Streamlit（计划）
- **允许但默认关闭**：RAG 知识检索、多智能体专家节点（ADR-007，`RAG_ENABLED=false` / `AGENTS_ENABLED=false`）
- 不使用：训练模型、Docker、前端框架、Neo4j/GraphRAG、向量数据库、Postgres/Redis

## 快速开始

```powershell
# 1) 创建虚拟环境（必须用 3.12，不要用系统默认 python）
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

# 2) 运行全链路（无需 Key：抽取会自动降级；字段规则标记跳过）
.\.venv\Scripts\python.exe -m app.graph_demo
# 含红色风险 → 图会停在人工确认，打印审批载荷 + review_id + 恢复命令

.\.venv\Scripts\python.exe -m app.graph_demo data\samples\sample_clean_contract.txt
# 无红色风险 → 快速通道，直接完成

.\.venv\Scripts\python.exe -m app.graph_demo --json

# 3) 恢复人工决定（SQLite 默认持久化，可跨进程）
.\.venv\Scripts\python.exe -m app.graph_demo --review-id <review_id> --decision approve --reviewer zhangsan --comment "已核对"
.\.venv\Scripts\python.exe -m app.graph_demo --review-id <review_id> --decision reject --reviewer zhangsan
.\.venv\Scripts\python.exe -m app.graph_demo --review-id <review_id> --decision timeout
# 超时/拒绝都不会变成通过；已终态再次恢复是幂等的

# 4) 测试与静态检查
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

环境变量：复制 `.env.example` 为 `.env` 后填写。**不要提交真实 Key**（`.env` 已在 `.gitignore`）。

配置 `LLM_API_KEY`（任意 OpenAI 兼容端点）后，同一命令会自动启用真实要素抽取；不配置时走降级路径，报告会写明“要素抽取未完整执行”并跳过字段规则。

```text
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=
LLM_MODEL=gpt-4.1-mini
LLM_TIMEOUT_SECONDS=60
LLM_MAX_REPAIR_RETRIES=1
MAX_EXTRACT_CLAUSES=40
CHECKPOINT_BACKEND=sqlite
CHECKPOINT_SQLITE_PATH=.data/checkpoints.sqlite
HITL_TIMEOUT_MINUTES=30
```

> HITL 状态：红色风险 → `running`（等待审批，`snapshot.next == ("human_review",)`）→ `approved / rejected / changes_requested / unreviewed_red_risk`。审批前不会生成最终报告；超时只能落到 `unreviewed_red_risk`。

## 目录结构

```text
app/
  config.py              # 环境变量与上限（唯一读取 .env 的地方）
  schemas.py             # Pydantic：State / Clause / Evidence / 抽取 schema / RuleEvaluation / Report / ApprovalPayload
  graph.py               # LangGraph 组装（7 节点 + 条件边 + 强制 checkpointer）
  review_service.py      # start / get / resume（幂等 + 惰性超时）
  graph_demo.py          # 命令行演示（SQLite 跨进程；--review-id / --decision）
  nodes/
    ingest.py            # TXT/Markdown/PDF/DOCX → canonical text + 页偏移 + sha256
    segment.py           # 标题切分 + 小条款合并 + 超长拆分（无标题时段落 fallback）
    extract.py           # LLM 17 字段抽取（唯一 LLM 抽取节点，按条款串行）
    validate.py          # 引文定位校验 + 数值归一 + 一致性 → facts / to_verify
    rules.py             # 调用规则引擎，产出唯一等级
    hitl.py              # 审批载荷 + interrupt() + 决策校验 + route_by_risk
    report.py            # 汇总非 pass 结果 → 可追溯报告（跟随人工终态）
  services/
    llm.py               # 结构化输出 + 1 次修复重试 + 未配置/输出错误类型
    evidence.py          # locate_quote：精确匹配 → NFC/空白规范化
    checkpointer.py      # memory / sqlite 工厂 + Pydantic 类型登记
  rules/
    definitions.yaml     # 7 条规则（5 文本 + 2 字段，version 2）
    dsl.py               # 白名单条件 DSL（无 eval/exec）
    engine.py            # 规则加载 + 求值 + fail-closed + 字段规则 skipped
data/samples/            # 2 份自拟脱敏合同（含风险 / 全部通过）
tests/                   # 131 个测试（含 14 个 HITL 测试，无需 Key）
tests/fakes.py           # Fake LLM（实现 StructuredLLM 协议）
docs/devlog/             # 项目状态、调研、ADR、开发日志、交接、待决事项、RAG 资料清单
```

## 设计底线

1. **规则唯一判级**：`red / yellow / pass` 只由 Python 规则产生；LLM 的 schema（抽取/解释/专家）中不出现 `risk_level`。
2. **LLM 只做两件事**：抽取 17 个合同要素（缺失为 null）、生成带原文引用的风险解释。RAG/专家只能增强解释，不能改级。
3. **抽取状态必须显式**：`ok / degraded / skipped` 进报告；`degraded` 时字段规则 `skipped`，不把“没抽到”说成“合同缺条款”。
4. **HITL 真中断**：节点内 `interrupt()` + checkpointer + `Command(resume=...)`；审批前零业务写入；超时标记 `unreviewed_red_risk`，绝不自动通过；重复恢复幂等。
5. **失败显式降级**：输入/解析/规则异常都有明确路径，不崩溃、不静默 pass；规则执行异常 → 系统 red 并进入人工确认；RAG 无命中 → 退化纯规则解释。
6. **证据可追溯**：每条风险引用格式 `文件名:p页:start-end`，可在原文精确定位；LLM 引文只允许空白/Unicode 规范化，不允许模糊匹配；知识引用格式 `source_id#section`（规划）。
7. **RAG 与多智能体默认关闭**（ADR-007）：`RAG_ENABLED=false`、`AGENTS_ENABLED=false`；Supervisor 仅路由，不判级。

## 已知限制（当前步骤）

- 支持 TXT / Markdown / 文本型 PDF / DOCX；**扫描件与加密 PDF 明确报错**，不做 OCR。
- PDF 表格/多栏可能打乱列顺序，只在 `warnings` 提示人工核对；DOCX 无真实页码，统一 `p1`。
- 条款切分依赖标题格式（`第X条` / `ARTICLE N` / `1.` 等）；无标题合同走段落 fallback，可能切得不理想。
- 7 条规则（5 文本 + 2 字段），**未覆盖**责任上限、不可抗力、所有权保留、合规条款等。
- 未配置 `LLM_API_KEY` 时抽取降级：文本规则照常跑，字段规则跳过（报告有 limitation）。
- 条款数超过 `MAX_EXTRACT_CLAUSES`（默认 40）时只抽取部分条款，字段规则跳过；长合同精度有限。
- **中文 PDF / 复杂版式未验证**；真实模型抽取效果**无数据**。
- **无 LLM 解释、无 RAG、无 API/UI**；报告只有规则结果与人工决定。
- HITL 超时是惰性检查，且 pending 时间戳仅存进程内存：进程重启后超时判定失效（ISSUE-017，第 6 步修复）。
- **没有评测数据**：README 与文档中的任何指标都必须来自 `eval/results/*.json`，当前为空。

## 第三方代码与许可

- 本项目代码为独立实现，未复制任何调研仓库的源代码。
- 调研参考项目（仅借鉴设计，未复制代码）：aurelien-henrion/contract-agent（MIT）、laolaola278-dev/enterprise-contract-review-agent（Apache-2.0）、bcefghj/multi-agent-contract-review（Apache-2.0）；zihan154896-jpg/intelligent-contract-review、Harvey-cream/Langchain_DG、kashifumair125/ContractSentinel 无 LICENSE，仅阅读设计。
- 依赖许可：pypdf（BSD）、python-docx（MIT）、LangGraph/LangChain（MIT）、FastAPI（MIT）、Streamlit（Apache-2.0）、PyYAML（MIT）。未引入 PyMuPDF（AGPL/商业双许可）。

## 文档索引

- 项目状态（3 分钟接手）：[`docs/devlog/00_PROJECT_STATE.md`](docs/devlog/00_PROJECT_STATE.md)
- 调研与借鉴决策：[`docs/devlog/01_RESEARCH_LOG.md`](docs/devlog/01_RESEARCH_LOG.md)
- 架构决策：[`docs/devlog/02_ARCHITECTURE_DECISIONS/README.md`](docs/devlog/02_ARCHITECTURE_DECISIONS/README.md)
- 开发日志：[`docs/devlog/03_DEV_LOGS/`](docs/devlog/03_DEV_LOGS/)
- 交接说明：[`docs/devlog/04_HANDOVER.md`](docs/devlog/04_HANDOVER.md)
- 待解决问题：[`docs/devlog/05_OPEN_ISSUES.md`](docs/devlog/05_OPEN_ISSUES.md)
- RAG 与多智能体资料清单：[`docs/devlog/06_RAG与多智能体资料清单.md`](docs/devlog/06_RAG与多智能体资料清单.md)
- 范围变更决策：[`ADR-007`](docs/devlog/02_ARCHITECTURE_DECISIONS/ADR-007-范围变更-RAG与多智能体.md)
