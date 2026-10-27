# ADR-002：HITL 实现方式

- 状态：**已接受（2026-10-26，用户确认「ADR 确认，开始第三阶段」）**
- 日期：2026-10-26
- 决策人：用户 + Trae AI
- 关联：`开发提示词.md` 硬约束；ADR-001、ADR-004；`01_RESEARCH_LOG.md` 模式 B
- 影响范围：`app/nodes/hitl.py`、`app/graph.py`、`app/services/checkpointer.py`、`app/api.py`、`app/ui.py`、HITL 测试

---

## 1. 背景

硬约束要求：

- 红色风险必须由人工确认；
- 使用 LangGraph 的 `interrupt()`；
- 状态通过 checkpointer 持久化；
- 恢复用 `Command(resume=...)`；
- HITL 超时必须有不崩溃的降级路径，且**不能自动通过**。

调研发现三种常见做法：

1. bcefghj：只把状态改成 `AWAITING_HUMAN`，没有真正中断，API 还关闭了 checkpoint；
2. zihan：`interrupt_before=["human_review"]` + `aupdate_state` + `ainvoke(None)`，能暂停/恢复，但不是节点内 `interrupt()`；
3. aurelien：节点内 `interrupt()` + checkpointer + `Command(resume=...)`，并且审批前只做纯读取，审批后才写入，测试断言“审批前零业务写入”。

本项目选择 3，因为语义最明确，最符合硬约束，也最容易证明“真的暂停了”。

---

## 2. 可选方案

| 方案 | 描述 | 优点 | 缺点 |
|---|---|---|---|
| A. 状态标记（伪 HITL） | 节点返回 `AWAITING_HUMAN`，后续由外部系统改状态 | 实现简单 | 图并没有暂停；无法 `Command(resume=...)`；刷新/重启后流程丢失；评审演示会露馅 |
| B. `interrupt_before` | 编译时在节点前暂停，恢复时 `update_state + ainvoke(None)` | 与 LangGraph 兼容；代码少 | 中断点由编译配置决定，节点内无审批契约；恢复靠“更新状态再空跑”，容易误触发后续节点；不是硬约束指定的 `interrupt()` |
| C. 节点内 `interrupt()` | 节点内调用 `interrupt(payload, response_schema=...)`，恢复用 `Command(resume=...)` | 语义明确；审批载荷与响应 schema 在节点内；恢复值有类型；易测试 | 节点在 resume 时会从顶部重跑，必须保证 interrupt 前无副作用；必须注入 checkpointer |
| D. 外部审批服务/队列 | 把待审任务发给外部系统，回调后恢复 | 可多人协作、可扩展 | 对 10 天单机 MVP 过重；引入服务依赖；演示复杂 |

---

## 3. 决策

**采用方案 C：节点内 `interrupt()` + checkpointer + `Command(resume=HitlDecision)`。**

### 3.1 触发条件

- `route_by_risk` 在以下任一情况进入 `human_review`：
  - 任意 `RuleEvaluation.risk_level == "red"`；
  - 规则执行异常产生的系统级 red finding（`rule_id = "SYS-RULE-ERROR"`，`is_system_finding = true`）。
- 没有 red：快速通道，直接 `explain_risks → build_report`。
- yellow 不触发 HITL，但在报告中显示“建议人工关注”；人工可自行复核。

### 3.2 审批载荷（payload）

```json
{
  "type": "red_risk_approval",
  "review_id": "rev_ab12cd34ef56",
  "overall_level": "red",
  "findings": [
    {
      "rule_id": "R-PAY-001",
      "clause_id": "C003",
      "risk_level": "red",
      "reason": "付款方式为赊销且未约定付款担保",
      "matched_text": "payment shall be made within 90 days after delivery",
      "citation": "sales_contract.pdf:p2:1834-1902",
      "evidence": "……原文片段……"
    }
  ],
  "extraction_summary": {
    "payment_method": "open account",
    "payment_terms": "90 days after delivery",
    "incoterms": null
  },
  "to_verify": ["incoterms: 未在合同中找到明确贸易术语"],
  "instructions": "请确认红色风险是否属实；可批准、要求修改或拒绝。"
}
```

**载荷不包含**：
- LLM 生成的解释（解释在批准后才生成，避免人工被 LLM 措辞影响）；
- 任何“建议通过/拒绝”的模型判断；
- 时间戳（时间戳由 API 在检测到中断后写入 pending 元数据，保持节点可重跑且载荷稳定）。

### 3.3 响应 schema

```python
class HitlDecision(BaseModel):
    action: Literal["approve", "request_changes", "reject", "timeout"]
    reviewer: str = Field(min_length=1, max_length=64)
    comment: str | None = Field(default=None, max_length=2000)
    overrides: dict[str, str] = Field(default_factory=dict)
```

> **API 预检查（2026-10-26，`langgraph==1.2.17` wheel）**：`interrupt(value, *, response_schema=...)` 确实存在；`Command` 从 `langgraph.types` 导入；`StateGraph.compile(checkpointer=...)` 签名已核对；图 resume 会从 `interrupt()` 所在节点顶部重跑（官方 docstring 明确说明）。因此本 ADR 的“审批前纯读取”不是可选优化，而是正确性要求。

- `overrides` 只允许“人工意见”，例如 `{"R-PAY-001": "已与客户确认，接受"}`；**不得改写规则等级**。报告同时展示“规则等级”和“人工意见”。
- 若用户想改变等级，应新增/修改规则后重新运行，而不是在审批里静默改级。

### 3.4 状态迁移

| 当前状态 | 事件 | 新状态 | 后续 |
|---|---|---|---|
| `running` | 检测到 red，节点 `interrupt()` | `awaiting_human` | 图暂停，等待 resume |
| `awaiting_human` | `approve` | `approved` | 生成解释 → 报告 |
| `awaiting_human` | `reject` | `rejected` | 跳过 LLM 解释，生成“被拒绝”报告 |
| `awaiting_human` | `request_changes` | `changes_requested` | 跳过 LLM 解释，生成“待修改”报告；MVP 不自动重跑 |
| `awaiting_human` | 超时 | `unreviewed_red_risk` | 跳过 LLM 解释，生成“红色风险未确认”报告 |
| `running` | 无 red | `running` | 解释 → 报告 → `completed` |
| 任意 | 不可恢复异常 | `failed` | 返回错误，不生成“通过”报告 |

> 任何路径都不允许把 `timeout` 映射为 `approved`。

**关于 `status` 的一个实现细节（必须按此测试）**：`interrupt()` 在节点返回前抛出，LangGraph 不会提交该节点准备返回的 state 更新。因此暂停时 checkpoint 里的 `ContractReviewState.status` 可能仍是 `running`；`awaiting_human` 由 **API 根据 `snapshot.next == ("human_review",)` + `pending/{review_id}.json` 派生**。不要在 `human_review` 节点里“先写 status 再 interrupt”，那不会被提交；resume 之后节点返回的 `{"status": "approved"/...}` 才是最终业务状态。

### 3.5 “审批前零写入”的确切含义

节点内 `interrupt()` 之前只允许：

- 读取 state；
- 纯函数计算审批 payload；
- 不写最终报告、不写审计“已通过”事件、不调用外部业务系统、不发送邮件/消息。

允许：

- checkpointer 持久化图状态（HITL 的前提）；
- API 在检测到 `__interrupt__` 后写一条 **pending 元数据**（`review_id / thread_id / requested_at / status=awaiting_human`），用于列表展示与超时判断；
- 写运行日志（不含最终结论）。

这样既满足“审批前不产生业务结论”，又能让 API/UI 找到待审任务。

### 3.6 恢复与幂等

```python
# 首次运行
result = await graph.ainvoke(initial_state, config)

# 若暂停
snapshot = await graph.aget_state(config)
if snapshot.next == ("human_review",):
    # 等待人工
    ...

# 恢复
result = await graph.ainvoke(
    Command(resume=decision.model_dump()),
    config,
)
```

- `thread_id = review_id`，一个 review 对应一个 thread；
- 恢复前读取 `snapshot.values["status"]`：
  - 如果已经是 `approved/rejected/changes_requested/unreviewed_red_risk`，直接返回现有结果，**不重复应用决策**；
  - 如果 `snapshot.next` 不包含 `human_review`，说明没有待审任务，返回冲突错误。
- API 对同一 `review_id` 使用 `asyncio.Lock` 串行化 `resume`，避免并发双写；
- 若进程重启，checkpointer 仍在 SQLite，`aget_state` 可恢复；pending 元数据也在 `.data/pending/`，用于列表。

### 3.7 超时

- 配置 `HITL_TIMEOUT_MINUTES=30`；
- MVP 不启动后台线程，采用**惰性检查**：`GET /review/{id}` 或 Streamlit 轮询时，若 `status=awaiting_human` 且 `now - requested_at > timeout`，自动 `Command(resume={"action":"timeout","reviewer":"system",...})`；
- 超时报告状态 `unreviewed_red_risk`，页面显示黄色/红色警示条：“红色风险未获人工确认，报告不得作为通过结论”；
- 任何“自动通过”或“默认接受”都不允许；
- 若以后需要主动超时，可加 APScheduler/后台任务，但不引入 Celery/Redis。

### 3.8 API 契约（计划）

| 方法 | 路径 | 作用 | 返回 |
|---|---|---|---|
| `POST` | `/review` | 上传/提交合同，运行到完成或中断 | `{review_id, status, report?}`；若中断则 `status=awaiting_human` |
| `GET` | `/review/{id}` | 查询状态/报告；惰性超时检查 | `{review_id, status, report?, hitl?}` |
| `POST` | `/review/{id}/resume` | 提交 `HitlDecision` 恢复 | `{review_id, status, report?}` |
| `GET` | `/review/{id}/report` | 下载 JSON/Markdown 报告 | 文件流或 JSON |
| `GET` | `/reviews/pending` | 待审列表（可选） | `[{review_id, requested_at, ...}]` |

### 3.9 Streamlit 交互

1. 上传合同 → 点击“开始审查”；
2. 若返回 `awaiting_human`：展示红色风险卡片（规则 ID、等级、理由、原文高亮、页码/字符偏移）、抽取字段、`to_verify`；
3. 单选“批准 / 要求修改 / 拒绝”，填写复核人（默认 `demo-reviewer`）与意见；
4. 点击“提交确认” → 调 `POST /resume` → 展示最终报告；
5. 若超时：页面提示“红色风险未确认”，仍可下载报告（状态明确）。

---

## 4. 被否决方案及原因

| 方案 | 否决原因 |
|---|---|
| 状态标记（伪 HITL） | 不暂停、不可恢复、不可演示；违反硬约束 |
| `interrupt_before` + `update_state/ainvoke(None)` | 可作为备选，但硬约束明确要求 `interrupt()`；且恢复语义不如 `Command(resume=...)` 明确 |
| 外部审批系统 | 10 天 MVP 过重；引入网络/服务依赖；演示环境不可控 |
| 自动超时通过 | 直接违反“红色必须人工确认” |
| 把审批结果写回规则等级 | 破坏规则唯一判级与审计；人工意见只能独立记录 |
| 在 `interrupt()` 之前写最终报告 | 审批前产生业务结论；resume 重跑会导致重复写入 |

---

## 5. 后果

### 正面

- HITL 是真正的阻塞门，刷新/重启后仍可恢复；
- 审批载荷与响应有 Pydantic schema，API/UI 可复用；
- 可以写出确定性测试：暂停、审批前无最终报告、approve 只写一次、reject 不写、timeout 不通过；
- 规则等级与人工意见分离，报告可审计。

### 代价与风险

- 必须使用持久 checkpointer；没有 checkpointer 时图不能启用 HITL（编译期直接报错，不允许静默降级为假 HITL）；
- SQLite 单进程/单写者限制，不能水平扩展；比赛演示足够；
- 节点 resume 会从顶部重跑，任何新增的“写操作”都必须放在 `interrupt()` 之后，代码评审要专门检查；
- 超时采用惰性检查，若无人访问 `GET`，任务会一直 pending；可在 UI 轮询中触发，后续再加后台 sweeper；
- 审批载荷可能较大（多个 red findings + 原文），需要限制展示条数（建议最多 20 条 red + 其余折叠/摘要）。

### 测试清单（必须实现）

| 测试 | 断言 |
|---|---|
| `test_hitl_pauses` | 有 red 时返回 `__interrupt__`；`snapshot.next == ("human_review",)`；状态 `awaiting_human` |
| `test_no_red_fast_path` | 无 red 时不停顿，直接完成，状态 `completed` |
| `test_no_business_write_before_approval` | 审批前没有最终报告/审计通过记录/外部调用；pending 元数据可以有 |
| `test_approve_resumes_and_writes_once` | `Command(resume=approve)` 后状态 `approved`；报告只落一次；actor=reviewer |
| `test_reject_skips_explanation` | 拒绝后不调用解释 LLM；报告状态 `rejected` |
| `test_timeout_never_approves` | 超时后状态 `unreviewed_red_risk`；报告不出现“通过/批准” |
| `test_duplicate_resume_idempotent` | 第二次 resume 不重复写、不重复调 LLM |
| `test_checkpointer_required` | 未注入 checkpointer 时编译/启动直接报错 |

---

## 6. 证据

- aurelien `src/contract_agent/graph.py:108-148`：`interrupt()`、resume 重跑、审批前纯读取；
- aurelien `tests/test_graph.py:132-169`：暂停断言、审批前 registry/audit 为空、approve 只写一次；
- zihan `python/src/pipeline/graph.py:383-418`、`services/review_service.py:288-289`：`interrupt_before` + `aupdate_state` + `ainvoke(None)` 对照；
- bcefghj `python/src/pipeline/graph.py:42-52`、`api/main.py:112-115`：伪 HITL 反例；
- `01_RESEARCH_LOG.md` 第 4 节模式 B、第 5 节不借鉴清单。

---

## 7. 实现回填（2026-10-27，第三阶段第 4 步）

> 本节只记录“实际实现与原决策的差异/细化”，不改变 §1~§6 的结论。

### 7.1 落地文件

| 文件 | 内容 |
|---|---|
| `app/nodes/hitl.py` | `build_approval_payload()`、`interrupt()`、决策解析与 fail-closed、`route_by_risk()` |
| `app/services/checkpointer.py` | `memory_checkpointer()` / `sqlite_checkpointer()` / `open_checkpointer()` + `JsonPlusSerializer` 类型登记 |
| `app/review_service.py` | `ReviewService.start()/get()/resume()`、惰性超时、幂等 |
| `app/graph.py` | 7 节点 + `add_conditional_edges("evaluate_rules", route_by_risk, ...)` + 强制 checkpointer |
| `tests/test_hitl.py` | 14 个 HITL 测试（覆盖 §5 测试清单并多于 8 条） |

### 7.2 与原决策的差异

| 项 | 原决策 | 实际实现 | 原因 |
|---|---|---|---|
| checkpointer | 运行 `AsyncSqliteSaver` | 同步 `SqliteSaver`（`sqlite3.connect(..., check_same_thread=False)`） | CLI 同步调用最简单；未引入异步运行时；FastAPI 阶段如需异步再评估 |
| 超时触发 | `GET /review/{id}` 惰性检查 | `ReviewService.get()` 惰性检查（API/UI/CLI 共用） | 先把语义固定在 service 层，API/UI 只做展示 |
| 决策 schema | `HitlDecision` | 同左，但**非法/缺失决策按 fail-closed 处理** | 不能让异常输入被解释成 approve |
| 人工 override | 未细化 | 仅产生 warning，不写入等级 | 守住“人工不改规则等级”边界 |
| 载荷上限 | 建议最多 20 条 red | `MAX_PAYLOAD_FINDINGS=20`，超出给 `truncated` | 与建议一致，已测试 |
| 恢复幂等 | 第二次 resume 不重复写 | 已终态直接返回现有结果，不重跑图 | 已终态再执行会重复生成报告 |

### 7.3 状态语义（实测）

- `invoke()` 暂停返回 `{"__interrupt__": [...], ...state}`，`state.status` 仍为 `running`；
- `snapshot.next == ("human_review",)` 是“等待审批”的唯一可靠判据；`awaiting_human` 由 service 派生；
- `resume` 时节点从顶部重跑，因此 `build_approval_payload()` 必须保持纯读取/纯计算；
- 审批前不写最终报告（`report is None`），测试 `test_no_business_write_before_approval` 断言。

### 7.4 已知不足（对应 ISSUE-017）

`ReviewService._requested_at` 为进程内存字典，重启后惰性超时失效；第 6 步随 FastAPI 落盘 `.data/pending/<review_id>.json` 修复。修复前不得对外宣称“超时一定会触发”。
