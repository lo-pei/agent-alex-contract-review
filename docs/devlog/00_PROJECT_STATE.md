# 项目状态快照

> 更新时间：2026-10-26 23:34
> 当前阶段：**第二阶段（架构设计）初稿完成，等待确认后进入第三阶段代码**
> 项目目录：`d:\A项目\Agent_Alex外贸合同智审助手`

## 一句话了解项目

面向“国际货物销售合同”的 AI 预审智能体：上传 PDF/DOCX/TXT → 条款切分 → LLM 抽取关键要素 → **Python 规则引擎判定红/黄/绿风险**（唯一等级来源）→ 红色风险经 **LangGraph `interrupt()` 真人工确认** → LLM 依据规则结果和原文生成解释与建议 → 输出可追溯报告。交付：Streamlit + 命令行 + FastAPI，10 天完成。

## 当前完成度

| 模块 | 状态 | 说明 |
|---|---|---|
| 第一阶段：GitHub 调研 | ✅ 100% | 8 个仓库源码级分析（原 6 个 + 2 个替代）；用户已确认 |
| 第二阶段：架构设计 | ✅ 初稿 100%，待确认 | ADR-001 ~ ADR-006 已写出；ADR-006 已接受，ADR-001~005 待确认 |
| 第三阶段：代码实现 | ⏳ 0% | 尚无 `app/`、`tests/`、`pyproject.toml`；等 ADR 确认 |
| 第四阶段：测试与评测 | ⏳ 0% | 评测集/gold 尚未创建 |
| 第五阶段：文档与交付 | ⏳ 0% | 目前只有 `docs/devlog/` |

## 最近一次产出（2026-10-26 第二轮）

- `docs/devlog/02_ARCHITECTURE_DECISIONS/ADR-001-图结构选型.md`：确定性顺序主干 + 两个条件边 + 单一 HITL 门；否决 Supervisor/并行/单体 ReAct。
- `ADR-002-HITL实现方式.md`：节点内 `interrupt()` + checkpointer + `Command(resume=...)`；审批前零业务写入；超时不自动通过；API/UI 契约与 8 条 HITL 测试。
- `ADR-003-规则与LLM边界.md`：规则唯一判级；17 个抽取字段；schema 禁止 `risk_level`；引文核验、越权表述拦截、失败兜底、评测口径。
- `ADR-004-状态持久化与线程模型.md`：运行/演示用 AsyncSqliteSaver，测试用 InMemorySaver；`thread_id=review_id`；pending/报告/审计分离；惰性超时。
- `ADR-005-文档解析与证据模型.md`：pypdf + python-docx + TXT；canonical text + 页/全局偏移；`文件名:p页:start-end`；精确/空白规范化定位；扫描件不支持。
- `ADR-006-运行环境与依赖策略.md`：**已接受**；Python 3.12 + LangGraph 1.2.17 等；OpenAI 兼容接口；无 Docker/Redis/Postgres。已下载 wheel 预检查 `interrupt(response_schema=...)`、`Command`、`AsyncSqliteSaver` 导入路径，均与 ADR 一致。
- `02_ARCHITECTURE_DECISIONS/README.md`：ADR 索引与关键设计一句话。
- `05_OPEN_ISSUES.md`：按“按建议继续”关闭 7 项，剩 ISSUE-009（规则集范围）、ISSUE-011（git 未初始化）。

## 核心设计（已写入 ADR，待确认）

```text
START → ingest → segment → extract(LLM) → validate → rules(Python)
   → [有 red?] → human_review(interrupt)
   │                ├─ approve → explain(LLM) → report → END
   │                └─ reject/change/timeout → report → END
   └─ 无 red → explain(LLM) → report → END
```

- 等级只来自 Python 规则；LLM 的抽取/解释 schema 中都没有 `risk_level`；
- HITL 用 `interrupt()`，不是状态字段；`thread_id=review_id`；SQLite 持久化；
- 证据 `文件名:p页:start-end`；LLM 引文必须能在原文定位；
- LLM/解析/规则异常都有明确降级，不崩溃、不静默 pass。

## 下一步（按顺序，不跳步）

1. **你确认 ADR-001 ~ ADR-005**（ADR-006 已接受）。可直接回复“ADR 确认，开始第三阶段”，或指出要改的点。
2. 确认后进入第三阶段第 1 步：
   - 创建 `.venv`（Python 3.12）并安装 ADR-006 依赖，记录实际版本；
   - 创建最小可运行 LangGraph 图（2–3 个纯函数节点，不接 LLM），验证环境、编译、调用链；
   - 同步创建 `.gitignore`、`pyproject.toml`/`requirements.txt`、`tests/` 最小测试。
3. 最小图跑通后，再逐个加：规则引擎 → 文档解析/条款切分 → LLM 抽取 → 条件边/HITL → LLM 解释 → 报告 → FastAPI/Streamlit。
4. 每完成一步，更新本文件、`03_DEV_LOGS/`、`04_HANDOVER.md`、`05_OPEN_ISSUES.md`。

## 当前阻塞 / 需要你拍板

| 事项 | 状态 | 需要你做什么 | 默认 |
|---|---|---|---|
| ADR-001~005 | 待确认 | 确认架构或提出修改 | 按 ADR 初稿执行 |
| API Key / 模型名 | 待提供 | 提供 OpenAI 兼容 Key 与模型名；不提供也可先做规则/图/测试 | 先不阻塞开发，全链路演示前给 |
| 合同样例 | 待创建 | 确认可自拟 3 份脱敏样例（FOB/CIF、L/C、检验+仲裁） | 阶段 3 自拟 |
| Git 初始化 | 未做 | 是否同意 `git init` + `.gitignore`（不提交 Key/合同原件） | 阶段 3 第一步做 |

## 3 分钟了解项目（给新接手的人）

1. 先读根目录 `开发提示词.md` 的“一、项目概述 / 二、技术约束 / 三、禁止事项”。
2. 再读 `02_ARCHITECTURE_DECISIONS/README.md` 的“关键设计一句话”，然后按需读 ADR-001~006。
3. 看 `05_OPEN_ISSUES.md` 的 `[OPEN]` 条目（当前只剩规则集范围与 git 初始化）。
4. 当前没有业务代码；不要以为 `app/` 已存在。下一步是 ADR 确认 + 最小图。

## 文件地图

```text
开发提示词.md                          # 项目需求与约束（只读，不改）
docs/devlog/
  00_PROJECT_STATE.md                  # 本文件：3 分钟接手
  01_RESEARCH_LOG.md                   # 第一阶段：调研与借鉴决策
  02_ARCHITECTURE_DECISIONS/
    README.md                          # ADR 索引
    ADR-001-图结构选型.md
    ADR-002-HITL实现方式.md
    ADR-003-规则与LLM边界.md
    ADR-004-状态持久化与线程模型.md
    ADR-005-文档解析与证据模型.md
    ADR-006-运行环境与依赖策略.md
  03_DEV_LOGS/
    2026-10-26.md                      # 调研 + ADR 当日日志
  04_HANDOVER.md                       # 环境、结构、启动、坑
  05_OPEN_ISSUES.md                    # 待决事项
```
