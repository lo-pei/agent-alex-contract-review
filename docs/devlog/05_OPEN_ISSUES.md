# 待解决问题 / 风险登记

> 更新时间：2026-10-28（界面轮 10：账户设置改成 B 端分区弹窗（个人信息 / 通用 / 数据管理 / 关于）+ 主题色 5 套 + 界面字号三档 + 侧栏不再显示昵称/邮箱；界面轮 9：个人账户弹窗（头像/昵称/系统设置/二次确认清数据）+ Skill 查看与编辑 + 仓库紧凑化 + 厂商 10→20 + 阻止密码自动填充；界面轮 8：注册 not found 根因（旧进程 0.9.0）+ Skill 支持 Markdown/文件夹导入；界面轮 7：Skill 仓库独立页 + 自绘下拉 + 页脚贴右/降高 + 输入区收窄；界面轮 6：审查历史子目录 + 记录改名/置顶/删除 + 侧栏 Skill 仓库 + 满屏 + 弹窗定高；界面轮 5：账号 / 审查记录 / Skill / BYOK；界面轮 4：侧栏保留 + 主区两屏；第四阶段第 4 轮：规则 version 5 + 保额邻近判定 + 第四批留出集）
> 状态标记：`[OPEN]` 待处理 / `[CLOSED]` 已解决 / `[DEFERRED]` 本阶段不处理
> 规则：未决事项不写进代码；影响架构的必须先拍板，再进第二阶段。
> 本轮变化：界面轮 10 把账户弹窗改成 **B 端设置形态**（左侧分区导航“个人信息 / 通用 / 数据管理 / 关于”，右侧面板切换；弹窗 760×560，窄屏导航转横向），通用区新增**主题色 5 套**（只换 `--accent`，风险语义色不动）与**界面字号 小/标准/大**（`--ui-text-scale` + 全量 `font-size: calc(...)`），个人信息补只读注册时间，数据管理加两张统计卡，关于区显示版本与政策入口；侧栏左下角**删掉昵称/邮箱**，只留“退出登录 + 头像”——**ISSUE-025** 补“偏好只在本机、无手动深色开关”，**ISSUE-022** 补“设置面板只做前端偏好、统计按需拉取”。界面轮 9 把 Skill 仓库列表改成**一行折叠**（点名称展开审查重点）、自建 Skill 可 `PATCH /api/skills/{id}` 编辑（推荐只读、可“存为我的”），右栏面板收紧凑；侧栏“退出登录”右侧加**圆形头像** → `#account-dialog`（换头像 / 改昵称 / 减少动效 / 自动聚焦 / 清除本机缓存 / 清空审查记录，两个清除动作都二次确认）；头像压成 128×128 JPEG 存 data URL（`users.avatar` 列 + 老库 `ALTER TABLE`）；厂商目录 10→20；API 配置 Key 输入改 `autocomplete="new-password"` 等属性，解决“点输入框弹出浏览器快捷填入账号密码”——**ISSUE-025** 补“无改密码/注销账号、头像不做服务端重编码”，**ISSUE-022** 补“清空记录逐条 DELETE、无批量接口”。界面轮 8 定位“注册显示 not found”是 **8000 端口跑着旧进程**（`openapi` 0.9.0，无 `/api/auth/*`）→ 重启为 1.0.0；并给 Skill 仓库加“从 Markdown 导入”（拖拽文件/文件夹 + 两个选择入口，前端解析 frontmatter/标题/首段，逐条 `POST /api/skills`，同名跳过、单次 30 个 / 单文件 200 KB）。**新增 ISSUE-026**（开发服务未开 `--reload`，前后端版本可能错位）。界面轮 7 把 Skill 仓库从弹窗改为独立页面 `#/skills`、原生 select 换成自绘 listbox、页脚铺满并贴右降高、输入区 880→720。界面轮 6 把“当前审查”改成侧栏“审查历史”子目录（记录可改名/置顶/删除，`PATCH|DELETE /api/reviews/{id}`），Skill 仓库入口收到侧栏、下拉末项固定为仓库，主区铺满屏幕，登录弹窗定高且登录/注册都必须手勾同意；**ISSUE-025** 补“同意条款未留痕（`consent_version`/`consent_at`）”与“删记录只清本机痕迹”；界面轮 5 按 ADR-013 增加账号、审查记录、Skill 仓库与 BYOK（**ISSUE-025**：账号/密钥的运维边界——密码找回、登录限流、主密钥备份、Cookie `Secure`、多 worker 运行时）；ISSUE-024 仍待做“这份报告怎么读”；ISSUE-021/020/009 与上轮一致（H39 故意不修、silver gold 待复核、覆盖率 52.4%）。
> 阅读提示：已关闭条目仍保留“决策前”的问题/选项/建议，最终以 **状态** 与 **决策** 段落为准。

---

## 汇总

| ID | 状态 | 优先级 | 问题 | 默认建议 |
|---|---|---|---|---|
| ISSUE-001 | CLOSED | — | 候选仓库 404 | 用 legal-tech-chat + graphrag 替代 |
| ISSUE-002 | CLOSED | — | GitHub clone 被重置 | codeload tar.gz 快照 |
| ISSUE-003 | CLOSED | P0 | LLM 供应商/模型/Key 未定 | OpenAI 兼容接口 + 环境变量，不绑定厂商（ADR-006） |
| ISSUE-004 | CLOSED | P0 | Python 3.9+ 与 2026 依赖冲突 | 改用 Python 3.12（ADR-006） |
| ISSUE-005 | CLOSED | P0 | 国际销售合同语料与 gold 未定 | 决策已定：50 份模拟合同 + 检索期望 gold 已就位；**规则级 gold 由 ISSUE-020 跟踪** |
| ISSUE-006 | CLOSED | P1 | HITL 超时策略 | 出“未审批”报告，绝不自动通过（ADR-002） |
| ISSUE-007 | CLOSED | P1 | PDF 解析库与扫描件范围 | pypdf 文本型 PDF；扫描件明确不支持（ADR-005） |
| ISSUE-008 | CLOSED | P1 | 无 LICENSE 仓库不能复用代码 | 只借鉴设计，重写实现（持续政策） |
| ISSUE-009 | OPEN | P1 | 国际销售合同规则集范围未定 | 已扩到 **13 条**（11 文本 + 2 字段）；覆盖率 52.4%（21 个 gold 现象 10 个无规则）；继续补检验/不可抗力缺失等主题 |
| ISSUE-010 | CLOSED | P2 | 指标口径与 baseline | 指标已写入 ADR-003 / ADR-005；实施时补结果文件 |
| ISSUE-011 | CLOSED | P2 | Git 仓库未初始化 | 已 `git init` + `.gitignore` + 首次提交 `cf0fd63` |
| ISSUE-012 | OPEN | P2 | 中文/复杂版式 PDF 未验证 | 补 CJK 字体 PDF fixture；用真实中文合同手测并记录 |
| ISSUE-013 | OPEN | P1 | 真实 LLM 未联调 | 待用户提供 Key/模型名；先用 Fake LLM 覆盖降级路径 |
| ISSUE-014 | OPEN | P2 | 长合同抽取覆盖不足（>40 条款跳过字段规则） | 先保守跳过；后续评估分块/提高上限并补评测 |
| ISSUE-015 | OPEN | P1 | RAG 知识库授权与检索评测未确认 | 真实语料已入库（14 篇，含 DOCX 条文切分）；下一步确认对外引用授权并做检索评测 |
| ISSUE-016 | OPEN | P2 | 多智能体专家角色与编排范围未定 | 阶段 B 再做；只做专家节点 + 路由，Supervisor 不得判级 |
| ISSUE-017 | CLOSED | P2 | HITL pending 时间戳只在进程内存 | 已落盘 `.data/pending/<review_id>.json`，跨进程超时判定有测试 |
| ISSUE-018 | OPEN | P1 | 检索评测问题集的 source_id 与 manifest 不一致 | 建立 `100问题.md` → manifest `source_id#section` 映射后再报召回率 |
| ISSUE-019 | OPEN | P2 | 并发锁仅进程内、上传/报告文件无清理策略 | 单机演示可接受；多进程部署前需换文件锁/数据库并加保留期 |
| ISSUE-020 | OPEN | P1 | 规则级 gold、留出合同集与模拟合同数量不符 | silver gold（21 现象）+ 四批留出集（40 份）已就位；**待人工复核**，且用户所称 60 份实为 50 份 |
| ISSUE-021 | OPEN | P1 | 规则对英文条款与同义改写漏报 | 已修两轮（version 4 → 5）：英文/同义改写、子串误命中、窗口截断、保额全文级判定、3 类措辞写法；holdout4 仍剩 H39 一个漏报（modal 与动词间插时间状语），下轮修 + 另写 holdout5 |
| ISSUE-022 | OPEN | P2 | 主区交互无自动化测试、待确认态依赖审批载荷口径、历史列表无分页、清空记录逐条删、偏好只在本地 | `tests/test_web.py` 覆盖加载/无外链/本地字体/不判级/侧栏保留且主区无工作台内容/待确认先展示规则风险/Skill 末项仓库/历史子目录工具/同意默认不勾选/Markdown 导入入口/Skill 行折叠与编辑/账户设置四分区与侧栏无昵称邮箱/LLM 表单不自填充；上传、抽屉、确认、改名置顶删除、账户分区切换仍靠真实浏览器 + CDP 冒烟；`approval` 只含 red，黄色风险只在确认后的报告出现；历史只取 20 条；导入上限与同名跳过只在前端执行，服务端仅校验长度；“清空审查记录”是前端逐条 `DELETE`（N 条 N 次请求），没有批量接口；主题/字号/动效只写 `localStorage`，统计卡按需拉 `GET /api/reviews?limit=500`，无设置表与统计接口 |
| ISSUE-023 | OPEN | P1 | 文档类型闸门边界：召回优先、非中英合同可能误拒、阈值需真实语料调参 | 闸门只判“是不是合同”，不判类型、不判风险；误拒/误放率无统计口径；扫描件无文本只能按“过短”拒绝并提示 OCR |
| ISSUE-024 | OPEN | P2 | 主区不再展示规则目录与报告全貌，用户无法自助判断“规则覆盖到哪” | 当前把规则范围、抽取状态、解释来源、limitations 全部放在 Markdown 报告；后续在结果页加“这份报告怎么读 / 规则覆盖范围”说明链接，而不是新增主区视图 |
| ISSUE-025 | OPEN | P1 | 账号与密钥的运维边界（找回密码、注销账号、登录限流、主密钥备份、Cookie `Secure`、多 worker、同意留痕、头像编码、偏好不随账号） | 演示形态：无找回/验证码/限流；**无改密码与注销账号**（口令哈希尚无版本化迁移）；主密钥与库必须一起备份，丢失只能重填 Key；Cookie 未加 `Secure`（本地 HTTP）；多 worker 时 `_RUNTIME` 不共享；登录/注册手勾同意但未记 `consent_version`/`consent_at`；头像只校验 `data:image/...;base64` 前缀与 400k 字符上限，服务端不重新编码/不扫描（前端压 128px）；主题色/字号/动效只存 `localStorage`，不跨设备同步，也没有手动深色开关 |
| ISSUE-026 | OPEN | P2 | 开发服务未开 `--reload`，8000 端口可能跑着旧代码（注册 404 “not found”） | 演示用单进程 uvicorn；改后端后手动重启，用 `GET /openapi.json` 的 `info.version` 核对是否为 1.0.0；长期方案是本地开 `--reload` 或启动脚本打印版本 |

---

## ISSUE-001 · 候选仓库 404

- **状态**：CLOSED
- **现象**：`Negbepierre/enterprise-doc-intelligence` 的 GitHub API 返回 `404 Not Found`；用户主页无公开仓库。
- **影响**：原定 7 个候选少 1 个，调研样本不足。
- **解决**：按提示检索替代项目，补充 `tomasonjo-labs/legal-tech-chat`（CUAD + LangGraph + Neo4j）与 `neo4j-product-examples/graphrag-contract-review`（GraphRAG），最终分析 8 个。
- **证据**：`01_RESEARCH_LOG.md` 0.1、0.3、2.7、2.8。

---

## ISSUE-002 · GitHub `git clone` 被重置

- **状态**：CLOSED
- **现象**：`git clone https://github.com/...` 在 `github.com:443` 连接被重置；REST API 与 `raw.githubusercontent.com` 可用。
- **影响**：无法用 git 历史/分支调研。
- **解决**：用 `https://codeload.github.com/{owner}/{repo}/tar.gz/refs/heads/{branch}` 下载默认分支快照，`tar.exe` 解压后阅读源码。
- **限制**：只看到默认分支最新快照，看不到提交历史与其他分支；文档已注明。
- **证据**：`01_RESEARCH_LOG.md` 8.1。

---

## ISSUE-003 · LLM 供应商、模型与 Key 未定

- **状态**：CLOSED（接口决策已定；实际 Key/模型名待提供）
- **决策**：采用 OpenAI 兼容接口；`.env` 配置 `LLM_BASE_URL / LLM_API_KEY / LLM_MODEL / LLM_TIMEOUT_SECONDS / LLM_MAX_REPAIR_RETRIES`；代码不写死厂商；结构化输出优先 `json_schema`，不支持时回退 `function_calling`；测试用 Fake LLM。详见 `ADR-006-运行环境与依赖策略.md`。
- **仍待用户提供**：实际 API Key 与可用模型名（不阻塞规则/图/测试开发，只影响全链路演示）。
- **优先级**：P0（阻塞第三阶段 LLM 节点）
- **需要决定**：
  1. 用哪家 API（OpenAI / Azure OpenAI / 国内兼容接口 / 本地模型）；
  2. 模型名与上下文上限；
  3. 谁提供 Key，比赛环境是否允许联网；
  4. 超时、重试、成本上限。
- **默认建议**：抽象成 OpenAI 兼容接口，用 `.env` 配置 `LLM_BASE_URL / LLM_API_KEY / LLM_MODEL`；代码不写死厂商；结构化输出优先 `with_structured_output(method="json_schema")`，不支持时回退 `function_calling`；单次调用超时 60s，最多 1 次修复重试。
- **影响**：影响抽取/解释节点、评测成本、演示稳定性；不影响规则引擎与 HITL 测试（测试用 Fake LLM）。

---

## ISSUE-004 · Python 版本约束冲突

- **状态**：CLOSED（2026-10-26）
- **决策**：采用 **Python 3.12**；本机 `py -3.12` 可用。原 `开发提示词.md` 的“3.9+”因 2026 年 LangGraph/Streamlit 依赖要求而调整；README 必须写明原因。详见 `ADR-006-运行环境与依赖策略.md`。
- **优先级**：P0（阻塞环境初始化）
- **现象**：`开发提示词.md` 写“Python 3.9+”；但 2026-10-26 最新依赖要求：
  - LangGraph 1.2.17 / LangChain 1.4.7 / FastAPI 0.162.0 / Pydantic 2.14.1：≥3.10；
  - Streamlit 1.66.1：**≥3.11**。
- **本机**：默认 `python` 是 3.14；已装 `py -3.12`（`C:\Users\lenovo\AppData\Local\Python\pythoncore-3.12-64`）。
- **选项**：
  - A. 用 Python 3.12（推荐）：享受当前 LangGraph HITL/checkpointer、Streamlit 新特性；需在 README 说明“实际 3.12，3.9 无法满足 2026 依赖”。
  - B. 严格 3.9：锁 LangGraph 0.2.x、Streamlit 旧版、Pydantic 2 低版本；HITL API 与文档能力受限，需要额外兼容测试，风险高。
  - C. 3.11：也可以，但本机未装；需额外安装。
- **建议**：A（3.12）。请用户确认；确认后写入 ADR-001/环境说明。
- **证据**：`04_HANDOVER.md` 3.2；PyPI requires-python 查询。

---

## ISSUE-005 · 国际销售合同语料与 gold 未定

- **状态**：CLOSED（决策已定；语料与检索期望 gold 已就位，规则级 gold 转 ISSUE-020）
- **进展（2026-10-27）**：用户提供 50 份模拟合同（`data/knowledge/模拟合同1..6.md`），已拆分到 `data/contracts/C01..C50.md`，并解析出自带映射摘要 → `data/eval/gold_contracts.json`（50 份 / 105 条“条款 → Q 编号 → 期望召回 → 干扰项”）。该 gold 是**检索期望**，不含 `red/yellow/pass`，因此不能直接用于规则准率。
- **决策**（保持不变）：gold 只标 `rule_id + red/yellow/pass + 原文 span`，不标“法律上是否有效”；评测集放 `data/eval/`；不直接使用 CUAD。
- **剩余工作**：见 ISSUE-020（规则级 gold 标注、留出合同集、模拟合同数量 50 ≠ 60 的口径确认）。
- **影响**：规则阈值、HITL 触发率、报告可信度、答辩演示。

---

## ISSUE-006 · HITL 超时策略

- **状态**：CLOSED（2026-10-26）
- **决策**：采用 C：超时后恢复并标记 `unreviewed_red_risk`，报告可下载但明确“红色风险未获人工确认”；惰性检查（GET /review/{id} 或 Streamlit 轮询）触发 `Command(resume={"action":"timeout"})`；绝不自动 approve。详见 `ADR-002-HITL实现方式.md`。
- **优先级**：P1（影响 HITL 契约）
- **问题**：红色风险暂停后，如果 30 分钟无人确认，系统该怎么办？
- **选项**：
  - A. 一直等待，不自动处理（演示可能卡住）；
  - B. 超时后自动 approve（**禁止**，违背硬约束）；
  - C. 超时后恢复并标记 `unreviewed_red_risk`，报告写明“红色风险未获人工确认”（推荐）；
  - D. 超时后取消本次 review，不生成报告。
- **建议**：C；由后台 sweeper 或 `GET /review/{id}` 惰性检查触发 `Command(resume={"action":"timeout"})`；报告可下载但状态明确未审批；Streamlit 显示黄色警示条。
- **影响**：API/UI 状态机、checkpointer 线程、报告字段 `hitl.status`。

---

## ISSUE-007 · PDF 解析库与扫描件范围

- **状态**：CLOSED（2026-10-26）
- **决策**：MVP 用 `pypdf`（BSD）+ `python-docx` + TXT/Markdown；扫描件/OCR 明确不支持；不默认引入 PyMuPDF（AGPL/商业许可）；表格/复杂版式只 warning + 人工核对。详见 `ADR-005-文档解析与证据模型.md`。
- **优先级**：P1（影响 ingest 节点）
- **问题**：
  - `pypdf` BSD，能取文本型 PDF，但对复杂版式/表格/扫描件弱；
  - `PyMuPDF` 能力更强，但 AGPL/商业双许可，不适合默认引入；
  - `pdfplumber` MIT，表格强但速度慢。
- **建议**：
  - MVP 用 `pypdf` + `python-docx` + TXT；
  - 明确“不支持扫描件/OCR”；上传扫描件时返回可读错误；
  - 若后续需要表格/复杂版式，再评估 `pdfplumber`（MIT）；
  - 不引入 PyMuPDF 作为默认依赖，除非用户确认许可证。
- **影响**：文档解析质量、证据偏移是否可靠、演示合同选择。

---

## ISSUE-008 · 无 LICENSE 仓库不能复用代码

- **状态**：CLOSED（政策已定，持续执行）
- **优先级**：P1（法律/合规风险）
- **事实**：zihan、Harvey、Sentinel 仓库没有 LICENSE 文件，默认保留全部权利。
- **处理**：
  - 只借鉴设计思想与架构模式，不复制源文件、不复制大段代码；
  - 可复用代码仅限 Apache-2.0（bcefghj、laolaola、graphrag）与 MIT（aurelien、legal-tech-chat），且保留版权/许可声明；
  - 所有引用记入 `README.md` 的“第三方代码与许可”。
- **证据**：`01_RESEARCH_LOG.md` 第 1 节、8.3。

---

## ISSUE-009 · 国际销售合同规则集范围未定

- **状态**：OPEN（2026-10-27 第 1 轮已扩到 13 条；覆盖仍不足）
- **优先级**：P1（影响规则引擎与评测）
- **当前进度**：`app/rules/definitions.yaml`（`version: 5`）已实现 **13 条**：
  | rule_id | 主题 | 等级 | 依赖 | 50 份语料命中 |
  |---|---|---|---|---|
  | R-TRD-001 | 使用贸易术语但未约定 Incoterms 版本 | yellow | 文本 | 0（修正 `®` 后） |
  | R-PAY-001 | 要求买方全额预付 | red | 文本 | 0 |
  | R-PAY-002 | 未约定付款方式/节点 | yellow | 文本 | 5 |
  | R-DIS-001 | 未约定适用法律 | red | 文本 | 0 |
  | R-DIS-002 | 未约定争议解决方式 | red | 文本 | 0 |
  | R-DLV-001 | 未抽取到交付期限 | yellow | 字段（`delivery_date`） | skipped（无 Key） |
  | R-INP-001 | 未抽取到检验标准/机构 | yellow | 字段（`inspection_standard`） | skipped（无 Key） |
  | R-DIS-003 | 仲裁与诉讼并列（“或裁或审”） | red | 文本 | 1（C47） |
  | R-DIS-004 | 仲裁裁决后仍可向法院起诉（“先裁后审”） | red | 文本 | 1（C48） |
  | R-INS-001 | CIF/CIP 约定投保但未写保额/比例 | yellow | 文本 | 1（C04） |
  | R-INC-001 | 贸易术语与运费承担矛盾 | yellow | 文本 | 1（C11） |
  | R-INC-002 | FOB/EXW 用于整箱集装箱货物 | yellow | 文本 | 1（C23） |
  | R-INP-002 | 检验或通知期限以小时计（极短） | yellow | 文本 | 1（C09） |
- **新规则准入四关**（ADR-010）：DSL 可确定性判定 → 正反 fixture + 证据 span 回填 → 50 份语料命中集合固化为回归测试 → 两份样例合同零误报。
- **抽取降级语义**：`requires_extraction: true` 的规则在抽取不可用（无 Key/失败/超上限）时标记 `skipped`，不落入 yellow，避免系统降级被误读为合同缺陷。
- **仍缺的主题（下一轮候选，要求可确定性判定）**：
  1. 不可抗力条款缺失（文本级，可判定）；
  2. 责任上限缺失/过低（字段 `liability_cap` 为空 → yellow；“过低”需阈值，暂不做）；
  3. 质保期缺失（字段 `warranty_period` 为空 → yellow）；
  4. 所有权保留/风险转移条款缺失（文本级）；
  5. 制裁/出口管制/反腐败条款缺失（文本级，中国出口场景）。
- **现状判断**：50 份合同中 39 份未命中任何规则，说明上述主题确实缺口明显；但模拟合同大量使用 `[C] 天`、`[X]` 占位符，数值/期限类规则需要容忍占位符，否则会误报。
- **建议**：下一轮每条新规则同样走准入四关；语义型规则（如“赔偿上限是否过低”）如果无法确定性判定，先不做，避免把 LLM 判断伪装成规则。
- **影响**：产品定位、评测 gold、答辩演示的风险列表。

---

## ISSUE-010 · 指标口径与 baseline

- **状态**：CLOSED（2026-10-26，口径已定；结果待补）
- **决策**：规则评测 micro P/R/F1 + 混淆矩阵；抽取字段 accuracy（含 null）+ 引文支撑率；解释 `explanation_grounded_rate`、改级率（应为 0）、越权表述率、兜底率；系统 HITL 触发 precision/recall、降级率、p95、token 成本。所有结果附样本数/模型/prompt 版本/日期/命令，并给 baseline。详见 `ADR-003-规则与LLM边界.md` 3.10。
- **优先级**：P2（影响评测与汇报）
- **要求**：
  - 规则评测：micro P/R/F1（按 `合同 × rule_id`），附混淆矩阵；
  - 抽取评测：字段级 accuracy（含 null）、引文支撑率；
  - 解释评测：`explanation_grounded_rate`、是否出现改级/越权表述；
  - 系统评测：HITL 触发 precision/recall、降级率、p95 延迟、token 成本；
  - 所有报告附：样本数、模型名、prompt 版本、日期、命令；
  - **必须给 baseline**（空抽取 / 全 pass 规则）作为对照。
- **禁止**：无评测集支撑的“94%”“8 分钟”“业界领先”。
- **影响**：README、答辩材料、评委追问。

---

## ISSUE-011 · Git 仓库未初始化

- **状态**：CLOSED（2026-10-26）
- **解决方式**：已执行 `git init`；提交 `.gitignore`（忽略 `.venv/`、`.env`、`.data/`、`*.sqlite*`、`__pycache__/`、`.pytest_cache/`、`.ruff_cache/`）；首次提交 `cf0fd63 chore: 初始化仓库并提交阶段1-3第1步成果`。
- **未提交**：`.venv/`、`.env`（尚不存在）、`.data/`、缓存；未提交任何真实合同或 Key。
- **备注**：提交前未单独确认提交信息风格，采用 `chore:` 前缀；如需调整可 `git commit --amend`（尚未 push）。

---

## ISSUE-012 · 中文 / 复杂版式 PDF 未验证

- **状态**：OPEN
- **优先级**：P2（影响真实合同可用性与演示选择）
- **现象**：
  - `tests/fixtures/pdf_builder.py` 只构造 ASCII（Helvetica/WinAnsi）单栏 PDF，**不能证明中文 PDF 可解析**；
  - 页眉/页脚/水印会被 pypdf 提取进正文；表格/多栏可能打乱列顺序（只在 `warnings` 提示）；
  - 尚未用真实中文合同（含 CJK 字体、盖章页、扫描混合页）做手测。
- **复现步骤**：用一份真实中文 PDF 执行
  `.\.venv\Scripts\python.exe -m app.graph_demo 合同.pdf`，检查 `clauses` 的标题/顺序/页码与 `report.findings` 引用是否可定位。
- **建议方向**：
  1. 手测 2–3 份中文 PDF（文本型），记录解析结果到开发日志；
  2. 如需自动化，构造嵌入 CJK 子集字体的 PDF fixture（不引入 reportlab，可用 pypdf 附件/字体子集方案）；
  3. 页眉/页脚过滤放到后续迭代，先靠规则关键词窄化 + 人工核对；
  4. 复杂版式明确不支持时，在 UI 提示转 DOCX。
- **影响**：演示合同选择、证据页码可信度、中文条款切分质量。

---

## ISSUE-013 · 真实 LLM 尚未联调

- **状态**：OPEN
- **优先级**：P1（影响全链路演示与抽取效果评估）
- **现象**：
  - 目前所有抽取测试都基于 `tests/fakes.py` 的 `FakeLLM`，`json_schema` → `function_calling` 的真实回退路径未在真实供应商上验证；
  - 未测真实模型对 17 字段 schema 的遵循度、超时行为、非 JSON 输出的实际频率；
  - 没有 Key/模型名，无法给出任何抽取准确率或延迟数字。
- **需要**：用户提供 OpenAI 兼容的 `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL`（写进本地 `.env`，不入库）。
- **联调步骤**：
  1. `.\.venv\Scripts\python.exe -m app.graph_demo`（不带 Key 走降级 → 带 Key 应显示 `要素抽取：ok`）；
  2. 检查 `facts`、`fact_evidence`、`to_verify` 是否合理；
  3. 记录模型名、prompt 版本、耗时到开发日志；
  4. 若供应商不支持 `json_schema`，确认回退 `function_calling` 成功（日志里应只有一次 `StructuredOutputError` 级别的重试）。
- **禁止**：在没有真实运行记录前写“抽取准确率 X%”。

---

## ISSUE-014 · 长合同抽取覆盖不足

- **状态**：OPEN
- **优先级**：P2（影响长合同可用性）
- **现象**：`MAX_EXTRACT_CLAUSES=40`，超过上限时只抽取“前言 + 相关类型优先”的前 40 条；由于 `extraction_status` 只有全量成功才算 `ok`，此时字段规则全部 `skipped`，报告只能靠文本规则。
- **风险**：长合同（>40 条款）的字段类风险（交付期限、检验标准、责任上限）会静默不判。
- **建议方向**：
  1. 短期：报告 limitation 已写明；UI 明确提示“条款过多，字段规则未执行”；
  2. 中期：按 `clause_type` 分批抽取（每批独立 `extract_fields` 调用）+ 明确批次状态；
  3. 长期：结合成本上限做“重要性排序 + 覆盖统计”，并在评测集里加入长合同样本。
- **不可接受**：为了“跑完”把部分覆盖当 `ok`，会直接产生误报。

---

## ISSUE-015 · RAG 知识库授权与检索评测未确认

- **状态**：OPEN（2026-10-27 语料已提供，链路已跑通；授权与评测待确认）
- **优先级**：P1（影响“知识引用能否对外展示”与检索质量结论）
- **已解决**：
  - 用户已将真实语料放入 `data/knowledge/`（CISG 中英、Incoterms 2020、民法典、涉外民事关系法律适用法、6 份最高法司法解释、UCP600/仲裁要点、内部红线清单）；
  - `manifest.yaml` 已登记 14 篇，含 `source_id/title/publisher/version/jurisdiction/effective_date/language/file/license`；
  - `app/services/rag.py` 已支持 `.docx` 按“第X条”切分（民法典 1260 条 → 1261 段）、英文 CISG `***Article N***` 标题、超长片段二次切分，并显式拒绝旧版 `.doc`；
  - 实测加载 14 篇 / 1834 段，最长 1599 字符；`根本违约`、`FOB 风险转移`、`仲裁 管辖`、`不可抗力` 均能命中合理引用。
- **仍未解决**：
  1. **授权边界**：`license` 字段只是当前标注（如 `ICC-copyright-internal-use-only`、`official-text-verify-reuse`），是否允许在演示/答辩中展示原文、是否允许再分发，仍需业务/法务确认；
  2. **effective_date 复核**：日期取文件标题/文件名标注，对外引用前需按官方文本核对；
  3. **旧版 `.doc`**（`最高人民法院关于涉外民商事案件诉讼管辖若干问题的规定_20201229.doc`）未入库，需转换为 `.docx` 或 `.md`；
  4. **检索评测**：尚未跑 `100问题.md` 的 100 条 query，且其 `source_id` 命名与 manifest 不一致（ISSUE-018）。
- **默认**：`RAG_ENABLED=false`；开启后只增强解释，不参与判级；知识引用必须能在 `source_id#section` 定位。
- **禁止**：把无授权文本、抓取的付费标准全文、或模型记忆当成知识库引用。

---

## ISSUE-016 · 多智能体专家角色与编排范围未定

- **状态**：OPEN
- **优先级**：P2（阶段 B 才做，不阻塞第 5/6 步）
- **背景**：ADR-007 允许专家节点与 Supervisor 路由。但“哪些专家、谁触发、如何合并”会直接影响延迟、成本与可测试性，必须先定范围。
- **候选角色**：
  | 角色 | 输入 | 输出（禁止 `risk_level`） |
  |---|---|---|
  | 付款专家 | 付款条款 + 规则结果 | 付款节点风险解释、改写建议 |
  | 交付/物流专家 | 交付、贸易术语、检验条款 | 交付与风险转移说明 |
  | 争议解决专家 | 适用法律、仲裁/管辖条款 | 争议路径说明 |
- **约束（不可变）**：专家只能依据既有规则结果补充解释与建议；不得改级、不得新增 red/yellow；Supervisor 只做白名单路由，不做判级；专家失败必须回退到单节点解释。
- **需要用户确认**：是否需要专家节点、专家资料（30–50 组“问题条款→改写”对照、让步顺序、品类模板）、是否接受额外 LLM 调用成本。
- **默认建议**：阶段 B 先做 2 个专家（付款、争议解决），用开关 `AGENTS_ENABLED=false` 默认关闭；先补 `test_agents_cannot_override_rule_level` 与 `test_supervisor_whitelist`。

---

## ISSUE-017 · HITL pending 时间戳只在进程内存

- **状态**：CLOSED（2026-10-27 第 6 步）
- **优先级**：P2（影响重启后的超时判定）
- **原现象**：`ReviewService._requested_at` 是进程内 `dict[review_id, datetime]`；进程重启后该表为空，`get()` 无法判断是否已超过 `HITL_TIMEOUT_MINUTES`，惰性超时失效。
- **解决方式**：
  1. 新增 `app/services/pending_store.py`：`FilePendingStore` 落盘 `.data/pending/<review_id>.json`（临时文件 + `os.replace` 原子写），`MemoryPendingStore` 供测试；
  2. `ReviewService` 注入 `PendingStore`：首次观察到暂停写时间戳（不覆盖已有值），恢复/超时后清理；
  3. `review_id` 用正则白名单校验，防路径穿越；损坏文件按“未记录”处理，**绝不据此判超时**；
  4. 同一 `review_id` 的 `get` / `resume` 加 `threading.RLock`（可重入），防止并发恢复把图跑两次。
- **证据**：`tests/test_pending_store.py`
  - `test_lazy_timeout_survives_service_restart`：换新 service + 新 store 实例后仍触发 `unreviewed_red_risk`；
  - `test_pending_removed_after_decision`、`test_file_store_ignores_corrupted_file`、非法 ID 参数化测试。
- **残余风险**：锁只在单进程内有效（ISSUE-019）。

---

## ISSUE-018 · 检索评测问题集的 source_id 与 manifest 不一致

- **状态**：OPEN
- **优先级**：P1（影响 RAG 检索评测与任何“召回率”数字）
- **现象**：`data/knowledge/100问题.md` 的 100 条 query 使用 `CISG-25`、`CISG-39(2)`、`INC`、`LAW`、`CC`、`JI`、`RISK` 等命名，而 manifest 的 `source_id` 是 `CISG-ZH / CISG-EN / CISG-KEY / INCOTERMS-2020 / CN-CIVIL-CODE / CN-LAW-APPLICATION / SPC-* / RISK-REDLINE`；section 也是自然语言描述而非 `sN` / `第X条`。
- **影响**：直接跑评测会把“正确命中”误判为“未命中”，无法给出可信召回率。
- **建议方向**：
  1. 建立映射表（query # → `expected_source_ids` + `expected_sections`），人工确认 20–30 条高置信样本先跑；
  2. 检索结果允许“多命中”，评测按 `source_id` 与条文号（docx）或章节语义（md）匹配；
  3. 评测结果写入 `eval/results/*.json`，含 `RAG_TOP_K` / `RAG_MIN_SCORE` / 语料版本。
- **禁止**：在映射完成前宣称“RAG 召回率 X%”。

---

## ISSUE-019 · 并发锁仅进程内、上传/报告文件无清理策略

- **状态**：OPEN
- **优先级**：P2（单机演示可接受）
- **现象**：
  - `ReviewService` 的锁是进程内 `threading.RLock`；多 worker（多进程 uvicorn）部署时仍可能并发 resume；
  - `.data/uploads/<review_id>/` 与 `.data/pending/<review_id>.json` 没有保留期/清理任务；
  - SQLite checkpointer 的 `check_same_thread=False` 只解决线程问题，不解决多进程写冲突。
- **建议方向**：
  1. 多进程前先改用文件锁（`filelock`）/SQLite 事务锁，或限制单 worker 部署并在 README 写明；
  2. 增加启动时清理 N 天前的 uploads/pending（先做脚本，不引入调度组件）；
  3. 评测/演示环境保留现状即可，但必须在文档中说明“单进程假设”。

---

## ISSUE-020 · 规则级 gold、留出合同集与模拟合同数量不符

- **状态**：OPEN（第 1 步已完成：silver gold + 指标 + 四批留出集；**待人工复核**）
- **优先级**：P1（决定能否对外报指标）
- **已完成（2026-10-27 第 2–4 轮，ADR-011）**：
  1. `data/eval/gold_rules.json`：21 个风险现象（11 个映射规则 + 10 个显式标为规则缺口），`provenance: silver`，标注口径写入文件；
  2. 四批留出合同：`holdout`（H01–H08，7 现象）、`holdout2`（H09–H20，9 现象）、`holdout3`（H21–H28，7 现象）、`holdout4`（H29–H40，9 现象，**当前唯一可对外报数**），均有对应 `gold_holdout*.json`；
  3. `eval/metrics.py`：`rule_level` / `contract_level` / `coverage` 三组指标；`run_eval.py --tag holdoutN` 输出独立结果文件；
  4. 指标：主集（50 份，同分布）TP=11 FP=0 FN=0；holdout4（12 份）**TP=8 FP=0 FN=1 → P=1.00 / R=0.889 / F1=0.941**；覆盖率 11/21 = 52.4%。
- **事实（仍需确认）**：用户称新增“60 份模拟合同”，实际 `data/knowledge/` 只有 6 个文件、**50 份合同（C01–C50）**，逐份核对无 C51–C60。
- **剩余工作**：
  1. **人工复核** 21（设计集）+ 36（四批留出集共 7+9+7+9=32，其中 4 条干净对照可只核“确实无风险”）个 gold 现象（等级、证据、是否真的构成风险），复核后把 `provenance` 改为 `gold-reviewed`；
  2. 请用户确认另外 10 份合同是否存在；若确实只有 50 份，全部文档与答辩统一按 50 份表述；
  3. 留出集累计已 40 份，但**可对外报数的只有 holdout4（12 份 / 132 个二分类对）**，置信区间仍宽；下轮修 H39 后须另写 holdout5 才能继续报数。
- **禁止**：把 `gold_contracts.json` 的检索期望当规则 gold；在主集上宣称准确率（同分布 P/R=1.0 是自证）；未复核前写“已验证准确率”。

---

## ISSUE-021 · 规则对英文条款与同义改写漏报

- **状态**：OPEN（已修两轮：`version: 4` 补英文/同义改写，`version: 5` 补三类措辞 + 保额邻近判定；**仍剩 1 个漏报 H39**）
- **优先级**：P1（当前最大的泛化风险）
- **第 1 步已完成（2026-10-27 第 3 轮，规则 `version: 4`）**：
  1. `R-DIS-003`/`R-DIS-004` 增英文分支（`arbitrat…\\s+or\\s+…court`、`award…may/shal…file/litigate/appeal…court`），且刻意排除“裁决可在法院执行 / 可撤销”这类正常条款；
  2. `R-INC-001` 增“海运费及订舱费用**由卖方承担**”“卖方承担…主运费”“freight … paid by the seller”三种语序，并**不收**“出口报关费用由卖方承担”（本就应由卖方负担）；
  3. `R-INS-001`/`R-INP-002` 补英文（`insure/insured`、`insure … for 110% of the invoice value`、`N hours … inspect/notify`）；
  4. `tests/test_rules.py` 新增 6 个英文/同义改写正反 fixture + 2 个回归测试。
- **第 2 步已完成（2026-10-27 第 4 轮，规则 `version: 5`；ADR-011 第 4 轮补充）**：
  | 对象 | 缺陷（holdout3 暴露） | 修法 |
  |---|---|---|
  | `R-DIS-003` 中文分支 | 只认“或 / 或者”，漏掉“**亦可 / 也可以 / 仍有权 / 有权 / 可选择**”（H21） | 并列连接词扩表 |
  | `R-INC-001` | 要求“卖方承担/预付/支付”紧邻，漏掉“卖方**负责/须/将**支付…运费”（H22/H40） | 允许情态词插入，间隔上限 12→14 |
  | `R-INP-002` | 只认阿拉伯数字，漏掉“**thirty-six (36)** hours”“**Twelve (12)** hours”（H24/H33） | 英文数词 + 括号数字，并补“动词在前、期限在后”的反向语序 |
  | `R-INS-001` | 保额判定是**全文级** `none_of`，任意“X% of the contract price”（如付款 40%）都会压制本规则 | 改为**保险语境邻近**（保险关键字 ±60 / 反向 ±40 字符，同句内），**不引入 DSL 新条件类型** |
- **修复的两处真实缺陷（holdout2 暴露，第 3 轮）**：
  | 缺陷 | 现象 | 修复 |
  |---|---|---|
  | 子串误命中 | `contains_any: [CIF, CIP]` 命中 “Pa**cif**ic / speci**fic**ation” → H13 误报 | 四条术语规则改用“前后非英文字母”边界（允许“FOB上海”） |
  | 距离窗口截断 | `R-INC-001` 200 字符窗口被“Freight and Charges”小标题吃掉 → H19 漏报 | 窗口放宽到 260，实测距离写进注释 |
- **当前指标口径（四批样本分工见 ADR-011 第 4 轮补充）**：
  | 样本 | 份数 | 结果 | 可否对外报数 |
  |---|---|---|---|
  | `data/contracts`（C01–C50） | 50 | TP=11 FP=0 FN=0（同分布，规则 version 5 无回归） | ❌ 回归守卫 |
  | `holdout`（H01–H08） | 8 | 修复后 TP=7 FP=0 FN=0 | ❌ 已消耗 |
  | `holdout2`（H09–H20） | 12 | 修复前 TP=8 FP=1 FN=1（P=R=0.889）；修复后 9/0/0 | ❌ 已消耗，回归守卫 |
  | `holdout3`（H21–H28） | 8 | 修复前 4/0/3（R=0.571）；**修复后 7/0/0** | ❌ 已消耗，回归守卫 |
  | **`holdout4`（H29–H40）** | 12 | **TP=8 FP=0 FN=1 → P=1.00 / R=0.889 / F1=0.941**，等级一致率 1.00 | ✅ 当前唯一可用 |
- **holdout4 暴露的 1 个漏报（本轮**故意不修**，下轮做）**：
  合同 H39：`The arbitral award shall be final, but either party may, within 30 days after the award is issued, commence proceedings before the High Court …`。`R-DIS-004` 英文分支要求 `may|shall` 后**紧跟**动作动词，此处 modal 与动词之间插入了时间状语。修法：把 modal 与动词之间放宽为 `[^.]{0,80}?`。
  按纪律本轮不修——holdout4 是唯一报数集，修完再引用它的结果就是“用测试集调参”。`tests/test_rules.py::test_holdout4_hits_are_stable` 里已用断言钉住“H39 必须是漏报”，修好那天测试会失败，强制作者更新期望集合、降级 holdout4、另写 holdout5。
- **下一步（下轮）**：
  1. 修 H39（modal 与动词之间允许时间状语），**另写 holdout5（8–12 份）** 再报数，对外数字只引用 holdout5；
  2. 若要做“英文合同”专项，建议另建 5–8 份**纯英文**合同（当前留出集是中英混排）；
  3. 保额邻近窗口是启发式（60/40 字符），如遇跨句/长条款写法仍可能失效，需在 holdout5 里继续覆盖。
- **影响**：英文合同（外贸主力场景）的检出率；对外指标的可信度。

---

## ISSUE-022 · 主区两屏：交互无自动化测试、待确认态依赖审批载荷口径

- **状态**：OPEN
- **优先级**：P2
- **背景**：界面轮 2 曾把主区做成 B 端审查工作台（6 步流水线 + 规则目录 + KPI + 抽取要素）；界面轮 4 按用户要求把主区收成“上传 → 风险点”两屏，删除规则集视图与 `/api/rules` 消费，但**侧栏/顶栏导航壳保留**（用户明确要求）；界面轮 5 把输入区改成对话式（审查重点 / 附件 / Skill）；界面轮 6 把仓库入口收到侧栏、“当前审查”改成可折叠的“审查历史”子目录（改名 / 置顶 / 删除），并铺满屏幕、给登录弹窗定高。
- **问题**：
  1. 项目禁止 npm/前端框架，因此没有 Playwright/Vitest 一类工具；`tests/test_web.py` 只能做静态断言（入口与静态资源 200、无外链、本地字体 `font/*` + OFL、不判级/不拼 `Command`、页面无工作台内容、待确认先展示规则风险、Skill 下拉末项为仓库、历史子目录有改名/置顶/删除、同意默认不勾选、弹窗 `min-height`）；
  2. 真正的交互（拖拽上传、换文件、窄屏抽屉开合、确认/拒绝、刷新 `#/review/{id}` 恢复、历史记录改名/置顶/删除、登录/注册切换后的等高）目前只靠真实浏览器（Edge headless 截图 + 零依赖 CDP 脚本）手工冒烟，脚本不入 CI；
  3. 待确认页渲染的是 `ReviewSummary.approval`（只含 red、quotes、citations），而完整报告在确认后才生成：页面必须区分两种数据源，否则会退化成“0 处风险 + 请确认”；
  4. 历史列表只取 `limit=20`，没有分页/搜索/滚动加载，记录多了以后只能看到最近 20 条；
  5. Skill 仓库页一次性渲染（7 个推荐 + 自建），没有搜索/分页；自建 Skill 已支持编辑（`PATCH /api/skills/{id}`，界面轮 9），推荐 Skill 只读、只能“存为我的”；
  6. Markdown 批量导入的约束（单次 30 个、单文件 200 KB、同名跳过、超长截断）**只在前端执行**：服务端仍只校验三字段长度，绕过页面直接 `POST /api/skills` 可以提交任意多次；导入也不做内容扫描（`.md` 写什么都按文本收下），只靠 `<untrusted_focus>` 与系统提示约束解释模型。
  7. 个人账户的“清空审查记录”没有批量接口，由前端先 `GET /api/reviews?limit=500` 再逐条 `DELETE`：记录上限 20 条时可用，分页/记录变多后会出现“清到一半失败”的中间态。
  8. 账户设置的“通用”只做**前端偏好**（主题色 / 字号 / 动效 / 自动聚焦，`localStorage`），服务端没有用户设置表；“数据管理”的两张统计卡是打开面板时按需拉 `GET /api/reviews?limit=500` 并在前端数自建 Skill，没有统计接口；界面轮 10 的分区弹窗（tab/tabpanel、↑↓ 切换、760×560 与 480px 横向导航）仍只靠 CDP 手工冒烟。
- **默认建议**：
  - 用零依赖的 CDP 脚本写一到两条**冒烟回归**：上传 C47 → 出现 3 条红 → approve → 报告出现全部风险与下载链接；再覆盖“历史改名 / 置顶 / 删除”；脚本放在 `scripts/smoke_web.mjs`，不进 CI 阻塞；
  - `approval` 若新增字段（如 yellow 预览），必须同时改 `app/schemas.py`、`tests/test_web.py` 与 `renderApproval`，保持“页面只渲染后端结论”；
  - 历史列表要扩容时，先给 `GET /api/reviews` 加 `offset`（或游标）再改前端，不把 200 条一次性塞进 DOM；Skill 仓库页同理，先加 `GET /api/skills` 的搜索/分页（自建编辑已落地，复用 `_clean_skill_fields()` 的校验，指令长度上限不变）。
  - 若未来确需批量审查/趋势图，仍须遵守无框架约束（手写 SVG），不得引入图表库。
  - 导入侧若要做服务端约束，先加 `POST /api/skills` 的**每账号配额**（例如 50 个）与速率限制，再考虑服务端解析 Markdown；不要为了“校验导入”把原文件落盘。
  - “清空所有记录”建议后续加 `DELETE /api/reviews?all=1`（服务端事务内批量删），前端只发一次请求；批量接口落地前，不要在确认文案里承诺“一条都不会留”。
- **证据**：`app/web/app.js`、`app/web/index.html`、`tests/test_web.py`、`tests/test_accounts.py`、`app/schemas.py`（`ApprovalPayload`）、ADR-009 第 5 轮补充、ADR-013 第 2/4/5 轮补充。

---

## ISSUE-023 · 文档类型闸门的边界：召回优先、非中英合同可能误拒、阈值需真实语料调参

- **状态**：OPEN
- **优先级**：P1
- **背景**：界面轮 3 新增 `precheck_document`（`app/services/document_type.py::classify_document`，ADR-012），在上传后先判断“是不是合同”，不是则 `status=not_contract` 直接出“未执行审查”报告。
- **问题**：
  1. **召回优先（宁可放过不误杀）**：评分阈值 4 是启发式，一份“抬头像合同、正文其实是产品说明书/招标文件”的材料可能被放行，进入切分与规则判级；
  2. **语言覆盖**：身份信号词表只有中文与英文（卖方/买方、Seller/Buyer、Sales Contract），日文、德文、法文合同可能因识别不到身份信号被误拒为“不是合同”；
  3. **扫描件/OCR**：无可提取文本时按“正文去空白 < 120 字”判否，只能提示用户提供可复制文本，本身无法判断内容；
  4. **只判“是不是合同”**：不区分合同类型（国际货物销售 / 国内买卖 / 服务合同），所有通过的文档都按同一套 13 条外贸规则审查；
  5. **阈值与词表缺少真实语料校准**：目前只有 90 份模拟合同 + 论文/法规各一份真实样本，误拒率与误放率都没有统计口径。
- **默认建议**：
  - 收集真实上传失败案例（尤其是“像合同的非合同”）作为 `data/eval` 的闸门评测集，分别统计**误拒率**（真实合同被判否）与**误放率**，两者口径分开报；
  - 语言扩展按需加词表（德/法/日），但保持“召回优先”，不要为了提高精度而把阈值抬到 5；
  - 若未来引入合同类型字段，应作为 `DocumentCheck` 的**附加信息**，不得改变“规则唯一判级”与“闸门不判风险”的边界；
  - 扫描件 OCR 仍属 DEFERRED，闸门只负责明确提示，不猜测内容。
- **证据**：`app/services/document_type.py`、`app/nodes/precheck.py`、`tests/test_document_type.py`、ADR-012、交接文档已知坑 88–91。

---

## ISSUE-024 · 主区不再展示规则目录，用户无法自助理解“覆盖到哪”

- **状态**：OPEN
- **优先级**：P2
- **背景**：界面轮 4 删除了 `#/rules` 规则集视图（含侧栏入口），主区只剩上传与风险点；规则覆盖范围、抽取状态、解释来源、limitations 都只在 Markdown 报告里。
- **问题**：用户看到“没有发现规则覆盖的风险点”时，容易理解成“合同没问题”，而真实含义是“13 条规则没命中”；页面上没有任何入口解释这一点。
- **默认建议**：
  1. 结果页在“没有发现风险”这一支加一条说明链接（“这份报告怎么读”），展开后只放：规则覆盖范围、未覆盖主题、抽取值只做辅助；不要新增主区视图；
  2. 说明内容从后端 `ReviewReport.limitations` 渲染，避免前端写死文案与后端漂移；
  3. 规则目录接口 `GET /api/rules` 继续保留给第三方与 `/docs`，页面不消费。
- **证据**：`app/web/app.js`（空结果分支）、`app/nodes/report.py`（`limitations`）、ADR-009 第 5 轮补充“代价与边界”。

---

## ISSUE-025 · 账号与密钥的运维边界

- **状态**：OPEN
- **优先级**：P1
- **背景**：界面轮 5 按 ADR-013 落地账号、审查记录、Skill 仓库与 BYOK：本地 SQLite（`users/sessions/skills/llm_configs/review_records`）、PBKDF2 口令、哈希会话、密文盒 API Key（`.data/secret.key`）、按 `review_id` 注册 `LLMRuntime`。
- **问题**（都是“演示可用、上生产要先补”的边界）：
  1. **无找回密码 / 无邮箱验证**：口令忘了只能手工改库；
  2. **无登录限流 / 验证码**：本地演示可接受，公网会被撞库；
  3. **主密钥与库必须一起备份**：只备份 `app.sqlite` 不备份 `secret.key`，已存 Key 无法解密（会提示重新填写）；
  4. **Cookie 未加 `Secure`**：本地 `http://127.0.0.1` 演示；上 HTTPS 应由反向代理补 `Secure`（`SameSite=Lax` + `HttpOnly` 已在）；
  5. **多 worker 不共享运行时**：`_RUNTIME` 是进程内字典，多 worker 时 `resume` 可能取不到该次审查的用户模型，会退到环境默认（等级不受影响，只是解释用错模型）；与 ISSUE-019 同源；
  6. **同意条款不留痕**：界面轮 6 要求登录/注册必须手勾“同意隐私条款与使用政策”（默认不勾选），但后端只收到邮箱与口令，**没有记录 `consent_version` / `consent_at`**，审计上无法证明用户同意过哪一版条款；
  7. **删记录只清本机痕迹**：`DELETE /api/reviews/{id}` 删索引行 + pending + checkpoint + 上传目录，但若以后接了外部存储/日志，这些地方还没有对应的清理入口。
  8. **外观偏好不随账号走**：主题色 / 字号 / 动效 / 自动聚焦只写 `localStorage`，换设备或换浏览器即回默认；也没有“跟随系统 / 强制浅色 / 强制深色”的手动深色开关（界面轮 10）。
- **默认建议**：
  1. 演示形态保持现状，对外说明“本地单机、单 worker、无找回密码”；
  2. 真要上线：口令重置走管理员命令行脚本；登录失败按 IP+邮箱计数；反向代理加 TLS 与 `Secure`；多 worker 前把 `LLMRuntime` 落库（不含明文 Key，存密文）或在同一 worker 内粘性路由；
  3. 备份脚本一并复制 `.data/app.sqlite` 与 `.data/secret.key`，并在文档里写明“缺一不可”；
  4. 同意条款要留痕：在 `users`（或独立的 `consents` 表）记 `consent_version` + `consent_at` + IP，注册/登录请求体带 `consent` 布尔并在服务端校验，前端弹窗每次打开都复位为未勾选；
  5. 偏好若要做跨设备同步：加 `user_settings` 表（`owner_id` + `theme` / `font` / `motion` / `autofocus`）与 `GET|PATCH /api/auth/preferences`，前端先读本机、再以服务端为准；深色开关则新增 `data-scheme` 三态并把深色变量抽成独立一套。
- **证据**：`app/services/accounts.py`、`app/services/secret_box.py`、`app/services/llm.py`（`_RUNTIME` / `review_llm_scope`）、`app/api.py`（`/api/reviews` 的 PATCH / DELETE）、ADR-013「代价 / 已知边界」与第 2 轮补充。

---

## ISSUE-026 · 开发服务未开 `--reload`，运行中的进程可能落后于代码

- **状态**：OPEN
- **优先级**：P2
- **背景**：界面轮 8 用户报“注册显示 not found”。排查发现 8000 端口是界面轮 3 时启动的进程（`/openapi.json` 的 `info.version = 0.9.0`，只有 `/api/reviews`、`/api/rules`、`/health`），当前代码已是 1.0.0 且有 `/api/auth/*`；前端 `POST /api/auth/register` 因此命中不存在的路由 → FastAPI 返回 404 `{"detail":"Not Found"}` → 弹窗原样显示 “Not Found”。
- **问题**：
  1. 启动命令是 `uvicorn app.api:create_app --factory --port 8000`，**没有 `--reload`**：只要忘了重启，前端看到的就是旧接口集合，症状会伪装成“前端写错了”；
  2. 页面没有“后端版本”可见入口（界面轮 3 按要求把接口版本从侧栏移除），用户无法自查；
  3. 前端 `api()` 对 404 直接显示 `detail` 原文，FastAPI 默认就是英文 “Not Found”，可读性差。
- **默认建议**：
  - 开发时用 `.\.venv\Scripts\python.exe -m uvicorn app.api:create_app --factory --reload --port 8000`（仅本地；生产/演示仍单进程无 reload）；
  - 排障口诀写进 README 与交接文档：**先 `GET /openapi.json` 看版本，再怀疑前端**（版本应为 1.0.0）；
  - 前端可把 404 且 `detail === "Not Found"` 归一成“后端版本不匹配，请重启服务”的提示，但不要把后端路径/版本硬编码进业务文案。
- **证据**：`app/api.py`（`API_VERSION`）、`README.md`「快速开始」、`docs/devlog/04_HANDOVER.md` 已知坑 124。

---

## ISSUE-027 · 审查结果页的“流式输出”是前端时序，不是真事件流

- **状态**：OPEN
- **优先级**：P2
- **背景**：界面轮 11 用户要求“以对话框对话的形式流式输出返回审查结果和审查报告”。当前实现是：先 `POST /api/reviews`（同步跑完图，遇 HITL 暂停）拿到真实结果，再 `GET /clauses` / `/report`，最后由前端 `streamText()` 每 18ms 写 3 个字符铺开。
- **问题**：
  1. 内容真实（全部来自后端），**节奏是前端造的**；后端仍在同步阻塞，用户看动画时任务其实已经结束；
  2. 合同越大、规则越多，`POST /api/reviews` 的等待越长，期间只有一个“审查中”状态，没有真实的阶段进度（解析 / 抽取 / 判级 / 解释）；
  3. `prefs.motion` 关闭动画时整段直出，观感与“流式”完全不同——说明它本质是展示层。
- **默认建议**：
  - 若要真流式：把 `POST /api/reviews` 拆成“提交任务（返回 review_id + 202）+ 事件流”，用 SSE（`text/event-stream`，FastAPI `StreamingResponse`）按节点推 `stage` / `clause` / `finding` / `done`，前端 `EventSource` 消费；HITL 仍走 `interrupt()`，事件流只推“等待人工确认”；
  - 若要最小改动：保留前端节奏，但把文案里的“正在读取/抽取/判定”与真实 `timings` 对齐，并在任务结束后补一句“以上为已完成结果的逐条展示”；
  - 不要把前端动画当进度上报（会误导用户“还在跑”）。
- **证据**：`app/web/app.js`（`streamText` / `stopStream` / `chatNarrative`）、`app/api.py`（`POST /api/reviews` 同步）、ADR-013 第 7 轮补充第 5 条。

---

## ISSUE-028 · 退出登录只做前端拦截，后端没有“取消审查任务”接口

- **状态**：OPEN
- **优先级**：P2
- **背景**：界面轮 11 要求“审查任务进行中退出要提示会中断任务并二次确认”。当前 `hasActiveTask()`（`busy || taskActive || reviewStatus ∈ {awaiting_human, running}`）命中时弹 `#logout-confirm`，确认后前端 `stopStream()` 并清本地状态、`POST /api/auth/logout`。
- **问题**：
  1. 后端没有任何“取消/清理”的动作：checkpoint 记录仍在，`pending/<review_id>.json` 仍在，上传目录也保留；用户重新登录后该记录仍显示“待确认”；
  2. 若退出时正处在 `POST /api/reviews` 的同步阶段（浏览器会中断请求），服务端可能继续跑完写库，前端却已看不到结果；
  3. 没有“放弃这次审查”的显式语义，用户无法主动清理未完成的记录（只能事后在审查历史里删除）。
- **默认建议**：
  - 新增 `POST /api/reviews/{id}/cancel`：先取进程内同 `review_id` 的可重入锁，置 `cancelled` 标记，删除 pending 文件与上传目录，checkpoint 保留只读（不物理删，便于追溯）；已 `approved` 的记录拒绝取消（409）；
  - 前端确认退出时若 `reviewStatus ∈ {awaiting_human, running}`，调用该接口并提示“本次审查已取消”；
  - 或在“审查历史”里给未完成记录加“放弃”入口，避免依赖退出动作。
- **证据**：`app/web/app.js`（`hasActiveTask` / `doLogout` / `#logout-confirm`）、`app/review_service.py`（pending / checkpoint 生命周期）、ADR-013 第 7 轮补充第 7 条。

---

## 本阶段不处理（DEFERRED）

| 事项 | 原因 |
|---|---|
| OCR / 扫描件解析 | 超出 10 天 MVP；先用文本型 PDF/DOCX/TXT |
| 多语言 UI | Streamlit 中文界面即可 |
| 多租户 / RBAC / SSO | 本地单账号登录已实现（ADR-013）；不做组织隔离、角色权限矩阵与企业单点登录 |
| 数据库/Redis/消息队列 | 规则与报告用本地文件 + SQLite checkpointer 足够 |
| 知识图谱 / GraphRAG | RAG 已放开（ADR-007），但图数据库与实体关系抽取不在 MVP；先做 BM25/字符 n-gram 检索 |
| 向量数据库 / 外部 embedding 服务 | 增加依赖与成本；MVP 用本地词法检索即可 |
| Supervisor 判级 / 专家改级 | 违反“规则唯一判级”，永远不会做 |
| 微调模型 | 禁止训练模型；用规则 + 结构化输出 |
| Docker 部署 | 明确禁止；本地 Streamlit/FastAPI 演示 |
