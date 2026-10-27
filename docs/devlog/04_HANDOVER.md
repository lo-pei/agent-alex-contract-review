# 开发交接文档（Handover）

> 更新时间：2026-10-27（第四阶段：规则扩充 + 合同级评测基线）
> 当前状态：**第三阶段第 6 步完成（解释 + 质量门 + RAG + FastAPI + Streamlit 全部可用）；第四阶段第 1 轮完成：规则 13 条、50 份模拟合同拆分为评测输入、规则级评测基线已跑出；209 个测试通过**；规则级 gold 与检索评测尚未完成
> 交接原则：任何新接手的人只读本文件 + `00_PROJECT_STATE.md` + `02_ARCHITECTURE_DECISIONS/README.md`，就能继续开发。

---

## 1. 项目是做什么的

面向“国际货物销售合同”的 AI 预审智能体。输入 PDF / DOCX / TXT 合同，输出结构化风险报告：

- 条款切分并保留页码、字符偏移；
- LLM 只做要素抽取与风险解释；
- Python 规则引擎唯一决定 `red / yellow / pass`；
- 红色风险触发 LangGraph `interrupt()`，人工确认后才出最终报告；
- 报告每条风险都有 `rule_id + reason + 原文引用 + 文件:页码:字符偏移`；
- 交付：Streamlit 演示 + 命令行 + FastAPI。

硬约束来自根目录 `开发提示词.md`：技术栈 Python / LangGraph / Streamlit / FastAPI / Pydantic；规则决定等级，LLM 只抽取与解释；HITL 必须暂停/恢复；全部代码要解释清、能测试、边界明确。**2026-10-27 用户明确放开 RAG 与多智能体（ADR-007）**：允许 RAG、专家节点与 Supervisor 路由，但判级仍只由 Python 规则产生、HITL 仍必须真中断、证据仍必须可追溯；RAG/多智能体默认关闭（`RAG_ENABLED=false`、`AGENTS_ENABLED=false`）。训练模型、Docker、前端框架仍禁止。

---

## 2. 当前完成度

| 项 | 状态 | 证据 |
|---|---|---|
| GitHub 调研 | ✅ 完成 | `01_RESEARCH_LOG.md`，8 个仓库源码级分析 |
| 架构 ADR | ✅ 完成，全部已接受 | `02_ARCHITECTURE_DECISIONS/ADR-001~010` |
| 环境与依赖 | ✅ 完成 | `.venv`（Python 3.12.10）+ `requirements*.txt`；实际版本见 ADR-006 §6 |
| 业务代码（第 3 步） | ✅ 解析/切分/抽取/校验/规则可用 | `app/` |
| HITL（第 4 步） | ✅ 条件边 + `interrupt()` + checkpointer | `app/nodes/hitl.py`、`app/review_service.py`、`app/services/checkpointer.py` |
| 解释 / RAG（第 5 步） | ✅ 质量门 + BM25 + 真实语料 | `app/nodes/explain.py`、`app/services/rag.py`、`data/knowledge/` |
| API / UI（第 6 步） | ✅ FastAPI + Streamlit + pending 落盘 | `app/api.py`、`app/ui.py`、`app/report_markdown.py`、`app/services/pending_store.py` |
| 测试 | ✅ 209 个通过 | `tests/`；`pytest` 全绿；Fake LLM 无需 Key |
| 规则集 | ✅ 13 条 | `app/rules/definitions.yaml`（`version: 3`）；6 条新规则各有语料命中集合回归（ADR-010） |
| 评测集 / 基线 | ⏳ 部分完成 | `data/contracts/` 50 份 + `data/eval/gold_contracts.json`（105 条检索期望）+ `eval/results/rules-20261027.json`；**规则级 gold 与准确率仍未做** |
| Git 仓库 | ✅ 已初始化 | `cf0fd63`、`71e8a9d`、`750cca3`、`625e9bd`、`e41d235`、`c7f24a9`，以及后续每步提交 |

> 不要在汇报里说“已通过评测”或“抽取准确率 X%”。当前有**规则级触发基线**（50 份模拟合同：11 份命中 / 39 份未命中，`pass:39 / yellow:9 / red:2`），但它只说明“规则是否触发”，**不是 precision/recall，也不代表合同真的无风险**。

### 2.1 架构决策速览（ADR-001~010）

| ADR | 结论 | 状态 |
|---|---|---|
| 001 图结构 | 确定性顺序主干 + 两个条件边（是否有 red / 是否 approve）+ 单一 HITL 门；不用 Supervisor/并行/单体 ReAct | **已接受**（两条条件边均已实现：`route_by_risk`、`route_after_human_review`） |
| 002 HITL | 节点内 `interrupt()` + checkpointer + `Command(resume=HitlDecision)`；审批前零业务写入；超时 → `unreviewed_red_risk`，绝不自动通过 | **已接受**（第 4 步已实现，回填见 ADR-002 §7） |
| 003 规则/LLM | 规则唯一判级；LLM 只抽 17 字段与解释；schema 禁止 `risk_level`；引文核验、越权表述拦截、失败兜底 | **已接受** |
| 004 持久化 | 运行用 `SqliteSaver`（同步，当前实现）/测试用 `InMemorySaver`；`thread_id=review_id`；pending/报告/审计分离；惰性超时 | **已接受**（ADR-004 原写 `AsyncSqliteSaver`，第 4 步实际用同步 `SqliteSaver`，见 ADR-002 §7） |
| 005 解析/证据 | pypdf + python-docx + TXT；canonical text + 页/全局偏移；`文件名:p页:start-end`；精确/空白规范化定位 | **已接受** |
| 006 环境 | Python 3.12 + LangGraph 1.2.17 等最新稳定依赖；OpenAI 兼容接口；无 Docker/Redis/Postgres | **已接受** |
| 007 范围变更 | 允许 RAG/多智能体/Supervisor（仅路由）；判级/HITL/证据边界不变；默认开关关闭 | **已接受**（2026-10-27；RAG 已实现，多智能体仍未实现） |
| 008 RAG/质量门 | 本地 BM25 + 中文二元组；`source_id#section` 白名单；Python 质量门拦截越权；无命中/配置错误降级 | **已接受**（第 5 步已实现） |
| 009 API/UI | API/UI 只依赖 `ReviewService`；pending 时间戳原子落盘；上传校验；Markdown 纯渲染 | **已接受**（第 6 步已实现） |
| 010 规则扩充/评测 | 规则 7 → 13 条；新规则准入四关；模拟合同拆入 `data/contracts/`；评测只报触发情况 | **已接受**（2026-10-27 第 1 轮已实现） |

---

## 3. 环境准备

### 3.1 本机现状（2026-10-26 验证）

| 项 | 结果 |
|---|---|
| 系统 | Windows，PowerShell 5 |
| 默认 `python` | 3.14（`C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64`） |
| 可用的 3.12 | `py -3.12` → `C:\Users\lenovo\AppData\Local\Python\pythoncore-3.12-64\python.exe` |
| uv 自带 3.12 | `C:\Users\lenovo\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\python.exe` |
| GitHub API | 可访问（HTTP 200） |
| `git clone github.com:443` | 连接被重置；调研用 `codeload.github.com` 快照替代 |
| PyPI | 可访问 |

### 3.2 版本决策（重要）

`开发提示词.md` 写“Python 3.9+”，但 2026-10-26 最新依赖的实际要求是：

| 包 | 最新版本 | requires-python |
|---|---|---|
| langgraph | 1.2.17 | ≥3.10 |
| langchain | 1.4.7 | ≥3.10 |
| langchain-openai | 1.7.2 | ≥3.10 |
| langgraph-checkpoint-sqlite | 3.1.2 | ≥3.10 |
| fastapi | 0.162.0 | ≥3.10 |
| uvicorn | 0.54.0 | ≥3.10 |
| streamlit | 1.66.1 | **≥3.11** |
| pydantic | 2.14.1 | ≥3.10 |
| python-docx | 1.2.0 | ≥3.9 |
| pypdf | 6.21.2 | ≥3.9 |
| pytest | 9.1.1 | ≥3.10 |
| ruff | 0.17.2 | ≥3.7 |

**结论：用 Python 3.12**（本机已装；用户已确认“按建议继续”）。如果必须严格支持 3.9，只能锁旧版本（LangGraph 0.2.x / Streamlit 旧版），会牺牲当前 API 与 HITL 文档能力，且需要额外兼容测试；不建议。该事项已关闭（ISSUE-004），决策记录在 `ADR-006-运行环境与依赖策略.md`。

### 3.3 初始化命令（已执行）

```powershell
cd "d:\A项目\Agent_Alex外贸合同智审助手"

# 1) 创建虚拟环境（用 3.12，不要用默认 3.14）
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip

# 2) 安装依赖（版本锁定在 requirements.txt / requirements-dev.txt）
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

# 3) 验证
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m app.graph_demo
```

实际安装结果（2026-10-26）：Python 3.12.10、LangGraph 1.2.17、Streamlit 1.66.1、FastAPI 0.162.0、Pydantic 2.14.1、pypdf 6.21.2、python-docx 1.2.0、PyYAML 6.0.3、pytest 9.1.1、ruff 0.17.2；无冲突。详见 ADR-006 §6。

> 注意：`pypdf` 是 BSD 许可；不要引入 PyMuPDF（AGPL/商业双许可）作为默认依赖。扫描件 OCR 不在 MVP 范围。

### 3.4 环境变量（`.env.example` 已提供，`.env` 尚未创建）

`.env.example` 已提交；真实 `.env` 尚未创建（没有 Key，不影响最小图与测试）。字段见下方模板。

```dotenv
# .env.example（不提交真实 Key）
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=
LLM_MODEL=gpt-4.1-mini
LLM_TIMEOUT_SECONDS=60
LLM_MAX_REPAIR_RETRIES=1
MAX_EXTRACT_CLAUSES=40

CHECKPOINT_BACKEND=sqlite
CHECKPOINT_SQLITE_PATH=.data/checkpoints.sqlite
HITL_TIMEOUT_MINUTES=30
PENDING_DIR=.data/pending
UPLOAD_DIR=.data/uploads

# RAG（默认关闭）
RAG_ENABLED=false
RAG_KNOWLEDGE_DIR=data/knowledge
RAG_TOP_K=3
RAG_MIN_SCORE=1.0

MAX_UPLOAD_MB=15
MAX_CONTRACT_CHARS=200000
MAX_PAGES=200
```

> 真实 `.env` 必须进 `.gitignore`；代码、日志、README 不得出现 Key。

---

## 4. 目录现状（第 6 步已创建的部分）

```text
Agent_Alex外贸合同智审助手/
├─ 开发提示词.md
├─ requirements.txt / requirements-dev.txt
├─ pyproject.toml                 # ruff + pytest 配置
├─ .env.example                   # 已提供；真实 .env 未创建
├─ .gitignore
├─ README.md
├─ app/
│  ├─ __init__.py
│  ├─ config.py                   # 环境变量、路径、上限（CHECKPOINT_* / HITL_TIMEOUT_MINUTES / PENDING_DIR / UPLOAD_DIR / RAG_*）
│  ├─ schemas.py                  # State/Clause/Evidence/ExtractedFieldSet/RuleEvaluation/Explanation/Report/ApprovalPayload
│  ├─ graph.py                    # 8 节点 + 两条条件边 + 强制 checkpointer
│  ├─ review_service.py           # start/get/resume（幂等 + 惰性超时 + pending 落盘 + review_id RLock）
│  ├─ graph_demo.py               # CLI（SQLite 跨进程；--review-id/--decision）
│  ├─ api.py                      # FastAPI（上传/查询/决定/下载；错误码 400/404/409/413/422）
│  ├─ ui.py                       # Streamlit（上传 → 审批 → 报告 → 下载）
│  ├─ report_markdown.py          # ReviewReport → Markdown（纯渲染）
│  ├─ nodes/
│  │  ├─ ingest.py                # TXT/MD/PDF/DOCX → pages + canonical text + 全局偏移
│  │  ├─ segment.py               # 标题切分 + 合并 + 超长拆分 + 段落 fallback
│  │  ├─ extract.py               # LLM 17 字段抽取（唯一 LLM 抽取节点）
│  │  ├─ validate.py              # 引文核验 + 数值归一 + 一致性 → facts / to_verify
│  │  ├─ rules.py                 # 规则节点（唯一等级来源）
│  │  ├─ hitl.py                  # 审批载荷 + interrupt() + 决策校验 + 两条条件边
│  │  ├─ explain.py               # LLM 解释 + Python 质量门 + RAG 引用白名单 + 规则兜底
│  │  └─ report.py                # 报告汇总（跟随人工终态 + limitation）
│  ├─ rules/
│  │  ├─ definitions.yaml         # 13 条规则（11 文本 + 2 字段，version 3）
│  │  ├─ dsl.py                   # 白名单条件 DSL
│  │  └─ engine.py                # 加载/求值/证据/fail-closed/skipped
│  ├─ services/
│  │  ├─ llm.py                   # 结构化输出 + 1 次修复 + 异常类型 + get_llm()
│  │  ├─ evidence.py              # locate_quote（精确 → NFC/空白规范化）
│  │  ├─ checkpointer.py          # memory/sqlite 工厂 + JsonPlusSerializer 类型登记
│  │  ├─ pending_store.py         # pending 时间戳原子落盘 + review_id 白名单
│  │  └─ rag.py                   # BM25 + 中文二元组 + MD/DOCX 切分 + manifest 校验 + 缓存
│  └─ __main__.py                 # 计划（未创建）
├─ tests/
│  ├─ conftest.py
│  ├─ fakes.py                    # Fake LLM（无需 Key）
│  ├─ test_ingest.py / test_ingest_formats.py / test_segment.py
│  ├─ test_evidence.py / test_llm_service.py / test_extract.py / test_validate.py / test_rules.py
│  │  └─ test_rules.py 含 6 条新规则正反 fixture + 50 份语料命中集合回归 + 样例零误报
│  ├─ test_hitl.py                # HITL 暂停/恢复/幂等/超时/载荷/非法决策（17 个）
│  ├─ test_explain.py             # 解释与质量门（13 个）
│  ├─ test_rag.py                 # BM25/manifest/DOCX/长段/缓存/真实语料（22 个）
│  ├─ test_pending_store.py       # 落盘/跨进程超时/损坏文件/非法 ID（11 个）
│  ├─ test_api.py                 # FastAPI 全流程与错误码（15 个）
│  ├─ test_report_markdown.py     # Markdown 渲染（3 个）
│  ├─ test_ui.py                  # Streamlit 冒烟（1 个）
│  ├─ test_graph.py / test_graph_extraction.py
│  └─ fixtures/pdf_builder.py     # 纯标准库构造最小 PDF
├─ data/
│  ├─ samples/                    # 2 份自拟脱敏合同（TXT）
│  ├─ contracts/                  # 50 份模拟合同（由 eval/prepare_contracts.py 生成，可重建）
│  ├─ eval/gold_contracts.json    # 50 份 / 105 条“条款 → Q 编号 → 期望召回 → 干扰项”
│  └─ knowledge/                  # 真实语料 14 篇 + manifest；模拟合同1..6.md 为评测来源，不进 manifest
├─ eval/
│  ├─ prepare_contracts.py        # 拆分模拟合同 → data/contracts/ + gold
│  ├─ run_eval.py                 # 规则级评测（不调 LLM）→ eval/results/rules-YYYYMMDD.json
│  └─ results/                    # 评测结果
└─ docs/
   └─ devlog/                     # 本目录
```

> 标注“计划”的文件/目录**尚不存在**；不要按规划假设它们已可用。

---

## 5. 启动方式

| 形态 | 命令 | 状态 |
|---|---|---|
| 全链路（TXT，无 Key 走降级） | `.\.venv\Scripts\python.exe -m app.graph_demo` | ✅ 可用（风险样例停在人工确认） |
| 全链路（PDF/DOCX） | `.\.venv\Scripts\python.exe -m app.graph_demo path\to\contract.pdf` | ✅ 可用 |
| 报告 JSON | `.\.venv\Scripts\python.exe -m app.graph_demo --json` | ✅ 可用 |
| 恢复人工决定 | `.\.venv\Scripts\python.exe -m app.graph_demo --review-id <id> --decision approve --reviewer zhangsan` | ✅ 可用（SQLite 跨进程） |
| 超时语义 | `.\.venv\Scripts\python.exe -m app.graph_demo --review-id <id> --decision timeout` | ✅ 可用 → `unreviewed_red_risk` |
| 测试 | `.\.venv\Scripts\python.exe -m pytest` | ✅ 209 个通过 |
| 静态检查 | `.\.venv\Scripts\python.exe -m ruff check .` | ✅ 通过 |
| 命令行（统一入口） | `python -m app --file data/samples/contract.txt` | ⏳ 计划（`__main__.py` 未创建） |
| API | `.\.venv\Scripts\python.exe -m uvicorn app.api:create_app --factory --port 8000` | ✅ 可用（`/docs` 可试；默认 SQLite + 文件 pending） |
| UI | `.\.venv\Scripts\python.exe -m streamlit run app/ui.py` | ✅ 可用（上传/审批/下载） |
| 拆合同 + gold | `.\.venv\Scripts\python.exe eval\prepare_contracts.py` | ✅ 可用（50 份合同 / 105 条映射） |
| 规则评测 | `.\.venv\Scripts\python.exe eval\run_eval.py` | ✅ 可用（无需 Key，输出 `eval/results/rules-YYYYMMDD.json`） |
| 全链路评测（含抽取/解释） | 计划 | ⏳ 未实现（需要 LLM Key，且规则级 gold 未标注） |

> 标 ✅ 的命令已实际执行验证；标 ⏳ 的尚不可用。`--decision` 支持 `approve / reject / changes(request_changes) / timeout`；`--memory` 用内存 checkpointer（仅单进程调试）。API 必须用 `--factory`（`create_app` 是工厂函数，不是模块级 `app`）；多 worker 未支持（ISSUE-019）。

---

## 6. 已确认的设计底线

1. **规则唯一判级**：`red / yellow / pass` 只能由 Python 规则产生；LLM 输出（抽取/解释/专家）里不允许有 `risk_level` 字段。
2. **LLM 只做两件事**：抽取条款要素（缺失写 null）；解释风险与给建议（必须引用原文）。RAG/专家节点只能增强解释，不能新增或改写等级。
3. **HITL 真中断**：节点内 `interrupt()`；checkpointer 持久化；`Command(resume=HitlDecision)` 恢复；审批前零业务写入；超时不自动通过。
4. **失败显式降级**：LLM 失败 → 抽取降级/解释兜底；规则执行异常 → fail-closed 系统 red（`is_system_finding=true`，进入 HITL）；HITL 超时 → `unreviewed_red_risk`；RAG 无命中 → 退化为纯规则解释。
5. **证据可定位**：`文件:第N页:字符start-end`；LLM 引文必须精确出现在条款原文（仅允许空白/Unicode 规范化）；知识引用必须能定位到 `source_id#section`。
6. **抽取状态是一等状态**：`ok / degraded / skipped` 都必须进报告；`degraded` 时字段规则 `skipped`，不得把系统降级伪装成“合同缺少条款”。
7. **图结构**：确定性顺序主干；两个条件边只用于“是否有 red”“是否 approve”；不用并行/单体 ReAct；Supervisor 仅白名单路由（ADR-007）。
8. **持久化**：运行用 SQLite checkpointer，测试用内存；`thread_id=review_id`；pending 时间戳落盘 `.data/pending/<review_id>.json`；报告由 state 派生。
9. **RAG/多智能体默认关闭**：`RAG_ENABLED=false`、`AGENTS_ENABLED=false`；开启后也只用于解释/建议/条款比对；Supervisor 与专家不得判级。
10. **入口分层**：CLI / FastAPI / Streamlit 全部只依赖 `ReviewService`；不拼 `Command(resume=...)`；API/UI 不判级（ADR-009）。
11. **不引入**：Neo4j/GraphRAG、向量数据库、训练模型、Docker、React/Vue、Postgres/Redis、PyMuPDF 默认依赖、无许可证仓库代码。

---

## 7. 已知坑（务必先看）

| # | 坑 | 处理 |
|---|---|---|
| 1 | 默认 `python` 是 3.14，直接 `python -m venv` 会装不上/跑不稳 | 显式用 `py -3.12 -m venv .venv`，命令都用 `.venv\Scripts\python.exe` |
| 2 | `git clone github.com` 在本机被重置 | 依赖安装走 PyPI；拉参考仓库用 `codeload.github.com` tar.gz；不要反复重试 clone |
| 3 | LangGraph resume 会从 `interrupt()` 所在节点顶部重跑 | interrupt 之前只做纯读取；所有写库/外部调用放到 interrupt 之后 |
| 4 | MemorySaver 不跨进程持久化 | 演示/生产用 `sqlite_checkpointer()`（同步 `SqliteSaver`）；MemorySaver 只用于测试（`memory_checkpointer()`） |
| 5 | `interrupt_before` 与节点内 `interrupt()` 两种方案混用会混淆 | 本项目统一用节点内 `interrupt()`；不要同时用 `interrupt_before`（ADR-002） |
| 6 | 让 LLM 输出等级会导致不可回归 | 抽取/解释 schema 都不含 `risk_level`；Pydantic `extra="forbid"` |
| 7 | PDF 解析是最大不确定性 | 只支持文本型 PDF（pypdf）；扫描件明确提示“不支持/需 OCR”；DOCX 用 python-docx；TXT 直接读（ADR-005） |
| 8 | 条款切分错误会让后续全错 | 先写规则切分（条款编号/标题/段落 fallback），加 fixture 快照测试；LLM 不参与切分 |
| 9 | 规则执行异常被静默忽略会漏红风险 | fail-closed：生成系统 red finding（`is_system_finding=true`），进入 HITL；报告中单独分组，不伪装成合同风险 |
| 10 | CUAD 不能代表国际销售合同 | 自建 20–30 条条款级 gold；CUAD 只作方法参考 |
| 11 | 无 LICENSE 仓库不能复制代码 | zihan / Harvey / Sentinel 只借鉴设计；引用 Apache-2.0/MIT 代码需保留声明 |
| 12 | Star 数与质量无关 | 文档中不把 Star 当技术优势；只写代码可验证的行为 |
| 13 | 不要在 README/答辩写无出处的准确率 | 所有指标来自 `eval/results/*.json`，附模型、样本数、日期、命令 |
| 14 | Git 仓库已初始化（`cf0fd63`），新增文件前先看 `.gitignore` | 不要提交 `.venv/`、`.env`、`.data/`、`*.sqlite*`、缓存；每完成一步提交一次 |
| 15 | 同一 review 并发 resume 可能重复应用决策 | 按 `review_id` 加 `asyncio.Lock`；恢复前检查状态幂等（ADR-004） |
| 16 | SQLite WAL 在 Windows 上偶发文件锁 | 连接生命周期由 FastAPI lifespan 管理；关闭前 checkpoint；测试用内存 checkpointer |
| 17 | 解释 LLM 可能改写等级或给出越权结论 | 解释 schema 无等级字段；Quality Gate 拦截“合同无效/已批准/已签署”等表述；失败用规则理由兜底（ADR-003） |
| 18 | `AsyncSqliteSaver` 导入路径容易写错 | 必须 `from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver`；`from_conn_string` 是异步上下文管理器 |
| 19 | `langgraph-checkpoint-sqlite` 会带入 `sqlite-vec` 原生扩展 | 已确认有 Windows amd64 wheel；若安装失败，记录错误并评估改用同步 `SqliteSaver`（需改 ADR） |
| 20 | Pydantic state 的 `timings` 是整体替换，不是合并 | 每个节点返回 `{**state.timings, "xxx_ms": ...}`；不能只返回自己的那一条 |
| 21 | `Settings` 是 frozen dataclass，测试里不能直接改属性 | 用 `dataclasses.replace(settings, max_contract_chars=100)` 后 monkeypatch 模块级 `settings` |
| 22 | Pydantic 只把 `ValueError` 当校验失败；`re.error` 会直接冒泡 | 正则校验里 `except re.error` 转 `ValueError`，保证规则加载期报 `ValidationError` |
| 23 | 缺失条款类规则（如“未约定适用法律”）没有原文命中区间 | 报告显示“无原文证据”是预期行为；不要用模糊匹配伪造证据，HITL/UI 需明确标注 |
| 24 | 文本级“缺失关键词”规则可能被无关表述误命中 | 关键词表要窄；扩规则时先加 fixture/gold，再做误报回归 |
| 25 | pypdf 会提取页眉/页脚/水印，污染条款正文 | MVP 不过滤；规则关键词要窄；扩评测时统计页眉误命中 |
| 26 | PDF 表格/多栏会打乱列顺序 | 只在 `warnings` 提示；重要表格条款必须人工核对；不静默当正确 |
| 27 | 扫描件判定阈值是“总文本 < 50 字符” | 低文本量但真实的 PDF 会被判失败；错误信息要求用户提供可复制文本文件 |
| 28 | DOCX 没有真实页码，统一 `p1` | 报告 limitation 必须说明；不要伪造页码 |
| 29 | `is_heading` 对纯数字编号有三重约束 | 改正则时先跑 `test_body_line_starting_with_number_is_not_heading`，否则正文会被切成标题 |
| 30 | 条款数 > 200 会让整次审查 `status="failed"` | 不是 bug，是防静默截断；UI/API 要提示“拆分合同或调大 `MAX_PAGES`/上限” |
| 31 | PDF 测试 fixture 只支持 ASCII（Helvetica/WinAnsi） | 中文 PDF fixture 需嵌入 CJK 字体，暂未做；不要用 ASCII fixture 证明中文 PDF 可用 |
| 32 | “部分条款抽取成功”若算 `ok`，字段规则会把“没抽到”判成“合同缺条款” | `extraction_status` 只有**全量成功**才是 `ok`；部分覆盖/失败一律 `degraded`，字段规则 skipped |
| 33 | `extra="forbid"` 只挡未知字段，挡不住“字段给了但引文是编的” | 非 null 字段必须有 `quote` 且 `locate_quote` 成功；否则丢弃字段 + `to_verify`（宁缺勿假） |
| 34 | 逐字符 `unicodedata.normalize` 无法合成组合字符 | `locate_quote` 必须整簇规范化（基字符 + 组合符一起），并用起止索引表映射回原文 |
| 35 | 数值字段 LLM 会返回 `"USD 620,000"` 之类带单位文本 | 归一为 float 但检测到单位/币种残留 → `to_verify`；不静默当作可信金额 |
| 36 | 同一字段在多个条款出现且不一致 | 保留首个并 `to_verify`；不自动选“看起来更合理”的值，也不做汇率换算 |
| 37 | `tests/fakes.py` 的 Fake LLM 必须实现 `StructuredLLM` 协议（`model_id` + `invoke`） | 新节点依赖 LLM 时用同一协议，测试注入 `FakeLLM`，禁止在业务代码里写 if-test 分支 |
| 38 | `get_llm()` 是 `lru_cache(maxsize=1)`；测试改 `settings` 后必须 `cache_clear()` | 否则会一直用旧 Key/模型；已在 `test_llm_service.py` 用 try/finally 示范 |
| 39 | 条款数 > `MAX_EXTRACT_CLAUSES`（默认 40）时只抽部分条款 | 按“全量成功才算 ok”的规则，此时字段规则全部 skipped；长合同要么调大上限，要么接受跳过并在报告提示 |
| 40 | SQLite checkpoint 会告警“Deserializing unregistered type app.schemas.X ... will be blocked in a future version” | 必须用 `app/services/checkpointer.py` 的 `_serde()`（`JsonPlusSerializer(allowed_msgpack_modules=[...])`）登记 `app.schemas` 全部 Pydantic 类型；不要直接用裸 `SqliteSaver`/`InMemorySaver` |
| 41 | `SqliteSaver.from_conn_string()` 不接受 `serde` | 手动 `sqlite3.connect(path, check_same_thread=False)` → `SqliteSaver(conn, serde=_serde())`，并在 `finally` 关闭连接 |
| 42 | `invoke()` 暂停时返回值含 `__interrupt__` 键，直接 `ContractReviewState.model_validate(raw)` 会因 extra 字段失败 | 用 `{k: v for k, v in raw.items() if not k.startswith("__")}` 过滤后再校验 |
| 43 | 暂停时 `state.status` 仍是 `running`，不是 `awaiting_human` | `awaiting_human` 由 `ReviewService` 从 `snapshot.next` 派生；不要把状态机写成“节点返回 awaiting_human” |
| 44 | 已终态 review 再次 `resume` 会重跑图/重复生成报告 | `ReviewService.resume()` 先查 `snapshot.next`；不在 `human_review` 且状态属于 `FINAL_STATUSES` 时直接返回现有结果（幂等） |
| 45 | CLI 误把 checkpointer 传给 `ReviewService`（第一个参数是 compiled graph） | 正确写法 `ReviewService(build_graph(checkpointer=sqlite_checkpointer()))`；`SqliteSaver` 没有 `invoke` |
| 46 | `interrupt()` 抛出的暂停不是异常，不会让 CLI 非零退出 | CLI 需要显式判断 `awaiting_human` 并打印 `review_id` 与恢复命令；不要用“进程失败”表示等待审批 |
| 47 | ~~`ReviewService._requested_at` 仅存进程内存，重启后惰性超时失效~~ | 已修复（第 6 步）：`app/services/pending_store.py` 落盘 `.data/pending/<review_id>.json`；缺失/损坏一律不判超时（ISSUE-017） |
| 48 | 人工意见里的 `overrides` 可能引用不存在的 `rule_id` | 节点只产生 warning，不写入报告等级；规则等级永远不会被人工意见改写 |
| 49 | `uvicorn app.api:app` 会失败（模块里只有工厂函数 `create_app`） | 用 `--factory`：`uvicorn app.api:create_app --factory`；或在 `api.py` 末尾加模块级 `app`（本项目故意不加，避免测试共享全局状态） |
| 50 | Streamlit 的 `st.cache_resource` 会跨会话复用 checkpointer 连接 | 用 `atexit` 关闭 SQLite 连接；测试用 `streamlit.testing.v1.AppTest` 只跑首屏，不做多会话并发 |
| 51 | TestClient 必须配 `httpx`，上传必须配 `python-multipart` | 前者在 `requirements-dev.txt`，后者在 `requirements.txt`；缺任一会在测试/上传时直接报错 |
| 52 | FastAPI 里 `Path(...)` 与 `pathlib.Path` 同名冲突 | 别名导入 `from fastapi import Path as ApiPath`；`review_id` 用 `pattern` 校验，非法值走 422 |
| 53 | 用户上传的文件名可能含 `..\`/`../` 或控制字符 | `_safe_filename()` 同时按 `\` 与 `/` 取 basename、去不可打印字符、限制长度；落盘目录固定为 `.data/uploads/<新 uuid>/` |
| 54 | `.doc` 与 `.docx` 是两个不同格式 | `.docx` 用 python-docx；`.doc` 明确 400 并提示另存为 `.docx`（RAG manifest 同样拒绝 `.doc`） |
| 55 | DOCX 法条通常全是 `Normal` 样式，不能靠标题样式切分 | 按 `^第X条` 正则切分，编/章/节作上下文前缀；`目录` 行丢弃；section 用条文号做引用 |
| 56 | 英文 CISG 用 `***Article N***` 而非 Markdown 标题 | `_heading_of()` 同时识别 `#` 标题、`***...***` 与结构性加粗；新增格式先加测试再改正则 |
| 57 | 单条法规超过 1600 字符会让 BM25 与提示词失真 | `_chunk_text()` 按空行段落 + 句末标点二次切分；同一标题依次 `s2`、`s2-2` |
| 58 | 每次 API/UI 请求都重载 500KB 语料会很慢 | `load_knowledge_base` 按 `(目录, manifest+文件 mtime/size)` 缓存；语料变更自动重建，测试用独立目录避免污染 |
| 59 | ICC 官方写作 `Incoterms® 2020`，带注册商标 `®` | 检测版本号的正则必须允许 `[®™]`，否则会把“写了版本”判成“没写版本”（真实误报 40/50，见 ADR-010） |
| 60 | 新规则容易“看起来合理、实际满语料误报” | 每条新规则先在 `data/contracts/` 上跑命中集合，命中集合写进 `EXPECTED_CORPUS_HITS` 回归测试；再跑两份样例确认零误报 |
| 61 | `data/contracts/` 是生成物，不是用户原始语料 | 用 `eval/prepare_contracts.py` 重建；不要手改单份合同，否则 gold 与原文会不一致 |
| 62 | “CIF 没写保险条款”不等于缺陷（Incoterms 默认规则补位） | `R-INS-001` 只在“约定了投保但没写保额/比例”时触发；新增保险类规则前先确认是否与默认规则重复 |
| 63 | 规则数量变化会让多处硬编码断言失败 | 新增/删除规则时同步 `test_load_default_rules`、`test_graph.py` 的规则数断言与文档中的“N 条规则” |
| 64 | 模拟合同自带映射摘要是“检索期望”，不是规则判级 gold | 不要用 `gold_contracts.json` 直接算规则 precision；规则级 gold 需另行标注 `合同 × rule_id → red/yellow/pass` |

---

## 8. 参考资料（按可信度排序）

| 优先级 | 资料 | 用途 |
|---|---|---|
| 1 | 本项目 `docs/devlog/01_RESEARCH_LOG.md` | 8 个仓库的事实、证据文件/行号、借鉴与不借鉴清单 |
| 2 | `开发提示词.md` | 需求、技术约束、禁止事项、交付要求 |
| 3 | aurelien-henrion/contract-agent（MIT） | 双 schema、Python 复核、HITL 安全写入门、脚本化 LLM 测试 |
| 4 | laolaola278-dev/enterprise-contract-review-agent（Apache-2.0） | 分页/字符偏移、citation、审计、确定性评测 |
| 5 | Harvey-cream/Langchain_DG（无 LICENSE） | 只读设计：Quality Gate、证据精确定位、等级下限、越权拦截 |
| 6 | zihan154896-jpg/intelligent-contract-review（无 LICENSE） | 只读设计：结构化修复重试、checkpointer 工厂、降级、Badcase |
| 7 | bcefghj/multi-agent-contract-review（Apache-2.0） | 规则 DSL 框架；**其 HITL 与 94% 指标不要照搬** |

---

## 9. 本次调研的第三方代码使用声明

- 没有把任何第三方仓库的源代码复制进本项目。
- 后续若复用 Apache-2.0 / MIT 代码，必须在文件头注明来源仓库、文件路径、许可证，并在 `README.md` 的“第三方代码与许可”一节列出。
- zihan / Harvey / Sentinel 无 LICENSE，**禁止复制代码**，只能按设计思想重写。

---

## 10. 下一步交接动作

1. ~~等用户确认 ADR-001 ~ ADR-005~~ ✅ 已确认（2026-10-26，全部“已接受”）。
2. ~~创建 `.venv`、安装依赖、`.gitignore`、git init~~ ✅ 已完成（Python 3.12.10，提交 `cf0fd63`）。
3. ~~最小图 ingest → segment → rules → report 跑通~~ ✅ 已完成（45 个测试通过）。
4. 下一步按顺序：
   - ~~**第 2 步**：`ingest` 接入 PDF（pypdf）/DOCX（python-docx）；`segment` 加标题识别、超长条款拆分、完整 `clause_type` 表；补 PDF/DOCX fixture。~~ ✅ 已完成（2026-10-26，63 个测试）。
   - ~~**第 3 步**：`app/services/llm.py` + `services/evidence.py` + `nodes/extract.py` + `nodes/validate.py`；Fake LLM 测试，无需 Key。~~ ✅ 已完成（2026-10-26，115 个测试；规则 5 → 7 条）。
   - ~~**第 4 步**：`route_by_risk` 条件边 + `interrupt()` + checkpointer（测试 `InMemorySaver`，运行 `SqliteSaver`）+ HITL 测试。~~ ✅ 已完成（2026-10-27，131 个测试；14 个 HITL 测试；SQLite 跨进程实测）。
   - ~~**第 5 步**：`nodes/explain.py` + Quality Gate + 报告合并；RAG MVP（BM25/字符 n-gram，默认 `RAG_ENABLED=false`）。~~ ✅ 已完成（2026-10-27，160 个测试）。
   - ~~**第 6 步**：FastAPI + Streamlit（上传、运行、展示/确认、下载；`.data/pending` 落盘 + 锁）。~~ ✅ 已完成（2026-10-27，197 个测试；真实语料 14 篇接入）。
   - **第四阶段第 1 轮（已完成，2026-10-27）**：规则 7 → 13 条（ADR-010）；50 份模拟合同拆入 `data/contracts/`；`eval/run_eval.py` 跑出触发基线（11/50 命中）；209 个测试通过。
   - **下一步（第四阶段）**：
     - 规则级 gold：为 50 份合同标注 `合同 × rule_id → red/yellow/pass + span`，再算 micro P/R/F1（ISSUE-005/020）；
     - 留出验证：新规则是在同一批 50 份合同上设计的，需另找/另写独立合同集做泛化验证（ISSUE-020）；
     - 继续补规则主题：不可抗力、责任上限、质保期、所有权保留、合规（ISSUE-009，当前 39/50 未命中）；
     - RAG 检索评测：先做 `100问题.md` → manifest 映射（ISSUE-018），再调 `RAG_TOP_K`/`RAG_MIN_SCORE`；
     - 语料授权与 `effective_date` 复核（ISSUE-015）；多智能体范围（ISSUE-016）阶段 B 再定。
6. 每完成一个阶段：更新 `00_PROJECT_STATE.md`、写当日 `03_DEV_LOGS/YYYY-MM-DD.md`、更新本文件的“当前完成度/已知坑”、更新 `05_OPEN_ISSUES.md`。

---

## 11. RAG / 多智能体边界（ADR-007）

| 允许 | 禁止 |
|---|---|
| 本地知识检索增强解释/建议（BM25、字符 n-gram） | 用 RAG 结果决定 `red / yellow / pass` |
| 知识引用格式 `source_id#section` | 引用未登记/无授权的文档 |
| 专家节点补充解释（付款/交付/争议） | 专家改级、新增 red/yellow、越权给法律结论 |
| Supervisor 白名单路由 | Supervisor 判级、自由规划、动态生成节点 |
| 开关控制（默认关闭） | 默认开启、隐式联网调用 embedding 服务 |

默认行为：`RAG_ENABLED=false` 时 `explain` 只用规则 `reason` + 合同原文；RAG 无命中时必须退化为纯规则解释，并在 `limitations` 说明“未使用知识库”。
