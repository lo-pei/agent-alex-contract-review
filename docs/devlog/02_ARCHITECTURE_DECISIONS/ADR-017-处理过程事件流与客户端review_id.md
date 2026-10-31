# ADR-017：处理过程事件流（节点级进度）与客户端 `review_id`

- 状态：**已接受（2026-10-31）**
- 日期：2026-10-31
- 决策人：用户（要求“像参考产品一样展示思考/处理过程”）+ Trae AI
- 关联：ADR-002（HITL 真中断）、ADR-004（状态持久化）、ADR-009（API/UI 接入）、ISSUE-027（旧的“流式输出”是前端动画）

## 1. 背景

用户反馈“我的 Agent 没有思考过程，这个过程没有以这种布局形式呈现”，并给了一张参考图：
顶部一行“处理中 16 秒 · 运行中 / 收起过程 ^”，下面逐行列出节点（正在启动 1 秒 / 正在处理 4 秒 /
Agent 开始处理 7 秒 / 法律法规检索 运行中 + 工具计数与条件明细）。

此时产品的真实行为是：

- `POST /api/reviews` **同步跑完图**（遇 HITL 才 `interrupt()`），浏览器在整段时间里只看到转圈；
- 界面轮 11 曾有一段“逐字流式输出”，但它是在拿到完整结果后由前端定时器铺字，不是真进度，
  界面轮 12 已删除（ISSUE-027 关闭）；
- 页面因此看起来“没有过程”，用户无法判断卡在读文件、切条款、跑规则还是等模型。

硬约束不变：**过程事件只描述“做了什么”，绝不携带 `risk_level`**；等级仍只来自 Python 规则（ADR-003），
红色风险仍必须人工确认（ADR-002）。

## 2. 选项

| 方案 | 优点 | 缺点 | 结论 |
|---|---|---|---|
| A. 前端动画模拟“思考中” | 零后端改动、立刻好看 | 与真实状态脱节；旧 ISSUE-027 已证明会误导用户 | 不选（禁止） |
| B. `POST /api/reviews` 改异步 + SSE 事件流 | 真推送、延迟最低 | 要改提交协议（202 + 任务句柄）、HITL 恢复链路、Streamlit 备用端；本轮改动面过大 | 不选（本轮） |
| C. 节点级事件写入进程内表 + 客户端轮询 | 不动图拓扑与 HITL；同步 POST 期间也能看到已完成节点；轮询失败不影响结论 | 事件只存在内存、重启即丢；不是“推送” | **采用** |
| D. 把过程事件写进 checkpointer / SQLite | 可跨进程、可回放 | 与业务状态耦合同一张表；清理与隐私边界变复杂 | 不选（事件是 UI 辅助数据） |

## 3. 决策

### 3.1 事件模型（`app/services/progress.py`）

- 每个节点一行事件：`node`、`label`（中文名）、`hint`（一句说明）、`status`
  （`running / done / waiting / failed`）、`detail`（结果摘要）、`duration_ms`、`started_at`。
- `ProgressStore` 用 `RLock` + `OrderedDict` 限制规模：最多 40 个 review、每个 review 最多 80 条事件，
  超出按最旧淘汰；`clear(review_id)` 在删除审查记录时同步调用。
- **只写过程，不写结论**：事件里没有 `risk_level`、没有 `overall_level`，也不参与报告生成；
  过程丢了不影响判级与报告。

### 3.2 图侧埋点（`app/graph.py`）

- 不新增节点、不改边：用 `_tracked(node, func)` 包一层 `builder.add_node`，
  进入节点 `begin()`，正常返回 `finish(detail=摘要)`，`GraphBubbleUp`（`interrupt()`）记 `waiting`，
  其他异常记 `failed` 后继续抛出。
- `_summary_of_node(node, updates)` 只从该节点返回值里取**可展示的结构化摘要**
  （页数/字符数、条款条数、命中红黄条数、工具调用次数、解释是否降级），不做二次判断。
- 拓扑、条件边、HITL、checkpointer 一律不动（ADR-001/002/004 不受影响）。

### 3.3 客户端 `review_id`

- 上传前浏览器用 `crypto.getRandomValues` 生成 16 字节 hex，作为表单字段 `review_id` 提交，
  这样**在 POST 还没返回时**就能轮询 `GET /api/reviews/{id}/progress`。
- 服务端校验：空串 → 服务端生成 UUID；不符合 `REVIEW_ID_PATTERN` → 400；已存在 → 409。
- 轮询 `GET /api/reviews/{review_id}/progress` 返回 `{review_id, running, events}`；
  只有 404 才停止轮询，网络抖动按间隔重试；审查结束后面板保留可折叠的结果，刷新/历史进入默认收起。

### 3.4 前端呈现（`app/web/app.js` + `styles.css`）

- 上传页输入框下方、结果页顶栏下方各有一个 `#process-slot`；卡片头是
  “处理中 · N 秒 / 收起过程”，列表逐行显示 `✓ / 脉冲点 / !` + 节点名 + 耗时 + 状态 + `detail`。
- 事件为空时先合成一行“正在启动”，避免空白；`done` 后秒数停住，仍可展开回看。
- 结果页其余布局按界面轮 17 重做（左原文高亮 / 右原因与修改意见），过程卡片不占用左右两栏。

## 4. 后果

- **正面**：同步 POST 期间的等待变成可读的过程；用户能区分“在读文件 / 在跑规则 / 在等模型”；
  事件与结论分离，不引入新的判级路径。
- **代价**：事件在进程内，重启丢失（可接受：它只是过程展示）；多 worker 时轮询可能打到没有该事件的
  worker（单 worker 演示部署下不成立，与 ISSUE-025 同源）；需要清理逻辑（已随 `delete_review` /
  `clear_reviews` 调用）。
- **不做**：不把事件做成持久化审计日志；不在事件里塞等级、得分或模型原始输出；不用前端动画伪造进度。
- **后续**：若要多 worker / 断线重连，再评估 SSE（选项 B），并新写 ADR 替代本条，不直接改历史结论。

## 5. 证据

- 代码：`app/services/progress.py`、`app/graph.py`（`_tracked` / `_summary_of_node`）、
  `app/api.py`（`review_id` 表单字段 + `GET /api/reviews/{id}/progress` + 清理）、
  `app/web/app.js`（`beginProcess` / `pollProcess` / `renderProcessSlot`）、`app/web/styles.css`（`.process`）。
- 测试：`tests/test_progress.py`（事件写入/中断记 waiting/端点不含等级/非法 id 400/重复 id 409/删除即清理）；
  `tests/test_web.py`（过程面板与结果页静态约束）。
- 实测（2026-10-31，`ui-check-063513`）：13 条事件依次为读取文件 30ms → 判断是不是合同 4ms →
  切分条款 4ms（17 条）→ 抽取关键要素“已降级” → 专家 4 条“未启用” → 规则判定 192ms（红 0 / 黄 2）
  → 检索补充材料 6.3s（工具 2 次）→ 生成解释 3.1s（回退规则理由）→ 生成报告。
