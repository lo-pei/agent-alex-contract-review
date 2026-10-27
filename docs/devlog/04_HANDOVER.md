# 开发交接文档（Handover）

> 更新时间：2026-10-26（第三阶段第 3 步完成后）
> 当前状态：**第三阶段第 3 步完成：LLM 要素抽取 + Python 校验已接入图（`ingest → segment → extract → validate → rules → report`）；115 个测试通过；仍无 HITL/解释/API/UI**
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
| 架构 ADR | ✅ 完成，全部已接受 | `02_ARCHITECTURE_DECISIONS/ADR-001~006` |
| 环境与依赖 | ✅ 完成 | `.venv`（Python 3.12.10）+ `requirements*.txt`；实际版本见 ADR-006 §6 |
| 业务代码（第 3 步） | 🚧 解析/切分/抽取/校验/规则/报告可用 | `app/`；尚无 HITL / 解释 / API / UI |
| 测试 | 🚧 115 个通过 | `tests/`；`pytest` 全绿；Fake LLM 无需 Key |
| 评测集 | ⏳ 未开始 | 无 `data/eval/`、无 `eval/results/`；**没有任何准确率数据** |
| Git 仓库 | ✅ 已初始化 | 提交 `cf0fd63`、`71e8a9d`、`750cca3`，以及 `feat: 接入LLM要素抽取与Python校验` |

> 不要在汇报里说“已有 HITL/API/UI”或“已通过评测”或“抽取准确率 X%”；当前只有解析、切分、抽取（Fake LLM 已验证）、校验、规则与报告。

### 2.1 架构决策速览（ADR-001~006）

| ADR | 结论 | 状态 |
|---|---|---|
| 001 图结构 | 确定性顺序主干 + 两个条件边（是否有 red / 是否 approve）+ 单一 HITL 门；不用 Supervisor/并行/单体 ReAct | **已接受** |
| 002 HITL | 节点内 `interrupt()` + checkpointer + `Command(resume=HitlDecision)`；审批前零业务写入；超时 → `unreviewed_red_risk`，绝不自动通过 | **已接受** |
| 003 规则/LLM | 规则唯一判级；LLM 只抽 17 字段与解释；schema 禁止 `risk_level`；引文核验、越权表述拦截、失败兜底 | **已接受** |
| 004 持久化 | 运行用 `AsyncSqliteSaver`，测试用 `InMemorySaver`；`thread_id=review_id`；pending/报告/审计分离；惰性超时 | **已接受** |
| 005 解析/证据 | pypdf + python-docx + TXT；canonical text + 页/全局偏移；`文件名:p页:start-end`；精确/空白规范化定位 | **已接受** |
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

MAX_UPLOAD_MB=15
MAX_CONTRACT_CHARS=200000
MAX_PAGES=200
```

> 真实 `.env` 必须进 `.gitignore`；代码、日志、README 不得出现 Key。

---

## 4. 目录现状（第 3 步已创建的部分）

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
│  ├─ config.py                   # 环境变量、路径、上限（MAX_PAGES / MAX_EXTRACT_CLAUSES）
│  ├─ schemas.py                  # State/Clause/Evidence/FieldValue/ExtractedFieldSet/RuleEvaluation/Report
│  ├─ graph.py                    # 6 节点顺序主干
│  ├─ graph_demo.py               # 演示入口（无 Key 自动走抽取降级路径）
│  ├─ nodes/
│  │  ├─ ingest.py                # TXT/MD/PDF/DOCX → pages + canonical text + 全局偏移
│  │  ├─ segment.py               # 标题切分 + 合并 + 超长拆分 + 段落 fallback
│  │  ├─ extract.py               # LLM 17 字段抽取（唯一 LLM 抽取节点）
│  │  ├─ validate.py              # 引文核验 + 数值归一 + 一致性 → facts / to_verify
│  │  ├─ rules.py                 # 规则节点（唯一等级来源）
│  │  ├─ report.py                # 报告汇总（抽取状态 limitation）
│  │  ├─ hitl.py                  # 计划（未创建）
│  │  └─ explain.py               # 计划（未创建）
│  ├─ rules/
│  │  ├─ definitions.yaml         # 7 条规则（5 文本 + 2 字段，version 2）
│  │  ├─ dsl.py                   # 白名单条件 DSL
│  │  └─ engine.py                # 加载/求值/证据/fail-closed/skipped
│  ├─ services/
│  │  ├─ llm.py                   # 结构化输出 + 1 次修复 + 异常类型 + get_llm()
│  │  ├─ evidence.py              # locate_quote（精确 → NFC/空白规范化）
│  │  └─ checkpointer.py          # 计划（未创建）
│  ├─ review_store.py             # 计划（未创建）
│  ├─ api.py                      # 计划（未创建）
│  ├─ ui.py                       # 计划（未创建）
│  └─ __main__.py                 # 计划（未创建）
├─ tests/
│  ├─ conftest.py
│  ├─ fakes.py                    # Fake LLM（无需 Key）
│  ├─ test_ingest.py              # TXT/编码/上限
│  ├─ test_ingest_formats.py      # PDF/DOCX/扫描件/加密/页数/文件头/表格顺序
│  ├─ test_segment.py             # 标题/合并/拆分/上限/页面映射
│  ├─ test_evidence.py            # 引文定位（精确/空白/NFC/失败）
│  ├─ test_llm_service.py         # 修复重试/异常/未配置
│  ├─ test_extract.py             # Fake LLM 成功/失败隔离/降级/上限/注入防护
│  ├─ test_validate.py            # 定位/丢弃/数值/冲突/一致性
│  ├─ test_rules.py               # 文本规则 + 字段规则 skipped/触发
│  ├─ test_graph.py               # 无 Key 全链路降级
│  ├─ test_graph_extraction.py    # Fake LLM 全链路
│  └─ fixtures/
│     └─ pdf_builder.py           # 纯标准库构造最小 PDF
├─ data/
│  └─ samples/                    # 2 份自拟脱敏合同（TXT）
├─ eval/                          # 计划（未创建）
└─ docs/
   └─ devlog/                     # 本目录
```

> 标注“计划”的文件/目录**尚不存在**；不要按规划假设它们已可用。

---

## 5. 启动方式

| 形态 | 命令 | 状态 |
|---|---|---|
| 全链路（TXT，无 Key 走降级） | `.\.venv\Scripts\python.exe -m app.graph_demo` | ✅ 可用 |
| 全链路（PDF/DOCX） | `.\.venv\Scripts\python.exe -m app.graph_demo path\to\contract.pdf` | ✅ 可用 |
| 报告 JSON | `.\.venv\Scripts\python.exe -m app.graph_demo --json` | ✅ 可用 |
| 测试 | `.\.venv\Scripts\python.exe -m pytest` | ✅ 115 个通过 |
| 静态检查 | `.\.venv\Scripts\python.exe -m ruff check .` | ✅ 通过 |
| 命令行 | `python -m app --file data/samples/contract.txt` | ⏳ 计划（`__main__.py` 未创建） |
| API | `uvicorn app.api:app --reload` | ⏳ 计划（`api.py` 未创建） |
| UI | `streamlit run app/ui.py` | ⏳ 计划（`ui.py` 未创建） |
| 规则评测 | `python eval/run_eval.py --mode rules` | ⏳ 计划（`eval/` 未创建） |
| 全链路评测 | `python eval/run_eval.py --mode full` | ⏳ 计划（需要 LLM Key） |

> 标 ✅ 的命令已实际执行验证；标 ⏳ 的尚不可用。

---

## 6. 已确认的设计底线

1. **规则唯一判级**：`red / yellow / pass` 只能由 Python 规则产生；LLM 输出里不允许有 `risk_level` 字段。
2. **LLM 只做两件事**：抽取条款要素（缺失写 null）；解释风险与给建议（必须引用原文）。
3. **HITL 真中断**：节点内 `interrupt()`；checkpointer 持久化；`Command(resume=HitlDecision)` 恢复；审批前零业务写入；超时不自动通过。
4. **失败显式降级**：LLM 失败 → 抽取降级/解释兜底；规则执行异常 → fail-closed 系统 red（`is_system_finding=true`，进入 HITL）；HITL 超时 → `unreviewed_red_risk`。
5. **证据可定位**：`文件:第N页:字符start-end`；LLM 引文必须精确出现在条款原文（仅允许空白/Unicode 规范化）。
6. **抽取状态是一等状态**：`ok / degraded / skipped` 都必须进报告；`degraded` 时字段规则 `skipped`，不得把系统降级伪装成“合同缺少条款”。
7. **图结构**：确定性顺序主干；只有“是否有 red”“是否 approve”两个条件边；不用 Supervisor/并行/单体 ReAct。
8. **持久化**：运行用 SQLite checkpointer，测试用内存；`thread_id=review_id`；报告/pending/审计与 checkpoint 分离。
9. **不引入**：Supervisor、多智能体、RAG 知识库、Neo4j、训练模型、Docker、React/Vue、Postgres/Redis、PyMuPDF 默认依赖、无许可证仓库代码。

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
   - **第 4 步（当前下一步）**：`is_red` 条件边 + `interrupt()` + checkpointer（测试用 InMemorySaver，运行用 AsyncSqliteSaver）+ 8 条 HITL 测试。
   - **第 5 步**：`nodes/explain.py` + Quality Gate + 报告合并。
   - **第 6 步**：FastAPI + Streamlit。
   - 规则扩到 10–12 条（ISSUE-009），再建 20–30 条 gold（ISSUE-005）。
5. 每完成一个阶段：更新 `00_PROJECT_STATE.md`、写当日 `03_DEV_LOGS/YYYY-MM-DD.md`、更新本文件的“当前完成度/已知坑”、更新 `05_OPEN_ISSUES.md`。
