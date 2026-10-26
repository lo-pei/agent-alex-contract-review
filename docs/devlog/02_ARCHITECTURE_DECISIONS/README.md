# 架构决策记录（ADR）索引

> 更新时间：2026-10-26（第三阶段启动）
> 阶段：**第二阶段架构设计已完成并经用户确认，第三阶段代码实现进行中**
> 说明：ADR-001 ~ ADR-006 全部为“已接受”。后续如需变更，写新 ADR 并在原 ADR 标注“已替代”，不直接改写历史结论。

## 为什么需要 ADR

本项目 10 天 MVP，技术面窄但硬约束多（规则唯一判级、真 HITL、无 Supervisor、无 RAG、无 Docker）。把关键取舍写成一页一条的 ADR，可以避免：
- 开发中途“顺手加个 Agent/加个数据库”，破坏硬约束；
- 评审追问“为什么这样拆分”时只能临场解释；
- 新接手的人重复讨论已经定过的事。

## 已产出的 ADR

| 编号 | 主题 | 状态 | 关键结论 | 文件 |
|---|---|---|---|---|
| ADR-001 | 图结构选型 | **已接受** | 确定性顺序主干 + 两个条件边 + 单一 HITL 门；不用 Supervisor/并行/单体 ReAct | [ADR-001-图结构选型.md](./ADR-001-图结构选型.md) |
| ADR-002 | HITL 实现方式 | **已接受** | 节点内 `interrupt()` + checkpointer + `Command(resume=...)`；审批前零业务写入；超时不自动通过 | [ADR-002-HITL实现方式.md](./ADR-002-HITL实现方式.md) |
| ADR-003 | 规则 / LLM 边界 | **已接受** | 规则唯一判级；LLM 只抽取 17 字段与解释；schema 禁止 `risk_level`；引文核验 + 失败兜底 | [ADR-003-规则与LLM边界.md](./ADR-003-规则与LLM边界.md) |
| ADR-004 | 状态持久化与线程模型 | **已接受** | 运行/演示用 AsyncSqliteSaver；测试用 InMemorySaver；`thread_id=review_id`；惰性超时 | [ADR-004-状态持久化与线程模型.md](./ADR-004-状态持久化与线程模型.md) |
| ADR-005 | 文档解析与证据模型 | **已接受** | pypdf + python-docx + TXT；canonical text + 页/全局偏移；`文件名:p页:start-end`；精确/空白规范化定位 | [ADR-005-文档解析与证据模型.md](./ADR-005-文档解析与证据模型.md) |
| ADR-006 | 运行环境与依赖策略 | **已接受** | Python 3.12；LangGraph 1.2.17 等最新稳定依赖；OpenAI 兼容接口；无 Docker/Redis/Postgres | [ADR-006-运行环境与依赖策略.md](./ADR-006-运行环境与依赖策略.md) |

## 关键设计一句话

```text
ingest → segment → extract(LLM) → validate → rules(Python)
   → [有 red?] → human_review(interrupt) → approve → explain(LLM) → report
                 → 无 red / 非 approve → report
```

- 等级只来自 Python 规则；LLM 输出 schema 中没有 `risk_level`；
- HITL 用 `interrupt()`，不是状态标记；
- 证据可定位到 `文件:页码:字符偏移`；
- LLM/解析失败都有降级路径，不崩溃。

## 建议的 ADR 模板

```markdown
# ADR-00X：标题

- 状态：提议 / 已接受 / 已拒绝 / 已替代
- 日期：YYYY-MM-DD
- 决策人：用户 + Trae AI

## 背景
为什么现在必须做这个决定？约束是什么？

## 选项
A. ...
B. ...
C. ...

## 决策
选哪个，为什么；明确不选哪个，为什么。

## 后果
正面影响、代价、风险、后续需要补的测试/文档。

## 证据
代码/文档/调研链接，确保可追溯。
```

## 进入第三阶段的条件

1. 用户确认 ADR-001 ~ ADR-005（或指出要改的点）；
2. ADR-006 已接受；
3. 阶段 3 严格按“最小图 → 逐个节点 → FastAPI/Streamlit”顺序，不一次性生成整个项目；
4. 每个节点/模块完成后，按 `开发提示词.md` 的日志规范更新 `00_PROJECT_STATE.md`、`03_DEV_LOGS/`、`04_HANDOVER.md`、`05_OPEN_ISSUES.md`。
