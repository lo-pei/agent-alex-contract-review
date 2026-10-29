# 架构决策记录（ADR）索引

> 更新时间：2026-10-29（阶段 4 第 7 轮：ADR-011 补“第 7 轮补充”——先写中英混合 holdout7（H65–H76）+ gold，**改规则之前**跑盲测基线 `TP=7 FP=0 FN=4 TN=121` → P=1.00 / R=0.636 / F1=0.778（漏报 H65 `for the Seller's account` / H66 跨句或裁或审 / H67 中文“全部价款” / H69 `bring the matter before the courts`），随后按基线修四处写法，规则 `version: 7`→**8**，holdout7 降级为回归集，ADR-010 证据改 `version: 8`；阶段 4 第 6 轮：ADR-011 补“第 6 轮补充”——纯英文 holdout6（H53–H64）盲测基线 P=1.00 / R=0.727 / F1=0.842，随后修 `R-INC-001`（卖方付运费倒装）、`R-DIS-003`（连接词后逗号）、`R-PAY-001`（entire/full … before shipment），规则 `version: 7`，holdout6 降级为回归集；阶段 4 第 5 轮 + 界面轮 16：先写 holdout5（H41–H52）跑基线再改 `R-DIS-004`，`version: 6`；界面轮 15：检索评测 gold 两层映射 + ranking/production 双口径 + 点名条号/来源排序加权，新增 ADR-016；界面轮 14：多智能体专家并行 + 只读工具层（本地工具 / MCP），新增 ADR-015；界面轮 13：图片 PDF 本地 OCR、外部 Skill 包内置、zip 导入，新增 ADR-014；界面轮 12：配色三档 / Skill 工具与附件 / 头像裁剪 / 左原文右意见；界面轮 5：账号 / 审查记录 / Skill 仓库 / BYOK，新增 ADR-013；界面轮 4：主区两屏 + 侧栏保留；界面轮 3 + 文档类型闸门：ADR-009 第 3 轮补充、ADR-012）
> 阶段：**第三阶段代码实现已打通 CLI + FastAPI + 两屏 Web 前端（Streamlit 备用）；第四阶段进行中（规则 13 条 / `version: 8` + 三组评测指标 + 七批留出集 76 份（全部已消耗）+ 检索评测 95 题；对外数字引 holdout7 盲测基线，下一批须新写 holdout8）**
> 说明：ADR-001 ~ ADR-016 全部为“已接受”。后续如需变更，写新 ADR 并在原 ADR 标注“已替代”，不直接改写历史结论。

## 为什么需要 ADR

本项目 10 天 MVP，技术面窄但硬约束多（规则唯一判级、真 HITL、异常降级、可追溯、可测试）。把关键取舍写成一页一条的 ADR，可以避免：
- 开发中途“顺手加个 Agent/加个数据库”，破坏硬约束；
- 评审追问“为什么这样拆分”时只能临场解释；
- 新接手的人重复讨论已经定过的事。

> 2026-10-27 用户放开 RAG 与多智能体（见 ADR-007）。**放开的只是能力边界，不是判级与 HITL 的边界**：等级仍只来自 Python 规则，红色风险仍必须人工确认。

## 已产出的 ADR

| 编号 | 主题 | 状态 | 关键结论 | 文件 |
|---|---|---|---|---|
| ADR-001 | 图结构选型 | **已接受** | 确定性顺序主干 + 两个条件边 + 单一 HITL 门；不用 Supervisor/并行/单体 ReAct | [ADR-001-图结构选型.md](./ADR-001-图结构选型.md) |
| ADR-002 | HITL 实现方式 | **已接受** | 节点内 `interrupt()` + checkpointer + `Command(resume=...)`；审批前零业务写入；超时不自动通过 | [ADR-002-HITL实现方式.md](./ADR-002-HITL实现方式.md) |
| ADR-003 | 规则 / LLM 边界 | **已接受** | 规则唯一判级；LLM 只抽取 17 字段与解释；schema 禁止 `risk_level`；引文核验 + 失败兜底 | [ADR-003-规则与LLM边界.md](./ADR-003-规则与LLM边界.md) |
| ADR-004 | 状态持久化与线程模型 | **已接受** | 运行/演示用 AsyncSqliteSaver；测试用 InMemorySaver；`thread_id=review_id`；惰性超时 | [ADR-004-状态持久化与线程模型.md](./ADR-004-状态持久化与线程模型.md) |
| ADR-005 | 文档解析与证据模型 | **已接受** | pypdf + python-docx + TXT；canonical text + 页/全局偏移；`文件名:p页:start-end`；精确/空白规范化定位 | [ADR-005-文档解析与证据模型.md](./ADR-005-文档解析与证据模型.md) |
| ADR-006 | 运行环境与依赖策略 | **已接受** | Python 3.12；LangGraph 1.2.17 等最新稳定依赖；OpenAI 兼容接口；无 Docker/Redis/Postgres | [ADR-006-运行环境与依赖策略.md](./ADR-006-运行环境与依赖策略.md) |
| ADR-007 | 范围变更：RAG 与多智能体 | **已接受** | 允许 RAG/多智能体/Supervisor（仅路由）；判级、HITL、证据边界不变；默认开关关闭 | [ADR-007-范围变更-RAG与多智能体.md](./ADR-007-范围变更-RAG与多智能体.md) |
| ADR-008 | RAG MVP 与解释质量门 | **已接受（已实现）** | 本地 BM25 + 中文二元组；`source_id#section` 引用白名单；Python 质量门拦截越权表述；无命中/配置错误降级为规则解释 | [ADR-008-RAG检索与解释质量门.md](./ADR-008-RAG检索与解释质量门.md) |
| ADR-009 | API/UI 接入与 pending 持久化 | **已接受（已实现；第 2 轮补充：原生 Web 前端；第 3 轮补充：B 端工作台）** | API/UI 只依赖 `ReviewService`；pending 时间戳原子落盘 `.data/pending/`；上传后缀/大小/文件名校验；报告 Markdown 纯渲染；**第 2 轮**：`app/web/` 原生 HTML/CSS/JS 由 FastAPI 托管（无框架、无 CDN、无构建）；**第 3 轮**：按 taste-skill `app-screens` 规则重做成 B 端工作台（侧栏 + 面包屑 + sheet + 四个 hash 路由视图 + 本地 IBM Plex 字体），新增只读 `GET /api/rules`（白名单投影，不返回正则/DSL，`API_VERSION` 0.8.0），Streamlit 保留为备用 | [ADR-009-API与UI接入及待审批状态持久化.md](./ADR-009-API与UI接入及待审批状态持久化.md) |
| ADR-010 | 规则扩充与合同级评测基线 | **已接受（已实现）** | 规则 7 → 13 条（新增 6 条确定性文本规则）；新规则准入四关（DSL 可判定 / 正反 fixture / 语料命中集合可复现 / 样例零误报）；模拟合同拆入 `data/contracts/`，评测结果落 `eval/results/` | [ADR-010-规则扩充与合同级评测基线.md](./ADR-010-规则扩充与合同级评测基线.md) |
| ADR-011 | 评测方法、silver gold 与留出验证口径 | **已接受（已实现）** | gold 分三层（检索期望 / silver 规则 gold / 留出 gold）；三组指标（rule_level / contract_level / coverage）；留出集未参与规则设计，**发现漏报也不回改规则**；**留出集一旦用于定位缺陷即“已消耗”，只能作回归守卫，对外报数须换新样本**；报数纪律（样本+版本+命令+日期） | [ADR-011-评测方法silver-gold与留出验证.md](./ADR-011-评测方法silver-gold与留出验证.md) |
| ADR-012 | 上传文档类型闸门 | **已接受（已实现）** | `ingest` 后新增 `precheck_document`：确定性规则判断“是不是合同”（抬头/编号/双方/条款结构/交易要素 + 论文与法规反向信号）；否 → 直接出 `not_contract` 报告，**不切条款、不抽取、不判级、不触发 HITL**；`API_VERSION` 0.9.0 | [ADR-012-上传文档类型闸门.md](./ADR-012-上传文档类型闸门.md) |
| ADR-013 | 账号体系、审查记录、Skill 仓库与 BYOK | **已接受（已实现）** | 账号/会话/Skill/记录/模型配置落本地 SQLite（零新依赖）；口令 PBKDF2 + 会话只存 token 哈希；API Key 标准库密文盒加密、接口只回尾号；按 `review_id` 登记 `LLMRuntime` + `ContextVar` 作用域；**审查重点 / Skill 只进 `<untrusted_focus>`，不得改等级**；侧栏只留登录入口，右侧主区为对话式首屏；`API_VERSION` 1.0.0 | [ADR-013-账号体系与BYOK.md](./ADR-013-账号体系与BYOK.md) |
| ADR-014 | 图片 PDF 的本地 OCR 与外部 Skill 包 / zip 导入 | **已接受（已实现）** | 上传上限 15→30 MB（单一配置源）；**只在 PDF 无文本层时**用 `pypdfium2` + `rapidocr-onnxruntime` 本地 OCR（离线、≤20 页、逐页降级），OCR 文本只进 `raw_text`、**不参与判级**；4 个外部 Skill 包复制到 `app/resources/skills/` 作 `builtin:*`；zip 导入只读文本、根目录 `SKILL.md` 必填、**不执行包内脚本**、`allowed-tools` 不映射 | [ADR-014-图片PDF的OCR与外部Skill包.md](./ADR-014-图片PDF的OCR与外部Skill包.md) |
| ADR-015 | 多智能体专家并行 + 只读工具层（本地工具 / MCP） | **已接受（已实现）** | `validate` 之后并行跑“付款 / 交付 / 争议”三个专家，路由是确定性 Python 白名单（不是聊天式 Supervisor）；专家 schema **无 `risk_level`**、引文定位不到就丢弃；`rules` 之后插入一次 `research_tools`：4 个本地只读工具 + MCP（stdio/JSON-RPC 子集、零新依赖、`shell=False`、超时杀进程），无 LLM 时退化为确定性检索；**两个开关默认关闭，关闭时拓扑与结论和原来完全一致** | [ADR-015-多智能体专家与只读工具层.md](./ADR-015-多智能体专家与只读工具层.md) |
| ADR-016 | 检索评测与条号加权 | **已接受（已实现）** | `100问题.md` 的概念标签经“通用条号正则 + 人工 YAML”两层映射成 `source_id#section`，一个标签允许多条可接受片段（中文原文 / 英文原文 / 解读稿）；`gaps` 显式登记、**缺口不进分母**（95 / 100）；同时报 `ranking`（top-5、`min_score=0`）与 `production`（真实 `RAG_TOP_K`/`RAG_MIN_SCORE`）× `lenient` / `strict`，**禁止混读**；检索侧只做**排序加权**（点名条号 ×2.5、条文原文 ×1.1、点名来源 ×1.15），不打分新片段、不过滤、不改判级；gold 过期即失败 | [ADR-016-检索评测与条号加权.md](./ADR-016-检索评测与条号加权.md) |

## 关键设计一句话

```text
ingest → precheck(是不是合同?) ─否→ report(not_contract，不判级)
   → 是 → segment → extract(LLM) → validate
   → [AGENTS_ENABLED] → 专家并行(付款 ∥ 交付 ∥ 争议，只提候选意见) → collect
   → rules(Python，唯一判级)
   → [有 red?] → human_review(interrupt) → approve → research_tools(只读工具/MCP)?
                 → 无 red → research_tools? 
   → explain(LLM [+RAG] [+专家] [+工具]) → report
   → reject / changes / timeout → report
```

- 等级只来自 Python 规则；LLM 输出 schema（抽取/解释/专家候选/工具计划）中都没有 `risk_level`；
- 上传对象先用**确定性规则**判断是不是合同（ADR-012），不是合同就不进入判级；
- HITL 用 `interrupt()`，不是状态标记；超时只能变成 `unreviewed_red_risk`；
- 证据可定位到 `文件:页码:字符偏移`；知识引用可定位到 `source_id#section`（已实现，BM25）；
- 检索评测另有一套纪律（ADR-016）：gold 由“概念标签 + 人工映射”两层翻成真实 citation，缺口不进分母；`ranking` 与 `production`、`lenient` 与 `strict` 分开报；点名条号/来源只做**排序加权**，不打分新片段、不过滤、不碰判级；
- LLM/解析/规则失败都有降级路径，不崩溃、不静默通过；
- RAG、专家并行、工具调用默认关闭，只做解释/建议增强，不参与判级（ADR-007/008/015）；
- 交付形态：CLI（`app/graph_demo.py`）+ FastAPI（`app/api.py`）+ B 端审查工作台（`app/web/`）+ Streamlit 备用（`app/ui.py`），全部只依赖 `ReviewService`（ADR-009）。

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
