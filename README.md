# Agent Alex · 外贸合同智审助手

面向**国际货物销售合同**的 AI 预审智能体：上传合同 → 条款切分 → LLM 抽取关键要素 → **Python 规则引擎判定红/黄/绿风险**（唯一等级来源）→ 红色风险经 **LangGraph `interrupt()` 真人工确认** → LLM 依据规则结果与原文生成解释 → 输出可追溯报告。

> 当前处于**第三阶段（代码实现）第 2 步**：最小可运行图已跑通（`ingest → segment → rules → report`，纯 Python、不接 LLM），并已支持 **TXT / Markdown / 文本型 PDF / DOCX** 解析与标题式条款切分。LLM 抽取/解释、HITL、FastAPI、Streamlit 尚未实现，详见 [`docs/devlog/00_PROJECT_STATE.md`](docs/devlog/00_PROJECT_STATE.md)。

## 当前完成度

| 阶段 | 状态 | 说明 |
|---|---|---|
| 1. GitHub 调研 | ✅ | 8 个开源项目源码级分析，产出借鉴/不借鉴清单 |
| 2. 架构设计 | ✅ | ADR-001 ~ ADR-006 全部已接受 |
| 3. 代码实现 | 🚧 第 2 步完成 | 环境、最小图、规则引擎（5 条规则）、PDF/DOCX/TXT 解析、标题切分、63 个测试 |
| 4. 测试与评测 | ⏳ 未开始 | 尚无评测集，**不公布任何准确率** |
| 5. 文档与交付 | ⏳ 进行中 | 开发日志与交接文档已建立 |

## 技术栈

- Python **3.12**（`开发提示词.md` 原写 3.9+，但 Streamlit 1.66.1 要求 ≥3.11，LangGraph 1.2 要求 ≥3.10；决策见 [ADR-006](docs/devlog/02_ARCHITECTURE_DECISIONS/ADR-006-运行环境与依赖策略.md)）
- LangGraph 1.2.17 + LangChain 1.4.7
- Pydantic 2.14（结构化输出与状态契约）
- FastAPI（计划）、Streamlit（计划）
- 不使用：Supervisor、多智能体、RAG 知识库、训练模型、Docker、前端框架

## 快速开始

```powershell
# 1) 创建虚拟环境（必须用 3.12，不要用系统默认 python）
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

# 2) 运行最小图（无需 LLM / API Key）
.\.venv\Scripts\python.exe -m app.graph_demo
.\.venv\Scripts\python.exe -m app.graph_demo data\samples\sample_clean_contract.txt
.\.venv\Scripts\python.exe -m app.graph_demo --json

# 3) 测试与静态检查
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

环境变量：复制 `.env.example` 为 `.env` 后填写。**不要提交真实 Key**（`.env` 已在 `.gitignore`）。

## 目录结构

```text
app/
  config.py              # 环境变量与文档上限（唯一读取 .env 的地方）
  schemas.py             # Pydantic：State / Clause / Evidence / RuleEvaluation / Report
  graph.py               # LangGraph 组装（当前为确定性顺序主干）
  graph_demo.py          # 最小图演示入口（无 LLM）
  nodes/
    ingest.py            # TXT/Markdown/PDF/DOCX → canonical text + 页偏移 + sha256
    segment.py           # 标题切分 + 小条款合并 + 超长拆分（无标题时段落 fallback）
    rules.py             # 调用规则引擎，产出唯一等级
    report.py            # 汇总非 pass 结果 → 可追溯报告
  rules/
    definitions.yaml     # 首批 5 条文本级规则
    dsl.py               # 白名单条件 DSL（无 eval/exec）
    engine.py            # 规则加载 + 求值 + fail-closed 聚合
data/samples/            # 2 份自拟脱敏合同（含风险 / 全部通过）
tests/                   # 63 个测试（ingest/PDF/DOCX/segment/rules/graph）
docs/devlog/             # 项目状态、调研、ADR、开发日志、交接、待决事项
```

## 设计底线

1. **规则唯一判级**：`red / yellow / pass` 只由 Python 规则产生；LLM 的 schema 中不出现 `risk_level`。
2. **LLM 只做两件事**：抽取 17 个合同要素（缺失为 null）、生成带原文引用的风险解释。
3. **HITL 真中断**：节点内 `interrupt()` + checkpointer + `Command(resume=...)`；审批前零业务写入；超时标记 `unreviewed_red_risk`，绝不自动通过。
4. **失败显式降级**：输入/解析/规则异常都有明确路径，不崩溃、不静默 pass；规则执行异常 → 系统 red 并进入人工确认。
5. **证据可追溯**：每条风险引用格式 `文件名:p页:start-end`，可在原文精确定位。

## 已知限制（当前步骤）

- 支持 TXT / Markdown / 文本型 PDF / DOCX；**扫描件与加密 PDF 明确报错**，不做 OCR。
- PDF 表格/多栏可能打乱列顺序，只在 `warnings` 提示人工核对；DOCX 无真实页码，统一 `p1`。
- 条款切分依赖标题格式（`第X条` / `ARTICLE N` / `1.` 等）；无标题合同走段落 fallback，可能切得不理想。
- 只有 5 条文本级规则；字段级规则待 LLM 抽取接入后启用。
- 无 LLM、无人工审批、无 API/UI；报告只有规则结果。
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
