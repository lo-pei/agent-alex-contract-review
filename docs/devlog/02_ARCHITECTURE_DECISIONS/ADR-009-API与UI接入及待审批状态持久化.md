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

---

## 第 2 轮补充（2026-10-27）：原生 Web 前端（无框架）取代 Streamlit 成为主界面

### 背景

第 6 步交付的“UI”是 Streamlit 脚本：功能完整，但它是**服务端脚本式界面**（页面结构由 Python 生成、每次交互整页重跑），与用户期望的“真正的前端”有差距。用户明确要求“我需要真正的前端”，浏览器端还出现过 Vite 的 `/@vite/client` 请求（404）。

同时有两条不能破的约束：

- **`开发提示词.md` 要求“Streamlit（极简前端）”，并禁止引入前端框架**（无 React/Vue/Svelte、无 npm 构建、无 CDN 依赖）；
- 前端不得判级、不得拼 `Command`，一切人工决定必须经 `ReviewService.resume()`（ADR-002/本 ADR 决策 1）。

### 选项

| 方案 | 结论 | 原因 |
|---|---|---|
| A. Vite + React/Vue SPA | 否 | 违反“禁止前端框架”；引入 npm/构建链与联网依赖，与离线演示、依赖最小化冲突 |
| B. 继续只用 Streamlit | 否 | 不能算“真正的前端”：无独立页面、无客户端交互状态、样式与布局受限 |
| C. 原生 HTML/CSS/JS 单页，FastAPI 直接托管（采用） | 是 | 浏览器原生页面、无框架/无 CDN/无构建；与现有 REST 接口天然契合，测试可完全离线跑 |

### 决策

1. 新增 `app/web/`：`index.html`、`styles.css`、`app.js`（约 28 KB），**零第三方依赖**，图标用内联 SVG / data URI；
2. `app/api.py` 增加：
   - `GET /` → `FileResponse(index.html, Cache-Control: no-store)`（`include_in_schema=False`）；
   - `app.mount("/static", StaticFiles(directory=WEB_DIR))`；
   - `API_VERSION` 0.6.0 → 0.7.0；
3. 页面是“上传 → 规则审查 → 人工确认 → 报告”的四步单页：
   - 上传：拖拽/点选 + 前端类型/大小/空文件校验，`FormData` 提交 `POST /api/reviews`；
   - 人工确认：逐条展示 `ApprovalPayload.findings`（理由、建议、条款、引用原文），三个结论 + “标记为超时”，提交 `POST /api/reviews/{id}/decisions`；
   - 报告：渲染 `ReviewReport`（红/黄清单、解释来源与质量门、抽取要素、待核对、限制），下载 JSON / Markdown；
   - 会话恢复：只在 `localStorage` 存 `review_id`，刷新后 `GET /api/reviews/{id}` 恢复；
4. **安全与边界**：
   - 所有后端文本经 `esc()` 转义后才进入 `innerHTML`（合同内容可能含 HTML）；
   - 页面不定义任何本地判级逻辑，不出现 `Command`；测试用正则钉住“不得给 `risk_level` / `overall_level` 赋值”；
   - 状态冲突（409）时重新拉取最新状态再渲染；网络错误时保留已填写的复核人与意见；
5. **Streamlit 保留**（`app/ui.py`），作为备用/内网演示界面，二者共用同一套 `ReviewService`；
6. **测试**：新增 `tests/test_web.py` 5 项——首页 200 + `no-store`、静态资源 200、无外链（仅允许 SVG 命名空间）、无本地判级/`Command`、资源存在且不写死 host/端口。

### 后果

**正面**

- 有真正的浏览器前端：独立页面、客户端状态、响应式布局、深浅色适配、打印样式；
- 无 npm、无构建、无 CDN：`git clone` 后启动 FastAPI 即可用，离线演示与比赛环境更稳；
- 与 API 同源部署，没有跨域与额外代理配置。

**代价 / 风险**

- 手写 DOM 与状态管理，复杂度高于框架；后续若要做复杂表格/图表，需要评估是否引入库（仍需遵守无框架约束）；
- 样式用到 `:has()`、`color-mix()`，需要较新的 Chrome/Edge/Safari（项目演示环境满足）；
- 无前端单测框架：靠 `tests/test_web.py` 的静态断言 + 手工冒烟，交互级回归依赖人工；
- 上传大小上限（15 MB）在前端与后端各写一份，改 `MAX_UPLOAD_MB` 时需同步 `app.js`（已在代码注释与 README 标注）。

### 证据

- 前端：`app/web/index.html`、`app/web/styles.css`、`app/web/app.js`
- 后端托管：`app/api.py`（`WEB_DIR` / `INDEX_FILE` / `/` / `/static`）
- 测试：`tests/test_web.py`（5 项）
- 验证：`pytest` 241 passed；`ruff check .` 通过；`node --check app/web/app.js` 通过；HTTP 冒烟 `POST /api/reviews → 201（3 条红色）→ decisions 200 → markdown 200（3482 B）`
