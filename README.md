# Agent Alex · 外贸合同智审助手

面向**国际货物销售合同**的 AI 预审智能体：上传合同 → 条款切分 →（可选）**付款 / 交付 / 争议三个专家并行**给参考意见（不判级）→ LLM 抽取关键要素 → **Python 规则引擎判定红/黄/绿风险**（唯一等级来源）→ 红色风险经 **LangGraph `interrupt()` 真人工确认** →（可选）**只读工具 / MCP 检索补材料** → LLM 依据规则结果与原文生成解释 → 输出可追溯报告。

> 当前处于**第四阶段（测试与评测）第 9 轮 + 界面轮 16**：主干 `ingest → precheck → segment → extract → validate → [专家并行?] → rules → [条件边] → human_review → [research_tools?] → explain_risks → report` 已全部打通，支持 **TXT / Markdown / PDF（文本型或图片型）/ DOCX** 解析（单个文件 ≤ 30 MB；图片/扫描 PDF 用本地 OCR 补文本，**OCR 只产文本、不参与判级**）、**先判断上传对象是不是合同**（论文/法规直接拒绝，不进入判级）、标题式条款切分、LLM 17 字段要素抽取与 Python 引文校验，**13 条规则**（11 条文本 + 2 条字段，`version: 9` 已覆盖中文与主要英文写法，保额判定改为“保险语境邻近”，裁决类允许情态动词与动作之间插时间状语，并补了英文“卖方付运费”倒装、`or,` 连接词、`entire … before shipment`、卖方账上运费迂回语态（`for/on the Seller's account`）、跨句或裁或审（含 `refer the dispute to the courts`）、中文“全部价款 / 收全款再发货”、“对裁决不服向法院上诉”、“立即检验 / 当日通知”），红色风险触发 **LangGraph `interrupt()` 真暂停**，经 `Command(resume=...)` 恢复后由 LLM 生成**带原文与知识引用**的解释。**界面轮 14 按 ADR-015 加了可选 Agent 层**：`AGENTS_ENABLED` 打开后三个专家并行出“值得注意的点 + 修改方向 + 原文引文”（schema 无 `risk_level`、引文定位不到即丢弃），`TOOLS_ENABLED` 打开后在规则之后跑一次只读工具规划（4 个本地工具 + MCP stdio/JSON-RPC 子集，无 Key 走确定性检索）；**两个开关默认关闭，关闭时链路与结论和原来逐字一致**。交付入口：**极简 C 端页“上传合同 → 看风险点”（FastAPI 托管）+ CLI + API；Streamlit 保留为备用界面**；Skill 仓库内置 **11 个**（含 4 个外部包 `builtin:*`），支持 Markdown / 文件夹 / **zip 包**导入（只读、不执行），结果页可切左栏“原文全文”看完整原文、右栏看到“参考 · 专家”与折叠的“Agent 轨迹”，并有两处“**这份报告怎么读**”导读（七节静态说明 + 后端 `limitations` 补第八节）。评测：50 份模拟合同 + 21 个 silver gold 现象 + **九批留出集 100 份（八批 88 份已消耗，仅 holdout9 未消耗）**；**当前对外数字只引 holdout9（中英混合）在 `version: 9` 规则上、当作盲测集跑出的基线**：规则级 **P=1.00 / R=0.545 / F1=0.706**（12 份 / 11 个现象，**漏报 H89/H90/H91/H92/H93 尚未修**；silver gold 待人工复核）；holdout8 的基线 `P=1.00 / R=0.545 / F1=0.706`（H77/H78/H79/H80/H83 已在 `version: 9` 修好，修后 `11/0/0` 只作回归）、holdout7 的 `P=1.00 / R=0.636 / F1=0.778`、holdout6 的 `P=1.00 / R=0.727 / F1=0.842`、holdout5 的 `P=1.00 / R=0.90 / F1=0.947` 作为历史记录保留；**再下一批对外数字须先写 holdout10**；**检索评测按 ADR-016 落地**：100 题 → **95 题可评测**（5 题语料未覆盖，不进分母），ranking `lenient` R@3 **0.958** / `strict` R@3 **0.758**（点名条号/来源加权后）。详见 [`docs/devlog/00_PROJECT_STATE.md`](docs/devlog/00_PROJECT_STATE.md)。

> 代码仓库：<https://github.com/lo-pei/agent-alex-contract-review>（private，默认分支 `master`）。本机 `github.com:443` 被网络拦截，推送走 `ssh.github.com:443` + 仓库 Deploy Key（见 [`docs/devlog/04_HANDOVER.md`](docs/devlog/04_HANDOVER.md) §3.1）。

> 上传先过“文档类型闸门”（ADR-012）：抬头 / 合同编号 / 买卖双方 / 条款结构 / 交易要素打分，叠加论文与法规的反向信号；判否时状态为 `not_contract`，只出“未执行审查”的报告，**不切条款、不抽取、不判级、不触发人工确认**。

## 当前完成度

| 阶段 | 状态 | 说明 |
|---|---|---|
| 1. GitHub 调研 | ✅ | 8 个开源项目源码级分析，产出借鉴/不借鉴清单 |
| 2. 架构设计 | ✅ | ADR-001 ~ ADR-016 全部已接受 |
| 3. 代码实现 | ✅ 第 6 步 + 界面轮 16 | 环境、13 节点图（含文档类型闸门、3 个并行专家、`research_tools`）、规则引擎（13 条规则，`version: 9`）、PDF（文本型 + 图片型 OCR）/DOCX/TXT 解析（≤30 MB）、标题切分、LLM 抽取 + 引文校验、HITL 真中断/恢复、LLM 解释 + Python 质量门、本地 BM25 RAG（默认关闭；本机 `.env` 已开启，真实语料 14 篇：模型不可用时解释回退规则理由，但仍列出检索到的 `source_id#section`；**点名条号/来源只改排序、不改判级**）、**多智能体专家并行 + 只读工具层（本地 4 个工具 + MCP stdio，默认关闭）**、FastAPI + 两屏 Web 前端（同一行标签 + 左栏“条款目录 / 原文全文” + 右栏意见，三块各自滚动；规则意见下有“参考 · 专家”中性色区块 + 折叠的 Agent 轨迹；结果页两处“这份报告怎么读”导读）+ 账号/审查历史（改名/置顶/删除，**一次请求清空**）/Skill 仓库独立页（内置 11 个、Markdown/文件夹/zip 导入、查看与编辑、可声明工具 + 只读附件）/账户设置（B 端分区：个人信息 / 通用（白天·黑夜·跟随系统 + 字号三档）/ 数据管理 / 关于）/BYOK（20 个厂商）+ Streamlit、**405 个测试** |
| 4. 测试与评测 | ⏳ 第 9 轮完成 + 检索评测 | 50 份模拟合同 + 21 个 silver gold 现象 + **九批留出集 100 份（八批 88 份已消耗，仅 holdout9 未消耗）**；三组指标（rule/contract/coverage）；**holdout9（中英混合）盲测基线（规则 `version: 9`）P=1.00 / R=0.545 / F1=0.706**，漏报 H89/H90/H91/H92/H93 **尚未修**（修完后 holdout9 降级，新数字须先写 holdout10）；holdout8 基线 P=1.00 / R=0.545 / F1=0.706（H77/H78/H79/H80/H83 已在 `version: 9` 修好，修后 11/0/0 只作回归）、holdout7 基线 P=1.00 / R=0.636 / F1=0.778（H65/H66/H67/H69 已在 `version: 8` 修好）、holdout6 基线 P=1.00 / R=0.727 / F1=0.842、holdout5 基线 P=1.00 / R=0.90 / F1=0.947 留作历史记录；silver gold 待人工复核；**检索评测已落地（ADR-016）**：95 题可评测、ranking/production × lenient/strict，lenient R@3 0.958 / strict R@3 0.758；剩 4 题语义指代（ISSUE-033） |
| 5. 文档与交付 | ⏳ 进行中 | 开发日志、ADR、交接文档、评测结果与 RAG 资料清单已建立 |

## 技术栈

- Python **3.12**（`开发提示词.md` 原写 3.9+，但 Streamlit 1.66.1 要求 ≥3.11，LangGraph 1.2 要求 ≥3.10；决策见 [ADR-006](docs/devlog/02_ARCHITECTURE_DECISIONS/ADR-006-运行环境与依赖策略.md)）
- LangGraph 1.2.17 + LangChain 1.4.7（含 `langgraph-checkpoint-sqlite`）
- Pydantic 2.14（结构化输出与状态契约）
- FastAPI 0.162 + Uvicorn 0.54（本地 HTTP 接口）
- 两屏 Web 页面（原生 HTML/CSS/JS，零依赖、零构建、零 CDN；由 FastAPI 托管；字体随包离线）
- **本地 OCR**：`pypdfium2`（PDF → 图）+ `rapidocr-onnxruntime`（PP-OCR 的离线 ONNX 版，模型随包、**不联网**），只在 PDF 无文本层时兜底
- 本地 SQLite：checkpoint、账号/会话/Skill/模型配置/审查记录（标准库 `sqlite3`，无新依赖）
- Streamlit 1.66（备用界面）
- **允许但默认关闭**：RAG 知识检索、多智能体专家节点（ADR-007/015，`RAG_ENABLED=false` / `AGENTS_ENABLED=false`）；只读工具层与 **MCP stdio 客户端**（`TOOLS_ENABLED=false`，手写 JSON-RPC 子集，**零新依赖**、不引入 `mcp` SDK）
- 不使用：训练模型、Docker、前端框架、Neo4j/GraphRAG、向量数据库、Postgres/Redis

## 快速开始

```powershell
# 1) 创建虚拟环境（必须用 3.12，不要用系统默认 python）
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

# 2) 运行全链路（无需 Key：抽取会自动降级；字段规则标记跳过）
.\.venv\Scripts\python.exe -m app.graph_demo
# 含红色风险 → 图会停在人工确认，打印审批载荷 + review_id + 恢复命令

.\.venv\Scripts\python.exe -m app.graph_demo data\samples\sample_clean_contract.txt
# 无红色风险 → 快速通道，直接完成

.\.venv\Scripts\python.exe -m app.graph_demo --json

# 3) 恢复人工决定（SQLite 默认持久化，可跨进程）
.\.venv\Scripts\python.exe -m app.graph_demo --review-id <review_id> --decision approve --reviewer zhangsan --comment "已核对"
.\.venv\Scripts\python.exe -m app.graph_demo --review-id <review_id> --decision reject --reviewer zhangsan
.\.venv\Scripts\python.exe -m app.graph_demo --review-id <review_id> --decision timeout
# 超时/拒绝都不会变成通过；已终态再次恢复是幂等的

# 4) FastAPI + 两屏页面（默认 SQLite checkpointer + 本地账号库；单 worker 演示）
.\.venv\Scripts\python.exe -m uvicorn app.api:create_app --factory --port 8000
# 打开 http://127.0.0.1:8000/      首屏：给审查重点 + 合同 + Skill → 风险点（#/ → #/review/{id}）
# 打开 http://127.0.0.1:8000/#/skills  Skill 仓库（推荐 / 我的 / 新建 / 从 Markdown 或 zip 包导入）
# ⚠️ 改了后端代码必须重启这条 uvicorn（没有 --reload）；旧进程可能只有 /api/reviews，
#    前端点“注册”就会看到 not found —— 用 curl http://127.0.0.1:8000/openapi.json 看版本应为 1.1.0
# 打开 http://127.0.0.1:8000/docs  Swagger UI，可直接试接口：
#   POST /api/reviews（multipart：file + focus + skill_id + 可选 reference）→ awaiting_human=true
#   POST /api/reviews/{id}/decisions  {"action":"approve","reviewer":"zhangsan"}
#   GET  /api/reviews/{id}/report?format=json|markdown
#   账号：POST /api/auth/register|login、POST /api/auth/logout、GET /api/auth/me、PATCH /api/auth/profile（昵称 / 头像）
#   记录：GET /api/reviews（需登录；未登录 401；跨账号 404）
#   记录运维：PATCH /api/reviews/{id}（title / pinned，空串恢复文件名）、DELETE /api/reviews/{id}（204，连带清 pending/checkpoint/上传目录）
#   清空全部：DELETE /api/reviews（一次事务只删本账号记录，返回 {"deleted": N}，顺带清 checkpoint 与上传目录）
#   Skill：GET /api/skills（未登录只给内置 11 个）、POST /api/skills、PATCH /api/skills/{id}（自建；推荐只读）、DELETE /api/skills/{id}
#   Skill 包：POST /api/skills/import（multipart：file=*.zip，需登录 → 201 {skill, warnings, files}；根目录必须有 SKILL.md，包内脚本不执行）
#   BYOK：GET /api/llm/providers、GET|PUT|DELETE /api/llm（只回 has_key + 尾号）、POST /api/llm/test
#   GET  /api/rules                  规则目录（只读；13 条，不返回正则/DSL；页面不再消费）
#   GET  /health                     版本 / checkpoint / rag_enabled / agents_enabled / tools_enabled

# 5) Streamlit 界面（备用/内网演示；与页面共用同一套 ReviewService）
.\.venv\Scripts\python.exe -m streamlit run app/ui.py
# 上传 → 开始审查 → 查看审批载荷 → 批准/要求修改/拒绝/标记超时 → 下载 JSON/Markdown

# 6) 测试与静态检查
.\.venv\Scripts\python.exe -m pytest
# 405 passed
.\.venv\Scripts\python.exe -m ruff check .
# All checks passed!

# 7) 规则级评测（不调用 LLM，不需要 Key）
.\.venv\Scripts\python.exe eval\prepare_contracts.py
# 50 份模拟合同 → data/contracts/；105 条映射 → data/eval/gold_contracts.json
.\.venv\Scripts\python.exe eval\run_eval.py
# 主集 50 份：命中 11 份；规则级 TP=11 FP=0 FN=0（同分布，仅作回归守卫）
# 合同级 P=1.00 R=0.79；覆盖率 21 个 gold 现象中 11 个有规则（0.5238）

# 8) 留出集评测——对外报数只引“改规则之前”的盲测基线
# ① holdout9（H89–H100，12 份中英混合 / 11 个现象）：**当前唯一对外数字，只引基线文件**
.\.venv\Scripts\python.exe eval\run_eval.py --contracts data\contracts_holdout9 `
  --gold data\eval\gold_holdout9.json --gold-rules data\eval\gold_holdout9.json --tag holdout9-baseline
# 规则 version 9 下跑出（非本批设计来源，唯一可对外引用）：TP=6 FP=0 FN=5 → P=1.00 R=0.545 F1=0.706
# 漏报 H89（FOB 下“The price is inclusive of all freight charges up to Jebel Ali”）、
# H90（“Either party may instead elect to have any dispute decided by the courts of Singapore”）、
# H91（中文“全部合同价款一次性汇入…确认收款后方可发运”）、H92（“向有管辖权的人民法院请求重新审理”）、
# H93（检验期限写成中文数字“二十四小时”）
# 五处**尚未修**：按基线修完（version 10）后 holdout9 即降级，新数字须先写 holdout10

# ② holdout8（H77–H88，12 份中英混合 / 11 个现象）——历史基线，第 9 轮已消耗
.\.venv\Scripts\python.exe eval\run_eval.py --contracts data\contracts_holdout8 `
  --gold data\eval\gold_holdout8.json --gold-rules data\eval\gold_holdout8.json --tag holdout8-baseline
# 规则 version 8 下跑出：TP=6 FP=0 FN=5 → P=1.00 R=0.545 F1=0.706
# 漏报 H77（“The ocean freight … is on the Seller's account”介词短语）、H78（“refer the dispute to the courts”）、
# H79（中文“七个工作日内付清全部货款”）、H80（“仲裁庭的裁决…收到裁决书之日起…提起上诉”）、H83（“inspect … immediately upon discharge”）
# 五处已在 version 9 修好（--tag holdout8-v9 得 11/0/0，只作回归守卫，不再对外引用）

# ③ holdout7（H65–H76，12 份中英混合 / 11 个现象）——历史基线，第 7 轮已消耗
.\.venv\Scripts\python.exe eval\run_eval.py --contracts data\contracts_holdout7 `
  --gold data\eval\gold_holdout7.json --gold-rules data\eval\gold_holdout7.json --tag holdout7-baseline
# 规则 version 7 下跑出：TP=7 FP=0 FN=4 → P=1.00 R=0.636 F1=0.778
# 漏报 H65（“the ocean freight … shall be for the Seller's account”）、H66（仲裁句与法院句分属两句）、
# H67（中文“装运前一次性支付合同项下全部价款”）、H69（“bring the matter before the courts”）
# 四处已在 version 8 修好（--tag holdout7-v8 得 11/0/0，只作回归守卫，不再对外引用）

# ③ holdout6（H53–H64，12 份纯英文 / 11 个现象）——历史基线，第 6 轮已消耗
.\.venv\Scripts\python.exe eval\run_eval.py --contracts data\contracts_holdout6 `
  --gold data\eval\gold_holdout6.json --gold-rules data\eval\gold_holdout6.json --tag holdout6-baseline
# 改规则之前跑出：TP=8 FP=0 FN=3 → P=1.00 R=0.727 F1=0.842；漏报 H53（FOB 下卖方付运费倒装）、
# H55（“or, at the Buyer's option, by proceedings …”）、H61（“pay the entire contract price before shipment”）
# 三处已在 version 7 修好，修后 11/0/0 只作回归

# ④ holdout5（H41–H52，12 份 / 10 个现象）——历史基线，第 5 轮已消耗
.\.venv\Scripts\python.exe eval\run_eval.py --contracts data\contracts_holdout5 `
  --gold data\eval\gold_holdout5.json --gold-rules data\eval\gold_holdout5.json --tag holdout5
# 基线曾是 TP=9 FP=0 FN=1 → P=1.00 R=0.90 F1=0.947（漏报 H41，version 6 已修）

# ⑤ 已消耗样本（holdout4 / holdout3 / holdout2 / holdout）：只作回归守卫，不得对外报数
.\.venv\Scripts\python.exe eval\run_eval.py --contracts data\contracts_holdout4 `
  --gold data\eval\gold_holdout4.json --gold-rules data\eval\gold_holdout4.json --tag holdout4
# 修 H39 后 TP=9 FP=0 FN=0（已消耗 → 回归结果，不是泛化证据）
.\.venv\Scripts\python.exe eval\run_eval.py --contracts data\contracts_holdout3 `
  --gold data\eval\gold_holdout3.json --gold-rules data\eval\gold_holdout3.json --tag holdout3
# 修完三类措辞后 TP=7 FP=0 FN=0（已消耗 → 回归结果，不是泛化证据）
.\.venv\Scripts\python.exe eval\run_eval.py --contracts data\contracts_holdout `
  --gold data\eval\gold_holdout.json --gold-rules data\eval\gold_holdout.json --tag holdout
# 修复 H01/H03 后 TP=7 FP=0 FN=0（同样只作回归守卫）
.\.venv\Scripts\python.exe eval\run_eval.py --contracts data\contracts_holdout2 `
  --gold data\eval\gold_holdout2.json --gold-rules data\eval\gold_holdout2.json --tag holdout2
# 12 份：TP=9 FP=0 FN=0 TN=123（修掉子串误命中与窗口截断后）

# 想再提升规则泛化：先按 holdout9 基线修那五处（version 10），再写 holdout10（8–12 份，换语种/版式）重跑基线，不要直接调权重或放宽正则

# 9) 检索评测（不调用 LLM，不需要 Key；ADR-016）
# ① 题目或语料一变，必须重建 gold（否则 pytest 的 gold 过期守卫会失败）
.\.venv\Scripts\python.exe -m eval.rag_gold --write
# 100 题 → 95 题可评测（5 题语料未覆盖：#42/#69/#86/#87/#88），写 data/eval/gold_rag.json

# ② 同时报两套口径：ranking（top-5 不过阈值）与 production（RAG_TOP_K=3 / RAG_MIN_SCORE=1.0）
.\.venv\Scripts\python.exe -m eval.run_rag_eval
# ranking lenient  R@1 0.747 / R@3 0.958 / R@5 0.979 / MRR 0.849
# ranking strict   R@1 0.305 / R@3 0.758 / R@5 0.821 / MRR 0.524
# 结果文件：eval/results/rag-20261028.json（含语料 chunk_count 与两个阈值）
# 报数纪律：必须同时说明“哪套口径 + 哪个子集”，不能写成“线上召回率”
```

环境变量：复制 `.env.example` 为 `.env` 后填写。**不要提交真实 Key**（`.env` 已在 `.gitignore`）。

配置 `LLM_API_KEY`（任意 OpenAI 兼容端点）后，同一命令会自动启用真实要素抽取；不配置时走降级路径，报告会写明“要素抽取未完整执行”并跳过字段规则。页面里还可以**按账号**填 Key（厂商目录 + 密文落库，只回尾号），优先级：本次审查的用户配置 → 环境默认 → 降级。

```text
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=
LLM_MODEL=gpt-4.1-mini
LLM_TIMEOUT_SECONDS=60
LLM_MAX_REPAIR_RETRIES=1
MAX_EXTRACT_CLAUSES=40
CHECKPOINT_BACKEND=sqlite
CHECKPOINT_SQLITE_PATH=.data/checkpoints.sqlite
HITL_TIMEOUT_MINUTES=30
PENDING_DIR=.data/pending
UPLOAD_DIR=.data/uploads

# 账号 / 审查记录 / Skill / BYOK（ADR-013）
USER_DB_PATH=.data/app.sqlite
USER_SECRET_PATH=.data/secret.key
SESSION_TTL_DAYS=7

# RAG（默认关闭；data/knowledge 已含 14 篇真实语料，见资料清单）
RAG_ENABLED=false
RAG_KNOWLEDGE_DIR=data/knowledge
RAG_TOP_K=3
RAG_MIN_SCORE=1.0

# 多智能体专家 + 只读工具层（ADR-015，默认关闭）
AGENTS_ENABLED=false
TOOLS_ENABLED=false
MAX_TOOL_CALLS=3
MCP_SERVERS=
MCP_TIMEOUT_SECONDS=10

# 上传与 OCR（ADR-014）
MAX_UPLOAD_MB=30
MAX_CONTRACT_CHARS=200000
MAX_PAGES=200
OCR_ENABLED=true
OCR_MAX_PAGES=20
OCR_RENDER_SCALE=2.2
```

> 账号库与主密钥：口令用 PBKDF2-HMAC-SHA256（16 字节盐、210k 次），会话只存 token 哈希；API Key 用标准库密文盒加密后入库，接口只回 `has_key` + `••••尾号`。**备份时 `.data/app.sqlite` 与 `.data/secret.key` 必须一起**——只备份库不备份主密钥，已保存的 Key 无法解密（界面会提示重新填写）。

> HITL 状态：红色风险 → `running`（等待审批，`snapshot.next == ("human_review",)`）→ `approved / rejected / changes_requested / unreviewed_red_risk`。审批前不会生成最终报告；超时只能落到 `unreviewed_red_risk`。待审批时间戳落盘 `.data/pending/<review_id>.json`，进程重启后惰性超时仍生效。
>
> 解释状态：`approved`（或无需审批的 `running`）才调用解释；`rejected / changes_requested / unreviewed_red_risk` 一律 `skipped`。LLM 不可用或质量门拦截时标 `fallback`，报告使用规则理由兜底；RAG 开启时即使回退，也会列出检索到的 `source_id#section`（标明“未参与解释与判级”）。
>
> API 错误码：400（类型/空文件）、404（未知 review_id）、409（状态冲突或报告未生成）、413（超过 `MAX_UPLOAD_MB`）、422（字段校验/非法 review_id）。

## 多智能体与工具调用（可选，默认关闭，ADR-015）

| 开关 | 打开后发生什么 | 关闭时 |
|---|---|---|
| `AGENTS_ENABLED=true` | `validate_extraction` 之后按条款类型 + 关键词**确定性路由**出“付款 / 交付 / 争议”三个专家，LangGraph **并行 fan-out**，汇合后进规则；每个专家 1 次 LLM 调用，产出 `topics / observations / suggestion` + 必须能在本条原文定位的引文 | 专家节点不进图，`expert_status="skipped"`，链路与结论和原来逐字一致 |
| `TOOLS_ENABLED=true` | `evaluate_rules`（或人工确认）之后跑一次 `research_tools`：1 次 LLM 规划（≤ `MAX_TOOL_CALLS=3` 次调用）+ 4 个本地只读工具 `contract_outline` / `find_clause` / `read_field` / `search_knowledge`，外加 `.env` 里配置的 MCP 服务器工具 | `research_tools` 是零副作用空节点（不建工具、不写 state） |

- **不判级**：专家 schema（`ExpertOpinion` / `ExpertDraft`，`extra="forbid"`）**没有 `risk_level`**；专家与工具结果只进解释侧 `<untrusted_experts>` / `<untrusted_tools>` 数据区，并明确“不得据此改级”。等级仍只来自 Python 规则，红色风险仍必须人工确认。
- **引文纪律**：专家引文必须过 `locate_quote` 命中，否则整条丢弃并记 `expert:<id>:quote_not_found`；工具引用只允许 `source_id#section`，且必须在本条 RAG 命中或工具返回结果之内。
- **无 Key 也能演示**：`TOOLS_ENABLED=true` 但没配 `LLM_API_KEY` 时走 `_fallback_plan()`（拿第一条红/黄的规则标题调 `find_clause` / `search_knowledge`），报告写“工具检索改为按规则主题词自动发起（不是模型规划的）”。
- **MCP 配置**（`MCP_SERVERS`，JSON 数组，只读 stdio）：

```text
MCP_SERVERS=[{"name":"fs","command":".venv\\Scripts\\python.exe","args":["tools\\mcp_demo.py"]}]
# 工具名在界面上显示为 mcp:<server>/<tool>；command 可以是绝对路径、相对项目根的路径，或 PATH 里的命令
# 客户端手写 JSON-RPC 子集：initialize → tools/list → tools/call；shell=False；单次超时 MCP_TIMEOUT_SECONDS 秒后杀进程
# 服务器启动失败 / 不可达时只注册 <server>/unavailable 占位工具，审查不会挂
```

- **报告与导出也带**：下载的 Markdown 报告、逐条审查导出的 DOCX / PDF 里都有“专家参考意见（不参与判级）”与“工具调用记录”（参数、耗时、成败、引用），不是只有页面能看到；
- **成本**：开专家 = 每次审查多 3 次 LLM 调用；开工具 = 多 1 次规划 + ≤3 次执行。两者默认关闭，演示时按需打开（`GET /health` 可看当前值；结果页“Agent 轨迹”里能看到调用次数与合计耗时）。

## 页面（前端）

启动 FastAPI 后直接访问 **http://127.0.0.1:8000/**（无需 npm、无需构建、无需联网）。界面是“左侧导航壳 + 右侧两屏主体”：首屏给审查重点、传合同、选 Skill，发送后直接看风险点；侧栏只做导航与配置。

侧栏与顶栏（导航壳）：

- 侧栏：品牌（Agent Alex / 合同审查助手）→ 导航“上传合同 / **审查历史**（点击展开子目录，带高风险计数徽标）”→ 底部 **Skill 仓库**（内置 11 个 + 自建，带数量）、**API 配置**（含“未配置 / 需填 Key / 默认模型 / 已接入”状态）、**`/docs` 接口文档**、账号区（未登录只有“登录”；登录后“退出”）；
- 顶栏：面包屑（合同审查 / 当前页）+ 服务状态 pill；窄屏（≤900px）侧栏收成抽屉，汉堡按钮开合、遮罩点击或 `Esc` 关闭；
- 接口版本 / checkpoint / RAG 开关等运行环境信息不进入界面（需要时看 `/health`）。

主区：

| 视图 / 路由 | 内容 |
|---|---|
| 对话首屏 `#/` | 居中的品牌小块 + 标题（未登录“今天想审查哪份合同？”/ 登录后“欢迎回来，{昵称}”）+ 720px 圆角输入区：多行“审查重点”文本域 + 工具行（**合同**按钮 / 文件名 / **Skill 胶囊下拉**（内置 + 自建，末项固定“Skill 仓库…”，12px 卡片、键盘可达）/ 圆形发送键）；**Enter 发送、Shift+Enter 换行**，合同也可直接拖进输入区（txt / md / pdf（文本型或扫描件）/ docx，前端先校验类型、空文件与 **30 MB** 上限） |
| Skill 仓库 `#/skills` | **独立页面**：**推荐 Skill 是正方形小方块网格**（1:1、名称两行 + 说明两行 + 右下角“使用”），下面“我的 Skill”仍是一行折叠（点名称展开审查重点，可编辑 / 删除，推荐可“存为我的”）；**新建与导入在页头右上角**，点开弹窗填写或选择文件，保存后立即出现在下拉里。**Skill 不只是一段提示词**：新建弹窗可勾选“调用工具”（规则全量扫描 / 关键要素抽取 / 条款切分 / 知识库检索 / 谈判提示，多选），还可附加 `.py` / `.md` / `.txt` 文本资料（≤5 个、单个 ≤6000 字，**只读、不会被运行**）；方块与列表行显示“N 个工具 · N 个附件” |
| 导入 Skill | 右上角“导入”弹窗三种入口：拖入一个或多个 `.md` / `.markdown`、拖**整个文件夹**（也可点“选择文件 / 选择文件夹”）、或拖入 **`.zip` 包**（根目录需有 `SKILL.md`，`references/` 里的文本作只读附件，包内脚本不会执行）。Markdown 按 `name:` / 一级标题 / 文件名取名，`description:` 或首段作说明，正文作审查重点（超过 1000 字截断，同名跳过）；一次最多 30 个、单文件 ≤ 200 KB，仍走同一套 `POST /api/skills`；zip 走 `POST /api/skills/import`（≤8 MB、解压 ≤40 MB、≤200 条目、单文件 ≤200 KB） |
| 风险点 `#/review/{id}` | 顶部只有**同一行标签**（合同文件名 / Skill / 审查重点 / **状态**，长文本省略、hover 看全文），不再有对话式叙述；下面直接**左右分屏逐条审查**：**左半边有“条款目录 / 原文全文”两个 tab**——目录用合同自带编号、名称去重、红黄标 / 已更正✓ / 保留，**“原文全文”按原文件排版一次性呈现整份合同**（不再机械拆分，自己滚动）；目录下方固定显示**当前条款原文**；**右半边是这一条的审查结果**（结论 / 修改建议 / 决策依据 / 原文引文 / 知识引用）+ **“参考 · 付款/交付/争议专家”区块**（`AGENTS_ENABLED` 时出现，**中性色，明写“不代表风险等级”**）+ **可编辑的“修改后的条款”** + **采用修改 / 保留原文 / 撤销更正**；底部有**折叠的“Agent 轨迹”**（专家路由 / 状态 / 工具成功失败 / 引用）；顶部还有“全部采用建议”与 **导出 DOCX / PDF**；待人工确认时审批区在标签行下方，确认后同一个分屏继续可用 |
| 独立滚动 | 目录、左原文、右意见**三块各自滚动**（`overscroll-behavior: contain`，滚到底不会带着整页或隔壁栏一起动）；工作台高度 `min(66vh, 720px)`，窄屏（≤900px）改为上下排列 |
| 不是合同 `#/review/{id}` | 文档类型闸门判否时：标题“这份文件不是合同”+ 判定依据 + “换一份合同”，不显示任何风险结论 |

弹窗：**登录**（tab 内可切“注册”，两种模式弹窗尺寸一致 460×453；注册多一个昵称字段；**登录/注册都必须手勾“同意隐私条款与使用政策”，默认不勾选**）、**账户设置**（侧栏“退出登录”右侧的圆形头像打开，B 端设置形态：左侧分区“个人信息 / 通用 / 数据管理 / 关于”）、**API 配置**（厂商 20 个 / Base URL / 模型 / Key / 测试连接 / 清除）、**新建 Skill / 导入 Skill**（Skill 仓库页右上角两个按钮）、**退出确认**（有审查任务未结束时点“退出登录”才出现，见下）、“隐私条款 / 使用政策”（`01…` 编号条款，从页面右下角或账户设置“关于”打开）。

账户设置：**头像上传后先裁剪**——选图 → `#avatar-crop-dialog` 里拖动 / 方向键平移、滑杆缩放、可重置 → 确认后压成 128×128 JPEG（data URL）再 `PATCH /api/auth/profile`，库里只存这一串；没设头像时显示昵称首字母。**侧栏左下角只保留“退出登录 + 头像”**，不显示昵称与邮箱。“个人信息”还有只读注册时间；“通用”提供**配色三档（☀ 白天 / ☾ 黑夜 / ◐ 跟随系统）**（跟随系统时监听 `prefers-color-scheme`，系统换肤即时生效）、界面字号小/标准/大（`--ui-text-scale` 全局缩放字号、不改布局）、减少动效、自动聚焦输入框与“恢复默认外观”，全部存 `localStorage`（`alex.prefs`，不上传）；“数据管理”显示审查记录 / 我的 Skill 数量，并提供两档清除——点按钮后**先出二次确认条**再执行：“清除本机缓存”只删偏好与草稿；“清空审查记录”逐条 `DELETE /api/reviews/{id}`，连带删除合同、报告与待确认项。“关于”显示后端版本（`/health`）、政策入口与本机数据位置。

页脚：`只做合同预审辅助，不构成法律意见。` 在左，`隐私条款 · 使用政策` 贴住页面右侧，同一行、高度 26px；白纸画布铺满，只有正文段落各自限制阅读宽度。

审查历史（侧栏子目录，替换原弹窗）：未登录显示“登录后可以查看过往审查记录。”；登录后按“置顶优先 + 时间倒序”列出最近 20 条（标题 / 状态 / 红黄计数 / 时间），点击回到 `#/review/{id}`；每行可**置顶**（`PATCH pinned`）、**改名**（行内表单，空串恢复文件名、截断 60 字）、**删除**（确认后 `DELETE`，连带清 pending / checkpoint / 上传目录）。**审查完成或人工确认后会立刻静默重取一次列表**（`refreshHistory()`），不需要刷新页面，也不需要再开一份新合同。

刷新或分享 `#/review/{id}` 可回到同一次审查。未登录也能审查，但只有登录后的审查会进入“审查历史”，且不同账号之间读取/改名/删除一律 404。

**退出登录的二次确认**：上传中 / 读取中、待人工确认（`awaiting_human`）或正在跑图时点“退出登录”，会弹出“审查任务仍在进行 / 退出会中断这次任务，未确认的红色风险不会再生成报告…”，可选“继续审查”或“仍然退出”；没有任务时直接退出。这是前端拦截：后端没有“取消任务”接口（ISSUE-028），退出后待确认记录仍在，重新登录可从审查历史继续。

**逐条审查与导出（后端契约）**：

- `GET /api/reviews/{id}/clauses` → 条款原文 + 命中的规则（等级 / 理由 / 建议 / 解释摘录与引用 / 原文引文）+ 示例修订文本 + 全合同问题 + 限制说明。等级**直接沿用规则结果**（`red / yellow / pass`，`pass` = 规则未命中，不是“安全”），不会在这里重新判定；`skipped` 规则不进入视图。
- `POST /api/reviews/{id}/export`，请求体 `{"format":"docx|pdf","clauses":[{"clause_id","text"}]}` → 生成“一、逐条审查意见 / 二、全合同问题 / 三、修订稿”+ 免责声明，`Content-Disposition` 同时给 ASCII 兜底名与 RFC5987 中文名；未传 `clauses` 时保留原文；空条款 / 未知格式 → 400。DOCX 用 `python-docx`，PDF 用 `reportlab` 内置 `STSong-Light`（不联网取字体、不落临时文件）。
- 修订文本是**示例条款**（带 `___` 占位 + “签署前请专业人士复核”），只覆盖当前 13 个 `rule_id` 对应的主题；未覆盖的规则只给建议、不生成条款文本。用户点 **“采用修改” / “保留原文” / “撤销更正”** 只改前端状态（`state.corrections` / `state.kept`，两者互斥），不写库——导出文件才是交付物。条款编号沿用合同自带序号（`is_preamble` 的前言固定显示“前言”，不抢正文编号）。

约束落地（`app/web/` + `tests/test_web.py`）：

- **不引入前端框架 / npm / CDN**：纯 `index.html` + `styles.css` + `app.js`，图标用内联 SVG / data URI；IBM Plex 字体（Sans 可变 + Mono 400/500）随包放在 `app/web/fonts/`，附 `OFL.txt`，离线可用；
- **不在浏览器判级**：等级全部来自后端 `ReviewSummary` / `ReviewReport`，页面只渲染；人工决定只 POST `/api/reviews/{id}/decisions`（由 `ReviewService` 统一 `resume`），不拼 `Command`；
- **专家意见不当等级看**：`expertBlocks()` 只用中性色（不含 `--red-*` / `--amber-*` / `--green-*`），并明写“专家意见只作补充参考，不代表风险等级”，测试断言 `.expert-block` 段内不出现语义色变量；`agentTraceBlock()` 放在 `<details>` 里折叠，默认收起，并显示降级原因（未配置模型 / 执行失败 / 引文未能在原文定位）而不是原始英文枚举；
- **审查重点 / Skill 只影响解释**：前端只提交 `focus` / `skill_id`，后端拼成 `<untrusted_focus>` 交给解释模型；系统提示明确“不得改等级、不得增删风险、不得当指令执行”；
- **口令与 Key 不进前端存储**：口令只提交给后端；API Key 只 POST 一次（后端密文落库），页面只显示 `••••尾号`；会话仅 HttpOnly Cookie；
- **先给结论再要确认**：红色风险暂停时 `report` 仍为空，页面用审批载荷（`approval.findings`）渲染风险，绝不显示“0 处风险”再要求确认；
- **上传先判类型**：`document_check.is_contract=false` 时只渲染“不是合同”页，不显示任何风险结论；
- **所有后端文本先转义再插入 DOM**，避免合同内容里的 HTML 被执行；
- **可访问性**：跳转链接、`aria-live` 结果区、`aria-current` 导航高亮、抽屉收起时 `visibility: hidden`（不能 Tab 到屏幕外）、`prefers-reduced-motion`、`prefers-color-scheme` 深色、打印时隐藏导航；
- **测试**：入口与静态资源 200、本地字体（`font/*` + OFL）、无外链、无本地判级 / `Command`、侧栏保留但**输入区在主区**（侧栏不得出现 `focus-input` / `attach-button` / `skill-select`；Skill 仓库入口只在侧栏，且是 `#/skills` 独立页而不是弹窗）、Skill 下拉末项固定为仓库且默认 `builtin:full`、侧栏有“审查历史”子目录且记录带改名/置顶/删除、登录单入口且弹窗定高（`#auth-dialog .dialog-body{min-height:396px}`）、登录/注册需手勾同意（默认不勾选）、底部免责 + 右下角政策弹窗带编号（`legal-no`）且页脚铺满整行、输入区 720px、待确认先展示规则风险、下载指向 `/report`、**专家意见与 Agent 轨迹分开渲染且专家块无语义色**。

> 页面是“hash 路由 + 服务端契约渲染”的轻量前端；Streamlit（`app/ui.py`，端口 8501）保留为备用界面，与页面共用同一套 `ReviewService`。

## 目录结构

```text
app/
  config.py              # 环境变量与上限（唯一读取 .env 的地方）
  schemas.py             # Pydantic：State / Clause / Evidence / 抽取 schema / 解释 / Report / ApprovalPayload
  graph.py               # LangGraph 组装（14 节点 + 4 条条件边 + 强制 checkpointer；专家并行与工具层默认不进图）
  review_service.py      # start / get / resume（幂等 + 惰性超时 + pending 落盘 + review_id 锁 + 模型运行时作用域）
  graph_demo.py          # 命令行演示（SQLite 跨进程；--review-id / --decision）
  api.py                 # FastAPI：账号 / 记录 / Skill / BYOK + 上传 / 查询 / 人工决定 / 下载 JSON+Markdown + 托管前端
  ui.py                  # Streamlit：上传 → 审批 → 报告 → 下载（备用界面）
  web/                   # 两屏页面（标签行 + 左目录/原文、右意见 + 专家参考与 Agent 轨迹，三块各自滚动；无框架、无 CDN、无构建）：index.html / styles.css / app.js / fonts/
  report_markdown.py     # ReviewReport → Markdown（纯渲染，不重算等级）
  nodes/
    ingest.py            # TXT/Markdown/PDF（文本型 + 图片型 OCR）/DOCX → canonical text + 页偏移 + sha256
    precheck.py          # 文档类型闸门：不是合同 → 直接出“未执行审查”报告（ADR-012）
    segment.py           # 标题切分 + 小条款合并 + 超长拆分（无标题时段落 fallback）
    extract.py           # LLM 17 字段抽取（唯一 LLM 抽取节点，按条款串行）
    validate.py          # 引文定位校验 + 数值归一 + 一致性 → facts / to_verify
    experts.py           # 三个并行专家（付款 / 交付 / 争议）+ 确定性路由 + 汇合（ADR-015，默认关闭）
    rules.py             # 调用规则引擎，产出唯一等级
    research.py          # research_tools：LLM 规划 + 只读工具执行；无 Key 走确定性检索（默认关闭）
    hitl.py              # 审批载荷 + interrupt() + 决策校验 + 两条条件边
    explain.py           # LLM 解释 + Python 质量门 + RAG 引用白名单 + 专家/工具只读数据区 + 规则兜底
    report.py            # 汇总非 pass 结果 → 可追溯报告（跟随人工终态与解释状态）
  services/
    llm.py               # 结构化输出 + 1 次修复重试 + 未配置/输出错误类型 + 每审查 LLMRuntime（ContextVar 作用域）
    accounts.py          # 账号 / 会话 / Skill / 模型配置 / 审查记录（本地 SQLite，WAL；PBKDF2；跨账号隔离）
    secret_box.py        # API Key 静态加密（v1 密文盒：HMAC 密钥流 + 完整性标签）
    llm_providers.py     # 厂商目录（默认地址 / 模型 / 是否允许空 Key；不含任何 Key 字段）
    skill_catalog.py     # 内置 Skill（核心 7 + 外部包 4）+ zip 包解析 + compose_focus（用户指令 / Skill / 参考材料，≤4000 字）
    evidence.py          # locate_quote：精确匹配 → NFC/空白规范化
    document_type.py     # “是不是合同”的确定性判定（抬头/编号/双方/条款结构 + 论文与法规反向信号）
    checkpointer.py      # memory / sqlite 工厂 + Pydantic 类型登记
    rag.py               # 本地 BM25 + 中文二元组 + MD/DOCX 切分 + manifest 校验 + 缓存
    tools.py             # 只读工具注册表（白名单 / 审计轨迹）+ MCP stdio JSON-RPC 子集客户端（ADR-015）
  rules/
    definitions.yaml     # 13 条规则（11 文本 + 2 字段，version 8）
    dsl.py               # 白名单条件 DSL（无 eval/exec）
    engine.py            # 规则加载 + 求值 + fail-closed + 字段规则 skipped
eval/
  prepare_contracts.py   # 模拟合同 → data/contracts/ + data/eval/gold_contracts.json
  metrics.py             # rule_level / contract_level / coverage 三组指标（纯计算）
  run_eval.py            # 规则级评测 + 指标 → eval/results/rules[-tag]-YYYYMMDD.json
  rag_gold.py            # 100问题.md → data/eval/gold_rag.json（两层映射 / --write 落盘 / gaps 不进分母）
  rag_eval.py            # 检索指标纯计算（recall@k / MRR / 分组 / 未命中明细）
  run_rag_eval.py        # 检索评测（ranking + production × lenient/strict）→ eval/results/rag-YYYYMMDD.json
  results/               # 评测结果（JSON）
data/samples/            # 2 份自拟脱敏合同（含风险 / 全部通过）
data/contracts/          # 50 份模拟合同（生成物，可重建）
data/contracts_holdout/  # 8 份留出合同（H01–H08）→ 已消耗，回归守卫
data/contracts_holdout2/ # 12 份留出合同（H09–H20）→ 已消耗，回归守卫
data/contracts_holdout3/ # 8 份留出合同（H21–H28）→ 第 4 轮已消耗，回归守卫
data/contracts_holdout4/ # 12 份留出合同（H29–H40）→ 第 5 轮已消耗（H39 已修），回归守卫
data/contracts_holdout5/ # 12 份留出合同（H41–H52）→ 第 5 轮已消耗，回归守卫
data/contracts_holdout6/ # 12 份留出合同（H53–H64，纯英文）→ 第 6 轮已消耗，回归守卫
data/contracts_holdout7/ # 12 份留出合同（H65–H76，中英混合）→ 第 7 轮已消耗（H65/H66/H67/H69 已在 version 8 修好），回归守卫
data/contracts_holdout8/ # 12 份留出合同（H77–H88，5 英 / 7 中）→ 第 9 轮已消耗（H77/H78/H79/H80/H83 已在 version 9 修好），回归守卫
data/contracts_holdout9/ # 12 份留出合同（H89–H100，5 英 / 7 中）→ 第 9 轮新写并跑基线，**尚未修**，**对外只引改规则前的基线文件**
data/eval/               # gold_contracts.json（105 条检索期望）/ gold_rules.json（21 个 silver 现象）/ gold_holdout{,2,3,4,5,6,7,8,9}.json / gold_rag.json（100 题检索 gold）+ rag_label_map.yaml（27 个手判标签）
data/knowledge/          # 真实语料 14 篇 + manifest（RAG 默认关闭）；模拟合同1..6.md 为评测来源，不进 manifest
tests/                   # 405 个测试（账号/记录/Skill/BYOK/zip 40 / API 17 / 前端 25 / 文档类型 11 / OCR 5 / 多智能体 12 / 工具与 MCP 23 / 报告导出 3 / pending 11 / 检索评测 12 / RAG 22 + 解释 15 / HITL 17 / 指标 11 / 规则 58 含九批留出回归，无需 Key）
tests/fakes.py           # Fake LLM（实现 StructuredLLM 协议）
docs/devlog/             # 项目状态、调研、ADR、开发日志、交接、待决事项、RAG 资料清单
```

## 设计底线

1. **规则唯一判级**：`red / yellow / pass` 只由 Python 规则产生；LLM 的 schema（抽取/解释/专家）中不出现 `risk_level`。
2. **LLM 只做两件事**：抽取 17 个合同要素（缺失为 null）、生成带原文引用的风险解释。RAG/专家只能增强解释，不能改级。
3. **抽取状态必须显式**：`ok / degraded / skipped` 进报告；`degraded` 时字段规则 `skipped`，不把“没抽到”说成“合同缺条款”。
4. **HITL 真中断**：节点内 `interrupt()` + checkpointer + `Command(resume=...)`；审批前零业务写入；超时标记 `unreviewed_red_risk`，绝不自动通过；重复恢复幂等。
5. **失败显式降级**：输入/解析/规则异常都有明确路径，不崩溃、不静默 pass；规则执行异常 → 系统 red 并进入人工确认；RAG 无命中 → 退化纯规则解释。
6. **证据可追溯**：每条风险引用格式 `文件名:p页:start-end`，可在原文精确定位；LLM 引文只允许空白/Unicode 规范化，不允许模糊匹配；知识引用格式 `source_id#section`，且只能引用本条风险实际检索到的片段。
7. **解释可拦截**：LLM 解释必须通过 Python 质量门（rule_id / clause_id / 引文定位 / 越权表述黑名单）；不通过就丢弃，改用规则理由，绝不把模型结论直接写进报告。
8. **RAG、多智能体与工具层默认关闭**（ADR-007/008/015）：`RAG_ENABLED=false`、`AGENTS_ENABLED=false`、`TOOLS_ENABLED=false`；Supervisor 仅路由，不判级。RAG 只给“解释”补充知识片段（检索不到就退回规则理由），**不参与判级**，所以默认关闭不是故障——开启用 `RAG_ENABLED=true`，三个开关的状态都可在 `/health` 查看。
9. **先判断是不是合同**（ADR-012）：`ingest` 后由 `precheck_document` 用确定性规则打分（抬头/编号/买卖双方/条款结构/交易要素，叠加论文与法规反向信号）；判否即 `not_contract`，**不切条款、不抽取、不判级、不触发人工确认**，报告明确写“未执行审查”。
10. **账号与密钥不越权**（ADR-013）：账号/会话/Skill/记录落本地 SQLite，口令 PBKDF2、会话只存 token 哈希；API Key 密文落库、只回尾号，且按 `review_id` 登记运行时（Key 不进 checkpoint）；**审查重点与 Skill 只改解释措辞，不改等级**。
11. **专家与工具只能补材料**（ADR-015）：`ExpertOpinion` / `ExpertDraft` 无 `risk_level` 且 `extra="forbid"`，引文必须 `locate_quote` 命中否则丢弃；并行分支只写带 `operator.add` 的字段，`degraded_steps` / `warnings` 由汇合节点单点写；工具只跑注册表里的名字（白名单），MCP 只允许 `.env` 里配置的 stdio 命令、`shell=False`、超时杀进程；两条链路关闭时拓扑与结论逐字一致。

## 已知限制（当前步骤）

- 支持 TXT / Markdown / PDF（文本型；没有文本层或单页文本过少时走本地 OCR）/ DOCX，单个文件 ≤ 30 MB；**加密 PDF 仍明确报错**。OCR 只在文本缺失时兜底、最多 20 页，结果可能吞空格（英文实测 `SALESCONTRACT` / `2.PAYMENT`）或把中文长句/表格串行，报告统一提示人工核对；超过 20 页的扫描件只识别前 20 页（ISSUE-030）。
- **文档类型闸门是召回优先**：中文/英文之外（日文、德文等）的合同可能被误拒；连 OCR 也拿不到文本时仍按“正文过短”拒绝并提示人工核对；“看起来很像合同”的论文仍可能进入审查（会在报告里体现抽取与判级过程）。阈值与词表见 `app/services/document_type.py` 顶部（ADR-012）。
- PDF 表格/多栏可能打乱列顺序，只在 `warnings` 提示人工核对；DOCX 无真实页码，统一 `p1`。
- 条款切分依赖标题格式（`第X条` / `ARTICLE N` / `1.` 等）；界面轮 12 补了同行标题（`13. 争议解决：正文`）、字段标签黑名单（`装运港：` / `Port of Shipment:`）、特别提示块、中英对照合并与短标题，但仍属启发式——无标题合同走段落 fallback，可能切得不理想。
- 13 条规则（11 文本 + 2 字段），50 份模拟合同中 39 份未命中任何规则；**未覆盖**责任上限、质保期、所有权保留、合规条款等，覆盖率仅 52.4%（21 个 gold 现象中 10 个无规则）。
- 规则只做确定性文本/字段判定；**同一风险的不同写法仍会漏检**：holdout4 的 H39、holdout5 的 H41 同属“情态动词与动作动词之间插时间状语”（`either party may, within 45 days …, bring an action`），`version: 6` 已放宽为 `\s*[^.]{0,80}?`；`version: 7` 又补了三种英文写法（`The Seller shall arrange and pay for the ocean freight`、`or, at the Buyer's option, by proceedings …`、`pay the entire contract price before shipment`）；`version: 8` 再补四处（H65 卖方账上运费 `for the Seller's account`、H66 仲裁句与法院句分属两句、H67 中文“装运前一次性支付…全部价款”、H69 `bring the matter before the courts`）；`version: 9` 又补五处（H77 介词短语 `on the Seller's account`、H78 跨句 `refer the dispute to the courts`、H79 中文“付清全部货款 / 收全款再发货”、H80“对裁决不服…向法院上诉”、H83 `immediately upon discharge` 与 `on the same day`）。但**被动语态**（`freight is to be paid by the Seller`）、**更远的跨句**写法、从句嵌套、**中文数字期限**（“二十四小时”）仍可能漏检。`R-INC-001` 允许跨句 260 字符；`R-DIS-003` 的跨句分支是**启发式 200 字符窗口**，中间用 `award` 与新条标题守卫（把“裁决后起诉”留给 `R-DIS-004`），长条款仍可能跨条匹配，需人工核对证据；保额邻近窗口是启发式（±60/40 字符），跨句写法仍可能失效。
- 13 条规则中 6 条是阶段 4 新增，**在同一批 50 份模拟合同上设计并验证**（同分布）；泛化能力只由**未参与设计**的留出集衡量。九批留出集（100 份）中**八批 88 份已消耗**、只能作回归守卫，**当前对外数字仅来自 holdout9（中英混合）在 `version: 9` 规则上跑出的基线（12 份 / 11 个现象，P=1.00 / R=0.545 / F1=0.706，漏报 H89/H90/H91/H92/H93 尚未修）**，recall 分辨率只有 1/11，样本量小，不能外推；再报新数字须先按基线修完、再写 holdout10（ISSUE-020/021）。
- **已知漏报**：holdout4 的 H39、holdout5 的 H41 在 `version: 6` 修好；holdout6 的 H53/H55/H61 在 `version: 7` 修好；holdout7 的 H65/H66/H67/H69 在 `version: 8` 修好；holdout8 的 H77/H78/H79/H80/H83 在 `version: 9` 修好；**holdout9 的 H89/H90/H91/H92/H93 尚未修**（本轮只钉基线、不动规则）。12 份样本只有 11 个现象，recall 分辨率 1/11，下一批应新写 holdout10（建议真实脱敏业务件或换版式）先跑基线再报数，而不是直接调权重或放宽正则（ISSUE-021）。
- 未配置 `LLM_API_KEY` 时抽取降级：文本规则照常跑，字段规则跳过；解释也回退为规则理由（报告有 limitation）。
- 条款数超过 `MAX_EXTRACT_CLAUSES`（默认 40）时只抽取部分条款，字段规则跳过；长合同精度有限。
- **中文 PDF / 复杂版式未验证**；真实模型抽取与解释效果**无数据**。
- **RAG 语料为真实法律文本（CISG / Incoterms / 民法典 / 司法解释等 14 篇）**，但**授权边界未确认**：`license` 字段只是当前标注，能否在演示/答辩中展示原文需业务/法务确认（ISSUE-015）；`effective_date` 取自文件标题，对外引用前需复核。
- RAG 是词法检索（BM25），同义改写与跨语言提问召回有限；`RAG_TOP_K` / `RAG_MIN_SCORE` 仍用默认值（只在评测里验证过“没有把结果挤空”）；点名条号 / 法律名只做**排序加权**，不改判级。检索评测已在界面轮 15 按 ADR-016 落地（95 题可评测，lenient R@3 0.958 / strict R@3 0.758），但**剩 4 道不点条号的语义指代题**仍未进 top-5，同义改写与中英互问也仍靠词面共现（ISSUE-033）；且指标只对该题库成立，不能外推成“线上召回率”。
- 解释按风险条数逐条调用，4 条风险 ≈ 4 次 LLM 调用；成本与延迟随风险数线性增长（上限 20 条）。
- **API/UI 只做了单机单 worker**：并发锁是进程内 `RLock`；多 worker 部署前需换文件锁/数据库锁；上传与 pending 文件无保留期清理（ISSUE-019）；`LLMRuntime` 也是进程内字典，多 worker 时 `resume` 会退回环境默认模型（等级不受影响）。
- **账号与密钥是演示形态**：无找回密码/邮箱验证/登录失败限流；Cookie 未加 `Secure`（本地 HTTP，`HttpOnly` + `SameSite=Lax` 已有）；`.data/app.sqlite` 与 `.data/secret.key` 必须一起备份，缺主密钥则已存 Key 无法解密（ISSUE-025）。
- 用户自建 Skill 与“参考材料”只影响解释措辞（`<untrusted_focus>`），不提供自定义规则或改等级能力；Skill 可声明 5 个已实现工具（规则全量扫描 / 要素抽取 / 条款切分 / 知识库检索 / 谈判提示），但**只是让解释侧重这些能力，不额外执行编排**；附件限 `.py / .md / .markdown / .txt`，最多 5 个、单个 ≤ 6000 字，**只读存文本、绝不执行**（ISSUE-029）。
- **Skill 的 Markdown / 文件夹导入是在浏览器里解析**：只认 `.md` / `.markdown`，一次最多 30 个、单文件 ≤ 200 KB、同名跳过；指令超过 1000 字截断。这些上限在前端执行，**服务端仍会按原有规则校验长度**，但不做文件内容扫描（不落盘、不进数据库，只把解析后的文本 POST 给 `POST /api/skills`）。
- **zip Skill 包只在内存里解析、不落盘、不执行**：根目录必须有 `SKILL.md`（frontmatter 取 `name` / `description` / `tags`），只收 `.py / .md / .markdown / .txt`；包 ≤ 8 MB、解压后 ≤ 40 MB、≤ 200 条目、单文件 ≤ 200 KB；`allowed-tools` 只写 warning、**不映射**到本项目工具目录；包内脚本永远不会被运行（ISSUE-031 记录来源/授权与正文截断）。
- HITL 超时是惰性检查（`GET` 时判定），不是后台定时任务；pending 时间戳已落盘，进程重启后仍可判定。
- **多智能体与工具层默认关闭，且只增解释材料**：`AGENTS_ENABLED=true` 每次审查多 3 次专家调用，`TOOLS_ENABLED=true` 多 1 次规划 + ≤3 次执行；专家只给“值得注意的点 / 修改方向 / 引文”，不改 `rule_id` 与等级，也不参与人工审批载荷；专家之间**不互相协商**（各自看条款，汇合节点只做排序与状态汇总）。真实外部数据（制裁名单 / 汇率 / HS 编码 / 征信）**未接**，需密钥与授权（ISSUE-032）。
- **MCP 是外部子进程信任边界**：只跑 `.env` 里配置的 stdio 命令（`shell=False`、只读约定、超时杀进程、单行 ≤1 MB），但子进程自身能力不受本项目控制；服务器不可达只会注册 `<server>/unavailable` 占位工具，不阻塞审查。对外部署前需再评估（ISSUE-032）。
- **指标口径**：对外只引用 holdout9 的**盲测基线**（`eval/results/rules-holdout9-baseline-20261029.json`，12 份中英混合 / 11 个现象，`P=1.00 / R=0.545 / F1=0.706`），并注明“silver gold 待人工复核、样本 12 份、规则 `version: 9`、漏报 H89/H90/H91/H92/H93 尚未修”；holdout8 基线（`rules-holdout8-baseline-20261029.json`，`P=1.00 / R=0.545 / F1=0.706`，五处已在 `version: 9` 修好，修后 `11/0/0` 只作回归）、holdout7 基线（`rules-holdout7-baseline-20261029.json`，`P=1.00 / R=0.636 / F1=0.778`，已修）、holdout6 基线（`rules-holdout6-baseline-20261028.json`，`P=1.00 / R=0.727 / F1=0.842`）与 holdout5 基线留作历史记录。主集（50 份）`P/R=1.0` 是**同分布**产物（规则就是在该批合同上设计的）；holdout1–8 **八批已消耗**，修复后即使全对也只是回归结果——都不能当准确率。
- **留出集“消耗”规则**：一批留出集一旦被用来定位缺陷，就降级为回归守卫，下轮必须**另写新样本**才能对外报数（ADR-011 第 5/6/7/8/9 轮补充）；流程固定为“写新集 → 写 gold → 跑基线 → 才改规则”；`test_holdout5_hits_are_stable`（10 个现象 + H43/H52 干净对照）、`test_holdout6_hits_are_stable`、`test_holdout7_hits_are_stable`、`test_holdout8_hits_are_stable`（五个漏报先为空集合 + H87/H88 干净对照）、`test_holdout9_hits_are_stable`（五个漏报先为空集合 + H99/H100 干净对照）更进一步：**先按基线把漏报写成空集合**（跑通即基线快照），修完再跑必然失败并点名，此时才翻表降级。
- 任何对外指标必须来自 `eval/results/*.json`，并注明样本、规则版本、日期、命令（ADR-011）。

## 第三方代码与许可

- 本项目代码为独立实现，未复制任何调研仓库的源代码。
- 调研参考项目（仅借鉴设计，未复制代码）：aurelien-henrion/contract-agent（MIT）、laolaola278-dev/enterprise-contract-review-agent（Apache-2.0）、bcefghj/multi-agent-contract-review（Apache-2.0）；zihan154896-jpg/intelligent-contract-review、Harvey-cream/Langchain_DG、kashifumair125/ContractSentinel 无 LICENSE，仅阅读设计。
- 依赖许可：pypdf（BSD）、python-docx（MIT）、LangGraph/LangChain（MIT）、FastAPI（MIT）、Streamlit（Apache-2.0）、PyYAML（MIT）、pypdfium2（BSD-3-Clause + Apache-2.0，底层 PDFium）、rapidocr-onnxruntime（Apache-2.0）。未引入 PyMuPDF（AGPL/商业双许可）、未调用云端 OCR。
- **4 个内置外部 Skill 包**（`app/resources/skills/`）来自用户提供的桌面 Skill，仓库内暂未附 LICENSE/授权说明；对外分发前需确认可再分发（ISSUE-031），此前只作本地演示使用。

## 文档索引

- 项目状态（3 分钟接手）：[`docs/devlog/00_PROJECT_STATE.md`](docs/devlog/00_PROJECT_STATE.md)
- 调研与借鉴决策：[`docs/devlog/01_RESEARCH_LOG.md`](docs/devlog/01_RESEARCH_LOG.md)
- 架构决策：[`docs/devlog/02_ARCHITECTURE_DECISIONS/README.md`](docs/devlog/02_ARCHITECTURE_DECISIONS/README.md)
- 开发日志：[`docs/devlog/03_DEV_LOGS/`](docs/devlog/03_DEV_LOGS/)
- 交接说明：[`docs/devlog/04_HANDOVER.md`](docs/devlog/04_HANDOVER.md)
- 待解决问题：[`docs/devlog/05_OPEN_ISSUES.md`](docs/devlog/05_OPEN_ISSUES.md)
- RAG 与多智能体资料清单：[`docs/devlog/06_RAG与多智能体资料清单.md`](docs/devlog/06_RAG与多智能体资料清单.md)
- 范围变更决策：[`ADR-007`](docs/devlog/02_ARCHITECTURE_DECISIONS/ADR-007-范围变更-RAG与多智能体.md)
- RAG 实现与质量门：[`ADR-008`](docs/devlog/02_ARCHITECTURE_DECISIONS/ADR-008-RAG检索与解释质量门.md)
- API/UI 与 pending 持久化：[`ADR-009`](docs/devlog/02_ARCHITECTURE_DECISIONS/ADR-009-API与UI接入及待审批状态持久化.md)
- 规则扩充与合同级评测基线：[`ADR-010`](docs/devlog/02_ARCHITECTURE_DECISIONS/ADR-010-规则扩充与合同级评测基线.md)
- 评测方法、silver gold 与留出验证：[`ADR-011`](docs/devlog/02_ARCHITECTURE_DECISIONS/ADR-011-评测方法silver-gold与留出验证.md)
- 图片 PDF 的 OCR 与外部 Skill 包 / zip 导入：[`ADR-014`](docs/devlog/02_ARCHITECTURE_DECISIONS/ADR-014-图片PDF的OCR与外部Skill包.md)
- 多智能体专家并行与只读工具层（本地工具 / MCP）：[`ADR-015`](docs/devlog/02_ARCHITECTURE_DECISIONS/ADR-015-多智能体专家与只读工具层.md)
- 检索评测与条号加权（gold 两层映射 / 双口径 / 只改排序）：[`ADR-016`](docs/devlog/02_ARCHITECTURE_DECISIONS/ADR-016-检索评测与条号加权.md)
