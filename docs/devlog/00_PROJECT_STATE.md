# 项目状态快照

> 更新时间：2026-10-28（界面轮 10：账户设置改成 B 端分区弹窗（个人信息 / 通用 / 数据管理 / 关于）+ 主题色 5 套 + 界面字号三档 + 侧栏不再显示昵称与邮箱；界面轮 9：个人账户弹窗（头像/昵称/系统设置/二次确认清数据）+ Skill 查看与编辑 + 仓库紧凑化 + 厂商 20 个 + 阻止密码自动填充；界面轮 8：注册 not found 根因（旧进程 0.9.0）+ Skill 支持 Markdown/文件夹批量导入；界面轮 7：Skill 仓库独立页面 + 自绘 Skill 下拉 + 页脚贴右/降高 + 输入区收窄；界面轮 6：审查历史子目录 + 记录改名/置顶/删除 + 侧栏 Skill 仓库 + 满屏布局 + 登录弹窗定高与同意勾选；界面轮 5：账号/审查记录/Skill 仓库/BYOK + 右侧对话式首屏；界面轮 4：极简 C 端页“上传合同 → 看风险点”；界面轮 3：非合同闸门 + 收掉内部信息；界面轮 2：B 端工作台；第四阶段第 4 轮：规则 version 5 + 保额邻近判定 + 第四批留出集）
> 当前阶段：**交付形态补齐：对话式 Web 前端（`app/web/` 原生 HTML/CSS/JS，右侧对话式首屏 + 结果页；侧栏 = 导航壳 + API 配置 + 接口文档 + 账号区；无框架/无 CDN/无构建/本地字体）；账号体系按 **ADR-013** 落地（本地 SQLite：口令 PBKDF2、会话只存哈希、审查记录按账号隔离、Skill 仓库、BYOK 密文盒 + 每审查模型运行时，`API_VERSION 1.0.0`）；上传先做**文档类型闸门**（论文/法规不进入判级）；第四阶段（测试与评测）进行中：规则 13 条（`version: 5`）；silver gold 21 个现象；四批留出集 40 份；当前唯一可对外报的数来自 holdout4（12 份）：P=1.00 / R=0.889 / F1=0.941（唯一漏报 H39，故意不修）**
> 项目目录：`d:\A项目\Agent_Alex外贸合同智审助手`
> Git：`cf0fd63`、`71e8a9d`、`750cca3`、`625e9bd`（第 3 步）、`e41d235`（第 4 步）、`c7f24a9`（第 6 步）、`6eaff8c`（第 4 阶段第 1 轮）、`5dc05bd`（第 2 轮）、`c540259`（第 3 轮）、`eba67c0`（界面轮 1）、`892ddf2`（界面轮 2），本轮提交见 `git log`
> 范围变更：2026-10-27 用户明确「可以做 rag 和多 agent」→ **ADR-007**；第 5 步按 **ADR-008** 落地 RAG MVP；第 6 步按 **ADR-009** 落地 API/UI 与 pending 持久化（第 2 轮：原生 Web 前端；第 3 轮：B 端工作台 + `/api/rules` + 本地字体；第 4 轮：移除运行环境块 + 非合同页；第 5 轮：侧栏保留、主区对话式）；界面轮 3 按 **ADR-012** 增加“是不是合同”的类型闸门；界面轮 5 按 **ADR-013** 增加账号、审查记录、Skill 仓库与 BYOK（RAG/多智能体仍默认关闭，只增强解释、不判级）

## 一句话了解项目

面向“国际货物销售合同”的 AI 预审智能体：上传 PDF/DOCX/TXT → **判断是不是合同（不是就停）** → 条款切分 → LLM 抽取关键要素 → **Python 规则引擎判定红/黄/绿风险**（唯一等级来源）→ 红色风险经 **LangGraph `interrupt()` 真人工确认** → LLM 依据规则结果、合同原文与知识片段生成解释 → Python 质量门校验后输出可追溯报告。交付：**对话式 Web 前端（`app/web/`，FastAPI 托管：给审查重点/附件/Skill → 查看风险点 → 人工确认 → 下载报告）+ 账号与审查记录 + BYOK 模型配置** + 命令行 + API（Streamlit 备用），10 天完成。

## 当前完成度

| 模块 | 状态 | 说明 |
|---|---|---|
| 第一阶段：GitHub 调研 | ✅ 100% | 8 个仓库源码级分析；用户已确认 |
| 第二阶段：架构设计 | ✅ 100% | ADR-001 ~ ADR-013 全部**已接受**（ADR-007 范围变更、ADR-008 RAG、ADR-009 API/UI、ADR-010 规则扩充、ADR-011 评测方法与 gold 口径、ADR-012 上传文档类型闸门、ADR-013 账号体系与 BYOK） |
| 第三阶段第 1 步：环境 + 最小图 | ✅ 100% | `.venv`/依赖/最小图/规则引擎/测试/git |
| 第三阶段第 2 步：解析 + 切分 | ✅ 100% | TXT/MD/文本型 PDF/DOCX；标题切分/合并/超长拆分/上限 |
| 第三阶段第 3 步：LLM 抽取 + 校验 | ✅ 100% | 17 字段抽取/引文核验/降级/字段规则 skipped；Fake LLM 测试 |
| 第三阶段第 4 步：HITL 真中断 | ✅ 100% | 条件边/`interrupt()`/审批载荷/checkpointer/幂等/惰性超时；15 个 HITL 测试 |
| 第三阶段第 5 步：解释 + 质量门 + RAG MVP | ✅ 100% | `explain_risks` 节点/越权拦截/引用定位/BM25 检索/引用白名单；28 个新测试 |
| 第三阶段第 6 步：FastAPI + Streamlit | ✅ 100% | 上传/审查/人工决定/下载 JSON+Markdown；pending 落盘；37 个新测试 |
| 界面轮 11：方块 Skill + 弹窗化 + 对话式逐条审查 | ✅ 100% | 推荐 Skill 改 1:1 方块网格（`aspect-ratio`，7 个 130×130）；新建/导入移到页头右上角、改静态弹窗（`#skill-new-dialog` / `#skill-import-dialog`，委托挂到 `document`）；上传后先对话式逐段输出审查结论（`#ai-stream`，18ms/3 字），再左右分屏逐条审查（`#clause-list` / `#clause-detail`），有问题条款给建议 + 示例条款 + 一键更正/撤销/全部更正，并可导出 DOCX/PDF（`GET /clauses`、`POST /export`）；任务未结束时退出登录先弹“会中断任务”二次确认；全量 **323 测试** + CDP 复核 |
| 界面轮 10：账户设置 B 端弹窗 + 侧栏收口 | ✅ 100% | 左下角只留“退出登录 + 头像”，不再显示昵称/邮箱；`#account-dialog` 改为左侧分区导航（个人信息 / 通用 / 数据管理 / 关于）+ 右侧面板；通用区含主题色 5 套（只换 `--accent`）、界面字号 小/标准/大（`--ui-text-scale`）、减少动效 / 自动聚焦 / 恢复默认；数据区含统计卡与两档清除（仍二次确认）；关于区显示版本、政策入口与数据位置；全量 **308 测试** + CDP 21 项 |
| 界面轮 9：个人账户 / Skill 编辑 / 紧凑 / 厂商扩容 | ✅ 100% | 侧栏“退出登录”右侧 26px 圆形头像 → `#account-dialog`（头像 128px JPEG、昵称、系统设置、清除本机缓存 / 清空审查记录均二次确认）；仓库列表一行折叠、自建可编辑（`PATCH /api/skills/{id}`）、推荐可“存为我的”；右栏面板收紧；厂商 10→20；API Key 输入 `autocomplete=new-password` 等属性阻止浏览器快捷填入；全量 **308 测试** + CDP 冒烟 |
| 界面轮 8：注册 not found + Skill 导入 | ✅ 100% | 注册失败根因是 8000 端口跑着旧进程（`openapi` 0.9.0，无 `/api/auth/*`）→ 重启为 `API_VERSION 1.0.0` 后 `/api/auth/me` 200；Skill 仓库新增“从 Markdown 导入”：拖拽文件/文件夹 + 两个选择入口，前端解析 frontmatter/标题/首段后逐条 `POST /api/skills`（同名跳过、超长截断、单次 30 个 / 单文件 200 KB）；全量 **298 测试** + CDP 10 项 |
| 界面轮 7：仓库独立页 / 自绘下拉 / 页脚贴右 / 输入区收窄 | ✅ 100% | `#/skills` 独立页面（推荐 7 + 我的 + 新建），删除仓库弹窗；系统 select 换成胶囊 + 自绘 listbox（12px 卡片、键盘可达、末项仓库、8 项无滚动条）；页脚铺满整行、政策链接贴右、高度 26px；输入区 880→720；全量 **297 测试** + CDP 20 项 |
| 界面轮 6：历史子目录 / Skill 归位 / 满屏 / 弹窗定高 | ✅ 100% | “当前审查”改“审查历史”并在侧栏展开子目录（改名 / 置顶 / 删除）；Skill 仓库入口收到侧栏、下拉末项固定“Skill 仓库…”且默认 `builtin:full`；主区铺满屏幕；登录弹窗两种模式定高 460×453；登录/注册都必须手勾同意；`PATCH|DELETE /api/reviews/{id}`；全量 **295 测试** |
| 界面轮 5：账号 / 记录 / Skill / BYOK + 对话式首屏 | ✅ 100% | 本地 SQLite 五表（账号/会话/Skill/模型配置/审查记录）、PBKDF2 口令与哈希会话、密文盒 Key（只回尾号）、每审查 `LLMRuntime`、7 个内置 Skill + 自建、右侧对话式输入区（Enter 发送/拖拽/审查重点/Skill 下拉）、底部免责 + 右下角政策弹窗；`API_VERSION 1.0.0`；`tests/test_accounts.py` 24 项 + `tests/test_web.py` 14 项；全量 **288 测试** |
| 界面轮 4：侧栏保留 + 主区极简 | ✅ 100% | `app/web/` 主区收成两屏（上传 → 风险点），侧栏/顶栏导航壳保留；待确认态直接列出审批载荷中的红色风险；下载改指 `/report`；`tests/test_web.py` 10 项；全量 261 测试 |
| 界面轮 3：非合同闸门 + 收掉内部信息 | ✅ 100% | 新增 `precheck_document`（`app/services/document_type.py`，纯规则）；`status=not_contract` 直接出“未执行审查”报告，不切条款/不抽取/不判级/不触发 HITL；`ReviewSummary.document_check`；前端新增“不是合同”页并移除侧栏“运行环境”；API 0.9.0；11 个闸门测试 + 1 个 API 测试 + 1 个前端测试 |
| 界面轮 2：B 端审查工作台 | ✅ 100% | `app/web/` 重写为工作台（侧栏 + 面包屑 + sheet 画布 + hash 路由四视图）；本地 IBM Plex 字体（无 CDN）；新增只读 `GET /api/rules`；6 个前端测试 + 1 个规则目录测试 |
| 第四阶段：测试与评测 | ⏳ 85% | 规则 13 条（`version: 5`：三类措辞 + 保额邻近判定）；50 份合同 + 21 个 silver gold 现象 + 四批留出集 40 份；**当前唯一未消耗的 holdout4：P=1.00 / R=0.889 / F1=0.941**（漏报 H39，故意不修）；检索评测（ISSUE-018）与人工复核 gold 仍未做 |
| 第五阶段：文档与交付 | ⏳ 45% | README/状态/交接/ADR/资料清单/开发日志已同步；答辩材料未做 |

## 最新产出（2026-10-28 界面轮 11：推荐 Skill 方块、新建/导入弹窗、对话式逐条审查 + 修订导出、退出中断确认）

- **起因（用户原话 4 条）**：
  1. 推荐 Skill 组件不喜欢**长矩形**，改成**正方形小方块排列**；
  2. 新建 Skill 和导入 Skill 需要放在**右上角的按钮**，点击后**弹窗**使用；
  3. 上传合同后以**对话形式流式输出**审查结果与报告；判为合同则**逐条拆分**、**左右分屏**逐条审查并给意见；有问题的条款给**修改建议 + 修改后的条款**，提供**一键更正**；可**一键导出 DOCX / PDF**；
  4. 审查任务进行中点退出，必须**弹窗提示会中断任务**并再次确认。
- **Skill 仓库（`app/web/app.js`、`index.html`、`styles.css`）**：
  - `skillTile()` → `.skill-tiles` 网格（`repeat(auto-fill, minmax(122px, 1fr))`），卡片 `aspect-ratio: 1/1`，卡内“名称 2 行 + 说明 2 行 + 右下角‘使用’胶囊”；实测 7 个 130×130；
  - 页头改为 `.skills-head`（左标题 + 右 `.skills-head-actions`），`#skill-new-open` / `#skill-import-open` 固定在右上角；右栏 `.skills-grid` / `.skills-side` / `.skill-form` 全部删除；
  - 新建与导入改成 `index.html` 里的静态弹窗（`#skill-new-dialog` / `#skill-import-dialog`），编辑自建 Skill 复用同一弹窗（`PATCH /api/skills/{id}`），推荐 Skill “存为我的”只是预填；
  - 弹窗在 `#view` 外，`bindSkills()` 的事件委托**全部改到 `document`**（click / submit / change / drop / keydown 按 id 过滤）。
- **后端（新增 2 接口 + 2 服务，不新增判级）**：
  - `app/schemas.py`：`ClauseFinding` / `ClauseReview` / `ClauseReviewList`（条款原文 + 命中规则 + 示例修订 + 合同级问题 + `limitations`）；
  - `app/services/clause_review.py`：从图状态聚合，**等级只搬规则结果**（`red > yellow > pass`，`pass` = 规则未命中），`skipped` 与非红/黄不入视图；`REVISION_TEMPLATES` 14 条示例条款（带 `___` 占位）、按“红在前”拼接且按 `rule_id` 去重；无条款归属的规则进 `contract_findings`；
  - `app/services/clause_export.py`：DOCX（`python-docx`）+ PDF（`reportlab` 内置 `STSong-Light`，不下载字体/不联网），三节“逐条意见 / 全合同问题 / 修订稿”+ 免责声明，内存生成不落临时文件；
  - `GET /api/reviews/{id}/clauses`、`POST /api/reviews/{id}/export`（`format: docx|pdf` + 已更正条款数组；`ExportError`→400；`filename*=UTF-8''…` + ASCII 兜底名；沿用 `authorize()` 的归属校验，越权/不存在统一 404）。
- **前端审查结果页**：
  - `.review-shell` = 用户气泡 + 助手气泡（`#ai-stream`）+ `#approval-slot` + `#workbench`；`chatNarrative()` 用真实数据拼句，`streamText()` 18ms/3 字逐段写入（`prefs.motion` 时整段直出，`stopStream()` 负责清理）；
  - 流式结束才展开工作台；`.workbench-grid` 左 `#clause-list`（序号 / 名称 / 等级 / 已更正✓，首行“全合同”）、右 `#clause-detail`（原文 / 意见 / 建议 / 依据 / 原文引文 / 知识引用 / 可编辑修订 / 一键更正 / 撤销）；
  - “全部更正”批量套用，`state.corrections` 只在前端保存；导出把最终文本 POST 给 `/export`，`Content-Disposition` 解中文名后 `blob` 下载；
  - `renderApproval()` 改为**只返回 HTML**（保留 `approval.findings` / `findings_total` / “待您确认”），由 `#approval-slot` 挂载后 `bindConfirm()`。
- **退出确认**：`hasActiveTask()` = `busy || taskActive || reviewStatus ∈ {awaiting_human, running}`；命中则 `#logout-confirm`（“审查任务仍在进行 / 退出会中断这次任务…”），取消不退出，确认走 `doLogout()`（先 `stopStream()` 再清状态）。这是**前端拦截**，后端没有“取消任务”接口（ISSUE-028）。
- **验证**：`pytest` **323 passed**（`tests/test_clause_review.py` 11 项新增 + `tests/test_web.py` 26 项）；`ruff check .` 通过；`node --check app/web/app.js` 通过；Edge headless + CDP 复核：方块 130×130、右上角按钮右边缘与页头齐平、两个弹窗可开可关、上传后 450ms 仅 105/276 字符（确为流式）、结束后分屏两栏 376/709 并排、红条款有意见/建议/示例条款、一键更正与撤销生效、导出 DOCX 39,086 B / PDF 9,205 B、任务中退出弹确认且取消不退出。
- **仍未做**：不是真 SSE（后端同步跑图，前端按时序铺开真实内容，ISSUE-027）；更正不落库（导出才是交付物）；修订文本是示例条款（未覆盖的规则只给建议）；退出中断没有后端清理接口（ISSUE-028）。

## 上一轮产出（2026-10-28 界面轮 10：账户设置 B 端分区弹窗、主题色与字号、侧栏不再显示昵称/邮箱）

- **起因（用户原话 2 条）**：
  1. 左下角**不用显示**“王勃森 / 2650406850@qq.com”；
  2. 个人信息弹窗**太简单**，希望按系统功能扩展（比如主题颜色），并采用**B 端侧边栏架构**（个人信息、通用（可调字号等）、数据管理……）。
- **侧栏（`app/web/index.html`、`app/web/app.js`、`app/web/styles.css`）**：
  - 删除 `#account-line`（连同 `accountLine`、`.account-line` / `.account-name` / `.account-mail`），左下角只剩“退出登录 + 26px 圆形头像”；`renderAccount()` 不再把昵称/邮箱写进侧栏；
  - 头像仍是无头像时的昵称首字母，点击打开设置弹窗；未登录仍只有“登录”。
- **弹窗改成 B 端设置形态**：
  - `.dialog.account-dialog` = **760×560**（覆盖 `.dialog` 默认 460px 必须先提高特异性），左 **164px 分区导航** + 右内容区；窄屏（≤640px）导航转顶部横向标签、弹窗 `calc(100vw - 16px)`、无横向溢出；
  - 四个分区（`data-account-panel` / `data-account-section`，`role="tab"` + `role="tabpanel"`、↑↓ 可移）：**个人信息**（大头像 + 更换/移除、昵称、只读邮箱、只读注册时间、保存资料）、**通用**（主题色 5 套、界面字号 小/标准/大、减少动效、自动聚焦、恢复默认外观）、**数据管理**（审查记录数 / 我的 Skill 数两张统计卡、清除本机缓存、清空审查记录）、**关于**（版本 1.0.0、隐私条款 / 使用政策入口、本机 SQLite 与密文 Key 说明）；
  - 数据统计**按需拉取**：打开“数据管理”才请求 `GET /api/reviews?limit=500` 并数本地自建 Skill；打开“关于”才请求 `/health` 取版本。
- **主题色与字号（只影响观感，不影响判级）**：
  - `html[data-theme]` 只换 `--accent`：松石绿（默认 `#1b6b7d`）/ 靛青 `#3a4f9b` / 石墨 `#3f4448` / 陶土 `#96522a` / 绛紫 `#6d4a7d`；深色 `prefers-color-scheme` 下换同色系亮版；风险红/黄/绿语义色不动；
  - `html[data-font]` 改 `--ui-text-scale`（小 0.94 / 标准 1 / 大 1.1），样式表里**所有** `font-size: Npx` 已改成 `calc(Npx * var(--ui-text-scale, 1))`，只缩放字号、不动 padding/宽度/图标；
  - 五项偏好都写 `localStorage`（`alex.prefs`：`motion` / `autofocus` / `theme` / `font`），关窗、刷新后保留；“恢复默认外观”只复位这四项。
- **验证**：
  - `pytest` **308 passed**（`tests/test_web.py` 22 项；个人账户测试改为分区断言，并断言侧栏**不再**有 `#account-line` 与 `accountLine`），`ruff check .` All checks passed，`node --check app/web/app.js` 通过；
  - **CDP 21 项全过、`exceptions: []`**（临时 8101 + 临时库 + Edge headless）：侧栏不含邮箱与昵称、弹窗 760×560 且左侧导航 164px、四分区分明、主题切到靛青后 `--accent=#3a4f9b` 且落盘、字号大档标题 23→25.3px 且小字同步、数据统计 0/0、空记录提示“不需要清除”、确认条可取消、关于版本 1.0.0、关窗后偏好保留、重开回到“个人信息”、480px 导航转横向且无横向溢出；截图复核 `account-v2.png` / `account-v2-general.png` / `account-v2-data.png` / `account-v2-mobile.png`。
- **仍未做**：偏好只在本机、不随账号同步（ISSUE-025）；没有“深色模式手动开关”（仍跟随系统）；字号三档不缩放布局尺寸；没有改密码 / 注销账号（ISSUE-025）。

## 上一轮产出（2026-10-28 界面轮 9：个人账户弹窗、Skill 查看/编辑、仓库紧凑化、厂商目录扩容、阻止密码自动填充）

- **起因（用户原话 6 条，来自两轮输入）**：
  1. 仓库页头那段“推荐 Skill 开箱可用…风险等级仍由规则判定”**可以删掉**；
  2. 推荐 Skill 点击可以**查看与修改**，UI 组件要**小巧**；
  3. 仓库整体布局**紧凑**，尤其右侧“新建 Skill”和“从外部导入”；
  4. API 配置里**增加一些厂商和模型类型**；
  5. 点 API 配置的填写框会弹**浏览器“快捷填入账号密码”**；
  6. “退出登录”右边加**圆形个人账户头像**，点击弹窗可设昵称/头像/系统设置/清除数据（清数据要二次确认）。
- **前端（`app/web/*`）**：
  - 仓库页去掉 `page-head` 说明段；列表项由“两行卡片”改成**一行**（名称 + 推荐/我的标签 + 折叠箭头 + 使用），点名称才展开说明、审查重点与“编辑/存为我的/删除”（`.skill-head` / `.skill-toggle` / `.skill-detail`，行高 36px→展开后按内容长），`aria-expanded` + `aria-controls` 同步；
  - 右侧两卡片收紧：`.panel` 18→12/13px 内边距、`.field-compact` 30px 输入、textarea 68px、`.btn-compact` 30px，卡片间距 14→10px；
  - 表单支持**新建 / 编辑**两种模式：点自建 Skill 的“编辑”把内容填进右栏（标题变“编辑我的 Skill”、按钮变“保存修改”、“取消”出现），提交走 `PATCH /api/skills/{id}`；推荐 Skill 只读，点“存为我的”预填并改名“（我的）”，提交仍是 `POST`；
  - 侧栏账号区改成 `.account-row`：左“退出登录”，右 **26px 圆形头像**（无头像时显示昵称首字母）；
  - 新增 `#account-dialog`：大头像 + “更换/移除”、昵称、只读邮箱、系统设置（减少动效 / 自动聚焦输入框）、数据区（清除本机缓存 / 清空审查记录），两个清除动作都**先出红色二次确认条**再执行；
  - 头像在浏览器里居中裁成正方形并压到 **128×128 JPEG**（`squareThumbnail`）后 `PATCH /api/auth/profile`，只传 data URL；偏好写 `localStorage`（`alex.prefs`），`data-motion="off"` 时全局关过渡；
  - API 配置表单：`autocomplete="off"` + Key 输入 `autocomplete="new-password"` + `data-lpignore` + `data-form-type="other"` + `name="llm_api_key"`，并给厂商/地址/模型都加 `autocomplete="off"`，避免浏览器当成登录表单弹出“快捷填入账号密码”。
- **后端**：
  - `PATCH /api/auth/profile`（`ProfileUpdate`：`display_name` ≤40、`avatar` ≤400k 且必须是 `data:image/(png|jpeg|webp|gif);base64,…`），`users` 表新增 `avatar` 列并通过 `_ensure_user_columns()` 对老库 `ALTER TABLE` 升级；`User` 模型带 `avatar`，`/api/auth/me` 一并返回；
  - `PATCH /api/skills/{id}`（自建可改；`builtin:*` 返回 400“请另存为我的 Skill”；跨账号 404；未登录 401），`update_skill` 与 `create_skill` 共用 `_clean_skill_fields()` 做 40/160/1000 校验；
  - 厂商目录 10 → **20**：新增 Gemini（OpenAI 兼容）、xAI、Groq、Mistral、Together、火山方舟（豆包）、百度千帆、腾讯混元、MiniMax、阶跃星辰、LM Studio（本地，Key 可空），每个都带默认 Base URL 与候选模型。
- **验证**：
  - `pytest` **308 passed**（账号/记录/Skill/BYOK 35、前端 `test_web.py` 22），`ruff check .` All checks passed，`node --check app/web/app.js` 通过；
  - **CDP 冒烟全过**（临时 8101 + 临时库 + Edge headless）：头像按钮在“退出登录”右侧且 <40px、点开弹窗、改昵称后首字母跟着变、`data-motion="off"` 生效、两个清除按钮都先出确认条、取消后隐藏、无记录时提示“不需要清除”、上传 PNG 后头像变成 128×128 JPEG、列表折叠/展开高度变化、编辑自建后列表改名、推荐 Skill 显示“存为我的”且预填成功、右栏表单 318px / 导入 187px（gap 10px）、厂商 option = 20 且包含火山与 Gemini、Key 输入 `autocomplete=new-password`；`exceptions: []`（无运行时报错）；截图复核 `skills-compact.png`、`account-dialog.png`。
- **仍未做**：没有“改密码 / 绑定邮箱 / 注销账号”；头像上限只按 data URL 长度拦（未做服务端重新编码）；清除审查记录是前端逐条 `DELETE`（N 条 N 次请求，没有批量接口）；推荐 Skill 仍不可直接改（设计如此）。

## 更早产出（2026-10-27 界面轮 8：注册 not found 根因、Skill 支持 Markdown/文件夹导入）

- **起因（用户原话 2 条）**：
  1. “为什么我注册账号显示 not found”；
  2. “skill 仓库增加，用户可以自己上传文件夹或 md 格式，来快捷纳入 skill”。
- **注册 not found 的根因**：不是前端路径写错，而是 8000 端口跑的是**旧进程**——`GET /openapi.json` 的 `info.version` 是 **0.9.0**（界面轮 3 的代码，只有 `/api/reviews`、`/api/rules`、`/health`），没有 `/api/auth/*`；前端 `POST /api/auth/register` 命中不存在的路由，FastAPI 返回 404 `{"detail":"Not Found"}`，`api()` 把 detail 原文显示到 `#auth-error`，用户看到的就是 “Not Found”。处理：停掉旧进程，用 `.venv\Scripts\python.exe -m uvicorn app.api:create_app --factory --port 8000 --host 127.0.0.1` 重启当前代码；复测 `version=1.0.0`、`GET /api/auth/me` → **200**。（uvicorn 没有 `--reload`，改后端必须手动重启；这条已写进 README 快速开始。）
- **Skill 导入（前端解析，不新增后端接口）**（`app/web/app.js`、`app/web/styles.css`）：
  - 仓库页右栏在“新建 Skill”表单下方新增 `<section class="panel skill-import">`：虚线 `.dropzone`（可聚焦、Enter/空格触发选择）+ 两个入口“选择 .md 文件”（`accept=".md,.markdown,text/markdown"`、`multiple`）与“选择文件夹”（`webkitdirectory directory multiple`）+ 错误行 `<p class="alert" id="skill-import-error">` + 结果日志 `<ul class="import-log">`；
  - 拖拽支持**整个文件夹**：`DataTransferItem.webkitGetAsEntry()` → `FileSystemDirectoryReader.readEntries()` 递归（`readEntryFiles`），非 md 后缀一律过滤；
  - 解析 `parseSkillMarkdown(fileName, rawText)`：优先 frontmatter（`name:` / `description:` / `instruction:`），其次一级标题、文件名、首段；长度与服务端上限对齐（名称 40 / 说明 160 / 指令 1000），超长截断并在日志里标注；
  - 逐条 `POST /api/skills`，**只提交 `name`/`description`/`instruction` 三字段**（`SkillCreate` 是 `extra="forbid"`，不能把 `truncated` 一起发）；同名（与已有列表比对）直接标记“已有同名 Skill，跳过”；
  - 上限：单次 **30** 个文件、单文件 **≤200 KB**；未登录先拦下并弹登录框（登录后不自动重试）；401 立即停止后续提交；全部失败时提示看日志原因；
  - 成功后 `loadSkills()` + `renderSkillList()` + `renderSkillSelect()`，侧栏 `#skill-count` 与下拉立即出现新 Skill。
- **验证**：
  - `pytest` **298 passed**（`tests/test_web.py` 新增 `test_skill_repo_imports_markdown_files_and_folders`，共 19 项），`ruff check .` All checks passed，`node --check app/web/app.js` 通过；
  - **CDP 冒烟 10 项全过**：拖拽区与两个入口存在、`accept` 正确、拖入时 `.is-over` 高亮、2 个 md 建成 2 个 Skill 且 `.txt` 被过滤、frontmatter 的 `name/description` 生效、侧栏计数 8→9、同名第二次导入被跳过、未登录导入被拦并弹登录、480px 无横向溢出；截图复核 `skills-import-done.png`、`skills-import-480.png`。
- **仍未做**：导入只在浏览器解析（服务端仅校验长度，不扫描文件内容）；上限只在前端执行（直接调 API 可绕过）；没有“批量导入预览/逐条编辑”；`GET /api/skills` 仍无搜索/分页（ISSUE-022）。

## 更早产出（2026-10-27 界面轮 7：Skill 仓库独立页、自绘下拉、页脚贴右、输入区收窄）

- **起因（用户原话 4 条）**：
  1. Skill 仓库不要弹窗，要**独立的页面**；
  2. Skill 配置按钮下面的下拉组件**太丑**，重做；
  3. 底部“只做合同预审辅助，不构成法律意见。”与“隐私条款 · 使用政策”**没有挨到页面右侧**，且**高度太高**；
  4. **对话框长度缩短**。
- **Skill 仓库独立页**（`app/web/index.html`、`app/web/app.js`、`app/web/styles.css`）：侧栏入口从 `<button>` 改成 `<a href="#/skills" data-nav="skills">`；删除 `#skills-dialog` 整块；`route()` 新增 `#/skills` 分支，`setShell("skills")` 让面包屑显示“Skill 仓库”、侧栏高亮；`renderSkillsPage()` 渲染两栏：左侧“推荐 Skill（7 个）+ 我的 Skill”，右侧“新建 Skill”表单（名称 / 一句话说明 / 审查重点指令），仍是同一套 `GET|POST|DELETE /api/skills`；列表里的“使用”跳回 `#/` 并带上所选 Skill，新建成功后 `state.skillId` 指向新 Skill；列表操作走 `#view` 事件委托，避免整页重渲染后监听失效。
- **Skill 下拉重做**：原生 `<select class="tool-select">` 换成 `.skill-picker` —— 触发器是胶囊按钮（`Skill` 小标签 + 当前 Skill 名 + 旋转箭头，`aria-haspopup="listbox"` / `aria-expanded` / `aria-controls`），菜单是自绘 `ul[role="listbox"]`：12px 圆角白卡片、轻投影、右侧弹出、选中项高亮加粗、每项带“推荐 / 我的”标签、最后固定“Skill 仓库… · 管理”；支持 ↑↓ 移动、Esc 收起、点空白处收起；`max-height:336px` 让 8 项一次全显示，不再出现小滚动条；窄屏（≤640）菜单改为与胶囊左对齐，避免右对齐越出屏幕左侧。
- **页脚贴右 + 降高**：`.sheet-foot` 去掉 `max-width: var(--content)`（820px，正是“没挨到右侧”的原因），改 `width:100%; max-width:none`；`padding-top` 16→8、字号 12→11.5、行高 1.6→1.45；`.sheet` 底部内边距 32→16，页脚实测高度 **26px**、右边缘距白纸内容区 0px（只差 32px 画布内边距）；`.foot-links{margin-left:auto}` 保持政策链接贴右。
- **输入区收窄**：`.composer-box` 与 `.chat-error` 的 `max-width` 880→720，`textarea` 最小高度 56→44，首屏观感更紧凑；1440 下仍居中、无横向溢出。
- **验证**：
  - `pytest` **297 passed**（新增 2 个前端测试：仓库是独立页、输入区与页脚尺寸），`ruff check .` All checks passed，`node --check app/web/app.js` 通过；
  - **CDP 冒烟 20 项全过**：输入区 720、页脚右边缘 1399/1432（差 33px 内边距）、页脚高 26px、政策链接右对齐、下拉 8 项末项“Skill 仓库…”、默认“全量体检”、菜单 12px 圆角且无滚动条、选中回写、点仓库跳到 `#/skills`、仓库页推荐 7 个 + 表单 + 0 个打开中的 dialog、面包屑同步、点“使用”回到 `#/`、480px 无溢出且菜单不越界；截图复核 `menu-open.png`、`skills-page-1440.png`、`chat-480-menu.png`。
- **仍未做**：仓库页没有搜索/分页（7 个推荐 + 自建一次性渲染）；“我的 Skill”还没有编辑（只有新建与删除）；同意勾选仍未留痕（ISSUE-025）。

## 上一轮产出（2026-10-27 界面轮 6：历史可运维、Skill 入口归位、铺满屏幕、弹窗定高）

- **起因（用户原话 7 条）**：
  1. 删掉首屏三行说明（“上传合同，先判断是不是合同…”“也可以把合同文件拖进输入区…”“审查重点只影响解释的侧重…”）；
  2. Skill 下拉把“不使用 Skill”换成“Skill”，默认配几个 Skill，**最后一个固定为 Skill 仓库**，删掉输入区的“Skill 仓库”按钮；
  3. 左侧侧边栏增加 **Skill 仓库**，并配置默认的、跟审理合同有关的几个 Skill；
  4. 页面没有填充整个屏幕、图片右侧大量空白 → 充分利用屏幕；
  5. 登录弹窗中邮箱与密码之间空隙太大 → 均匀排列；
  6. 登录和注册都要勾选同意隐私政策与使用条款，**默认不勾选**；
  7. “当前审查”改为“审查历史”，点击展开子目录，可查看过往记录并**重命名 / 置顶 / 删除**。
- **首屏与布局**（`app/web/app.js`、`app/web/styles.css`）：`.chat-sub / .chat-note / .chat-fine` 与三行文案全部删除；`.view` 改为 `display:flex; flex-direction:column; width:100%; max-width:none`，`.chat{flex:1; justify-content:center; padding:0 0 8vh}` 让首屏在整屏内垂直居中、输入区 `max-width:880px`；CDP 在 1440 量到白纸右边缘距视口 8px、1440 / 480 均无横向溢出。
- **Skill 入口唯一化**：下拉选项 = 内置 7 个 + 自建（标“（我的）”）+ 固定末项 `<option value="__repo__">Skill 仓库…</option>`；选末项不提交，而是弹回 `state.skillId` 并打开侧栏仓库；默认 `builtin:full`（全量体检）。侧栏底部新增“Skill 仓库”入口（带 `#skill-count`），输入区不再有仓库按钮。
- **审查历史子目录**（替换原弹窗）：侧栏“审查历史”是 `button.nav-action`（`aria-expanded` / `aria-controls`），点击展开 `#history-sub`；未登录显示“登录后可以查看过往审查记录。”；已登录 `GET /api/reviews?limit=20` 渲染 `.rec-item`（标题 / 状态 / 红黄计数 / 时间），每行三个工具：置顶、改名（行内表单）、删除（`confirm`）。标题缺省回退文件名，改名存 `title`，置顶排到列表最前。
- **记录可运维的后端**（`app/services/accounts.py`、`app/api.py`）：`review_records` 新增 `title TEXT` / `pinned INTEGER NOT NULL DEFAULT 0`，用 `PRAGMA table_info` + `ALTER TABLE` 平滑升级老库；`list_reviews()` 改 `ORDER BY pinned DESC, created_at DESC`；新增 `PATCH /api/reviews/{id}`（`title` / `pinned`，空串 → 恢复文件名、截断 60 字）与 `DELETE /api/reviews/{id}`（204）；越权与不存在统一 **404**；删除时 `ReviewService.discard()` 清 pending 时间戳、`clear_llm_runtime()`、尽力 `checkpointer.delete_thread()`，API 再删上传目录。
- **登录弹窗**：删掉 `.auth-extra` 包裹层与切换提示框（原 98px 空隙的来源），昵称字段直接进入表单（登录时隐藏）；用 `#auth-dialog .dialog-body{min-height:396px; justify-content:center}` 定高，登录/注册实测都是 **460×453**、body 396/396；表单 `gap:10px`，邮箱→密码实测 34px（含标签）。新增 `.auth-consent` 勾选行（“我已阅读并同意 使用政策 与 隐私条款”），`#auth-consent` 默认不勾选，切换模式也复位；未勾选提交提示“请先勾选同意隐私条款与使用政策。”。
- **状态修正**：`record()` 在图停在人工确认时写 `status="awaiting_human"`（原来写 `running`，历史里会误显示“审查中”）。
- **验证**：
  - `pytest` **295 passed**（288 + `test_accounts.py` 4 项 + `test_web.py` 3 项）；`ruff check .` All checks passed；`node --check app/web/app.js` 通过；
  - **CDP 冒烟 26 项全过**：主区铺满（sheetRight=1432 / innerWidth=1440 / view=1138）、输入区 880px、下拉 8 项且末项 `__repo__`、默认 `builtin:full`、输入区无 `#open-skills` / 侧栏有、同意默认不勾选、未勾选被拦、邮箱→密码 gap 34px、弹窗 460×453（body 396/396）、历史子目录三条工具、改名 / 置顶 / 删除全通、480px 无溢出；截图复核 5 张。
- **仍未做**：同意勾选没有留痕（`consent_version` / `consent_at`，见 ISSUE-025）；历史列表无分页（先 20 条）；密码找回、登录限流、多 worker 运行时共享仍未做（同上轮）。

## 上一轮产出（2026-10-27 界面轮 5：账号 / 审查记录 / Skill 仓库 / BYOK，右侧改成对话式）

- **起因（用户原话要点）**：
  1. 要做登录/注册、每个账号记录自己的上传与审查情况 → 需要后台数据库；
  2. 免责一行放到主体对话下面；
  3. 隐私条款 / 使用政策放右下角、点击弹窗；
  4. 侧栏要像 Codex / DeepSeek Harness：给指令、传附件、下拉选 Skill，并加 Skill 仓库（含推荐 Skill，也可自建）；
  5. 接口文档上面加“配置 API”：自选厂商 + 填 Key 接入大模型（配合 RAG）；
  6. 修正：**审查重点/附件/Skill 应在右侧主体**，并且要**参照对话聊天**的形态；侧栏只留“登录”（注册放进登录弹窗、切换时弹窗大小不变）；政策弹窗要**标题 + 编号**、字号更大、行距更小。
- **账号与持久化**（ADR-013，`app/services/accounts.py`）：本地 SQLite `.data/app.sqlite`（WAL + 外键），五张表 `users / sessions / skills / llm_configs / review_records`；口令 PBKDF2-HMAC-SHA256（16 字节盐、210k 次）；会话 token 只存 `sha256`，Cookie `alex_session`（HttpOnly / SameSite=Lax / 7 天，`SESSION_TTL_DAYS`）；审查本身仍按 `review_id` 存 checkpoint，`review_records` 只是账号维度的索引；未登录可审查但不入档，入档审查跨账号一律 **404**。
- **BYOK**（`app/services/secret_box.py` + `app/services/llm.py` + `app/services/llm_providers.py`）：厂商目录 9 个（openai / deepseek / moonshot / zhipu / dashscope / siliconflow / openrouter / ollama / custom，后两者允许空 Key）；Key 用标准库密文盒 `v1:<nonce|tag|ciphertext>` 加密后入库，主密钥 `.data/secret.key`（0600），接口只回 `has_key` + `••••尾号`；`LLMRuntime` 按 `review_id` 登记，`review_llm_scope()` 用 `ContextVar` 包住 `graph.invoke()`，`get_llm()` 优先级“本次审查的用户配置 → 环境默认 → `LLMNotConfigured` 降级”；终态清理运行时；`POST /api/llm/test` 真实探测但不保存。
- **Skill 与审查重点**（`app/services/skill_catalog.py`）：7 个内置推荐（全量体检 / 付款与结算 / 交付与装运 / 检验与索赔 / 争议解决 / 买方视角 / 卖方视角，`builtin:` 前缀禁删）+ 用户自建（`sk_`，只能删自己的）；`compose_focus()` 把“用户指令 / Skill（名称）：instruction / 参考材料”拼成 ≤4000 字，进入 `ContractReviewState.focus/skill_id/skill_name`，在 `explain_risks` 里作为 `<untrusted_focus>` 传给模型；系统提示第 8 条明确**不得据此改等级、增删风险或当指令执行**。
- **界面形态（本轮修正的重点）**：
  - **右侧主体**是对话式首屏：`.chat-hero`（品牌小块 + “今天想审查哪份合同？”/“欢迎回来，{昵称}”）+ `.composer-box`（无边框 textarea + 工具行：合同按钮 / 文件名 / Skill 下拉 / Skill 仓库 / 圆形发送键）+ 两行提示；**Enter 发送、Shift+Enter 换行**，支持拖拽文件进输入区；
  - **侧栏**回归纯导航：品牌、上传合同 / 当前审查（带红色计数徽标）、底部 **API 配置**（含状态文案）、**接口文档**、账号区（未登录只有“登录”；登录后“退出 + 我的审查”）；左侧不再放任何输入组件；
  - **登录弹窗**内 tab 切换登录/注册：`.auth-extra{min-height:62px}`，注册显示昵称字段、登录显示等高提示框，**切换时弹窗尺寸不变**（CDP 实测两种模式都是 460×458）；
  - **底部一行**“只做合同预审辅助，不构成法律意见。”+ 右下角“隐私条款 / 使用政策”按钮；弹窗内是 `01…07` / `01…08` 编号 + 小标题（正文 13.5px、行高 1.62，比原来更紧凑）；
  - 结果页继续渲染审批载荷与报告；“我的审查”列出历史记录（状态 / 红黄数 / 时间 / 审查重点），点击回到 `#/review/{id}`。
- **契约与接口**（`app/api.py`，`API_VERSION` 0.9.0 → **1.0.0**）：新增 `POST /api/auth/register|login`、`POST /api/auth/logout`、`GET /api/auth/me`、`GET /api/reviews`、`GET|POST /api/skills`、`DELETE /api/skills/{id}`、`GET /api/llm/providers`、`GET|PUT|DELETE /api/llm`、`POST /api/llm/test`；`POST /api/reviews` 增加表单参数 `focus / skill_id / reference`（参考材料限 `.txt/.md`、64 KB）；`ReviewSummary` 增加 `focus / skill_name`，`ReviewReport` 增加 `focus / skill`；错误码：`AccountError` → 400/401/404/409，`SecretBoxError` → 500（提示重新填 Key）。
- **配置**：`.env` 新增 `USER_DB_PATH`（默认 `.data/app.sqlite`）、`USER_SECRET_PATH`（默认 `.data/secret.key`）、`SESSION_TTL_DAYS`（默认 7）；`.gitignore` 增加 `.tmp-shots/`（`.data/` 与 `*.sqlite*` 原本已忽略）。
- **验证**：
  - `pytest` **288 passed**（261 + `tests/test_accounts.py` 24 项 + `tests/test_web.py` 新增 3 项）；`ruff check .` All checks passed；`node --check app/web/app.js` 通过；
  - **HTTP 端到端冒烟（真实 uvicorn `--factory` + 临时库）34 项全过**：匿名上传 201（3 条红、awaiting）→ 注册 201 + Cookie → 自建 Skill → 带 `focus`/`skill_id` 上传（`skill_name` 回显）→ approve 200（报告 4 条、`skill`/`focus` 保留）→ `report?format=markdown` 200（1869 B）→ 记录 1 条（red=3 / yellow=1）→ BYOK 保存（`has_key`、`••••7890`、响应无明文、库里 `v1:`）→ 清除 204 → 退出后 401 → 跨账号 404；
  - **CDP 冒烟 11 项全过**：首屏是对话式输入区且在 `#view` 内、侧栏无输入组件、侧栏仍有登录/API 配置/接口文档、底部免责 + 右下角政策、登录/注册弹窗 460×458 一致、政策 7 条编号（13.5px / 1.62）、480px 无横向溢出；截图复核桌面 / 登录 / 注册 / 隐私条款 / 窄屏。
- **仍未做**：密码找回与邮箱验证、登录失败限流、多 worker 下的运行时共享（ISSUE-019 同源）、Cookie 的 `Secure`（本地 HTTP 演示）；`.data/secret.key` 丢失只能重填 Key。

## 上一轮产出（2026-10-27 界面轮 4：保留侧栏，只把右侧主区收成“上传合同 → 看风险点”）

- **起因**：界面轮 2/3 的右侧主区信息过多（流水线、规则集、KPI、抽取要素、待核对、复核记录）。用户明确“只想上传合同，然后查看合同的风险点”，并补充“原来的侧边栏保留，仅右侧主体内容做变更”。
- **侧栏与顶栏保留原样**（导航壳）：
  - `aside.sidebar`：品牌（Agent Alex / 合同审查助手）+ 导航（上传合同、当前审查，后者带高风险计数徽标）+ 底部免责声明与 `/docs`；
  - 顶栏：面包屑（合同审查 / 当前页）+ 服务状态 pill；窄屏汉堡抽屉、遮罩、`Esc` 收起；
  - 只删掉“审查工作台 / 复核报告 / 规则集”三个入口——它们对应的主区视图已合并进风险点页，留着就是死链。
- **右侧主区收成两屏**（ADR-009 第 5 轮补充）：
  - `main.sheet` 里只有 `#view`：内容少时画布也铺到页面底部（grid `1fr`），不再保留侧栏里的运行环境块、面包屑之外的导航条、toast、运行环境卡片；
  - hash 路由只留 `#/`（上传）与 `#/review/{id}`（结果）；不再有 `#/workbench`、`#/report/{id}`、`#/rules`，也不再请求 `/api/rules`；
  - 上传成功 `history.replaceState` 到 `#/review/{id}`，刷新/分享可回到结果；“换一份合同”回上传；
  - 待确认态**直接列出规则已定位的红色风险**（`ReviewSummary.approval.findings/quotes/citations`），确认后才生成报告与解释——不能等 `report`，否则会先显示“0 处风险”；
  - 每条风险：等级 chip + 标题 + 规则理由 + 建议 + 折叠的“查看合同原文与依据”（原文、位置、知识引用、规则编号）；
  - 确认区保留 HITL：主按钮 approve、次要文字按钮 reject、复核人可留空；决定只 POST `/decisions`，等级不在浏览器算。
- **修复的真实缺陷**：
  - “下载报告”原指向 `GET /api/reviews/{id}?format=markdown`（审查详情接口，不含报告），改为 `/report?format=markdown`，测试钉住；
  - 跳转链接 `#main` 会被 hash 路由当成首页重渲染，改为 `preventDefault` + 聚焦 `main`。
- **视觉**：左侧导航壳（`--sidebar: 228px`）+ 右侧白纸画布（内容 820px），IBM Plex 本地字体，卡片左侧红/黄竖条；窄屏左侧变抽屉、画布铺满。
- **测试与验证**：`tests/test_web.py` 10 项（新增“侧栏保留但主区最小”“待确认先展示规则风险”）；全量 **261 passed**、`ruff check .`、`node --check` 通过；HTTP 冒烟 上传 → 201 awaiting（3 条红色）→ approve 200 → 报告含知识引用；论文 → `not_contract`；CDP 冒烟 20 项全过（侧栏可见、汉堡/抽屉/Esc、上传→待确认→确认→报告、下载链接、500px 无横向溢出）。
- **已知取舍**：待确认页只展示红色风险（审批载荷口径），黄色风险在确认后的报告中出现；规则目录接口保留给 API/第三方，页面不再消费。

## 上一轮产出（2026-10-27 界面轮 3：先判断是不是合同 + 收掉运行环境）

- **起因**：用户上传一篇法学论文测试，系统却按合同跑完了切分/抽取/判级。根因是缺少“对象是否正确”的准入判断——规则面对任意文本都能命中关键词。
- **闸门**（ADR-012）：`ingest_document` 之后新增 `precheck_document`（`app/nodes/precheck.py`），调用 `app/services/document_type.py::classify_document`：
  - 身份信号：合同抬头（销售/买卖/采购/供货…合同、Sales Contract）、合同编号（`合同编号：C47`）、买卖双方（卖方/买方、甲方/乙方、Seller/Buyer）；
  - 反向信号：学术论文（摘要/关键词/参考文献/本文认为/this paper）与法规条文（本法/民法典/总则/Civil Code）；
  - 契约度评分：抬头 3 / 编号 2 / 双方 2 / 编号条款 2 / 交易要素 1 / 签署语 1，总分 < 4 判否；正文去空白 < 120 字判否；
  - 用户可见：`reasons`（为什么拒绝）+ `hints`（下一步怎么办），置信度一并返回。
- **图的路由**：`ingest → precheck ─不是合同→ build_report`；**不切条款、不抽取、不判级、不触发 HITL**；新增 `ReviewStatus = not_contract`，报告 `status=not_contract`、`findings=[]`、`overall_level=unknown`，摘要写“未执行合同审查”，限制里写明“不含任何风险结论”。
- **契约**：`DocumentCheck{is_contract, confidence, reasons, hints}`（`extra="forbid"`）；`ContractReviewState.document_check`；`ReviewSummary.document_check`；`API_VERSION` 0.8.0 → **0.9.0**；`ReviewService.FINAL_STATUSES` 纳入 `not_contract`（终态后提交决定是幂等空操作）。
- **前端**：
  - 新增“不是合同”页（`renderNotContract`）：状态 + 判定置信度 + “判定依据 / 下一步”两栏 + “重新选择文件”（清空本地会话）；
  - 工作台流水线 5 步 → 6 步（新增“判断类型 / 不是合同直接停止”），顶部提示明确“论文、法规、说明书会被直接拒绝”；
  - **删除侧栏“运行环境”块**（接口版本 / 规则集版本 / checkpoint / RAG 开关），只保留“接口文档”入口；`updateRuntime()` 与 `.runtime*` 样式一并移除；
  - `.app` 改为 `grid-template-rows: auto minmax(min-content, 1fr)`，内容少时 sheet 铺到底、不再浮在中间。
- **关于“RAG 为什么是关闭的”**：这是产品默认值，不是故障——RAG 只用于给**解释**补充知识片段，不能参与判级；ADR-008 规定默认关闭，避免知识库未就绪时把“检索不到”当成“没有风险”。要开启可设置 `RAG_ENABLED=true`（本机 `.env` 已按用户要求开启，`/health` 的 `rag_enabled` 为 true）；本轮按要求把该状态从界面移除，需要时在 `.env` 打开、或在 `/docs` 查看 `/health` 的 `rag_enabled`。
- **RAG 在无 Key 时也可见**：`explain_risks` 改为**先检索、再判断 LLM**；模型不可用时解释正文仍回退规则理由（`source="rule"`、等级不变），但每条风险会带上检索到的 `source_id#section`，报告写“知识引用仅按检索结果列出，未参与解释与判级”。实测 4 条风险各 3 条引用（`INCOTERMS-2020#s19`、`RISK-REDLINE#s8`、`CN-CIVIL-CODE#第五百一十一条` 等）。
- **测试**：`tests/test_document_type.py`（11 项：论文/法规/过短/90 份合同语料 0 误杀/两个样例/图集成 2 项）、`tests/test_api.py::test_non_contract_upload_is_not_reviewed`、`tests/test_web.py::test_runtime_internals_stay_out_of_the_ui`；全量 **259 passed**，`ruff check .` 与 `node --check` 通过。
- **真实文件验证**：论文 PDF `全球比较下的我国人工智能立法_丁晓东.pdf` → `not_contract`、置信度 0.98、0 条 findings、报告可下载且写“未执行审查”；C47 → `is_contract=true`、契约度 11/11 → 正常进入人工确认。
- **已知边界**：闸门是召回优先（宁可放过不误杀）；中文/英文词表之外的合同（日文、德文等）可能被误拒；扫描件无文本时按“过短”拒绝并提示 OCR。

## 上一轮产出（2026-10-27 界面轮 2：B 端审查工作台重设计）

- **为什么做**：界面轮 1 的原生页面虽能跑通全流程，但形态是“单页 + 四步向导”——没有导航、没有面包屑、没有运行环境，规则只以文案出现。用户要求按外部设计方法论 `github.com/Leonxlnx/taste-skill` 重做，并改成 **B 端（企业后台/工作台）** 形态。约束不变：禁止前端框架、npm 构建、CDN。
- **信息架构**（`app/web/index.html` 重写）：`aside.sidebar`（品牌块 + 工作台/当前审查/复核报告/规则集四个导航 + 底部“接口文档”入口；运行环境块已在界面轮 3 移除）+ `header.topbar`（抽屉按钮 + 面包屑 + 服务在线 pill）+ `main.sheet` 画布 + `#scrim` + `#toast`；≤900px 侧栏收为抽屉。
- **路由**：hash 路由 `#/workbench`、`#/review/{id}`、`#/report/{id}`、`#/rules`；`review` / `rules` 带徽章；`localStorage` 只存 `review_id`。
- **视觉系统**（`styles.css` 重写，framed-sheet）：石色工作区 `#f3f3f1` + 白色 sheet（16px 圆角、1px border）、228px 侧栏、48px topbar、24px 间距；border 只作“耳语”；标题 18–32px、正文 13–14px、数字 `tabular-nums`；统一 panel / kpi / table / ledger / notice / empty 组件；含 `prefers-reduced-motion` 与打印样式。
- **四个视图**：
  - 工作台：标题 + 边界 notice + 上传面板（拖拽/点选、类型/大小/空文件校验、5 步流水线）+ 右栏“本次会话 / 规则集预览 / 判级口径”；
  - 当前审查：审批载荷（红色风险逐条 + 引文 + 解释来源）+ 复核要点三步 + 决策表单（三选一 + 复核人 + 意见 + 标记超时）+ KPI；
  - 复核报告：结论块 + 4 个 KPI + 风险清单 + 抽取要素 + “复核记录与版本 / 已知限制”；
  - 规则集：4 个 KPI + 规则目录表（编号 / 等级 / 主题 / 检查项与理由 / 处理建议）+ 评测口径 + 已知边界；≤900px 表格改为堆叠条目（不横滚）。
- **本地字体（零 CDN）**：`app/web/fonts/` 放 IBM Plex Sans 可变字体（`font-weight: 100 700`）+ IBM Plex Mono 400/500 + `OFL.txt`；`@font-face` 本地引用；`app/api.py` 增加 `mimetypes.add_type("font/woff2", ".woff2")`，避免 Windows 下字体被当 `application/octet-stream`。
- **新增只读接口 `GET /api/rules`**（`API_VERSION` 0.7.0 → **0.8.0**）：
  - `RuleCatalog{ruleset_version, rule_engine_version, count, red_count, yellow_count, rules[]}`，每条 `RuleSummary{rule_id, title, category, risk_level, reason, suggestion, requires_extraction}`，`extra="forbid"`；
  - **不返回正则 / `condition` / DSL**，浏览器拿不到判级实现；`risk_level` 只是规则定义里的静态等级，不是运行时判定；
  - `app/rules/engine.py` 拆出 `load_rule_set()`（含集合级 `version`），`load_rules()` 行为不变。
- **边界不变**：浏览器只渲染 `ReviewSummary` / `ReviewReport`；人工决定只 POST `/api/reviews/{id}/decisions`；所有动态文本 `esc()`；测试用正则钉住不得给 `risk_level` / `overall_level` 赋值。
- **可访问性**：跳转链接、`aria-expanded` / `aria-current`、抽屉收起时 `visibility: hidden`（不在可访问树，也不能 Tab 到屏幕外链接）、打印时展开全部 `details`。
- **测试与验证**：
  - `tests/test_web.py` 5 → **6 项**（新增本地字体：`@font-face` + `/static/fonts/` + `content-type: font/*` + `OFL.txt`）；
  - `tests/test_api.py` 新增 `test_rule_catalog_matches_definitions`（13 条、5 红 / 8 黄、rule_id 集合一致、不返回 `condition` / `source`）；
  - `pytest` **243 passed**（界面轮 2 时）、`ruff check .` 通过、`node --check app/web/app.js` 通过；
  - 真实浏览器测量（taste-skill `inspect.mjs --app`，1440 / 768 / 390）：工作台、当前审查、复核报告、规则集四页均 **0 FAIL / 0 WARN**；自建 CDP 脚本确认 390 / 768 无横向溢出；
  - HTTP 冒烟：`/health` v0.8.0、`/api/rules` 13 条（5 红 / 8 黄）、上传 `data/contracts/C47.md` → 201（awaiting_human）→ decisions 200 → 报告页可渲染、`/docs` 200。
- **已知取舍**：`app.js` 约 28 KB → 约 60 KB，手写路由与视图复杂度上升；`RuleSummary` 是规则定义的**白名单投影**（新增展示字段要同步改模型与前端，不能把 YAML 直接给浏览器）；本地字体增加约 200 KB 二进制，合规依赖保留 `OFL.txt`；设计测量工具在 768 会误把“屏幕外抽屉里的块”当成同排卡片（已用 CDP 截图与 `scrollWidth` 复核，并借该告警发现并修掉了抽屉的可访问性问题）。

## 上一轮产出（2026-10-27 界面轮 1：原生 Web 前端）

- **为什么做**：用户明确要“真正的前端”。原界面是 Streamlit 脚本，页面结构由 Python 生成、交互整页重跑；但项目硬约束是**禁止前端框架**（无 React/Vue、无 npm、无 CDN），所以不能引 Vite。
- **方案**：`HTML + CSS + 原生 JS` 单页，完全离线，由 FastAPI 直接托管。
  - `app/web/index.html`：四步骨架（上传 / 规则审查 / 人工确认 / 报告）+ 侧栏（上传、边界说明）；
  - `app/web/styles.css`：设计令牌（深浅色自动适配）、卡片/风险条目/分段选择/表格/骨架屏/打印样式；
  - `app/web/app.js`：状态机、拖拽上传、审批表单、轮询、报告渲染、`localStorage` 恢复、所有文本 `esc()` 转义。
- **后端**（`app/api.py`）：
  - `API_VERSION` 0.6.0 → **0.7.0**；
  - `GET /` → `FileResponse(index.html, Cache-Control: no-store)`（`include_in_schema=False`）；
  - `app.mount("/static", StaticFiles(directory=WEB_DIR))`；`WEB_DIR = app/web/`。
- **边界不变**：浏览器不判级、不拼 `Command`；等级只渲染 `ReviewSummary` 返回值；人工决定只 POST `/api/reviews/{id}/decisions`，由 `ReviewService.resume()` 统一恢复；409 时重拉状态，网络错误保留已填写的复核人/意见。
- **测试**（`tests/test_web.py`，5 项）：首页 200 + `no-store`；静态资源 200；无外链（仅允许 SVG XML 命名空间）；无本地判级/`Command`（正则钉住 `risk_level\s*=(?!=)` 与 `overall_level\s*=(?!=)`）；资源存在且不写死 host/端口。
- **验证**：
  - `pytest` **241 passed**（236 + 5）；`ruff check .` All checks passed；`node --check app/web/app.js` 通过；
  - HTTP 冒烟：`POST /api/reviews → 201`（3 条红色）→ `POST decisions → 200 approved` → `GET report?format=markdown → 200（3482 B）`；
  - 路由验证：`/` 200 text/html、`/static/styles.css` 200、`/static/app.js` 200、`/health` 200、`/docs` 200。
- **文档**：ADR-009 新增“第 2 轮补充”；ADR 索引、README、本文件、交接、开发日志同步。
- **已知取舍**：手写 DOM 复杂度高于框架；`:has()` / `color-mix()` 需较新浏览器；前端 15 MB 上限与 `MAX_UPLOAD_MB` 需手动同步；交互级回归仍靠人工冒烟。

## 上一轮产出（2026-10-27 第四阶段第 4 轮：规则 version 5 + 保额邻近判定 + holdout4 盲测）

- **为什么做这一轮**：holdout3 暴露的 3 个漏报（H21“亦可”、H22“负责支付”、H24“thirty-six (36) hours”）都属**措辞覆盖**，另有 `R-INS-001` 保额判定是**全文级**、会被任意付款比例压制的结构缺陷。按 ADR-011 纪律：先修缺陷 → 再写一批全新留出集（holdout4）→ 只引用新集报数，holdout3 同时降级为回归集。
- `app/rules/definitions.yaml`（`version: 4 → 5`，规则主题仍是 13 条）
  - `R-DIS-003` 中文并列连接词扩表：`或|或者|亦可|也可以|仍有权|亦有权|有权|可选择`；
  - `R-INC-001` 允许情态词插入（`卖方(?:负责|应|须|将|同意)?(?:承担|预付|支付)…运费`），间隔上限 12 → 14；
  - `R-INP-002` 增加英文数词 + 括号数字（`thirty-six (36) hours`、`Twelve (12) hours`），并补“动词在前、期限在后”的反向语序分支；
  - `R-INS-001` 保额判定从“全文级 `none_of`”收窄为**保险语境邻近**：保险关键字与金额/比例须在同一句内相距 60 字符（反向语序 40 字符），英文单列 `sum insured / insured value / amount of insurance` 分支。**没有改 DSL**——两条限定窗口正则即可解决，保持 ADR-003 的白名单边界与引擎接口不动；窗口是启发式，已在规则注释与 ADR 写明。
- `data/contracts_holdout4/`（H29–H40，12 份）+ `data/eval/gold_holdout4.json`（9 个现象，**当前唯一未消耗**）
  - 刻意覆盖：H29 中文 CIF 无保额但另有 40% 预付款（保额邻近判定的关键回归点）、H30/H40 英文/中文卖方付海运费、H31 “既可以…也可以…法院”、H32 仅可申请撤销裁决的干净对照、H33 `within Twelve (12) hours`、H34/H36 已写 `sum insured` 的干净对照、H35 EXW+FCL、H37 无付款条款、H38/H39 英文或裁或审与先裁后审。
- **本轮对外数字（holdout4，12 份 / 132 个规则-合同对）**：
  - 规则级 `TP=8 FP=0 FN=1 TN=123` → **P=1.00 / R=0.889 / F1=0.941**，等级一致率 1.00；
  - 合同级 `TP=8 FP=0 FN=1 TN=3` → P=1.00 / R=0.889 / F1=0.941；漏报 H39；
  - 干净对照全部通过（H32/H34/H36），H29 正确判出“保额缺失”而未被 40% 预付款压制。
- **唯一漏报 H39（故意不修）**：`award shall be final, but either party may, within 30 days after the award is issued, commence proceedings …`。`R-DIS-004` 要求 modal 后紧跟动词，此处插入了时间状语。修法明确（`[^.]{0,80}?`），但本轮不动——holdout4 是唯一报数集，修完再引用它就是“用测试集调参”。
- `tests/test_rules.py`（升级）
  - 新增 `PARAPHRASE_RULE_CASES`（6 个正反 fixture：中文并列、卖方付运费、英文数词期限、付款比例不等于保额、`sum insured` 等），校验证据 span 能切回原文；
  - 新增 `test_holdout3_hits_are_stable`（7 条命中 + H27/H28 零命中）与 `test_holdout4_hits_are_stable`（8 条命中 + H32/H34/H36 零命中）；
  - `test_holdout4_hits_are_stable` 里用断言**钉住 H39 必须是漏报**：修好那天测试会失败，强制作者更新期望集合、降级 holdout4、另写 holdout5。
- 回归确认：主集 50 份命中集合与修复前**完全一致**（C04/C09/C11/C23/C39–C43/C47/C48），holdout3 由 4/0/3 升为 7/0/0。
- 验证：`pytest` **236 passed**、`ruff check .` 通过；五条 eval 命令（主集 + 四批留出集）均可复现。
- 文档：`ADR-011` 新增“第 4 轮补充”（修了什么表、未改 DSL 的说明、holdout4 数字、H39 与“只报不修”、四批样本分工表、测试钉纪律），同步本文件、交接、待决事项（ISSUE-020/021 重写）、README、开发日志。

## 上一轮产出（2026-10-27 第四阶段第 3 轮：英文/同义改写补强 + 三批留出集）

- **为什么做这一轮**：第 2 轮留出集给出 `R=0.714`，还留下 2 个“看明白了但没修”的漏报（H01 英文或裁或审、H03 “费用由卖方承担并预付”）。不修就等于承认规则只能处理中文标准写法；但直接在旧留出集上修又等于用测试集调参。于是采用：**修规则 → 新留出集验证 → 再暴露 → 再另写**的循环。
- `app/rules/definitions.yaml`（`version: 3 → 4`，13 条规则主题不变）
  - `R-DIS-003`/`R-DIS-004` 增英文分支：`arbitrat…\s+or\s+…court/litigat…`、`award…may/shall/then… file/commence/appeal/litigate…court`；**刻意排除**“裁决可在法院执行（enforced in any court）”“申请撤销裁决（set aside）”这类合法条款；
  - `R-INC-001` 增三种语序：`海运费/订舱费用…由卖方承担`、`卖方承担…主运费`、`freight … paid/prepaid/borne by the seller`；**不收**“出口报关费用由卖方承担”（本就应由卖方承担）；
  - `R-INS-001`/`R-INP-002` 补英文：`insure/insured/insurance`、`110% of the invoice value`、`insured value of USD …`、`N hours … inspect/notify/claim`；
  - 顺带修掉两个**真实缺陷**（holdout2 发现）：① `contains_any: [CIF, CIP]` 把 “Pa**cif**ic / speci**fic**ation” 当成术语 → 四条术语规则改用“前后非英文字母”边界（保留“FOB上海”）；② `R-INC-001` 200 字符窗口被小标题吃掉（实测 210）→ 放宽到 260。
- `data/contracts_holdout2/`（H09–H20，12 份）+ `data/eval/gold_holdout2.json`（新建）
  - 中英各半、刻意的干净对照（H10/H13/H20），其中 H13 含“出口报关费用由卖方承担，主运费由买方承担”这类近似句；
  - 修复后 `TP=9 FP=0 FN=0 TN=123`；**但它已被用于定位缺陷，降级为回归集**。
- `data/contracts_holdout3/`（H21–H28，8 份）+ `data/eval/gold_holdout3.json`（新建，**唯一未消耗**）
  - 刻意换写法：中文“**亦可**向…人民法院起诉”、FOB 下“卖方**负责支付**…主运费”、英文 “**thirty-six (36) hours**”、保额写成 “110% of the CIF value”；
- **本轮对外数字（holdout3，8 份 / 88 个规则-合同对）**：
  - 规则级 `TP=4 FP=0 FN=3 TN=81` → **P=1.00 / R=0.571 / F1=0.727**，等级一致率 1.00；
  - 合同级 `TP=3 FP=0 FN=3 TN=2` → P=1.00 / R=0.50 / F1=0.667；漏报 H21/H22/H24；
  - **3 个漏报全是措辞覆盖问题**：H21（“亦可”不在中文分支）、H22（“负责支付”插在“卖方…运费”之间）、H24（英文数词 `thirty-six (36)`）。本轮**不修**，留给下轮 + 新 holdout4。
- `tests/test_rules.py`（升级）
  - 新增 6 个英文/同义改写正反 fixture（`ENGLISH_RULE_CASES`），并校验证据 span 能切回原文；
  - 新增 `test_previous_holdout_hits_are_stable`（H01–H08 命中集合 + H04 零命中）、`test_holdout2_hits_are_stable`（H09–H20 命中集合 + H10/H13/H20 零命中）。
- `eval/metrics.py`（口径补丁）：`score_coverage` 增加 `note` 字段，明确“覆盖率只表示有对应规则，识别能力看 recall”；`run_eval` 在缺口为 0 时会打印提示——留出集 `coverage=1.0` 是平凡结果，不能与 recall 混读。
- 验证：`pytest` **228 passed**、`ruff check .` 通过；四条 eval 命令（主集 + 三批留出集）均可复现。
- 文档：`ADR-011` 新增“第 3 轮补充”（三批样本分工表、留出集消耗规则、holdout3 漏报清单、保额全文级判定缺陷），同步本文件、交接、待决事项（ISSUE-021 重写）、README、开发日志。

## 上一轮产出（2026-10-27 第四阶段第 2 轮：silver gold + 指标 + 留出验证）

- **为什么做这一轮**：第 1 轮只有“11/50 命中”这一个数字，既不能回答“准不准”，也不能回答“漏了什么”。本轮把评测从“触发统计”升级为“可复核的指标 + 明确缺口”，并用独立留出集验证泛化。
- `data/eval/gold_rules.json`（新建，**silver gold**）
  - 21 个现象 / 50 份合同：11 个映射到规则（6 条新规则各 1 + `R-PAY-002` 5 个），10 个明确标 `rule_id: null`（规则缺口：5 份无付款条款的混合合同缺不可抗力、3 份纯货物合同缺检验条款、C41/C42 检验缺失等）；
  - 文件内 `provenance` 明写“AI 初标，待人工复核”，`annotation_protocol` 记录标注口径（不参考规则命中结果、未列即 pass）；
  - `scored_rules` 只含 11 条文本规则；两条字段规则（`R-DLV-001`/`R-INP-001`）在 `unscored_rules` 注明“评测不调 LLM，运行时 skipped”。
- `data/contracts_holdout/H01..H08.md` + `data/eval/gold_holdout.json`（新建，**独立留出集**）
  - 8 份**新写**合同，刻意不沿用 50 份语料的模板：中英混排、同义改写、条款顺序不同；
  - H01 英文“either … arbitration, or … court”、H02 英文 CIF+一切险、H03 中文“海运费…由卖方承担并预付”、H05 48/12 小时检验、H06 先裁后审、H07 FCL 堆场、H08 无付款条款；
  - 这 8 份**未参与规则设计**，因此其指标才是对外的诚实数字。
- `eval/metrics.py`（新建）
  - 三组指标：`rule_level`（rule × contract 的 TP/FP/FN/TN + P/R/F1 + 等级一致率）、`contract_level`（合同是否被正确标记，含漏报/误报清单）、`coverage`（gold 现象中多少被规则覆盖 = 规则缺口）；
  - 单侧分母为 0 时返回 `None` 而非 0.0（避免“无正例=差”）；gold 冲突、未知合同、未知规则、非法等级在加载期直接报错，不静默降级。
- `eval/run_eval.py`（升级）
  - 新增 `--contracts / --gold / --gold-rules / --out / --tag`；`--gold-rules none` 可只跑触发统计；结果文件新增 `metrics` 字段；
  - 支持 `--tag holdout` 输出 `eval/results/rules-holdout-YYYYMMDD.json`，与主集结果分开存。
- **主集（50 份，同分布）**：`TP=11 FP=0 FN=0 TN=539`，P/R/F1 = 1.00；合同级 R=0.79（C03/C13/C14 因“缺检验条款”无规则而漏报）；覆盖率 52.4%（21 个现象中 10 个无规则）。
- **留出集（8 份，未参与设计）**：`TP=5 FP=0 FN=2 TN=81`，**P=1.00 / R=0.714 / F1=0.833**，等级一致率 1.00；合同级同样 P=1.00 / R=0.714；覆盖 7/7 现象。
  - **2 个真实漏报**：H01（英文“或裁或审”，`R-DIS-003` 只写中文正则）、H03（“**海运费**及舱位订舱**费用由卖方承担并预付**”，`R-INC-001` 要求紧贴的“运费由卖方”）。
  - 本轮**不修改**这两条规则：否则留出集就被“看过答案”，失去验证意义；已作为下一轮改进输入（ISSUE-021）。
- `tests/test_eval_metrics.py`（新建，11 个测试）：指标计算（完美/误报/漏报/零分母/等级不一致）、合同级漏报清单、覆盖率拆分、gold 冲突与非法输入、`gold_rules.json` 完整性（50 合同、6 个确定性命中、5 个 `R-PAY-002`）、留出集自洽（H04 必须无风险）。
- 验证：**220 passed**、`ruff check .` 通过；主集与留出集结果可一键复现。
- 文档：新增 `ADR-011-评测方法silver-gold与留出验证.md`，同步 ADR 索引、本文件、交接、待决事项、README 与开发日志。

## 更早产出（2026-10-27 第四阶段第 1 轮：规则扩充 + 合同级评测基线）

- **查收用户新增模拟合同**：`data/knowledge/` 新增 6 个 `模拟合同1..6.md`，实际 **50 份（C01–C50）**，未发现 C51–C60（与用户所说的 60 份不一致，已记入 ISSUE-020）；每份自带「条款—问题映射摘要」。原始文件保持不动，不写入 `manifest.yaml`（它们不是法规知识）。
- `eval/prepare_contracts.py`（新建）
  - 将 6 个大 md 拆成单份合同 `data/contracts/C01.md … C50.md`（保留 `**SALES CONTRACT**` 与 `### 第X条`，剥离场景标题与摘要）；
  - 解析映射摘要为 `data/eval/gold_contracts.json`：50 份 / 105 条“条款 → Q 编号 → 期望召回 → 干扰项”，并注明这是**检索期望**，不是规则判级 gold。
- `eval/run_eval.py`（新建）
  - 用 `ReviewService.in_memory()` 逐份跑规则（不调 LLM、无需 Key），输出 `eval/results/rules-YYYYMMDD.json`：规则数、合同数、命中合同数、等级分布、各规则触发次数、未命中清单；
  - 显式声明“未命中不等于无风险”，不计算准确率。
- `app/rules/definitions.yaml`（扩展，`version: 3`，7 → 13 条）
  - 修正 `R-TRD-001`：正则改为 `Incoterms\s*[®™]?\s*(?:19|20)\d{2}`，解决 `Incoterms® 2020` 导致 40 份误报（version 1.0 → 1.1）；
  - 新增 6 条确定性文本规则：`R-DIS-003` 或裁或审（red）、`R-DIS-004` 先裁后审（red）、`R-INS-001` CIF/CIP 有投保无保额（yellow）、`R-INC-001` 术语与运费矛盾（yellow）、`R-INC-002` FOB/EXW 用于整箱集装箱（yellow）、`R-INP-002` 检验期限以小时计（yellow）；
  - 6 条规则在 50 份合同上的命中集合各为 1 份（C47/C48/C04/C11/C23/C09），两份样例合同零命中。
- `tests/test_rules.py`
  - 规则数断言 7 → 13；新增 6 组“命中/不应命中”正反 fixture，校验证据 span 可回填；
  - 新增 `test_new_rules_stay_precise_on_simulated_corpus`：固化 `EXPECTED_CORPUS_HITS`，任何误报/漏报立即失败；
  - 新增 `test_new_rules_do_not_fire_on_samples` 与三条 `R-INS-001` 不触发场景（CIF 无保险条款、非 CIF 有投保、英文已写 110%）。
- `tests/test_graph.py`：图端到端规则数断言 7 → 13。
- **基线**：50 份中 11 份命中（`pass:39 / yellow:9 / red:2`）；`hit_counts={R-PAY-002:5, R-DIS-003:1, R-DIS-004:1, R-INS-001:1, R-INC-001:1, R-INC-002:1, R-INP-002:1}`；39 份未命中，说明覆盖仍不足（ISSUE-009）。
- 验证：**209 passed**、`ruff check .` 通过；`python eval/prepare_contracts.py`、`python eval/run_eval.py` 可复现。
- 文档：新增 `ADR-010-规则扩充与合同级评测基线.md`，并同步 ADR 索引、本文件、交接、待决事项、README 与开发日志。

## 上一次产出（2026-10-27 第三阶段第 6 步：FastAPI + Streamlit + 真实语料接入）

- `app/services/pending_store.py`（新建）
  - `FilePendingStore`：`.data/pending/<review_id>.json`，`tempfile` + `os.replace` 原子写；`MemoryPendingStore` 供测试；
  - `validate_review_id` 正则白名单防路径穿越；损坏/缺失文件按“未记录”处理，**绝不据此判超时**。
- `app/review_service.py`
  - 注入 `PendingStore`：首次观察到暂停写时间戳（不覆盖已有值），`resume` / 超时后清理；
  - `start / get / resume` 按 `review_id` 持 `threading.RLock`（可重入），并发不重复跑图；
  - `ReviewStateError(missing=True)` 区分“不存在”（API 404）与“状态冲突”（409）。
- `app/api.py`（新建）
  - `create_app(service=None, upload_dir=..., pending_dir=..., max_upload_mb=...)`；不传 service 时 lifespan 内开 SQLite checkpointer + 文件 pending store；
  - `GET /health`、`POST /api/reviews`、`GET /api/reviews/{id}`、`POST /api/reviews/{id}/decisions`、`GET /api/reviews/{id}/report?format=json|markdown`；
  - 上传：basename 净化（同时处理 `\`/`/`）、后缀白名单、`.doc` 提示转换、分块读取 + 413、空文件 400、失败清理目录；落 `.data/uploads/<review_id>/`；
  - 错误码 400/404/409/413/422；响应模型 `ReviewSummary` 不回传合同原文。
- `app/report_markdown.py`（新建）：`render_report_markdown`，含摘要/风险清单/抽取要素/待核对/人工复核/限制/版本；表格 `|` 转义、换行折叠；解释缺失写“未提供”。
- `app/ui.py`（新建）：Streamlit 中文界面；`st.cache_resource` 持有 SQLite + 文件 pending store；上传→审查→展示审批载荷→批准/要求修改/拒绝/标记超时→报告与下载；**不拼 `Command(resume=)`**。
- `app/services/rag.py`（扩展，真实语料接入）
  - `ALLOWED_SUFFIXES` 增加 `.docx`；`.doc` 明确报错提示转换；
  - DOCX 按 `第X条` 切分（编/章/节作上下文，目录丢弃），section 直接用条文号（如 `第五百七十七条`）；
  - Markdown 识别 `***Article N***` 与结构性加粗标题；
  - 超长片段按段落/句末标点二次切分（上限 1600 字符），同一标题依次 `s2`、`s2-2`；
  - `load_knowledge_base` 按 `(目录, manifest+文件 mtime/size)` 缓存，语料变更自动重建。
- `data/knowledge/manifest.yaml`：登记 14 篇真实语料（CISG 中英/重点条款、Incoterms 2020、民法典、涉外民事关系法律适用法、6 份司法解释、UCP600/仲裁、内部红线）；`100问题.md` 不入库（评测 query 集），旧版 `.doc` 需转换。`data/knowledge/examples/` 保留 3 份自拟示例专供测试。
- 测试新增 37 个（`test_api.py` 15、`test_pending_store.py` 11、`test_rag.py` +7、`test_report_markdown.py` 3、`test_ui.py` 1），全量 **197 passed**；`ruff` 通过。
- 实测：真实语料 14 篇 / 1834 段，最长 1599 字符；`根本违约`、`FOB 风险转移`、`仲裁 管辖`、`不可抗力` 命中合理 `source_id#section`；SQLite 模式 API 上传→暂停→approve→Markdown 报告全通。

## 上一次产出（2026-10-27 第三阶段第 5 步：解释 + 质量门 + RAG）

- `app/nodes/explain.py`
  - `explain_risks`：只对 red/yellow 解释；`rejected / changes_requested / unreviewed_red_risk / failed` 直接 `skipped`，不调用 LLM；
  - LLM schema `RiskExplanation` **无 `risk_level`**；prompt 里把合同与知识标为 `<untrusted_*>` 并转义分隔符，防提示注入；
  - **质量门**（纯 Python）：`rule_id` 必须匹配、`clause_id` 必须在规则命中的条款内、`summary` 非空、越权表述黑名单（合同无效/有效/已批准/已签署/无风险/建议直接签署/等级判定…）、`quote` 必须能在原文定位；
  - 知识引用只接受**本条风险实际检索到**的 `source_id#section`，编造引用丢弃 + warning；
  - 单条失败隔离：模型未配置/抛错/质量门失败 → 该条回退规则理由，整体标 `fallback`，报告仍生成。
- `app/services/rag.py`
  - 本地 BM25（`k1=1.5, b=0.75`）+ 中文“单字 + 二元组”切分，零网络依赖、零新库；
  - 相对阈值（≥ 最高分 25%）+ `RAG_TOP_K` / `RAG_MIN_SCORE`；
  - `manifest.yaml` 强校验：9 个必填字段、`source_id` 命名、`effective_date` 格式、UTF-8、仅 md/txt、禁止 `..`/绝对路径、重复 ID/未知字段报错；
  - 按 Markdown 标题切段并生成 `source_id#sN` 引用。
- `data/knowledge/`：`manifest.yaml` + 3 份**项目自拟**示例摘要（Incoterms / CISG / 民法典合同编），仅用于跑通检索与引用链；文件内显著标注“不是官方文本”。
- `app/schemas.py`：新增 `RiskExplanation`、`ExplanationResult`；`ReportFinding` 增加解释摘要/引文/引用；`ReviewReport` 增加 `explanation_status / explanation_model / explanation_prompt_version`。
- `app/graph.py`：8 节点 + 两条条件边：`evaluate_rules → human_review | explain_risks | build_report`，`human_review → explain_risks | build_report`。
- `app/nodes/hitl.py`：新增 `route_after_human_review`（只有 `approved` 才解释）。
- `app/nodes/report.py`：`explanation_status` 进摘要与 limitation（`fallback` / “未使用知识库”）。
- `app/config.py` / `.env.example`：新增 `RAG_ENABLED / RAG_KNOWLEDGE_DIR / RAG_TOP_K / RAG_MIN_SCORE`，默认关闭。
- `tests/test_rag.py`（15 个）、`tests/test_explain.py`（13 个）；`tests/test_hitl.py` 增补 `route_after_human_review`。
- `docs/devlog/02_ARCHITECTURE_DECISIONS/ADR-008-RAG检索与解释质量门.md`：记录选项、决策、质量门、后果。
- 验证：**160 passed**；`ruff` 通过；CLI 实测（无 Key）解释 `fallback`、报告仍完整；Fake LLM + RAG 实测引用命中 `EX-INCOTERMS#s3`、`EX-CN-CONTRACT#s3` 等。

## 上一次产出（2026-10-27 第三阶段第 4 步：HITL）

- `app/nodes/hitl.py`
  - `build_approval_payload()`：只读 + 纯计算，**在 `interrupt()` 之前**完成（resume 会重跑节点顶部）；
  - 审批载荷 `ApprovalPayload` 不含 LLM 解释、不含时间戳、不含“建议通过/拒绝”；红色风险最多展示 20 条，超出给 `truncated` 计数；每条最多 3 段原文、每段截断 300 字符；
  - `interrupt(payload)` → `Command(resume=...)` 的决策经 Pydantic 校验；**决策缺失/非法一律 fail-closed** → `unreviewed_red_risk`，绝不当成 approve；
  - `route_by_risk()`：`failed` 直接走报告；有任一红色（含系统级 red）→ `human_review`，否则快速通道。
- `app/services/checkpointer.py`
  - `memory_checkpointer()`（测试）/ `sqlite_checkpointer()`（运行，`SqliteSaver`）/ `open_checkpointer()`（按 `CHECKPOINT_BACKEND` 选择）；
  - 自建 `JsonPlusSerializer(allowed_msgpack_modules=[...])` 登记 `app.schemas` 下全部 Pydantic 类型，消除 SQLite 反序列化“未登记类型”的未来阻断告警。
- `app/review_service.py`
  - API/UI/CLI 共用薄封装：`start()` / `get()` / `resume()`；
  - `get()` 做**惰性超时**：`now - requested_at >= HITL_TIMEOUT_MINUTES` → 自动 `resume(TIMEOUT_DECISION)` → `unreviewed_red_risk`；
  - 幂等：已是终态时再次 `resume` 直接返回现有结果，不重跑图、不重复生成报告；未知 `review_id` 抛 `ReviewStateError`。
- `app/graph.py`
  - 7 节点：`ingest → segment → extract → validate → rules → [条件边] → human_review → build_report`；
  - **未注入 checkpointer 时编译直接 `ValueError`**，不允许静默退化为假 HITL。
- `app/nodes/report.py`
  - 报告状态跟随人工终态（`approved / rejected / changes_requested / unreviewed_red_risk`）；
  - 摘要与 limitation 显式写“人工确认 / 已拒绝 / 要求修改 / 超时未确认，不得作为通过结论”；
  - 人工意见只进 `hitl`，**不改写规则等级**。
- `app/schemas.py`：新增 `ApprovalFinding` / `ApprovalPayload`（`extra="forbid"`）。
- `app/graph_demo.py`：CLI 支持 `--review-id` / `--decision {approve,reject,changes,timeout}` / `--reviewer` / `--comment` / `--memory`；默认 SQLite，跨进程可恢复。
- `tests/test_hitl.py`：14 个 HITL 测试（暂停、审批前零写入、快速通道、批准只写一次、拒绝不解释、要求修改、超时不通过、惰性超时、非法决策 fail-closed、幂等、未知 ID、载荷截断、未知 override 告警）。
- 文档：`ADR-007`（范围变更）、`06_RAG与多智能体资料清单.md`、`02_ARCHITECTURE_DECISIONS/README.md` 索引、开发日志 2026-10-26 追加 2026-10-27 章节。

## 上一次产出（2026-10-26 第三阶段第 3 步）

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

## 核心设计（ADR-001~013，已接受）

```text
START → ingest → precheck(是不是合同?) ─否→ report(not_contract)
   → 是 → segment → extract(LLM) → validate → rules(Python)
   → [有 red?] → human_review(interrupt)
   │                ├─ approve → explain(LLM [+RAG]) → report → END
   │                └─ reject / request_changes / timeout → report → END
   └─ 无 red → explain(LLM [+RAG]) → report → END
```

- 当前已实现全部 8 个节点：`ingest → precheck → segment → extract → validate → rules → [条件边] → human_review → explain → report`；
  三种交付入口均可用：CLI（`graph_demo.py`）、FastAPI + 对话式 Web 前端（`api.py` + `web/`）、Streamlit 备用（`ui.py`），全部只依赖 `ReviewService`。
- 账号/记录/Skill/BYOK（ADR-013）：本地 SQLite + 标准库密文盒 + 每审查 `LLMRuntime`；**审查重点与 Skill 只进解释提示（`<untrusted_focus>`），不改等级**；
- 等级只来自 Python 规则；LLM 的抽取/解释/专家候选 schema 中都没有 `risk_level`；
- HITL 用 `interrupt()`，不是状态字段；`thread_id=review_id`；SQLite 持久化已接入；
- 审批前零业务写入；超时 → `unreviewed_red_risk`，绝不自动通过；重复 resume 幂等；
- pending 时间戳落盘 `.data/pending/<review_id>.json`（原子写），重启后惰性超时仍有效；同 `review_id` 加进程内可重入锁；
- 解释必须通过 Python 质量门；知识引用只能是本条风险实际检索到的 `source_id#section`；
- 证据 `文件名:p页:start-end`；报告固定包含 limitation；
- 输入/解析/规则异常都有明确降级，不崩溃、不静默 pass；
- 抽取降级（无 Key/失败/超上限）时字段规则标记 `skipped`，不把“没抽到”说成“合同缺条款”；
- RAG/多智能体（ADR-007/008）：**允许但默认关闭**（`RAG_ENABLED=false`、`AGENTS_ENABLED=false`），只用于解释/建议/条款比对，不参与判级。

## 验证方式（可复现）

```powershell
.\.venv\Scripts\python.exe -m pytest
# 323 个用例：247 基础 + 前端（test_web.py 26）+ 规则目录 + 文档类型闸门 11
#   + 账号/记录/Skill/BYOK（test_accounts.py 35）+ RAG 兜底
#   + 逐条审查与修订导出（test_clause_review.py 11）

.\.venv\Scripts\python.exe -m ruff check .
# All checks passed!

# 评测：拆合同 + gold（可重建），再跑规则级指标（不调 LLM、不需要 Key）
.\.venv\Scripts\python.exe eval\prepare_contracts.py
# 50 份合同 → data/contracts/；105 条映射 → data/eval/gold_contracts.json
.\.venv\Scripts\python.exe eval\run_eval.py
# 合同 50 份；命中规则 11 份；未命中 39 份；等级 pass 39 / yellow 9 / red 2
# 规则级 TP=11 FP=0 FN=0 TN=539（同分布，仅作回归守卫）
# 合同级 P=1.00 R=0.79（漏报 C03/C13/C14：无检验条款且无对应规则）
# 覆盖率 21 个 gold 现象中 11 个有规则（0.5238）
# 结果：eval/results/rules-YYYYMMDD.json

# 留出集（对外报数只能用**当前未被消耗**的那一批；见 ADR-011 第 4 轮补充）
# ① 本轮唯一未消耗：holdout4（H29–H40，12 份）——引用这一组对外报数
.\.venv\Scripts\python.exe eval\run_eval.py --contracts data\contracts_holdout4 `
  --gold data\eval\gold_holdout4.json --gold-rules data\eval\gold_holdout4.json --tag holdout4
# 规则级 TP=8 FP=0 FN=1 TN=123 → P=1.00 R=0.889 F1=0.941，等级一致率 1.00
# 合同级 TP=8 FP=0 FN=1 TN=3 → P=1.00 R=0.889 F1=0.941；漏报 H39（已知，故意不修）
# 结果：eval/results/rules-holdout4-YYYYMMDD.json

# ② 已消耗样本：只作回归守卫，不得再对外报数
.\.venv\Scripts\python.exe eval\run_eval.py --contracts data\contracts_holdout3 `
  --gold data\eval\gold_holdout3.json --gold-rules data\eval\gold_holdout3.json --tag holdout3
# 修完三类措辞后：8 份 TP=7 FP=0 FN=0 TN=81（已消耗，属回归结果，不是泛化证据）

.\.venv\Scripts\python.exe eval\run_eval.py --contracts data\contracts_holdout `
  --gold data\eval\gold_holdout.json --gold-rules data\eval\gold_holdout.json --tag holdout
# 修复 H01/H03 后：TP=7 FP=0 FN=0（同样只作回归守卫）

.\.venv\Scripts\python.exe eval\run_eval.py --contracts data\contracts_holdout2 `
  --gold data\eval\gold_holdout2.json --gold-rules data\eval\gold_holdout2.json --tag holdout2
# 12 份：TP=9 FP=0 FN=0 TN=123（修掉子串误命中与窗口截断后；同样只作回归守卫）

# HITL：含风险样例会停在人工确认（退出码 0，状态 running，等待审批）
.\.venv\Scripts\python.exe -m app.graph_demo --memory
# 条款数量 8；总体等级 red；3 红 1 黄；extraction_status=degraded（无 Key）
# 风险解释：skipped（尚未批准）；输出审批载荷与“恢复命令”

# 同一 review_id 恢复（SQLite 跨进程）
.\.venv\Scripts\python.exe -m app.graph_demo --review-id <id> --decision approve --reviewer zhangsan --comment "已核对"
# status=approved；解释 status=fallback（无 Key，回退规则理由）
# 摘要含“红色风险已经人工确认”；timings 含 human_review_ms / explain_risks_ms
# 已批准后再次 --decision reject → 仍 approved（幂等，不重跑图）

.\.venv\Scripts\python.exe -m app.graph_demo --review-id <id> --decision timeout
# status=unreviewed_red_risk；解释 skipped；摘要“未获人工确认（审批超时），报告不得作为通过结论”

# 干净合同：无 red → 快速通道 → 解释 skipped（不调用 LLM）→ completed
.\.venv\Scripts\python.exe -m app.graph_demo data\samples\sample_clean_contract.txt

# FastAPI（默认 SQLite + .data/pending；同时托管对话式 Web 前端）
.\.venv\Scripts\python.exe -m uvicorn app.api:create_app --factory --port 8000
# 浏览器打开 http://127.0.0.1:8000/      对话式首屏（#/ 给审查重点/附件/Skill → #/review/{id} 风险点）
# http://127.0.0.1:8000/docs           Swagger UI
# POST /api/reviews（multipart：file + focus + skill_id + 可选 reference）→ awaiting_human=true
# → POST .../decisions（approve）→ GET /api/reviews/{id}/report?format=json|markdown
# 账号（ADR-013）：POST /api/auth/register|login、POST /api/auth/logout、GET /api/auth/me
# 记录：GET /api/reviews（需登录；未登录 401）
# 记录运维：PATCH /api/reviews/{id}（title / pinned，空串恢复文件名）、DELETE /api/reviews/{id}（204，连带清 checkpoint/pending/上传目录）
# Skill：GET /api/skills（未登录只给内置 7 个）、POST /api/skills、DELETE /api/skills/{id}
# BYOK：GET /api/llm/providers、GET|PUT|DELETE /api/llm（只回 has_key + 尾号）、POST /api/llm/test
# 只读规则目录（页面不消费）：GET /api/rules（13 条、5 红 / 8 黄；不返回正则/DSL）
# 逐条审查（界面轮 11）：GET /api/reviews/{id}/clauses → 条款原文 + 命中规则 + 示例修订 + 合同级问题
# 修订稿导出：POST /api/reviews/{id}/export {"format":"docx|pdf","clauses":[{"clause_id","text"}]}
#   → attachment（RFC5987 中文名）；未传 clauses 时保留原文；空条款/未知格式 400
# 前端资源：GET /、GET /static/styles.css、GET /static/app.js、GET /static/fonts/*.woff2（均 200，无外链）

# 前端语法检查（可选，需本机 node）
node --check app\web\app.js

# Streamlit（备用界面）
.\.venv\Scripts\python.exe -m streamlit run app/ui.py
```

Fake LLM 端到端（`tests/test_graph_extraction.py`）：`extraction_status=ok`、`facts.total_amount=3100000.0`、字段规则正常 pass、报告 `extracted_fields` 与 `facts` 一致；单条款超时 → 降级且字段规则 skipped，报告状态 `approved`（测试显式批准）。

HITL 端到端（`tests/test_hitl.py`，17 个）：`__interrupt__` 暂停、审批前零报告、无 red 快速通道、approve 只写一次、reject 不解释、request_changes、timeout 不通过、惰性超时、非法决策 fail-closed、重复 resume 幂等、未知 ID 报错、载荷截断、未知 override 告警、`build_graph()` 无 checkpointer 报错、两条条件边。

API/UI（`tests/test_api.py` 16 个 + `tests/test_web.py` 6 个 + `tests/test_pending_store.py` 11 个 + `tests/test_report_markdown.py` 3 个 + `tests/test_ui.py` 1 个）：上传暂停、审批后下载 JSON/Markdown、报告 409、快速通道幂等、404/422/413、文件名净化、跨 service 超时、损坏 pending、Markdown 章节与转义、Streamlit 首屏、`/api/rules` 目录与 `definitions.yaml` 一致且不泄露正则；**前端：首页/静态资源 200、无外链、本地字体（`font/*` + OFL）、无本地判级与 `Command`、资源不写死 host**。

解释/RAG 端到端（`tests/test_explain.py` 13 个 + `tests/test_rag.py` 22 个）：正常解释与引文定位、越权表述拦截、引文不可定位、rule_id/clause_id 不匹配、schema 禁 `risk_level`、无 Key 回退、拒绝/干净合同不调用 LLM、引用白名单（编造引用丢弃）、知识库配置错误降级、无命中告警、manifest 9 字段/路径穿越/重复 ID/编码校验、DOCX 条文切分、`***Article N***` 标题、超长片段二次切分、缓存重建、真实语料冒烟。

## 下一步（按顺序，不跳步）

1. ~~**第 2 步：文档解析与条款切分**~~ ✅ 已完成（2026-10-26）。
2. ~~**第 3 步：LLM 抽取 + Python 校验**~~ ✅ 已完成（2026-10-26）。
3. ~~**第 4 步：条件边 + HITL**~~ ✅ 已完成（2026-10-27）。
4. ~~**第 5 步：LLM 解释 + Quality Gate + 报告合并 + RAG MVP**~~ ✅ 已完成（2026-10-27，160 个测试）。
5. ~~**第 6 步：FastAPI + Streamlit**~~ ✅ 已完成（2026-10-27，197 个测试）
   - 上传（大小/类型/文件名净化）、运行、展示审批载荷、确认/拒绝/超时、下载报告 JSON/Markdown；
   - pending 时间戳落盘 `.data/pending`（ISSUE-017 已关闭）；按 `review_id` 的 `RLock` 防并发 resume；
   - UI/API 均不拼 `Command(resume=...)`，一律走 `ReviewService`。
   - ~~界面轮 1：原生 Web 前端~~ ✅ 已完成（2026-10-27，241 个测试）：`app/web/` 单页由 FastAPI 托管 `/` 与 `/static`，无框架/无 CDN/无构建；Streamlit 降为备用。
   - ~~界面轮 2：B 端审查工作台重设计（taste-skill）~~ ✅ 已完成（2026-10-27，243 个测试）：侧栏 + 面包屑 + sheet 画布 + hash 路由四视图；本地 IBM Plex 字体；新增只读 `GET /api/rules`；四页在 1440/768/390 均 0 FAIL / 0 WARN。
   - ~~界面轮 3：非合同闸门 + 收掉内部信息~~ ✅ 已完成（2026-10-27，259 个测试）：`precheck_document` 先判断是不是合同；`not_contract` 直接出“未执行审查”报告；前端新增“不是合同”页并移除侧栏运行环境；`API_VERSION 0.9.0`；修复顶部“选择合同”按钮；`.env` 开启 RAG，且模型不可用时仍列出检索到的知识引用。
   - ~~界面轮 4：侧栏保留 + 主区两屏~~ ✅ 已完成（2026-10-27，261 个测试）：主区只留“上传合同 / 风险点”，待确认态先展示审批载荷中的红色风险；下载改指 `/report?format=markdown`。
   - ~~界面轮 5：账号 / 记录 / Skill 仓库 / BYOK + 右侧对话式~~ ✅ 已完成（2026-10-27，288 个测试）：本地 SQLite 五表 + PBKDF2 口令 + 哈希会话；密文盒 Key（只回尾号）+ 每审查 `LLMRuntime`；7 个内置 Skill + 自建；审查重点/附件/Skill 移到右侧对话式输入区；侧栏只留登录（注册在弹窗内、尺寸不变）；底部免责 + 右下角政策弹窗（编号排版）；`API_VERSION 1.0.0`。
   - ~~界面轮 6：审查历史可运维 + Skill 归位 + 满屏 + 弹窗定高~~ ✅ 已完成（2026-10-27，295 个测试）：删掉首屏三行说明；Skill 下拉末项固定“Skill 仓库…”并默认 `builtin:full`，仓库入口移到侧栏；“当前审查”→“审查历史”侧栏子目录（改名 / 置顶 / 删除，`PATCH|DELETE /api/reviews/{id}`）；主区铺满整屏；登录/注册弹窗定高 460×453、邮箱→密码 gap 34px；两种模式都需手勾同意。
   - ~~界面轮 7：Skill 仓库独立页 + 自绘下拉 + 页脚贴右 + 输入区收窄~~ ✅ 已完成（2026-10-27，297 个测试）：`#/skills` 两栏页面（推荐 7 / 我的 / 新建）替换仓库弹窗；系统 select 换成胶囊 + `role=listbox` 卡片（键盘可达、末项仓库、8 项无滚动条、窄屏左对齐）；页脚 `max-width:none` 铺满、政策链接贴右、高度 26px；输入区 880→720。
   - ~~界面轮 8：注册 not found 根因 + Skill 导入~~ ✅ 已完成（2026-10-27，298 个测试）：8000 端口旧进程（`openapi` 0.9.0、无 `/api/auth/*`）导致注册 404，重启为 1.0.0 后 `/api/auth/me` 200；仓库页新增“从 Markdown 导入”（拖拽文件/文件夹 + 两个选择入口，frontmatter/标题/首段解析，逐条 `POST /api/skills`，同名跳过、单次 30 个、单文件 200 KB）。
   - ~~界面轮 9：个人账户 + Skill 查看/编辑 + 紧凑 + 厂商扩容~~ ✅ 已完成（2026-10-28，308 个测试）：删掉仓库页头说明；列表一行折叠、点开看审查重点；自建可 `PATCH /api/skills/{id}`，推荐可“存为我的”；右栏两卡片收紧；侧栏“退出登录”右侧圆形头像 → `#account-dialog`（头像压 128px JPEG、昵称、减少动效/自动聚焦、清除本机缓存与清空审查记录都二次确认）；厂商 10→20；API Key 输入加 `autocomplete=new-password` 等属性避免浏览器快捷填入账号密码。
6. **第四阶段（进行中）**：
   - ~~第 1 轮：规则 7 → 13 条（ISSUE-009）~~ ✅ 每条新规则都有语料命中集合回归；
   - ~~第 2 轮：silver gold（21 现象）+ 指标（rule/contract/coverage）+ 独立留出集（8 份）~~ ✅ 留出集 P=1.00 / R=0.71 / F1=0.83，暴露 2 个英文/同义改写漏报（ISSUE-021）；
   - ~~第 3 轮：规则 `version: 4` 补英文/同义改写 + 修子串误命中与运费窗口截断 + 新写 holdout2(12)/holdout3(8)~~ ✅ holdout3 盲测 **P=1.00 / R=0.571 / F1=0.727**，暴露 3 个措辞漏报（H21/H22/H24）；
   - ~~第 4 轮：规则 `version: 5` 修三类措辞 + `R-INS-001` 保额邻近判定 + 新写 holdout4(12)~~ ✅ holdout4 盲测 **P=1.00 / R=0.889 / F1=0.941**，仅剩 H39 一个漏报（故意不修）；holdout3 回归 7/0/0；
   - 下一步：① 修 H39（modal 与动词间允许时间状语），**另写 holdout5（8–12 份）** 再报数（ISSUE-021）；② 人工复核 silver gold（ISSUE-020）；③ 补规则缺口：检验条款缺失/不可抗力缺失等（ISSUE-009）；④ `100问题.md` → manifest 的检索评测映射（ISSUE-018）；⑤ 阶段 B 多智能体专家节点（ISSUE-016）。

## 当前阻塞 / 需要你拍板

| 事项 | 状态 | 需要你做什么 | 默认 |
|---|---|---|---|
| LLM API Key / 模型名 | 待提供 | 全链路演示前提供 OpenAI 兼容 Key/模型 | 代码开发不阻塞（Fake LLM 覆盖）；真实抽取/解释效果需 Key |
| RAG 知识库授权（ISSUE-015） | 语料已提供，授权待确认 | 确认真实语料可否在演示/答辩中展示原文、可否再分发 | 语料已入库 14 篇；`RAG_ENABLED=false` 默认关闭 |
| RAG 检索评测（ISSUE-015/018） | 待映射 | 把 `100问题.md` 的 source_id/section 映射到 manifest 引用 | 映射完成前不宣称召回率 |
| 多智能体角色与编排（ISSUE-016） | 待确认 | 确认是否需要专家节点（付款/交付/争议）及其资料 | 阶段 B 再做；Supervisor 仅路由 |
| 规则集范围（ISSUE-009） | 第 1 轮已扩 | 确认 13 条是否够用，或指定下一批主题（不可抗力/责任上限/质保/合规） | 13 条已落地；39/50 合同仍无命中 |
| 评测 gold（ISSUE-020） | silver 已完成，待复核 | 是否需要你/业务专家人工复核 21 个银标现象 + 四批留出的 32 个现象 | 已按 silver 跑出指标；复核前对外标注“待复核” |
| 英文/同义改写漏报（ISSUE-021） | 已修两轮，仍剩 H39 | 是否需要继续追写法覆盖（成本高、收益递减），或转去做规则缺口/检索评测 | 下轮修 H39，另写 holdout5 再报数 |
| 首批真实 PDF/DOCX 样例 | 待提供 | 有真实脱敏合同时优先用真实件 | 已有程序化 PDF/DOCX fixture，不阻塞 |
| 长合同抽取覆盖 | 已知限制 | 是否接受 > 40 条条款时字段规则跳过 | 先保持保守（宁可跳过不误报） |
| 多进程部署 | 已知限制 | 是否需要多 worker（当前锁仅进程内） | 单机单 worker 演示（ISSUE-019） |

## 3 分钟了解项目（给新接手的人）

1. 读根目录 `README.md` 的“设计底线 / 已知限制 / 快速开始”。
2. 读 `02_ARCHITECTURE_DECISIONS/README.md` 的“关键设计一句话”，再按需读 ADR-001~013。
3. 代码入口：`app/graph.py`（图组装）→ `app/review_service.py`（启动/查询/恢复 + 模型运行时作用域）→ `app/graph_demo.py` / `app/api.py`（+ `app/web/` 前端）/ `app/ui.py` → `app/nodes/explain.py`（解释与质量门）；账号与 BYOK 在 `app/services/accounts.py`、`secret_box.py`、`llm.py`；规则在 `app/rules/definitions.yaml`（13 条），评测在 `eval/`。
4. 当前已实现 ingest/segment/extract/validate/rules/human_review/explain/report、RAG 检索、FastAPI + 对话式 Web 前端（账号/记录/Skill/BYOK；Streamlit 备用）；未配置 Key 时抽取降级、解释回退规则理由。
5. 未解决事项看 `05_OPEN_ISSUES.md`（ISSUE-009 规则覆盖、ISSUE-020 silver gold 待复核、ISSUE-021 英文/措辞漏报与 H39、ISSUE-022 前端交互冒烟、ISSUE-023 类型闸门边界、ISSUE-024 报告阅读说明、**ISSUE-025 账号/Key 运维边界**、ISSUE-015/018 检索评测/授权、ISSUE-019 单进程假设）；RAG/多智能体资料要求看 `06_RAG与多智能体资料清单.md`；RAG 设计看 `ADR-008`，API/UI 与 pending 落盘看 `ADR-009`，规则扩充看 `ADR-010`，评测方法、gold 口径与留出集消耗规则看 `ADR-011`，上传类型闸门看 `ADR-012`，账号/记录/Skill/BYOK 看 `ADR-013`。

## 文件地图

```text
开发提示词.md                          # 需求与约束（RAG/多智能体部分以 ADR-007 为准）
README.md                              # 项目介绍、启动、设计底线、限制
requirements.txt / requirements-dev.txt# 锁定依赖（Python 3.12）
pyproject.toml                         # ruff / pytest 配置
.env.example                           # 环境变量模板（无真实 Key）
app/
  config.py                            # 环境变量与上限（MAX_* / CHECKPOINT_* / HITL_TIMEOUT_MINUTES / PENDING_DIR / UPLOAD_DIR / RAG_* / USER_* / SESSION_TTL_DAYS）
  schemas.py                           # Pydantic 契约（抽取 schema / RuleEvaluation / Report / ApprovalPayload / Explanation / focus+skill）
  graph.py                             # LangGraph 组装（9 节点 + 三条条件边 + 强制 checkpointer）
  review_service.py                    # start/get/resume（幂等 + 惰性超时 + pending 持久化 + review_id 锁 + 模型运行时作用域）
  graph_demo.py                        # CLI 演示（SQLite 跨进程；--decision 恢复）
  api.py                               # FastAPI（账号/记录/Skill/BYOK + 审查/决定/报告；错误码 400/401/404/409/413/422；托管 `/` 与 `/static`；API_VERSION 1.0.0）
  web/index.html                       # 壳层：侧栏（导航 + API 配置 + 接口文档 + 账号）+ 对话式主区 + 弹窗（登录/Skill/模型/记录/法务）
  web/styles.css                       # 设计系统 / 对话式输入区 / 本地字体 @font-face / 响应式 / 打印（无框架、无 CDN）
  web/app.js                           # hash 路由 + 对话式首屏 + 风险点渲染 + 账号/Skill/BYOK/记录/法务弹窗（不判级、不拼 Command）
  web/fonts/                           # IBM Plex Sans 可变字体 + Mono 400/500 + OFL.txt（离线随包）
  ui.py                                # Streamlit 中文界面（备用：上传/审批/报告/下载）
  report_markdown.py                   # ReviewReport → Markdown（纯渲染，不重算等级）
  nodes/ingest.py                      # TXT/MD/PDF/DOCX → canonical text + 页偏移
  nodes/precheck.py                    # 文档类型闸门（不是合同 → 直接出“未执行审查”报告）
  nodes/segment.py                     # 标题切分/合并/超长拆分/段落 fallback
  nodes/extract.py                     # LLM 17 字段抽取（唯一 LLM 抽取节点）
  nodes/validate.py                    # 引文核验/数值归一/一致性 → facts + to_verify
  nodes/rules.py                       # 规则节点（等级唯一来源）
  nodes/hitl.py                        # 审批载荷 + interrupt() + 决策校验 + 条件边
  nodes/report.py                      # 报告汇总（跟随人工终态 + limitation）
  services/llm.py                      # 结构化输出 + 1 次修复重试 + 异常类型 + 每审查 LLMRuntime（ContextVar 作用域）
  services/accounts.py                 # 账号/会话/Skill/模型配置/审查记录（本地 SQLite，WAL；口令 PBKDF2；跨账号隔离）
  services/secret_box.py               # API Key 静态加密（v1 密文盒：HMAC 密钥流 + 完整性标签）
  services/llm_providers.py            # 厂商目录（默认地址/模型/是否允许空 Key；不含任何 Key 字段）
  services/skill_catalog.py            # 7 个内置 Skill + compose_focus（用户指令/Skill/参考材料，≤4000 字）
  services/evidence.py                 # locate_quote（精确 → NFC/空白规范化）
  services/document_type.py            # “是不是合同”的确定性判定（抬头/编号/双方/条款结构/论文与法规反向信号）
  services/checkpointer.py             # memory/sqlite 工厂 + JsonPlusSerializer 类型登记
  services/pending_store.py            # pending 时间戳落盘（原子写 + review_id 白名单）
  services/rag.py                      # 本地 BM25 + 中文二元组 + MD/DOCX 切分 + manifest 校验 + 缓存
  rules/definitions.yaml               # 13 条规则（11 文本 + 2 字段，version 5）
  rules/dsl.py                         # 条件 DSL
  rules/engine.py                      # 规则加载/求值/证据/fail-closed/skipped
eval/
  prepare_contracts.py                 # 拆分模拟合同 → data/contracts/ + data/eval/gold_contracts.json
  metrics.py                           # 指标纯计算（rule_level / contract_level / coverage），无第三方依赖
  run_eval.py                          # 规则级评测 + 指标（不调 LLM）→ eval/results/rules[-tag]-YYYYMMDD.json
  results/                             # 评测结果（JSON，可版本化；主集 + 四批留出集各一份）
data/samples/                          # 2 份自拟脱敏样例
data/contracts/                        # 50 份模拟合同（由 eval/prepare_contracts.py 生成，可重建）
data/contracts_holdout/                # 8 份留出合同（H01–H08）→ 已消耗，回归守卫
data/contracts_holdout2/               # 12 份留出合同（H09–H20）→ 已消耗，回归守卫
data/contracts_holdout3/               # 8 份留出合同（H21–H28）→ 第 4 轮已消耗，回归守卫
data/contracts_holdout4/               # 12 份留出合同（H29–H40）→ 唯一未消耗，对外报数用这一批
data/eval/gold_contracts.json          # 50 份 / 105 条“条款 → Q 编号 → 期望召回 → 干扰项”（检索期望）
data/eval/gold_rules.json              # silver gold：21 个风险现象（11 有规则 / 10 为规则缺口），待人工复核
data/eval/gold_holdout.json            # 留出 gold：7 个现象（H04 为干净对照）
data/eval/gold_holdout2.json           # 留出 gold：9 个现象（H10/H13/H20 为干净对照）
data/eval/gold_holdout3.json           # 留出 gold：7 个现象（H27/H28 为干净对照）
data/eval/gold_holdout4.json           # 留出 gold：9 个现象（H32/H34/H36 为干净对照）
data/knowledge/                        # 真实语料 14 篇 + manifest；模拟合同1..6.md 为评测来源，不进 manifest
tests/                                 # 259 个测试（API 17 / 前端 8 / 文档类型 11 / pending 11 / RAG + 解释 24 / HITL 17 / 规则含四批留出回归 / 指标 11）
tests/fakes.py                         # Fake LLM（无需 Key）
tests/fixtures/pdf_builder.py          # 纯标准库构造最小 PDF（测试用）
docs/devlog/
  00_PROJECT_STATE.md                  # 本文件
  01_RESEARCH_LOG.md                   # 第一阶段调研
  02_ARCHITECTURE_DECISIONS/           # ADR-001~012（均已接受）
  03_DEV_LOGS/2026-10-26.md            # 调研 + ADR + 第 1/2/3/4/5/6 步日志
  03_DEV_LOGS/2026-10-27.md            # 第四阶段第 1/2/3/4 轮：规则扩充、评测基线、silver gold、留出验证、英文补强、三类措辞与保额邻近判定；界面轮 1/2/3：原生前端、B 端工作台、非合同闸门
  04_HANDOVER.md                       # 交接说明
  05_OPEN_ISSUES.md                    # 待决事项
  06_RAG与多智能体资料清单.md          # RAG/多智能体需要准备的资料与目录格式
```

