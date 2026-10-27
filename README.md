# Agent Alex · 外贸合同智审助手

面向**国际货物销售合同**的 AI 预审智能体：上传合同 → 条款切分 → LLM 抽取关键要素 → **Python 规则引擎判定红/黄/绿风险**（唯一等级来源）→ 红色风险经 **LangGraph `interrupt()` 真人工确认** → LLM 依据规则结果与原文生成解释 → 输出可追溯报告。

> 当前处于**第四阶段（测试与评测）第 3 轮**：第三阶段的 `ingest → segment → extract → validate → rules → [条件边] → human_review → explain_risks → report` 已全部打通，支持 **TXT / Markdown / 文本型 PDF / DOCX** 解析、标题式条款切分、LLM 17 字段要素抽取与 Python 引文校验，**13 条规则**（11 条文本 + 2 条字段，`version: 4` 已覆盖中文与主要英文写法），红色风险触发 **LangGraph `interrupt()` 真暂停**，经 `Command(resume=...)` 恢复后由 LLM 生成**带原文与知识引用**的解释。交付入口：**CLI + FastAPI + Streamlit**；未配置 `LLM_API_KEY` 时抽取降级、解释回退规则理由，字段规则标记跳过。评测：50 份模拟合同 + 21 个 silver gold 现象 + **三批留出集 28 份**；**当前唯一未被“消耗”的 holdout3 给出规则级 P=1.00 / R=0.571 / F1=0.727**（silver gold 待人工复核）。详见 [`docs/devlog/00_PROJECT_STATE.md`](docs/devlog/00_PROJECT_STATE.md)。

## 当前完成度

| 阶段 | 状态 | 说明 |
|---|---|---|
| 1. GitHub 调研 | ✅ | 8 个开源项目源码级分析，产出借鉴/不借鉴清单 |
| 2. 架构设计 | ✅ | ADR-001 ~ ADR-011 全部已接受 |
| 3. 代码实现 | ✅ 第 6 步完成 | 环境、8 节点图、规则引擎（13 条规则）、PDF/DOCX/TXT 解析、标题切分、LLM 抽取 + 引文校验、HITL 真中断/恢复、LLM 解释 + Python 质量门、本地 BM25 RAG（默认关闭，真实语料 14 篇）、FastAPI + Streamlit、228 个测试 |
| 4. 测试与评测 | ⏳ 第 3 轮完成 | 50 份模拟合同 + 21 个 silver gold 现象 + 三批留出集 28 份；三组指标（rule/contract/coverage）；**holdout3（唯一未消耗）P=1.00 / R=0.571 / F1=0.727，silver gold 待人工复核**；检索评测未做 |
| 5. 文档与交付 | ⏳ 进行中 | 开发日志、ADR、交接文档、评测结果与 RAG 资料清单已建立 |

## 技术栈

- Python **3.12**（`开发提示词.md` 原写 3.9+，但 Streamlit 1.66.1 要求 ≥3.11，LangGraph 1.2 要求 ≥3.10；决策见 [ADR-006](docs/devlog/02_ARCHITECTURE_DECISIONS/ADR-006-运行环境与依赖策略.md)）
- LangGraph 1.2.17 + LangChain 1.4.7（含 `langgraph-checkpoint-sqlite`）
- Pydantic 2.14（结构化输出与状态契约）
- FastAPI 0.162 + Uvicorn 0.54（本地 HTTP 接口）
- Streamlit 1.66（人工复核界面）
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

# 4) FastAPI（默认 SQLite checkpointer + 落盘 pending；单 worker 演示）
.\.venv\Scripts\python.exe -m uvicorn app.api:create_app --factory --port 8000
# 打开 http://127.0.0.1:8000/docs 试接口：
#   POST /api/reviews（上传）→ awaiting_human=true
#   POST /api/reviews/{id}/decisions  {"action":"approve","reviewer":"zhangsan"}
#   GET  /api/reviews/{id}/report?format=json|markdown

# 5) Streamlit 人工复核界面
.\.venv\Scripts\python.exe -m streamlit run app/ui.py
# 上传 → 开始审查 → 查看审批载荷 → 批准/要求修改/拒绝/标记超时 → 下载 JSON/Markdown

# 6) 测试与静态检查
.\.venv\Scripts\python.exe -m pytest
# 228 passed

.\.venv\Scripts\python.exe -m ruff check .
# All checks passed!

# 7) 规则级评测（不调用 LLM，不需要 Key）
.\.venv\Scripts\python.exe eval\prepare_contracts.py
# 50 份模拟合同 → data/contracts/；105 条映射 → data/eval/gold_contracts.json
.\.venv\Scripts\python.exe eval\run_eval.py
# 主集 50 份：命中 11 份；规则级 TP=11 FP=0 FN=0（同分布，仅作回归守卫）
# 合同级 P=1.00 R=0.79；覆盖率 21 个 gold 现象中 11 个有规则（0.5238）

# 8) 留出集评测——对外报数只能用**当前未被消耗**的那一批
# ① holdout3（H21–H28，8 份，唯一未消耗）：引用这一组
.\.venv\Scripts\python.exe eval\run_eval.py --contracts data\contracts_holdout3 `
  --gold data\eval\gold_holdout3.json --gold-rules data\eval\gold_holdout3.json --tag holdout3
# 规则级 TP=4 FP=0 FN=3 → P=1.00 R=0.571 F1=0.727；漏报 H21（“亦可…起诉”）、H22（“负责支付…运费”）、H24（“thirty-six (36) hours”）

# ② 已消耗样本（H01–H08 / H09–H20）：只作回归守卫，不得对外报数
.\.venv\Scripts\python.exe eval\run_eval.py --contracts data\contracts_holdout `
  --gold data\eval\gold_holdout.json --gold-rules data\eval\gold_holdout.json --tag holdout
# 修复 H01/H03 后 TP=7 FP=0 FN=0（已消耗 → 回归结果，不是泛化证据）
.\.venv\Scripts\python.exe eval\run_eval.py --contracts data\contracts_holdout2 `
  --gold data\eval\gold_holdout2.json --gold-rules data\eval\gold_holdout2.json --tag holdout2
# 12 份：TP=9 FP=0 FN=0 TN=123（修掉子串误命中与窗口截断后）
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
PENDING_DIR=.data/pending
UPLOAD_DIR=.data/uploads

# RAG（默认关闭；data/knowledge 已含 14 篇真实语料，见资料清单）
RAG_ENABLED=false
RAG_KNOWLEDGE_DIR=data/knowledge
RAG_TOP_K=3
RAG_MIN_SCORE=1.0
```

> HITL 状态：红色风险 → `running`（等待审批，`snapshot.next == ("human_review",)`）→ `approved / rejected / changes_requested / unreviewed_red_risk`。审批前不会生成最终报告；超时只能落到 `unreviewed_red_risk`。待审批时间戳落盘 `.data/pending/<review_id>.json`，进程重启后惰性超时仍生效。
>
> 解释状态：`approved`（或无需审批的 `running`）才调用解释；`rejected / changes_requested / unreviewed_red_risk` 一律 `skipped`。LLM 不可用或质量门拦截时标 `fallback`，报告使用规则理由兜底。
>
> API 错误码：400（类型/空文件）、404（未知 review_id）、409（状态冲突或报告未生成）、413（超过 `MAX_UPLOAD_MB`）、422（字段校验/非法 review_id）。

## 目录结构

```text
app/
  config.py              # 环境变量与上限（唯一读取 .env 的地方）
  schemas.py             # Pydantic：State / Clause / Evidence / 抽取 schema / 解释 / Report / ApprovalPayload
  graph.py               # LangGraph 组装（8 节点 + 两条条件边 + 强制 checkpointer）
  review_service.py      # start / get / resume（幂等 + 惰性超时 + pending 落盘 + review_id 锁）
  graph_demo.py          # 命令行演示（SQLite 跨进程；--review-id / --decision）
  api.py                 # FastAPI：上传 / 查询 / 人工决定 / 下载 JSON+Markdown
  ui.py                  # Streamlit：上传 → 审批 → 报告 → 下载
  report_markdown.py     # ReviewReport → Markdown（纯渲染，不重算等级）
  nodes/
    ingest.py            # TXT/Markdown/PDF/DOCX → canonical text + 页偏移 + sha256
    segment.py           # 标题切分 + 小条款合并 + 超长拆分（无标题时段落 fallback）
    extract.py           # LLM 17 字段抽取（唯一 LLM 抽取节点，按条款串行）
    validate.py          # 引文定位校验 + 数值归一 + 一致性 → facts / to_verify
    rules.py             # 调用规则引擎，产出唯一等级
    hitl.py              # 审批载荷 + interrupt() + 决策校验 + 两条条件边
    explain.py           # LLM 解释 + Python 质量门 + RAG 引用白名单 + 规则兜底
    report.py            # 汇总非 pass 结果 → 可追溯报告（跟随人工终态与解释状态）
  services/
    llm.py               # 结构化输出 + 1 次修复重试 + 未配置/输出错误类型
    evidence.py          # locate_quote：精确匹配 → NFC/空白规范化
    checkpointer.py      # memory / sqlite 工厂 + Pydantic 类型登记
    rag.py               # 本地 BM25 + 中文二元组 + MD/DOCX 切分 + manifest 校验 + 缓存
  rules/
    definitions.yaml     # 13 条规则（11 文本 + 2 字段，version 4）
    dsl.py               # 白名单条件 DSL（无 eval/exec）
    engine.py            # 规则加载 + 求值 + fail-closed + 字段规则 skipped
eval/
  prepare_contracts.py   # 模拟合同 → data/contracts/ + data/eval/gold_contracts.json
  metrics.py             # rule_level / contract_level / coverage 三组指标（纯计算）
  run_eval.py            # 规则级评测 + 指标 → eval/results/rules[-tag]-YYYYMMDD.json
  results/               # 评测结果（JSON）
data/samples/            # 2 份自拟脱敏合同（含风险 / 全部通过）
data/contracts/          # 50 份模拟合同（生成物，可重建）
data/contracts_holdout/  # 8 份留出合同（H01–H08）→ 已消耗，回归守卫
data/contracts_holdout2/ # 12 份留出合同（H09–H20）→ 已消耗，回归守卫
data/contracts_holdout3/ # 8 份留出合同（H21–H28）→ 唯一未消耗，对外报数用这一批
data/eval/               # gold_contracts.json（105 条检索期望）/ gold_rules.json（21 个 silver 现象）/ gold_holdout{,2,3}.json
data/knowledge/          # 真实语料 14 篇 + manifest（RAG 默认关闭）；模拟合同1..6.md 为评测来源，不进 manifest
tests/                   # 228 个测试（API 15 / pending 11 / RAG 22 / 解释 13 / HITL 17 / 指标 11 / 规则含三批留出回归，无需 Key）
tests/fakes.py           # Fake LLM（实现 StructuredLLM 协议）
docs/devlog/             # 项目状态、调研、ADR、开发日志、交接、待决事项、RAG 资料清单
```

## 设计底线

1. **规则唯一判级**：`red / yellow / pass` 只由 Python 规则产生；LLM 的 schema（抽取/解释/专家）中不出现 `risk_level`。
2. **LLM 只做两件事**：抽取 17 个合同要素（缺失为 null）、生成带原文引用的风险解释。RAG/专家只能增强解释，不能改级。
3. **抽取状态必须显式**：`ok / degraded / skipped` 进报告；`degraded` 时字段规则 `skipped`，不把“没抽到”说成“合同缺条款”。
4. **HITL 真中断**：节点内 `interrupt()` + checkpointer + `Command(resume=...)`；审批前零业务写入；超时标记 `unreviewed_red_risk`，绝不自动通过；重复恢复幂等。
5. **失败显式降级**：输入/解析/规则异常都有明确路径，不崩溃、不静默 pass；规则执行异常 → 系统 red 并进入人工确认；RAG 无命中 → 退化纯规则解释。
6. **证据可追溯**：每条风险引用格式 `文件名:p页:start-end`，可在原文精确定位；LLM 引文只允许空白/Unicode 规范化，不允许模糊匹配；知识引用格式 `source_id#section`，且只能引用本条风险实际检索到的片段。
7. **解释可拦截**：LLM 解释必须通过 Python 质量门（rule_id / clause_id / 引文定位 / 越权表述黑名单）；不通过就丢弃，改用规则理由，绝不把模型结论直接写进报告。
8. **RAG 与多智能体默认关闭**（ADR-007/008）：`RAG_ENABLED=false`、`AGENTS_ENABLED=false`；Supervisor 仅路由，不判级。

## 已知限制（当前步骤）

- 支持 TXT / Markdown / 文本型 PDF / DOCX；**扫描件与加密 PDF 明确报错**，不做 OCR。
- PDF 表格/多栏可能打乱列顺序，只在 `warnings` 提示人工核对；DOCX 无真实页码，统一 `p1`。
- 条款切分依赖标题格式（`第X条` / `ARTICLE N` / `1.` 等）；无标题合同走段落 fallback，可能切得不理想。
- 13 条规则（11 文本 + 2 字段），50 份模拟合同中 39 份未命中任何规则；**未覆盖**责任上限、质保期、所有权保留、合规条款等，覆盖率仅 52.4%（21 个 gold 现象中 10 个无规则）。
- 规则只做确定性文本/字段判定；**同一风险的不同写法仍会漏检**：holdout3 中“亦可…起诉”“卖方负责支付…运费”“thirty-six (36) hours”三种写法都没命中；`R-INC-001` 允许跨句 260 字符，长条款可能跨条匹配，需人工核对证据。
- 13 条规则中 6 条是阶段 4 新增，**在同一批 50 份模拟合同上设计并验证**（同分布）；泛化能力只由**未参与设计**的留出集衡量。三批留出集（28 份）中已消耗的两批（H01–H08、H09–H20）只能作回归守卫；**当前对外数字仅来自 holdout3（8 份，P=1.00 / R=0.571 / F1=0.727）**，样本量小，不能外推（ISSUE-020/021）。
- 未配置 `LLM_API_KEY` 时抽取降级：文本规则照常跑，字段规则跳过；解释也回退为规则理由（报告有 limitation）。
- 条款数超过 `MAX_EXTRACT_CLAUSES`（默认 40）时只抽取部分条款，字段规则跳过；长合同精度有限。
- **中文 PDF / 复杂版式未验证**；真实模型抽取与解释效果**无数据**。
- **RAG 语料为真实法律文本（CISG / Incoterms / 民法典 / 司法解释等 14 篇）**，但**授权边界未确认**：`license` 字段只是当前标注，能否在演示/答辩中展示原文需业务/法务确认（ISSUE-015）；`effective_date` 取自文件标题，对外引用前需复核。
- RAG 是词法检索（BM25），同义改写召回有限；`RAG_TOP_K` / `RAG_MIN_SCORE` 尚未用评测集调优；`100问题.md` 的 source_id 与 manifest 不一致，**尚未跑检索评测**（ISSUE-018）。
- 解释按风险条数逐条调用，4 条风险 ≈ 4 次 LLM 调用；成本与延迟随风险数线性增长（上限 20 条）。
- **API/UI 只做了单机单 worker**：并发锁是进程内 `RLock`；多 worker 部署前需换文件锁/数据库锁；上传与 pending 文件无保留期清理（ISSUE-019）。
- HITL 超时是惰性检查（`GET` 时判定），不是后台定时任务；pending 时间戳已落盘，进程重启后仍可判定。
- **指标口径**：对外只引用**当前未被消耗**的留出集（holdout3，8 份，`P=1.00 / R=0.571 / F1=0.727`），并注明“silver gold 待人工复核、样本 8 份、规则 version 4”。主集（50 份）`P/R=1.0` 是**同分布**产物（规则就是在该批合同上设计的）；H01–H08、H09–H20 已被用于定位缺陷，修复后即使全对也只是回归结果——两者都不能当准确率。
- **留出集“消耗”规则**：一批留出集一旦被用来定位缺陷，就降级为回归守卫，下轮必须**另写新样本**才能对外报数（ADR-011 第 3 轮补充）。
- **已知漏报**：holdout3 暴露 3 个措辞漏报——H21（“**亦可**向…人民法院起诉”）、H22（“卖方**负责支付**…主运费”）、H24（“**thirty-six (36)** hours”）；另有 `R-INS-001` 的“已写保额”判定是全文级，合同中任意百分比都可能压制它（ISSUE-021，下轮修 + holdout4 重验）。
- 任何对外指标必须来自 `eval/results/*.json`，并注明样本、规则版本、日期、命令（ADR-011）。

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
- RAG 实现与质量门：[`ADR-008`](docs/devlog/02_ARCHITECTURE_DECISIONS/ADR-008-RAG检索与解释质量门.md)
- API/UI 与 pending 持久化：[`ADR-009`](docs/devlog/02_ARCHITECTURE_DECISIONS/ADR-009-API与UI接入及待审批状态持久化.md)
- 规则扩充与合同级评测基线：[`ADR-010`](docs/devlog/02_ARCHITECTURE_DECISIONS/ADR-010-规则扩充与合同级评测基线.md)
- 评测方法、silver gold 与留出验证：[`ADR-011`](docs/devlog/02_ARCHITECTURE_DECISIONS/ADR-011-评测方法silver-gold与留出验证.md)
