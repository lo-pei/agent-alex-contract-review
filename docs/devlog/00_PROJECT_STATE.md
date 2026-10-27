# 项目状态快照

> 更新时间：2026-10-27（第四阶段第 3 轮：英文/同义改写补强 + 三批留出集）
> 当前阶段：**第四阶段（测试与评测）进行中：规则 13 条；silver gold 21 个现象；三批留出集 28 份；当前唯一可对外报的数来自 holdout3（8 份）：P=1.00 / R=0.571 / F1=0.727**
> 项目目录：`d:\A项目\Agent_Alex外贸合同智审助手`
> Git：`cf0fd63`、`71e8a9d`、`750cca3`、`625e9bd`（第 3 步）、`e41d235`（第 4 步）、`c7f24a9`（第 6 步）、`6eaff8c`（第 4 阶段第 1 轮），本轮提交见 `git log`
> 范围变更：2026-10-27 用户明确「可以做 rag 和多 agent」→ **ADR-007**；第 5 步按 **ADR-008** 落地 RAG MVP；第 6 步按 **ADR-009** 落地 API/UI 与 pending 持久化；第 1 轮按 **ADR-010** 扩充规则并建立合同级评测基线；第 2、3 轮按 **ADR-011** 建立 silver gold、指标口径、留出验证与“留出集消耗”规则（RAG/多智能体仍默认关闭，只增强解释、不判级）

## 一句话了解项目

面向“国际货物销售合同”的 AI 预审智能体：上传 PDF/DOCX/TXT → 条款切分 → LLM 抽取关键要素 → **Python 规则引擎判定红/黄/绿风险**（唯一等级来源）→ 红色风险经 **LangGraph `interrupt()` 真人工确认** → LLM 依据规则结果、合同原文与知识片段生成解释 → Python 质量门校验后输出可追溯报告。交付：Streamlit + 命令行 + FastAPI，10 天完成。

## 当前完成度

| 模块 | 状态 | 说明 |
|---|---|---|
| 第一阶段：GitHub 调研 | ✅ 100% | 8 个仓库源码级分析；用户已确认 |
| 第二阶段：架构设计 | ✅ 100% | ADR-001 ~ ADR-011 全部**已接受**（ADR-007 范围变更、ADR-008 RAG、ADR-009 API/UI、ADR-010 规则扩充、ADR-011 评测方法与 gold 口径） |
| 第三阶段第 1 步：环境 + 最小图 | ✅ 100% | `.venv`/依赖/最小图/规则引擎/测试/git |
| 第三阶段第 2 步：解析 + 切分 | ✅ 100% | TXT/MD/文本型 PDF/DOCX；标题切分/合并/超长拆分/上限 |
| 第三阶段第 3 步：LLM 抽取 + 校验 | ✅ 100% | 17 字段抽取/引文核验/降级/字段规则 skipped；Fake LLM 测试 |
| 第三阶段第 4 步：HITL 真中断 | ✅ 100% | 条件边/`interrupt()`/审批载荷/checkpointer/幂等/惰性超时；15 个 HITL 测试 |
| 第三阶段第 5 步：解释 + 质量门 + RAG MVP | ✅ 100% | `explain_risks` 节点/越权拦截/引用定位/BM25 检索/引用白名单；28 个新测试 |
| 第三阶段第 6 步：FastAPI + Streamlit | ✅ 100% | 上传/审查/人工决定/下载 JSON+Markdown；pending 落盘；37 个新测试 |
| 第四阶段：测试与评测 | ⏳ 75% | 规则 13 条（`version: 4`，补英文/同义改写）；50 份合同 + 21 个 silver gold 现象 + 三批留出集 28 份；**当前唯一未消耗的 holdout3：P=1.00 / R=0.571 / F1=0.727**（漏报 H21/H22/H24）；检索评测（ISSUE-018）与人工复核 gold 仍未做 |
| 第五阶段：文档与交付 | ⏳ 45% | README/状态/交接/ADR/资料清单/开发日志已同步；答辩材料未做 |

## 最新产出（2026-10-27 第四阶段第 3 轮：英文/同义改写补强 + 三批留出集）

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

## 核心设计（ADR-001~010，已接受）

```text
START → ingest → segment → extract(LLM) → validate → rules(Python)
   → [有 red?] → human_review(interrupt)
   │                ├─ approve → explain(LLM [+RAG]) → report → END
   │                └─ reject / request_changes / timeout → report → END
   └─ 无 red → explain(LLM [+RAG]) → report → END
```

- 当前已实现全部 8 个节点：`ingest → segment → extract → validate → rules → [条件边] → human_review → explain → report`；
  三种交付入口均可用：CLI（`graph_demo.py`）、FastAPI（`api.py`）、Streamlit（`ui.py`），全部只依赖 `ReviewService`。
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
# 228 passed

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

# 留出集（对外报数只能用**当前未被消耗**的那一批；见 ADR-011 第 3 轮补充）
# ① 本轮唯一未消耗：holdout3（H21–H28，8 份）——引用这一组对外报数
.\.venv\Scripts\python.exe eval\run_eval.py --contracts data\contracts_holdout3 `
  --gold data\eval\gold_holdout3.json --gold-rules data\eval\gold_holdout3.json --tag holdout3
# 规则级 TP=4 FP=0 FN=3 TN=81 → P=1.00 R=0.571 F1=0.727，等级一致率 1.00
# 合同级 TP=3 FP=0 FN=3 TN=2 → P=1.00 R=0.50 F1=0.667；漏报 H21/H22/H24
# 结果：eval/results/rules-holdout3-YYYYMMDD.json

# ② 已消耗样本：只作回归守卫，不得再对外报数
.\.venv\Scripts\python.exe eval\run_eval.py --contracts data\contracts_holdout `
  --gold data\eval\gold_holdout.json --gold-rules data\eval\gold_holdout.json --tag holdout
# 修复 H01/H03 后：TP=7 FP=0 FN=0（P/R=1.0 —— 已消耗，属回归结果，不是泛化证据）

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

# FastAPI（默认 SQLite + .data/pending）
.\.venv\Scripts\python.exe -m uvicorn app.api:create_app --factory --port 8000
# POST /api/reviews（上传）→ awaiting_human=true → POST .../decisions（approve）
# → GET /api/reviews/{id}/report?format=json|markdown

# Streamlit
.\.venv\Scripts\python.exe -m streamlit run app/ui.py
```

Fake LLM 端到端（`tests/test_graph_extraction.py`）：`extraction_status=ok`、`facts.total_amount=3100000.0`、字段规则正常 pass、报告 `extracted_fields` 与 `facts` 一致；单条款超时 → 降级且字段规则 skipped，报告状态 `approved`（测试显式批准）。

HITL 端到端（`tests/test_hitl.py`，17 个）：`__interrupt__` 暂停、审批前零报告、无 red 快速通道、approve 只写一次、reject 不解释、request_changes、timeout 不通过、惰性超时、非法决策 fail-closed、重复 resume 幂等、未知 ID 报错、载荷截断、未知 override 告警、`build_graph()` 无 checkpointer 报错、两条条件边。

API/UI（`tests/test_api.py` 15 个 + `tests/test_pending_store.py` 11 个 + `tests/test_report_markdown.py` 3 个 + `tests/test_ui.py` 1 个）：上传暂停、审批后下载 JSON/Markdown、报告 409、快速通道幂等、404/422/413、文件名净化、跨 service 超时、损坏 pending、Markdown 章节与转义、Streamlit 首屏。

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
6. **第四阶段（进行中）**：
   - ~~第 1 轮：规则 7 → 13 条（ISSUE-009）~~ ✅ 每条新规则都有语料命中集合回归；
   - ~~第 2 轮：silver gold（21 现象）+ 指标（rule/contract/coverage）+ 独立留出集（8 份）~~ ✅ 留出集 P=1.00 / R=0.71 / F1=0.83，暴露 2 个英文/同义改写漏报（ISSUE-021）；
   - ~~第 3 轮：规则 `version: 4` 补英文/同义改写 + 修子串误命中与运费窗口截断 + 新写 holdout2(12)/holdout3(8)~~ ✅ holdout3 盲测 **P=1.00 / R=0.571 / F1=0.727**，暴露 3 个措辞漏报（H21/H22/H24）；
   - 下一步：① 修 H21/H22/H24 三类写法 + `R-INS-001` 保额全文级判定，**另写 holdout4** 再报数（ISSUE-021）；② 人工复核 silver gold（ISSUE-020）；③ 补规则缺口：检验条款缺失/不可抗力缺失等（ISSUE-009）；④ `100问题.md` → manifest 的检索评测映射（ISSUE-018）；⑤ 阶段 B 多智能体专家节点（ISSUE-016）。

## 当前阻塞 / 需要你拍板

| 事项 | 状态 | 需要你做什么 | 默认 |
|---|---|---|---|
| LLM API Key / 模型名 | 待提供 | 全链路演示前提供 OpenAI 兼容 Key/模型 | 代码开发不阻塞（Fake LLM 覆盖）；真实抽取/解释效果需 Key |
| RAG 知识库授权（ISSUE-015） | 语料已提供，授权待确认 | 确认真实语料可否在演示/答辩中展示原文、可否再分发 | 语料已入库 14 篇；`RAG_ENABLED=false` 默认关闭 |
| RAG 检索评测（ISSUE-015/018） | 待映射 | 把 `100问题.md` 的 source_id/section 映射到 manifest 引用 | 映射完成前不宣称召回率 |
| 多智能体角色与编排（ISSUE-016） | 待确认 | 确认是否需要专家节点（付款/交付/争议）及其资料 | 阶段 B 再做；Supervisor 仅路由 |
| 规则集范围（ISSUE-009） | 第 1 轮已扩 | 确认 13 条是否够用，或指定下一批主题（不可抗力/责任上限/质保/合规） | 13 条已落地；39/50 合同仍无命中 |
| 评测 gold（ISSUE-020） | silver 已完成，待复核 | 是否需要你/业务专家人工复核 21 个银标现象 + 三批留出的 23 个现象 | 已按 silver 跑出指标；复核前对外标注“待复核” |
| 英文/同义改写漏报（ISSUE-021） | 英文已补，仍有 3 个措辞漏报 | 是否需要继续追写法覆盖（成本高、收益递减），或转去做规则缺口/检索评测 | 下轮修 H21/H22/H24 + 保额全文级判定，另写 holdout4 再报数 |
| 首批真实 PDF/DOCX 样例 | 待提供 | 有真实脱敏合同时优先用真实件 | 已有程序化 PDF/DOCX fixture，不阻塞 |
| 长合同抽取覆盖 | 已知限制 | 是否接受 > 40 条条款时字段规则跳过 | 先保持保守（宁可跳过不误报） |
| 多进程部署 | 已知限制 | 是否需要多 worker（当前锁仅进程内） | 单机单 worker 演示（ISSUE-019） |

## 3 分钟了解项目（给新接手的人）

1. 读根目录 `README.md` 的“设计底线 / 已知限制 / 快速开始”。
2. 读 `02_ARCHITECTURE_DECISIONS/README.md` 的“关键设计一句话”，再按需读 ADR-001~011。
3. 代码入口：`app/graph.py`（图组装）→ `app/review_service.py`（启动/查询/恢复）→ `app/graph_demo.py` / `app/api.py` / `app/ui.py`（三种入口）→ `app/nodes/explain.py`（解释与质量门）；规则在 `app/rules/definitions.yaml`（13 条），评测在 `eval/`。
4. 当前已实现 ingest/segment/extract/validate/rules/human_review/explain/report、RAG 检索、FastAPI 与 Streamlit；未配置 Key 时抽取降级、解释回退规则理由。
5. 未解决事项看 `05_OPEN_ISSUES.md`（ISSUE-009 规则覆盖、ISSUE-020 silver gold 待复核、ISSUE-021 英文漏报、ISSUE-015/018 检索评测/授权、ISSUE-019 单进程假设）；RAG/多智能体资料要求看 `06_RAG与多智能体资料清单.md`；RAG 设计看 `ADR-008`，API/UI 与 pending 落盘看 `ADR-009`，规则扩充看 `ADR-010`，评测方法与 gold 口径看 `ADR-011`。

## 文件地图

```text
开发提示词.md                          # 需求与约束（RAG/多智能体部分以 ADR-007 为准）
README.md                              # 项目介绍、启动、设计底线、限制
requirements.txt / requirements-dev.txt# 锁定依赖（Python 3.12）
pyproject.toml                         # ruff / pytest 配置
.env.example                           # 环境变量模板（无真实 Key）
app/
  config.py                            # 环境变量与上限（MAX_* / CHECKPOINT_* / HITL_TIMEOUT_MINUTES / PENDING_DIR / UPLOAD_DIR / RAG_*）
  schemas.py                           # Pydantic 契约（抽取 schema / RuleEvaluation / Report / ApprovalPayload / Explanation）
  graph.py                             # LangGraph 组装（8 节点 + 两条条件边 + 强制 checkpointer）
  review_service.py                    # start/get/resume（幂等 + 惰性超时 + pending 持久化 + review_id 锁）
  graph_demo.py                        # CLI 演示（SQLite 跨进程；--decision 恢复）
  api.py                               # FastAPI（上传/查询/决定/下载；错误码 400/404/409/413/422）
  ui.py                                # Streamlit 中文界面（上传/审批/报告/下载）
  report_markdown.py                   # ReviewReport → Markdown（纯渲染，不重算等级）
  nodes/ingest.py                      # TXT/MD/PDF/DOCX → canonical text + 页偏移
  nodes/segment.py                     # 标题切分/合并/超长拆分/段落 fallback
  nodes/extract.py                     # LLM 17 字段抽取（唯一 LLM 抽取节点）
  nodes/validate.py                    # 引文核验/数值归一/一致性 → facts + to_verify
  nodes/rules.py                       # 规则节点（等级唯一来源）
  nodes/hitl.py                        # 审批载荷 + interrupt() + 决策校验 + 条件边
  nodes/report.py                      # 报告汇总（跟随人工终态 + limitation）
  services/llm.py                      # 结构化输出 + 1 次修复重试 + 异常类型
  services/evidence.py                 # locate_quote（精确 → NFC/空白规范化）
  services/checkpointer.py             # memory/sqlite 工厂 + JsonPlusSerializer 类型登记
  services/pending_store.py            # pending 时间戳落盘（原子写 + review_id 白名单）
  services/rag.py                      # 本地 BM25 + 中文二元组 + MD/DOCX 切分 + manifest 校验 + 缓存
  rules/definitions.yaml               # 13 条规则（11 文本 + 2 字段，version 4）
  rules/dsl.py                         # 条件 DSL
  rules/engine.py                      # 规则加载/求值/证据/fail-closed/skipped
eval/
  prepare_contracts.py                 # 拆分模拟合同 → data/contracts/ + data/eval/gold_contracts.json
  metrics.py                           # 指标纯计算（rule_level / contract_level / coverage），无第三方依赖
  run_eval.py                          # 规则级评测 + 指标（不调 LLM）→ eval/results/rules[-tag]-YYYYMMDD.json
  results/                             # 评测结果（JSON，可版本化；主集 + 三批留出集各一份）
data/samples/                          # 2 份自拟脱敏样例
data/contracts/                        # 50 份模拟合同（由 eval/prepare_contracts.py 生成，可重建）
data/contracts_holdout/                # 8 份留出合同（H01–H08）→ 已消耗，回归守卫
data/contracts_holdout2/               # 12 份留出合同（H09–H20）→ 已消耗，回归守卫
data/contracts_holdout3/               # 8 份留出合同（H21–H28）→ 唯一未消耗，对外报数用这一批
data/eval/gold_contracts.json          # 50 份 / 105 条“条款 → Q 编号 → 期望召回 → 干扰项”（检索期望）
data/eval/gold_rules.json              # silver gold：21 个风险现象（11 有规则 / 10 为规则缺口），待人工复核
data/eval/gold_holdout.json            # 留出 gold：7 个现象（H04 为干净对照）
data/eval/gold_holdout2.json           # 留出 gold：9 个现象（H10/H13/H20 为干净对照）
data/eval/gold_holdout3.json           # 留出 gold：7 个现象（H27/H28 为干净对照）
data/knowledge/                        # 真实语料 14 篇 + manifest；模拟合同1..6.md 为评测来源，不进 manifest
tests/                                 # 228 个测试（API 15 / pending 11 / RAG 22 / 解释 13 / HITL 17 / 规则含三批留出回归 / 指标 11）
tests/fakes.py                         # Fake LLM（无需 Key）
tests/fixtures/pdf_builder.py          # 纯标准库构造最小 PDF（测试用）
docs/devlog/
  00_PROJECT_STATE.md                  # 本文件
  01_RESEARCH_LOG.md                   # 第一阶段调研
  02_ARCHITECTURE_DECISIONS/           # ADR-001~011（均已接受）
  03_DEV_LOGS/2026-10-26.md            # 调研 + ADR + 第 1/2/3/4/5/6 步日志
  03_DEV_LOGS/2026-10-27.md            # 第四阶段第 1/2/3 轮：规则扩充、评测基线、silver gold、留出验证、英文补强与三批留出集
  04_HANDOVER.md                       # 交接说明
  05_OPEN_ISSUES.md                    # 待决事项
  06_RAG与多智能体资料清单.md          # RAG/多智能体需要准备的资料与目录格式
```

