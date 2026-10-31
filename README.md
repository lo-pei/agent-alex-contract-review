# Agent Alex · 外贸合同智审助手

面向**国际货物销售合同**的 AI 预审助手：上传合同 → 条款切分 →（可选）三个专家给参考意见 → LLM 抽取关键要素 → **Python 规则引擎判定红/黄/绿** → 红色风险经 **LangGraph `interrupt()` 真人工确认** → LLM 依据规则结果与原文生成解释 → 输出可追溯报告。

> **核心约束**：等级只来自 Python 规则；LLM 只做抽取与解释；红色风险必须人工确认；失败一律显式降级，不静默通过。

`Python 3.12` · `LangGraph 1.2` · `FastAPI` · `零前端框架` · `415 个测试` · 规则 `version: 11`

---

## 1. 它做什么

```text
ingest → precheck（是不是合同？）─否→ not_contract 报告（不判级）
      → segment → extract(LLM) → validate
      → [AGENTS_ENABLED] 专家并行（付款 ∥ 交付 ∥ 争议）
      → rules（Python，唯一判级）
      → [有 red?] human_review(interrupt) → approve → [TOOLS_ENABLED] 只读工具/MCP
      → explain(LLM + 可选 RAG/专家/工具) → report
```

| 能力 | 说明 |
|---|---|
| 输入 | TXT / Markdown / PDF（文本型或扫描件）/ DOCX，单文件 ≤ 30 MB |
| 条款切分 | 标题式切分（`第X条` / `ARTICLE N` / `1.` 等）+ 中英对照合并 + 超长拆分，无标题时按段落兜底 |
| 要素抽取 | LLM 抽 17 个字段，Python 做引文定位校验；未配 Key 时降级为 `degraded`，字段规则 `skipped` |
| 风险判定 | 13 条规则（11 条文本 + 2 条字段），等级 `red / yellow / pass` 只由规则产生 |
| 人工确认 | 红色风险在节点内 `interrupt()` 真暂停；超时只能落 `unreviewed_red_risk`，绝不自动通过 |
| 输出 | 可追溯报告（证据定位到 `文件名:p页:start-end`）、逐条修改建议、DOCX / PDF 导出 |
| 界面 | Web 工作台（无框架、无 CDN、无构建；处理过程逐节点展示，结果页左原文高亮 / 右原因与修改意见）+ CLI + API；Streamlit 备用 |

---

## 2. 当前状态（2026-10-31）

| 项 | 值 |
|---|---|
| 阶段 | 第四阶段（测试与评测）第 11 轮 + 界面轮 17 |
| 规则 | 13 条（11 文本 + 2 字段），`app/rules/definitions.yaml` `version: 11` |
| 图 | 14 节点 + 4 条条件边；专家分支与工具节点默认关闭（走直连 / 空节点，拓扑与结论不变） |
| 测试 | **415 个**，`ruff check .` 通过，前端 `node --check` 通过 |
| 对外指标 | **holdout11 盲测基线**：P=1.00 / R=0.545 / F1=0.706（12 份 / 11 现象，漏报 H113–H117 **尚未修**） |
| 检索评测 | 95 题可评测；ranking lenient R@3 **0.958** / strict R@3 **0.758** |
| API | `1.1.0`（`GET /health` / `GET /openapi.json` 可查） |
| 仓库 | <https://github.com/lo-pei/agent-alex-contract-review>（private，`master`） |

> 评测口径与“留出集消耗”规则见 [ADR-011](docs/devlog/02_ARCHITECTURE_DECISIONS/ADR-011-评测方法silver-gold与留出验证.md)；数字怎么读见 [§7](#7-评测数字怎么读)。

---

## 3. 设计底线

1. **规则唯一判级**：LLM 的抽取 / 解释 / 专家 schema 中都没有 `risk_level`。
2. **LLM 只做两件事**：抽 17 个合同要素、生成带原文引用的解释；RAG 与专家只增强解释。
3. **抽取状态显式**：`ok / degraded / skipped` 进报告；`degraded` 时字段规则 `skipped`，不把“没抽到”说成“合同缺条款”。
4. **HITL 真中断**：`interrupt()` + checkpointer + `Command(resume=...)`；审批前零业务写入；重复恢复幂等。
5. **失败显式降级**：解析 / 规则 / LLM 异常都有明确路径；规则执行异常 → 系统 red 并转人工。
6. **证据可追溯**：风险引用定位到原文；知识引用只允许本条实际检索到的 `source_id#section`。
7. **解释可拦截**：LLM 解释必须过 Python 质量门（rule_id / clause_id / 引文定位 / 越权表述黑名单），否则回退规则理由。
8. **先判断是不是合同**：`precheck` 判否即 `not_contract`，不切条款、不抽取、不判级、不触发人工确认。
9. **账号与密钥不越权**：口令 PBKDF2、会话只存 token 哈希；API Key 密文落库、只回尾号；审查重点与 Skill 只改解释措辞。
10. **可选能力默认关闭**：`RAG_ENABLED` / `AGENTS_ENABLED` / `TOOLS_ENABLED` 均为 `false`，关闭时拓扑与结论逐字一致。

---

## 4. 快速开始

```powershell
# 1) 环境（必须 3.12；不要用系统默认 python）
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env   # 需要真实模型时再填 LLM_API_KEY

# 2) CLI 全链路（无 Key 也可跑：抽取降级、字段规则跳过）
.\.venv\Scripts\python.exe -m app.graph_demo
.\.venv\Scripts\python.exe -m app.graph_demo data\samples\sample_clean_contract.txt
.\.venv\Scripts\python.exe -m app.graph_demo --json

# 3) 人工决定（SQLite 跨进程；approve / reject / changes / timeout）
.\.venv\Scripts\python.exe -m app.graph_demo --review-id <id> --decision approve --reviewer zhangsan

# 4) API + Web 工作台（单 worker）
.\.venv\Scripts\python.exe -m uvicorn app.api:create_app --factory --port 8000
# http://127.0.0.1:8000/       首屏：审查重点 + 合同 + Skill → 风险点
# http://127.0.0.1:8000/#/skills   Skill 仓库
# http://127.0.0.1:8000/docs    Swagger UI
# 注意：没有 --reload，改后端必须重启；注册报 not found 多半是旧进程

# 5) Streamlit 备用界面
.\.venv\Scripts\python.exe -m streamlit run app/ui.py

# 6) 测试与静态检查
.\.venv\Scripts\python.exe -m pytest        # 407 passed
.\.venv\Scripts\python.exe -m ruff check .
node --check app/web/app.js
```

常用接口（详见 `/docs`）：

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/api/reviews` | 上传审查（`file` + `focus` + `skill_id` + 可选 `reference` / `review_id`） |
| GET | `/api/reviews/{id}/progress` | 处理过程（节点级事件；只描述过程，不含等级，ADR-017） |
| POST | `/api/reviews/{id}/decisions` | 人工决定（`approve` / `reject` / `changes` / `timeout`） |
| GET | `/api/reviews/{id}/report?format=json\|markdown` | 报告 |
| GET | `/api/reviews/{id}/clauses` | 逐条审查意见（等级沿用规则结果） |
| POST | `/api/reviews/{id}/export` | 导出 DOCX / PDF |
| GET/PATCH/DELETE | `/api/reviews`、`/api/reviews/{id}` | 审查历史（改名 / 置顶 / 删除；`DELETE /api/reviews` 清空） |
| POST/GET | `/api/auth/*` | 注册 / 登录 / 登出 / 当前用户 / 资料 |
| GET/POST/PATCH/DELETE | `/api/skills`、`/api/skills/import` | Skill 仓库（内置 11 个；Markdown / 文件夹 / zip 导入） |
| GET/PUT/DELETE | `/api/llm`、`/api/llm/providers` | BYOK（只回 `has_key` + 尾号） |
| GET | `/api/rules` | 规则目录（只读，不返回正则 / DSL） |
| GET | `/health` | 版本 / checkpoint / 三个能力开关 |

错误码：400 类型或空文件 / 404 未知 review / 409 状态冲突 / 413 超上传上限 / 422 字段校验。

---

## 5. 配置

完整清单见 [`.env.example`](.env.example)（复制为 `.env`，**`.env` 已被 `.gitignore` 排除，不要提交 Key**）。最常用的几项：

```text
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=
LLM_MODEL=gpt-4.1-mini

CHECKPOINT_BACKEND=sqlite
CHECKPOINT_SQLITE_PATH=.data/checkpoints.sqlite
HITL_TIMEOUT_MINUTES=30

USER_DB_PATH=.data/app.sqlite
USER_SECRET_PATH=.data/secret.key

RAG_ENABLED=false        # 检索增强解释（默认关）
AGENTS_ENABLED=false     # 三专家并行（默认关）
TOOLS_ENABLED=false      # 只读工具 / MCP（默认关）

MAX_UPLOAD_MB=30
OCR_ENABLED=true
```

> **备份**：`.data/app.sqlite` 与 `.data/secret.key` 必须一起备份——只备份库不备份主密钥，已存的 Key 无法解密（界面会提示重新填写）。
>
> **优先级**：本次审查的账号级 BYOK → 环境变量默认 → 降级（无 Key 也能演示，报告会写明“要素抽取未完整执行”）。

---

## 6. 可选能力（默认关闭，不参与判级）

| 开关 | 打开后 | 关闭时 |
|---|---|---|
| `AGENTS_ENABLED=true` | `validate` 后按条款类型 + 关键词**确定性路由**出付款 / 交付 / 争议三个专家，LangGraph 并行，产出“值得注意的点 / 修改方向 / 原文引文” | 专家节点不进图，`expert_status="skipped"`，链路与结论和原来逐字一致 |
| `TOOLS_ENABLED=true` | 规则（或人工确认）后跑一次 `research_tools`：1 次 LLM 规划 + ≤3 次调用（4 个本地只读工具 + `.env` 配置的 MCP stdio 服务器） | 空节点，不建工具、不写 state |
| `RAG_ENABLED=true` | 本地 BM25（中文二元组）检索 14 篇真实法律语料，为解释补 `source_id#section` | 解释只用规则理由；检索不到也回退规则理由 |

三条边界（详见 [ADR-015](docs/devlog/02_ARCHITECTURE_DECISIONS/ADR-015-多智能体专家与只读工具层.md)、[ADR-008](docs/devlog/02_ARCHITECTURE_DECISIONS/ADR-008-RAG检索与解释质量门.md)）：

- 专家 schema 无 `risk_level` 且 `extra="forbid"`；引文定位不到整条丢弃；专家结果只进解释侧 `<untrusted_experts>` 数据区。
- 工具只跑白名单（`contract_outline` / `find_clause` / `read_field` / `search_knowledge`）+ MCP；MCP 手写 JSON-RPC 子集（`initialize → tools/list → tools/call`），`shell=False`、超时杀进程、单行 ≤1 MB，**零新依赖**；不可达只注册 `<server>/unavailable` 占位。
- 成本：开专家每次审查 +3 次 LLM 调用；开工具 +1 次规划 + ≤3 次执行。

---

## 7. 评测：数字怎么读

### 7.1 先看纪律（不看数字也行）

- **规则唯一判级**的评测不调用 LLM，不需要 Key；指标只有 `rule_level` / `contract_level` / `coverage` 三组。
- **主集（50 份）P/R=1.0 是同分布自证**，只能当回归守卫，不能当准确率。
- **留出集一旦用来定位缺陷即“已消耗”**，修复后即使全对也只能当回归，**对外数字必须来自新写的一批**。
- 新流程固定为：**写新集 → 写 gold → 跑基线 → 才改规则**；`test_holdout*_hits_are_stable` 会先把漏报写成空集合，修完必然失败并点名，此时才翻表降级。
- 对外报数必须同时给：样本 + 规则版本 + 命令 + 日期 + 结果文件；recall 分辨率是 1/11，**样本小，不能外推**。

### 7.2 十一批留出集的分工

| 批次 | 份数 / 现象 | 基线 P / R / F1 | 状态 |
|---|---|---|---|
| holdout（H01–H08） | 8 / 7 | 1.00 / 0.714 / 0.833 | ❌ 已消耗，回归守卫 |
| holdout2（H09–H20） | 12 / 9 | 修复后 1.00 | ❌ 已消耗，回归守卫 |
| holdout3（H21–H28） | 8 / 7 | 1.00 / 0.571 / 0.727 | ❌ 已消耗，回归守卫 |
| holdout4（H29–H40） | 12 / 9 | 1.00 / 0.889 / 0.941 | ❌ 已消耗（H39 已修） |
| holdout5（H41–H52） | 12 / 10 | 1.00 / 0.90 / 0.947 | ❌ 已消耗（H41 已修） |
| holdout6（H53–H64） | 12 / 11 | 1.00 / 0.727 / 0.842 | ❌ 已消耗（H53/H55/H61 已修） |
| holdout7（H65–H76） | 12 / 11 | 1.00 / 0.636 / 0.778 | ❌ 已消耗（H65–H69 已修） |
| holdout8（H77–H88） | 12 / 11 | 1.00 / 0.545 / 0.706 | ❌ 已消耗（五处已在 `version: 9` 修好） |
| holdout9（H89–H100） | 12 / 11 | 1.00 / 0.545 / 0.706 | ❌ 已消耗（五处已在 `version: 10` 修好，修后 11/0/0） |
| holdout10（H101–H112） | 12 / 11 | 1.00 / 0.545 / 0.706 | ❌ 已消耗（五处已在 `version: 11` 修好，修后 11/0/0） |
| **holdout11（H113–H124）** | **12 / 11** | **1.00 / 0.545 / 0.706** | ✅ **当前唯一可对外报数**（五处未修） |

### 7.3 当前对外数字

```powershell
.\.venv\Scripts\python.exe eval\run_eval.py --contracts data\contracts_holdout11 `
  --gold data\eval\gold_holdout11.json --gold-rules data\eval\gold_holdout11.json --tag holdout11-baseline
```

`eval/results/rules-holdout11-baseline-20261031.json`：`TP=6 FP=0 FN=5 TN=121` → **P=1.00 / R=0.545 / F1=0.706**；合同级 `5/0/5`。

漏报全部是刻意构造的 `version: 11` 未覆盖写法：H113（FOB 下 `all ocean freight charges … shall be absorbed by the Seller`）、H114（`Notwithstanding the arbitration clause …, the Buyer may elect … heard by the courts`）、H115（中文“电汇全额货款 … 收到全款后安排装运”）、H116（“对裁决有异议 … 法院请求改判”）、H117（检验期限“三日内”）。**下一轮按这五处修（`version: 11`→12），holdout11 随即降级；再报新数字必须先写 holdout12。**

主集与覆盖率：

```powershell
.\.venv\Scripts\python.exe eval\prepare_contracts.py   # 50 份 → data/contracts/ + gold_contracts.json
.\.venv\Scripts\python.exe eval\run_eval.py            # TP=11 FP=0 FN=0；覆盖率 11/21 = 0.5238
```

### 7.4 检索评测（ADR-016）

```powershell
.\.venv\Scripts\python.exe -m eval.rag_gold --write    # 100 题 → 95 题可评测（5 题语料未覆盖）
.\.venv\Scripts\python.exe -m eval.run_rag_eval
```

ranking（top-5，不设阈值）：lenient R@1 0.747 / R@3 0.958 / MRR 0.849；strict R@1 0.305 / R@3 0.758 / MRR 0.524。结果在 `eval/results/rag-20261028.json`。**两套口径必须分开报，不能写成“线上召回率”**。

---

## 8. 界面

启动 FastAPI 后打开 `http://127.0.0.1:8000/`：左侧导航壳 + 右侧两屏主体，**零 npm、零构建、零 CDN**，字体随包离线。

- **`#/`**：对话式首屏（审查重点 + 合同 + Skill 胶囊下拉，Enter 发送 / Shift+Enter 换行，可直接拖入文件）。
- **`#/skills`**：Skill 仓库（推荐网格 + 我的 Skill；新建可声明 5 类工具、附加只读文本资料；支持 Markdown / 文件夹 / zip 导入，**包内脚本永不执行**）。
- **`#/review/{id}`**：同一行标签 + 左右分屏——左侧“条款目录 / 原文全文”，右侧结论 / 建议 / 依据 / 引文 + 可编辑修订 + 采用/保留/撤销；专家意见为中性的“参考 · 专家”区块（明写不代表风险等级），Agent 轨迹折叠；支持导出 DOCX / PDF。
- **不是合同**：只显示判定依据与“换一份合同”，不显示任何风险结论。

细节（侧栏、账户设置、配色三档、审查历史、退出二次确认等）见 [`docs/devlog/03_DEV_LOGS/`](docs/devlog/03_DEV_LOGS/) 与 [`04_HANDOVER.md`](docs/devlog/04_HANDOVER.md)。

---

## 9. 目录结构

```text
app/
  graph.py / review_service.py / api.py / graph_demo.py / ui.py
  config.py / schemas.py / report_markdown.py
  nodes/      ingest · precheck · segment · extract · validate · experts
              · rules · research · hitl · explain · report
  services/   llm · accounts · secret_box · llm_providers · skill_catalog
              · evidence · document_type · checkpointer · rag · tools
  rules/      definitions.yaml（13 条，version 11）· dsl.py · engine.py
  web/        index.html / styles.css / app.js / fonts/（无框架）
eval/         prepare_contracts · metrics · run_eval · rag_gold · rag_eval · run_rag_eval · results/
data/         samples/（2 份）· contracts/（50 份）· contracts_holdout{,2..11}/ · eval/（gold）· knowledge/（14 篇）
tests/        407 个（规则 60 · API 17 · 前端 25 · 多智能体 12 · 工具/MCP 23 · 其余覆盖解析/HITL/账号等）
docs/devlog/  00_PROJECT_STATE · 01_RESEARCH_LOG · 02_ARCHITECTURE_DECISIONS · 03_DEV_LOGS
              04_HANDOVER · 05_OPEN_ISSUES · 06_RAG与多智能体资料清单
```

说明：`data/contracts/`、`data/contracts_holdout*/` 均为可重建/自拟的模拟件；`holdout11` 是当前唯一未消耗批次（holdout1–10 均已消耗，只作回归）。

---

## 10. 已知限制

- **输入与切分**：加密 PDF 明确报错；扫描件 OCR 最多 20 页，可能吞空格或把中文长句/表格串行（只产文本、不参与判级）；PDF 表格/多栏可能乱序；DOCX 无真实页码（统一 `p1`）；切分是启发式的，无标题合同走段落 fallback。
- **规则覆盖**：13 条规则只覆盖常见外贸条款；责任上限、质保期、所有权保留、合规等**无规则**（主集 21 个现象中 10 个无覆盖，覆盖率 52.4%）。同一风险的不同写法仍可能漏检：被动语态（`freight is to be paid by the Seller`）、更远的跨句、从句嵌套、中文数字期限等；`R-INC-001` 跨句窗口 260 字符、`R-DIS-003` 跨句窗口 200 字符、保额邻近 ±60/40 字符都是**启发式窗口**，长条款可能跨条匹配，需人工核对证据。
- **泛化数字**：只有 holdout11 基线可对外（12 份 / 11 现象，R=0.545，漏报 H113–H117 未修）；recall 分辨率 1/11，样本小，不能外推；silver gold **待人工复核**。
- **检索**：BM25 词法检索，同义改写与跨语言提问召回有限；仍有个别不点条号的语义指代题未进 top-5；评测数字只对该题库成立。
- **解释成本**：按风险条逐条调用（4 条风险 ≈ 4 次 LLM 调用，上限 20 条）；RAG / 专家 / 工具另有额外调用。
- **部署形态**：单机单 worker；并发锁是进程内 `RLock`，多 worker 前需换文件锁/数据库锁；`LLMRuntime` 亦为进程内字典；上传与 pending 文件无保留期清理。
- **账号与密钥**：演示形态——无找回密码 / 邮箱验证 / 登录限流；Cookie 未加 `Secure`（本地 HTTP）；备份必须库 + 主密钥一起。
- **Skill 能力边界**：自建 Skill 与参考材料只进 `<untrusted_focus>`，只改解释措辞，**不提供自定义规则或改等级**；声明工具只让解释侧重相关能力，不额外编排；附件与 zip 包只读、不执行、不落盘。
- **Agent 层信任边界**：专家之间不互相协商；MCP 子进程能力不受本项目控制，对外部署前需再评估；真实外部数据（制裁名单 / 汇率 / HS 编码 / 征信）未接入。
- **HITL 超时**是惰性检查（`GET` 时判定），不是后台定时任务；pending 时间戳已落盘，进程重启仍生效。

---

## 11. 第三方代码与许可

- 本项目代码为独立实现，未复制调研仓库源码；仅借鉴设计（contract-agent MIT、enterprise-contract-review-agent Apache-2.0、multi-agent-contract-review Apache-2.0，另有 3 个无 LICENSE 项目仅阅读）。
- 依赖：pypdf（BSD）、python-docx（MIT）、LangGraph/LangChain（MIT）、FastAPI（MIT）、Streamlit（Apache-2.0）、PyYAML（MIT）、pypdfium2（BSD-3-Clause + Apache-2.0）、rapidocr-onnxruntime（Apache-2.0）。**未引入 PyMuPDF（AGPL/商业双许可），未调用云端 OCR。**
- `app/resources/skills/` 下 4 个外部 Skill 包来自用户提供的桌面 Skill，仓库内暂未附授权说明，对外分发前需确认（[ISSUE-031](docs/devlog/05_OPEN_ISSUES.md)）。
- RAG 语料为真实法律文本（CISG / Incoterms / 民法典 / 司法解释等 14 篇），`license` 字段为当前标注，展示或对外引用前需业务/法务确认（[ISSUE-015](docs/devlog/05_OPEN_ISSUES.md)）。

---

## 12. 文档

| 想了解 | 看这里 |
|---|---|
| 3 分钟接手 / 当前进度 | [`00_PROJECT_STATE.md`](docs/devlog/00_PROJECT_STATE.md) |
| 调研与借鉴决策 | [`01_RESEARCH_LOG.md`](docs/devlog/01_RESEARCH_LOG.md) |
| 架构决策（ADR-001 ~ 016） | [`02_ARCHITECTURE_DECISIONS/README.md`](docs/devlog/02_ARCHITECTURE_DECISIONS/README.md) |
| 逐轮开发日志 | [`03_DEV_LOGS/`](docs/devlog/03_DEV_LOGS/) |
| 交接与命令速查 | [`04_HANDOVER.md`](docs/devlog/04_HANDOVER.md) |
| 未决问题 / 风险登记 | [`05_OPEN_ISSUES.md`](docs/devlog/05_OPEN_ISSUES.md) |
| RAG 与多智能体资料 | [`06_RAG与多智能体资料清单.md`](docs/devlog/06_RAG与多智能体资料清单.md) |

重点 ADR：[规则/LLM 边界](docs/devlog/02_ARCHITECTURE_DECISIONS/ADR-003-规则与LLM边界.md) · [HITL](docs/devlog/02_ARCHITECTURE_DECISIONS/ADR-002-HITL实现方式.md) · [评测方法](docs/devlog/02_ARCHITECTURE_DECISIONS/ADR-011-评测方法silver-gold与留出验证.md) · [多智能体与工具层](docs/devlog/02_ARCHITECTURE_DECISIONS/ADR-015-多智能体专家与只读工具层.md) · [检索评测](docs/devlog/02_ARCHITECTURE_DECISIONS/ADR-016-检索评测与条号加权.md)

> 本项目只做合同预审辅助，**不构成法律意见**。
