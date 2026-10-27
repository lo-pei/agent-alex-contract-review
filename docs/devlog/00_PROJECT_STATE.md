# 项目状态快照

> 更新时间：2026-10-26（第三阶段第 3 步完成）
> 当前阶段：**第三阶段（代码实现）第 3 步：LLM 要素抽取 + Python 校验已接入图并跑通**
> 项目目录：`d:\A项目\Agent_Alex外贸合同智审助手`
> Git：提交 `cf0fd63`、`71e8a9d`、`750cca3`，以及第 3 步的 `feat: 接入LLM要素抽取与Python校验`（完整哈希见 `git log`）

## 一句话了解项目

面向“国际货物销售合同”的 AI 预审智能体：上传 PDF/DOCX/TXT → 条款切分 → LLM 抽取关键要素 → **Python 规则引擎判定红/黄/绿风险**（唯一等级来源）→ 红色风险经 **LangGraph `interrupt()` 真人工确认** → LLM 依据规则结果和原文生成解释与建议 → 输出可追溯报告。交付：Streamlit + 命令行 + FastAPI，10 天完成。

## 当前完成度

| 模块 | 状态 | 说明 |
|---|---|---|
| 第一阶段：GitHub 调研 | ✅ 100% | 8 个仓库源码级分析；用户已确认 |
| 第二阶段：架构设计 | ✅ 100% | ADR-001 ~ ADR-006 全部**已接受** |
| 第三阶段第 1 步：环境 + 最小图 | ✅ 100% | `.venv`/依赖/最小图/规则引擎/测试/git |
| 第三阶段第 2 步：解析 + 切分 | ✅ 100% | TXT/MD/文本型 PDF/DOCX；标题切分/合并/超长拆分/上限 |
| 第三阶段第 3 步：LLM 抽取 + 校验 | ✅ 100% | 17 字段抽取/引文核验/降级/字段规则 skipped；Fake LLM 测试 |
| 第三阶段后续：HITL/解释/API/UI | ⏳ 0% | 按顺序逐个加入 |
| 第四阶段：测试与评测 | ⏳ 0% | 只有单元/图测试，尚无评测集与 gold |
| 第五阶段：文档与交付 | ⏳ 20% | README 已写；评测结果与答辩材料未做 |

## 最近一次产出（2026-10-26 第三阶段第 3 步）

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

## 核心设计（ADR-001~006，已接受）

```text
START → ingest → segment → extract(LLM) → validate → rules(Python)
   → [有 red?] → human_review(interrupt)
   │                ├─ approve → explain(LLM) → report → END
   │                └─ reject/change/timeout → report → END
   └─ 无 red → explain(LLM) → report → END

当前已实现：ingest → segment → extract → validate → rules → report（无 HITL/解释）
```

- 等级只来自 Python 规则；LLM 的抽取/解释 schema 中都没有 `risk_level`；
- HITL 用 `interrupt()`，不是状态字段；`thread_id=review_id`；SQLite 持久化（待接入）；
- 证据 `文件名:p页:start-end`；报告固定包含 limitation；
- 输入/解析/规则异常都有明确降级，不崩溃、不静默 pass；
- 抽取降级（无 Key/失败/超上限）时字段规则标记 `skipped`，不把“没抽到”说成“合同缺条款”。

## 验证方式（可复现）

```powershell
.\.venv\Scripts\python.exe -m pytest
# 115 passed

.\.venv\Scripts\python.exe -m app.graph_demo
# 条款数量 8（C000 前言 + 7 条）；总体等级 red；3 红 1 黄；
# extraction_status=degraded（无 Key）；R-PAY-001 带 p1:527-547；2 条字段规则 skipped

.\.venv\Scripts\python.exe -m app.graph_demo data\samples\sample_clean_contract.txt
# 条款数量 6；总体 pass；无风险项

.\.venv\Scripts\python.exe -m ruff check .
# All checks passed!
```

Fake LLM 端到端（`tests/test_graph_extraction.py`）：`extraction_status=ok`、`facts.total_amount=3100000.0`、字段规则正常 pass、报告 `extracted_fields` 与 `facts` 一致；单条款超时 → 降级且字段规则 skipped，报告仍 `completed`。

## 下一步（按顺序，不跳步）

1. ~~**第 2 步：文档解析与条款切分**~~ ✅ 已完成（2026-10-26）。
2. ~~**第 3 步：LLM 抽取 + Python 校验**~~ ✅ 已完成（2026-10-26）。
3. **第 4 步：条件边 + HITL**
   - `is_red` 条件边 + `interrupt()` 节点 + `InMemorySaver`（测试）/`AsyncSqliteSaver`（运行）；
   - 实现 ADR-002 的 8 条 HITL 测试与超时 `unreviewed_red_risk`。
4. **第 5 步：LLM 解释 + Quality Gate + 报告合并**。
5. **第 6 步：FastAPI + Streamlit**（只做上传、运行、展示/确认、下载）。
6. 规则从 7 条扩到 10–12 条（ISSUE-009），再建 20–30 条 gold 评测集（ISSUE-005）。

## 当前阻塞 / 需要你拍板

| 事项 | 状态 | 需要你做什么 | 默认 |
|---|---|---|---|
| LLM API Key / 模型名 | 待提供 | 全链路演示前提供 OpenAI 兼容 Key/模型 | 第 1–3 步不需要，不阻塞（Fake LLM 已覆盖） |
| 规则集范围（ISSUE-009） | 部分解决 | 确认是否按现有 7 条继续扩到 10–12 条 | 按国际销售高频风险扩 |
| 评测 gold | 待创建 | 是否接受自拟 20–30 条条款级 gold | 阶段 4 创建 |
| 首批真实 PDF/DOCX 样例 | 待提供 | 有真实脱敏合同时优先用真实件 | 已有程序化 PDF/DOCX fixture，不阻塞 |
| 长合同抽取覆盖 | 已知限制 | 是否接受 > 40 条条款时字段规则跳过 | 先保持保守（宁可跳过不误报） |

## 3 分钟了解项目（给新接手的人）

1. 读根目录 `README.md` 的“设计底线 / 已知限制 / 快速开始”。
2. 读 `02_ARCHITECTURE_DECISIONS/README.md` 的“关键设计一句话”，再按需读 ADR-001~006。
3. 代码入口：`app/graph.py`（图组装）→ `app/graph_demo.py`（可运行示例）。
4. 当前实现了图的前半段（ingest/segment/extract/validate/rules/report）；HITL/解释/API/UI 尚不存在。
5. 未解决事项看 `05_OPEN_ISSUES.md`。

## 文件地图

```text
开发提示词.md                          # 需求与约束（只读，不改）
README.md                              # 项目介绍、启动、设计底线、限制
requirements.txt / requirements-dev.txt# 锁定依赖（Python 3.12）
pyproject.toml                         # ruff / pytest 配置
.env.example                           # 环境变量模板（无真实 Key）
app/
  config.py                            # 环境变量与上限（MAX_PAGES / MAX_EXTRACT_CLAUSES）
  schemas.py                           # Pydantic 契约（含 17 字段抽取 schema）
  graph.py                             # LangGraph 组装（6 节点）
  graph_demo.py                        # 演示入口（无 Key 走降级路径）
  nodes/ingest.py                      # TXT/MD/PDF/DOCX → canonical text + 页偏移
  nodes/segment.py                     # 标题切分/合并/超长拆分/段落 fallback
  nodes/extract.py                     # LLM 17 字段抽取（唯一 LLM 抽取节点）
  nodes/validate.py                    # 引文核验/数值归一/一致性 → facts + to_verify
  nodes/rules.py                       # 规则节点（等级唯一来源）
  nodes/report.py                      # 报告汇总（含抽取状态 limitation）
  services/llm.py                      # 结构化输出 + 1 次修复重试 + 异常类型
  services/evidence.py                 # locate_quote（精确 → NFC/空白规范化）
  rules/definitions.yaml               # 7 条规则（5 文本 + 2 字段）
  rules/dsl.py                         # 条件 DSL
  rules/engine.py                      # 规则加载/求值/证据/fail-closed/skipped
data/samples/                          # 2 份自拟脱敏样例
tests/                                 # 115 个测试
tests/fakes.py                         # Fake LLM（无需 Key）
tests/fixtures/pdf_builder.py          # 纯标准库构造最小 PDF（测试用）
docs/devlog/
  00_PROJECT_STATE.md                  # 本文件
  01_RESEARCH_LOG.md                   # 第一阶段调研
  02_ARCHITECTURE_DECISIONS/           # ADR-001~006（均已接受）
  03_DEV_LOGS/2026-10-26.md            # 调研 + ADR + 第三阶段第 1/2/3 步日志
  04_HANDOVER.md                       # 交接说明
  05_OPEN_ISSUES.md                    # 待决事项
```

