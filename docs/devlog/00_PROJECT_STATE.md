# 项目状态快照

> 更新时间：2026-10-26（第三阶段第 1 步完成）
> 当前阶段：**第三阶段（代码实现）第 1 步：环境 + 最小可运行图已跑通**
> 项目目录：`d:\A项目\Agent_Alex外贸合同智审助手`
> Git：已初始化，首个提交 `cf0fd63 chore: 初始化仓库并提交阶段1-3第1步成果`

## 一句话了解项目

面向“国际货物销售合同”的 AI 预审智能体：上传 PDF/DOCX/TXT → 条款切分 → LLM 抽取关键要素 → **Python 规则引擎判定红/黄/绿风险**（唯一等级来源）→ 红色风险经 **LangGraph `interrupt()` 真人工确认** → LLM 依据规则结果和原文生成解释与建议 → 输出可追溯报告。交付：Streamlit + 命令行 + FastAPI，10 天完成。

## 当前完成度

| 模块 | 状态 | 说明 |
|---|---|---|
| 第一阶段：GitHub 调研 | ✅ 100% | 8 个仓库源码级分析；用户已确认 |
| 第二阶段：架构设计 | ✅ 100% | ADR-001 ~ ADR-006 全部**已接受** |
| 第三阶段第 1 步：环境 + 最小图 | ✅ 100% | `.venv`/依赖/最小图/规则引擎/测试/git |
| 第三阶段后续：解析/LLM/HITL/API/UI | ⏳ 0% | 按顺序逐个加入 |
| 第四阶段：测试与评测 | ⏳ 0% | 只有单元/图测试，尚无评测集与 gold |
| 第五阶段：文档与交付 | ⏳ 20% | README 已写；评测结果与答辩材料未做 |

## 最近一次产出（2026-10-26 第三阶段第 1 步）

- 环境：Python **3.12.10** + `.venv`，依赖按 ADR-006 安装成功，实际版本已回填 ADR-006 §6。
- 工程配置：`requirements.txt`、`requirements-dev.txt`、`pyproject.toml`（ruff/pytest）、`.gitignore`、`.env.example`、`README.md`。
- 业务代码：
  - `app/schemas.py`：`ContractReviewState` / `Clause` / `Evidence` / `RuleEvaluation` / `HitlDecision` / `ReviewReport` 等契约；
  - `app/nodes/ingest.py`：TXT/Markdown → canonical text + 页偏移 + sha256 + 编码/大小/空文件降级；
  - `app/nodes/segment.py`：空行分段 fallback → `Clause[]`（全局偏移、确定性类型分类）；
  - `app/rules/dsl.py` + `app/rules/engine.py`：白名单条件 DSL、规则加载校验、fail-closed、证据偏移回填；
  - `app/rules/definitions.yaml`：首批 **5 条**文本级规则；
  - `app/nodes/rules.py` + `app/nodes/report.py` + `app/graph.py` + `app/graph_demo.py`：等级聚合与可追溯报告。
- 样例：`data/samples/sample_sales_contract.txt`（3 red / 1 yellow）、`sample_clean_contract.txt`（全 pass）。
- 测试：`tests/` 共 **45 个**，覆盖 ingest / segment / DSL / 规则 / 图 / checkpointer。
- Git：`git init` + 首次提交（不包含 `.venv`、`.env`、`.data`、缓存）。

## 核心设计（ADR-001~006，已接受）

```text
START → ingest → segment → extract(LLM) → validate → rules(Python)
   → [有 red?] → human_review(interrupt)
   │                ├─ approve → explain(LLM) → report → END
   │                └─ reject/change/timeout → report → END
   └─ 无 red → explain(LLM) → report → END

当前已实现：ingest → segment → rules → report（无 LLM、无 HITL）
```

- 等级只来自 Python 规则；LLM 的抽取/解释 schema 中都没有 `risk_level`；
- HITL 用 `interrupt()`，不是状态字段；`thread_id=review_id`；SQLite 持久化（待接入）；
- 证据 `文件名:p页:start-end`；报告固定包含 limitation；
- 输入/解析/规则异常都有明确降级，不崩溃、不静默 pass。

## 验证方式（可复现）

```powershell
.\.venv\Scripts\python.exe -m pytest
# 45 passed

.\.venv\Scripts\python.exe -m app.graph_demo
# 总体等级：red；3 条红色风险，1 条黄色风险；R-PAY-001 带 p1:527-547 引用

.\.venv\Scripts\python.exe -m ruff check .
# All checks passed!
```

## 下一步（按顺序，不跳步）

1. **第 2 步：文档解析与条款切分**
   - `ingest` 接入 PDF（pypdf）+ DOCX（python-docx），保留页文本与全局偏移；
   - `segment` 增加标题识别（中英文条款标题）、超长条款拆分、`clause_type` 完整表；
   - 补 `test_ingest`/`test_segment` 的 PDF/DOCX fixture。
2. **第 3 步：LLM 抽取 + Python 校验**
   - `app/services/llm.py`（OpenAI 兼容 + 结构化输出 + 1 次修复 + 超时）；
   - `app/nodes/extract.py`、`app/nodes/validate.py`；Fake LLM 测试，无需 Key。
3. **第 4 步：条件边 + HITL**
   - `is_red` 条件边 + `interrupt()` 节点 + `InMemorySaver`（测试）/`AsyncSqliteSaver`（运行）；
   - 实现 ADR-002 的 8 条 HITL 测试与超时 `unreviewed_red_risk`。
4. **第 5 步：LLM 解释 + Quality Gate + 报告合并**。
5. **第 6 步：FastAPI + Streamlit**（只做上传、运行、展示/确认、下载）。
6. 规则从 5 条扩到 10–12 条（ISSUE-009），再建 20–30 条 gold 评测集（ISSUE-005）。

## 当前阻塞 / 需要你拍板

| 事项 | 状态 | 需要你做什么 | 默认 |
|---|---|---|---|
| LLM API Key / 模型名 | 待提供 | 全链路演示前提供 OpenAI 兼容 Key/模型 | 第 1–2 步不需要，不阻塞 |
| 规则集范围（ISSUE-009） | 部分解决 | 确认是否按现有 5 条继续扩到 10–12 条 | 按国际销售高频风险扩 |
| 评测 gold | 待创建 | 是否接受自拟 20–30 条条款级 gold | 阶段 4 创建 |
| 首批 PDF/DOCX 样例 | 待提供 | 有真实脱敏合同时优先用真实件 | 无则自拟/公开模板 |

## 3 分钟了解项目（给新接手的人）

1. 读根目录 `README.md` 的“设计底线 / 已知限制 / 快速开始”。
2. 读 `02_ARCHITECTURE_DECISIONS/README.md` 的“关键设计一句话”，再按需读 ADR-001~006。
3. 代码入口：`app/graph.py`（图组装）→ `app/graph_demo.py`（可运行示例）。
4. 当前只实现了图的前半段（无 LLM/HITL/API/UI）；不要以为 `extract`/`hitl`/`explain` 已存在。
5. 未解决事项看 `05_OPEN_ISSUES.md`。

## 文件地图

```text
开发提示词.md                          # 需求与约束（只读，不改）
README.md                              # 项目介绍、启动、设计底线、限制
requirements.txt / requirements-dev.txt# 锁定依赖（Python 3.12）
pyproject.toml                         # ruff / pytest 配置
.env.example                           # 环境变量模板（无真实 Key）
app/
  config.py                            # 环境变量与上限
  schemas.py                           # Pydantic 契约
  graph.py                             # LangGraph 组装
  graph_demo.py                        # 最小图演示入口
  nodes/ingest.py                      # 读取 + canonical text + 偏移
  nodes/segment.py                     # 分段 fallback + 类型分类
  nodes/rules.py                       # 规则节点（等级唯一来源）
  nodes/report.py                      # 报告汇总
  rules/definitions.yaml               # 首批 5 条规则
  rules/dsl.py                         # 条件 DSL
  rules/engine.py                      # 规则加载/求值/证据
data/samples/                          # 2 份自拟脱敏样例
tests/                                 # 45 个测试
docs/devlog/
  00_PROJECT_STATE.md                  # 本文件
  01_RESEARCH_LOG.md                   # 第一阶段调研
  02_ARCHITECTURE_DECISIONS/           # ADR-001~006（均已接受）
  03_DEV_LOGS/2026-10-26.md            # 调研 + ADR + 第三阶段第 1 步日志
  04_HANDOVER.md                       # 交接说明
  05_OPEN_ISSUES.md                    # 待决事项
```
