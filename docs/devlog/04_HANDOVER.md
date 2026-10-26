# 开发交接文档（Handover）

> 更新时间：2026-10-26 23:34
> 当前状态：**第二阶段 ADR 初稿完成，业务代码尚未开始**
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

硬约束来自根目录 `开发提示词.md`：技术栈 Python / LangGraph / Streamlit / FastAPI / Pydantic；禁止 Supervisor、多智能体、前端框架、RAG 知识库、训练模型、Docker；规则决定等级，LLM 只抽取与解释；HITL 必须暂停/恢复；全部代码要解释清、能测试、边界明确。

---

## 2. 当前完成度

| 项 | 状态 | 证据 |
|---|---|---|
| GitHub 调研 | ✅ 完成 | `01_RESEARCH_LOG.md`，8 个仓库源码级分析 |
| 架构 ADR | ✅ 初稿完成，待确认 | `02_ARCHITECTURE_DECISIONS/ADR-001~006`；ADR-006 已接受 |
| 业务代码 | ⏳ 未开始 | 无 `app/`、`pyproject.toml`、`requirements.txt` |
| 测试 | ⏳ 未开始 | 无 `tests/` |
| 评测集 | ⏳ 未开始 | 无 `data/eval/` |
| Git 仓库 | ⚠️ 未初始化 | 当前目录不是 git 仓库（`git status` 返回 not a git repository） |

> 不要在汇报里说“已有代码/已通过测试”；目前只有文档。

### 2.1 架构决策速览（ADR-001~006）

| ADR | 结论 | 状态 |
|---|---|---|
| 001 图结构 | 确定性顺序主干 + 两个条件边（是否有 red / 是否 approve）+ 单一 HITL 门；不用 Supervisor/并行/单体 ReAct | 提议 |
| 002 HITL | 节点内 `interrupt()` + checkpointer + `Command(resume=HitlDecision)`；审批前零业务写入；超时 → `unreviewed_red_risk`，绝不自动通过 | 提议 |
| 003 规则/LLM | 规则唯一判级；LLM 只抽 17 字段与解释；schema 禁止 `risk_level`；引文核验、越权表述拦截、失败兜底 | 提议 |
| 004 持久化 | 运行用 `AsyncSqliteSaver`，测试用 `InMemorySaver`；`thread_id=review_id`；pending/报告/审计分离；惰性超时 | 提议 |
| 005 解析/证据 | pypdf + python-docx + TXT；canonical text + 页/全局偏移；`文件名:p页:start-end`；精确/空白规范化定位 | 提议 |
| 006 环境 | Python 3.12 + LangGraph 1.2.17 等最新稳定依赖；OpenAI 兼容接口；无 Docker/Redis/Postgres | **已接受** |

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

### 3.3 建议的初始化命令（尚未执行）

```powershell
cd "d:\A项目\Agent_Alex外贸合同智审助手"

# 1) 创建虚拟环境（用 3.12，不要用默认 3.14）
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip

# 2) 安装运行依赖（版本以 2026-10-26 最新为准；锁定在 requirements.txt）
.\.venv\Scripts\python.exe -m pip install `
  langgraph==1.2.17 `
  langchain==1.4.7 `
  langchain-openai==1.7.2 `
  langgraph-checkpoint-sqlite==3.1.2 `
  fastapi==0.162.0 `
  uvicorn==0.54.0 `
  streamlit==1.66.1 `
  pydantic==2.14.1 `
  python-docx==1.2.0 `
  pypdf==6.21.2 `
  python-dotenv==1.2.4 `
  pytest==9.1.1 `
  pytest-asyncio==1.4.1 `
  ruff==0.17.2

# 3) 验证
.\.venv\Scripts\python.exe -c "import langgraph, langchain, streamlit, fastapi, pydantic; print('ok')"
.\.venv\Scripts\python.exe -m pytest -q
```

> 注意：`pypdf` 是 BSD 许可；不要引入 PyMuPDF（AGPL/商业双许可）作为默认依赖。扫描件 OCR 不在 MVP 范围。

### 3.4 环境变量（计划）

```dotenv
# .env.example（不提交真实 Key）
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=
LLM_MODEL=gpt-4.1-mini
LLM_TIMEOUT_SECONDS=60
LLM_MAX_REPAIR_RETRIES=1

CHECKPOINT_BACKEND=sqlite
CHECKPOINT_SQLITE_PATH=.data/checkpoints.sqlite
HITL_TIMEOUT_MINUTES=30

MAX_UPLOAD_MB=15
MAX_CONTRACT_CHARS=200000
```

> 真实 `.env` 必须进 `.gitignore`；代码、日志、README 不得出现 Key。

---

## 4. 目录规划（待创建）

```text
Agent_Alex外贸合同智审助手/
├─ 开发提示词.md
├─ pyproject.toml                 # 或 requirements.txt + requirements-dev.txt
├─ .env.example
├─ .gitignore
├─ README.md                      # 项目介绍、启动、评测结果
├─ app/
│  ├─ __init__.py
│  ├─ config.py                   # 环境变量、路径、上限
│  ├─ schemas.py                  # Pydantic：Clause/Evidence/RuleFinding/HitlDecision/State
│  ├─ graph.py                    # LangGraph 组装 + checkpointer
│  ├─ graph_demo.py               # 最小图（无 LLM）演示入口
│  ├─ nodes/
│  │  ├─ ingest.py                # PDF/DOCX/TXT → pages + 全文 + 偏移
│  │  ├─ segment.py               # 条款切分 → Clause[]
│  │  ├─ extract.py               # LLM 结构化抽取（唯一 LLM 抽取节点）
│  │  ├─ validate.py              # 引文核验/日期期限/一致性/to_verify
│  │  ├─ rules.py                 # 规则引擎（唯一等级来源）
│  │  ├─ hitl.py                  # interrupt() + 决策应用
│  │  ├─ explain.py               # LLM 解释（不得改级）
│  │  └─ report.py                # 报告汇总
│  ├─ rules/
│  │  ├─ definitions.yaml         # rule_id/severity/条件/理由/建议
│  │  └─ engine.py                # 纯函数，无 LLM
│  ├─ services/
│  │  ├─ llm.py                   # 结构化输出 + 修复重试 + 超时
│  │  ├─ evidence.py             # locate_quote / citation（共享）
│  │  ├─ checkpointer.py          # SQLite/Memory 工厂
│  │  └─ review_store.py         # pending/报告/审计落盘
│  ├─ api.py                      # FastAPI：POST /review, POST /resume, GET /review
│  ├─ ui.py                       # Streamlit 上传/运行/确认/下载
│  └─ __main__.py                 # 命令行入口（可选）
├─ tests/
│  ├─ test_ingest.py
│  ├─ test_segment.py
│  ├─ test_rules.py
│  ├─ test_validate.py
│  ├─ test_graph.py               # Fake LLM + 条件边
│  ├─ test_hitl.py                # interrupt/resume/审批前零写入/超时
│  └─ fixtures/
├─ data/
│  ├─ samples/                    # 3 份脱敏演示合同
│  └─ eval/                       # 评测集 + gold
├─ eval/
│  ├─ run_eval.py
│  ├─ metrics.py
│  └─ results/                    # 每次评测输出 JSON（含模型/日期/样本数）
└─ docs/
   └─ devlog/                     # 本目录
```

> 以上是**规划**，不是已存在目录。创建前先确认 `05_OPEN_ISSUES.md` 的未决项。

---

## 5. 启动方式（代码完成后应支持）

| 形态 | 命令（计划） | 用途 |
|---|---|---|
| 最小图 | `python -m app.graph_demo` | 无 LLM 跑通 ingest → rules → report |
| 命令行 | `python -m app --file data/samples/contract.txt` | 快速本地验证 |
| API | `uvicorn app.api:app --reload` | `POST /review`、`POST /review/{id}/resume`、`GET /review/{id}` |
| UI | `streamlit run app/ui.py` | 演示：上传 → 风险列表 → 红色风险人工确认 → 报告下载 |
| 测试 | `python -m pytest -q` | 单元 + 图 + HITL（Fake LLM，无需 Key） |
| 规则评测 | `python eval/run_eval.py --mode rules` | 确定性，进 CI |
| 全链路评测 | `python eval/run_eval.py --mode full` | 需要 LLM Key，手动跑 |

> 当前这些命令都还不可用，因为代码未创建。

---

## 6. 已确认的设计底线

1. **规则唯一判级**：`red / yellow / pass` 只能由 Python 规则产生；LLM 输出里不允许有 `risk_level` 字段。
2. **LLM 只做两件事**：抽取条款要素（缺失写 null）；解释风险与给建议（必须引用原文）。
3. **HITL 真中断**：节点内 `interrupt()`；checkpointer 持久化；`Command(resume=HitlDecision)` 恢复；审批前零业务写入；超时不自动通过。
4. **失败显式降级**：LLM 失败 → 抽取降级/解释兜底；规则执行异常 → fail-closed 系统 red（`is_system_finding=true`，进入 HITL）；HITL 超时 → `unreviewed_red_risk`。
5. **证据可定位**：`文件:第N页:字符start-end`；LLM 引文必须精确出现在条款原文（仅允许空白/Unicode 规范化）。
6. **图结构**：确定性顺序主干；只有“是否有 red”“是否 approve”两个条件边；不用 Supervisor/并行/单体 ReAct。
7. **持久化**：运行用 SQLite checkpointer，测试用内存；`thread_id=review_id`；报告/pending/审计与 checkpoint 分离。
8. **不引入**：Supervisor、多智能体、RAG 知识库、Neo4j、训练模型、Docker、React/Vue、Postgres/Redis、PyMuPDF 默认依赖、无许可证仓库代码。

---

## 7. 已知坑（务必先看）

| # | 坑 | 处理 |
|---|---|---|
| 1 | 默认 `python` 是 3.14，直接 `python -m venv` 会装不上/跑不稳 | 显式用 `py -3.12 -m venv .venv`，命令都用 `.venv\Scripts\python.exe` |
| 2 | `git clone github.com` 在本机被重置 | 依赖安装走 PyPI；拉参考仓库用 `codeload.github.com` tar.gz；不要反复重试 clone |
| 3 | LangGraph resume 会从 `interrupt()` 所在节点顶部重跑 | interrupt 之前只做纯读取；所有写库/外部调用放到 interrupt 之后 |
| 4 | MemorySaver 不跨进程持久化 | 演示/生产用 `AsyncSqliteSaver`；MemorySaver 只用于测试 |
| 5 | `interrupt_before` 与节点内 `interrupt()` 两种方案混用会混淆 | 本项目统一用节点内 `interrupt()`；不要同时用 `interrupt_before`（ADR-002） |
| 6 | 让 LLM 输出等级会导致不可回归 | 抽取/解释 schema 都不含 `risk_level`；Pydantic `extra="forbid"` |
| 7 | PDF 解析是最大不确定性 | 只支持文本型 PDF（pypdf）；扫描件明确提示“不支持/需 OCR”；DOCX 用 python-docx；TXT 直接读（ADR-005） |
| 8 | 条款切分错误会让后续全错 | 先写规则切分（条款编号/标题/段落 fallback），加 fixture 快照测试；LLM 不参与切分 |
| 9 | 规则执行异常被静默忽略会漏红风险 | fail-closed：生成系统 red finding（`is_system_finding=true`），进入 HITL；报告中单独分组，不伪装成合同风险 |
| 10 | CUAD 不能代表国际销售合同 | 自建 20–30 条条款级 gold；CUAD 只作方法参考 |
| 11 | 无 LICENSE 仓库不能复制代码 | zihan / Harvey / Sentinel 只借鉴设计；引用 Apache-2.0/MIT 代码需保留声明 |
| 12 | Star 数与质量无关 | 文档中不把 Star 当技术优势；只写代码可验证的行为 |
| 13 | 不要在 README/答辩写无出处的准确率 | 所有指标来自 `eval/results/*.json`，附模型、样本数、日期、命令 |
| 14 | 当前目录不是 git 仓库 | 阶段 3 开始时先 `git init` + `.gitignore`（`.venv/`、`.env`、`.data/`、`*.sqlite*`、`__pycache__/`），每次阶段提交 |
| 15 | 同一 review 并发 resume 可能重复应用决策 | 按 `review_id` 加 `asyncio.Lock`；恢复前检查状态幂等（ADR-004） |
| 16 | SQLite WAL 在 Windows 上偶发文件锁 | 连接生命周期由 FastAPI lifespan 管理；关闭前 checkpoint；测试用内存 checkpointer |
| 17 | 解释 LLM 可能改写等级或给出越权结论 | 解释 schema 无等级字段；Quality Gate 拦截“合同无效/已批准/已签署”等表述；失败用规则理由兜底（ADR-003） |
| 18 | `AsyncSqliteSaver` 导入路径容易写错 | 必须 `from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver`；`from_conn_string` 是异步上下文管理器 |
| 19 | `langgraph-checkpoint-sqlite` 会带入 `sqlite-vec` 原生扩展 | 已确认有 Windows amd64 wheel；若安装失败，记录错误并评估改用同步 `SqliteSaver`（需改 ADR） |

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

1. 等用户确认 `ADR-001 ~ ADR-005`（ADR-006 已接受）。
2. 确认后进入第三阶段第 1 步：创建 `.venv`（Python 3.12）、安装依赖并记录实际版本；创建 `.gitignore`；初始化 git。
3. 写最小可运行图（2–3 个纯函数节点：ingest → rules → report），验证环境、编译、调用链；先不接 LLM/HITL。
4. 最小图跑通后，按 ADR 逐个加：规则引擎 → 文档解析/条款切分 → LLM 抽取 → 条件边/HITL → LLM 解释 → 报告 → FastAPI/Streamlit。
5. 每完成一个阶段：更新 `00_PROJECT_STATE.md`、写当日 `03_DEV_LOGS/YYYY-MM-DD.md`、更新本文件的“当前完成度/已知坑”。
