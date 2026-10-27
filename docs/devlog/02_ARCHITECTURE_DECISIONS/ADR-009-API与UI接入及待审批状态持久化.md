# ADR-009：FastAPI / Streamlit 接入与待审批状态持久化

- 状态：**已接受（已实现）**
- 日期：2026-10-27
- 决策人：用户 + Trae AI
- 关联：ADR-002（HITL）、ADR-004（持久化/线程模型）、ADR-008（RAG 与解释质量门）、ISSUE-017/019

## 背景

第 5 步结束时只有 CLI 与库调用，缺两件事：

1. **交付形态**：比赛要求“Streamlit + FastAPI”，需要上传、运行、看到审批载荷、提交人工决定、下载报告；
2. **HITL 超时跨进程**：`ReviewService._requested_at` 是进程内 `dict`，进程重启后超时判定失效（ISSUE-017）。

同时有两个硬约束不能破：

- 等级只由 Python 规则判定，API/UI 不得重算或改写；
- 人工决定只能经 `ReviewService.resume()`，不允许外部直接拼 `Command(resume=...)`。

## 选项

### A. API/UI 直接调用 `graph.invoke` / `graph.get_state`

- 优点：代码少。
- 缺点：上传校验、幂等、惰性超时、pending 时间戳会散落在两处（CLI/API/UI），极易出现“UI 自己拼 Command”；违反 ADR-002。

### B. 抽一层 `ReviewService`，API/UI 只依赖它（采用）

- 优点：状态机与幂等只实现一次；CLI/API/UI 行为一致；测试可注入内存 checkpointer。
- 缺点：`ReviewService` 需要新增 pending store 与锁，稍微变厚。

### C. 引入任务队列（Celery/RQ）与消息中间件

- 优点：真正异步、可横向扩展。
- 缺点：硬约束禁止 Redis/消息队列；本项目审查是秒级同步操作，不需要。

### pending 时间戳的三种存法

| 方案 | 结论 | 原因 |
|---|---|---|
| 进程内 dict（现状） | 否 | 重启即失效（ISSUE-017） |
| checkpoint `updated_at` 兜底 | 否 | 与“进入人工确认”的时间不等价，且 `SqliteSaver` 未暴露稳定字段 |
| 独立 JSON 文件原子写（采用） | 是 | 零新依赖、可跨进程、易清理、易测试 |

## 决策

1. **`ReviewService` 是唯一入口**：`start / get / resume / get_state`；API 与 Streamlit 都只调它。
2. **pending 时间戳落盘**：新增 `app/services/pending_store.py`
   - `FilePendingStore` 写 `.data/pending/<review_id>.json`（`tempfile` + `os.replace` 原子替换）；
   - `MemoryPendingStore` 供测试；
   - `review_id` 正则白名单（`^[A-Za-z0-9_-]{1,64}$`）防路径穿越；
   - 文件损坏/缺失一律视为“未记录”，**不判超时**（绝不误伤刚开始的审批）。
3. **超时仍是惰性检查**：`get()` 发现 `awaiting_human` 且 `now - requested_at >= HITL_TIMEOUT_MINUTES` → `resume(TIMEOUT_DECISION)` → `unreviewed_red_risk`。
4. **并发**：`ReviewService` 内部按 `review_id` 维护 `threading.RLock`（`get` 里可能要重入 `resume`），`start/get/resume` 全部持锁；仅单进程有效，多进程限制写入 ISSUE-019。
5. **API**（`app/api.py`）：
   - `create_app(service=None, upload_dir=..., pending_dir=..., max_upload_mb=...)`；不传 `service` 时 lifespan 内开 `sqlite_checkpointer()` + `FilePendingStore`；
   - `GET /health`、`POST /api/reviews`（UploadFile）、`GET /api/reviews/{id}`、`POST /api/reviews/{id}/decisions`、`GET /api/reviews/{id}/report?format=json|markdown`；
   - 上传：只取 basename（同时处理 `\` 与 `/`）、后缀白名单（`.txt/.md/.markdown/.pdf/.docx`）、`.doc` 明确提示转换、分块读取 + 大小上限（413）、空文件 400；落盘 `.data/uploads/<review_id>/<filename>`，失败即清理目录；
   - 错误码：400（类型/空文件）、404（未知 review_id，`ReviewStateError.missing`）、409（状态冲突/报告未生成）、413（超限）、422（Pydantic 校验，含非法 review_id）；
   - 响应模型 `ReviewSummary` 只暴露 `status / overall_level / awaiting_human / approval / report / warnings / errors`，不返回完整 state，避免把合同原文塞进列表接口。
6. **报告 Markdown**（`app/report_markdown.py`）：纯渲染，不重算等级；表格单元格转义 `|`、正文折叠换行；解释缺失写“未提供”，不伪装。
7. **Streamlit**（`app/ui.py`）：
   - `st.cache_resource` 持有 SQLite checkpointer + `FilePendingStore` 的 service（`atexit` 关闭）；
   - 上传 → 开始审查 → 展示审批载荷（按条展开、原文用 `st.code`）→ 批准/要求修改/拒绝/标记超时 → 展示报告 + 下载 JSON/Markdown；
   - 不拼 `Command`；超时按钮显式标注“结果绝不会是通过”。
8. **依赖**：`requirements.txt` 增加 `python-multipart`（FastAPI 上传必需）；`requirements-dev.txt` 增加 `httpx`（TestClient 必需）。

## 后果

**正面**

- CLI / API / UI 行为一致，HITL 语义只需维护一处；
- 进程重启后惰性超时仍生效（`test_lazy_timeout_survives_service_restart`）；
- 上传路径不可穿越，文件名不会覆盖其他审查的文件；
- 报告 JSON 与 Markdown 同源（`ReviewReport`），不会出现“UI 显示与下载不一致”。

**代价 / 风险**

- 每次 `get` 都要读一次 pending JSON 与一次 checkpoint 快照；单机规模可接受；
- 上传目录与 pending 文件无保留期（ISSUE-019）；
- 进程内锁不覆盖多 worker 部署场景；
- Streamlit 用 `st.cache_resource` 持有 checkpointer 连接，热重载时依赖 `atexit` 释放，未做连接池。

**后续要补**

- 多进程/多 worker 的文件锁或“单 worker 部署”声明（ISSUE-019）；
- 上传/报告清理脚本与保留期；
- 检索评测映射（ISSUE-018）完成后，再把 RAG 引用效果写进评测结果。

## 证据

- `app/api.py`、`app/ui.py`、`app/report_markdown.py`、`app/services/pending_store.py`、`app/review_service.py`
- 测试：
  - `tests/test_api.py`：health、上传暂停、审批后下载 JSON/Markdown、报告 409、快速通道幂等、404、非法 review_id 422、坏后缀/空文件/大小限制、文件名净化、非法决策 422；
  - `tests/test_pending_store.py`：原子写、跨实例/跨 service 超时、损坏文件、非法 ID、决定后清理；
  - `tests/test_report_markdown.py`：章节完整、等级只读、表格转义、真实审查渲染；
  - `tests/test_ui.py`：Streamlit 首屏无异常。
- 全量：`pytest` 197 passed；`ruff check .` 通过。
