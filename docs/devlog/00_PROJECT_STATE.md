# 项目状态快照

> 更新时间：2026-10-26（第三阶段第 2 步完成）
> 当前阶段：**第三阶段（代码实现）第 2 步：PDF/DOCX 解析 + 标题式条款切分已跑通**
> 项目目录：`d:\A项目\Agent_Alex外贸合同智审助手`
> Git：已初始化；提交 `cf0fd63`（初始化）、`71e8a9d`（文档同步）；第 2 步代码待提交

## 一句话了解项目

面向“国际货物销售合同”的 AI 预审智能体：上传 PDF/DOCX/TXT → 条款切分 → LLM 抽取关键要素 → **Python 规则引擎判定红/黄/绿风险**（唯一等级来源）→ 红色风险经 **LangGraph `interrupt()` 真人工确认** → LLM 依据规则结果和原文生成解释与建议 → 输出可追溯报告。交付：Streamlit + 命令行 + FastAPI，10 天完成。

## 当前完成度

| 模块 | 状态 | 说明 |
|---|---|---|
| 第一阶段：GitHub 调研 | ✅ 100% | 8 个仓库源码级分析；用户已确认 |
| 第二阶段：架构设计 | ✅ 100% | ADR-001 ~ ADR-006 全部**已接受** |
| 第三阶段第 1 步：环境 + 最小图 | ✅ 100% | `.venv`/依赖/最小图/规则引擎/测试/git |
| 第三阶段第 2 步：解析 + 切分 | ✅ 100% | TXT/MD/文本型 PDF/DOCX；标题切分/合并/超长拆分/上限 |
| 第三阶段后续：LLM/HITL/API/UI | ⏳ 0% | 按顺序逐个加入 |
| 第四阶段：测试与评测 | ⏳ 0% | 只有单元/图测试，尚无评测集与 gold |
| 第五阶段：文档与交付 | ⏳ 20% | README 已写；评测结果与答辩材料未做 |

## 最近一次产出（2026-10-26 第三阶段第 2 步）

- `app/nodes/ingest.py`（重写）
  - 支持 `.txt` / `.md` / `.pdf`（pypdf）/ `.docx`（python-docx）；
  - PDF 逐页提取 → `canonical_text = 页文本以 "\\n\\n" 拼接`，页偏移全局连续；
  - 扫描件（总文本 < 50 字符）→ 明确失败；加密 PDF → 明确失败；页数 > `MAX_PAGES` → 明确失败；
  - DOCX 按 body 顺序读取段落与表格（表格行 ` | ` 拼接），统一单页 `p1`；
  - TXT 编码顺序 UTF-8 → GB18030 → Latin-1；文件名只保留 basename；
  - 校验文件头（`%PDF-` / `PK\x03\x04`），避免改扩展名绕过。
- `app/nodes/segment.py`（重写）
  - 标题识别：`第X条` / `一、` / `（一）` / `ARTICLE N` / `1.`（短行、非句末标点、≤6 个词）；
  - 标题前 → `C000` 前言；标题到下一个标题 → `C001...`；
  - 相邻 < 80 字符小条款合并到前一条款；> 4000 字符按段落/句号/分号拆分，`clause_id` 加 `-1/-2`；
  - 无标题 → 空行段落聚合（约 300–2000 字符）+ 明确 warning；
  - 条款数 > 200 → `status="failed"` + 可读错误（不静默截断）；
  - `clause_type` 先看标题行再全文，避免“Delivery 条款含 payment 字样”被误分类。
- `app/config.py` / `.env.example`：新增 `MAX_PAGES=200`。
- 测试：新增 `tests/test_ingest_formats.py`（PDF/DOCX/扫描件/加密/页数上限/文件头/表格顺序/文件名清洗）与 `tests/fixtures/pdf_builder.py`（纯标准库构造最小 PDF）；`test_segment.py` 扩到标题/合并/拆分/上限/页面映射。
- 测试总数：**63 个全部通过**。

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
# 63 passed

.\.venv\Scripts\python.exe -m app.graph_demo
# 条款数量 8（C000 前言 + 7 条）；总体等级 red；3 红 1 黄；R-PAY-001 带 p1:527-547

.\.venv\Scripts\python.exe -m ruff check .
# All checks passed!
```

PDF 全链路 smoke（临时文件，未入库）：2 页 PDF → `pages=2`，`C000@p1`、`C001@p2`，引用 `smoke_contract.pdf:p2:131-151`。

## 下一步（按顺序，不跳步）

1. ~~**第 2 步：文档解析与条款切分**~~ ✅ 已完成（2026-10-26）。
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
| LLM API Key / 模型名 | 待提供 | 全链路演示前提供 OpenAI 兼容 Key/模型 | 第 1–3 步不需要，不阻塞 |
| 规则集范围（ISSUE-009） | 部分解决 | 确认是否按现有 5 条继续扩到 10–12 条 | 按国际销售高频风险扩 |
| 评测 gold | 待创建 | 是否接受自拟 20–30 条条款级 gold | 阶段 4 创建 |
| 首批真实 PDF/DOCX 样例 | 待提供 | 有真实脱敏合同时优先用真实件 | 已有程序化 PDF/DOCX fixture，不阻塞 |

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
  config.py                            # 环境变量与上限（含 MAX_PAGES）
  schemas.py                           # Pydantic 契约
  graph.py                             # LangGraph 组装
  graph_demo.py                        # 最小图演示入口
  nodes/ingest.py                      # TXT/MD/PDF/DOCX → canonical text + 页偏移
  nodes/segment.py                     # 标题切分/合并/超长拆分/段落 fallback
  nodes/rules.py                       # 规则节点（等级唯一来源）
  nodes/report.py                      # 报告汇总
  rules/definitions.yaml               # 首批 5 条规则
  rules/dsl.py                         # 条件 DSL
  rules/engine.py                      # 规则加载/求值/证据
data/samples/                          # 2 份自拟脱敏样例
tests/                                 # 63 个测试
tests/fixtures/pdf_builder.py          # 纯标准库构造最小 PDF（测试用）
docs/devlog/
  00_PROJECT_STATE.md                  # 本文件
  01_RESEARCH_LOG.md                   # 第一阶段调研
  02_ARCHITECTURE_DECISIONS/           # ADR-001~006（均已接受）
  03_DEV_LOGS/2026-10-26.md            # 调研 + ADR + 第三阶段第 1/2 步日志
  04_HANDOVER.md                       # 交接说明
  05_OPEN_ISSUES.md                    # 待决事项
```
