# 开发交接文档（Handover）

> 更新时间：2026-10-31（阶段 4 第 10 轮：**先按 holdout9 基线只修那五处**（`version: 9`→10：`R-INC-001` 1.4→1.5“价格已含运费” / `R-DIS-003` 1.3→1.4 instead 式选择权（单列分支绕开 `award` 守卫）/ `R-PAY-001` 1.2→1.3 “全部/全额价款 + 确认收款后 + 发运” / `R-DIS-004` 1.4→1.5 中文“请求重新审理/再审/重新仲裁” / `R-INP-002` 1.3→1.4 中文数词期限），修后 holdout9 `11/0/0`、holdout1–8 全 FP=0、主集 `hit_counts` 与 v9 逐条相同；**再新写中英混合 holdout10（H101–H112，12 份：5 英 / 7 中）+ gold**（11 个现象 / 11 条文本规则，H111/H112 干净对照），在 `version: 10` 上**只跑一次盲测基线、不改规则** → `TP=6 FP=0 FN=5 TN=121`，**P=1.00 / R=0.545 / F1=0.706**（合同级 `5/0/5`）；五个漏报全是刻意构造的未覆盖写法：H101 FOB 下 `all costs of carriage … shall be defrayed by the Seller`、H102 `In lieu of arbitration … seek a ruling … from the High Court`、H103 中文“款项全额到账后方安排装运”、H104 “申请对裁决的实体问题进行复审”、H105 “两个工作日”；H111/H112 零触发；五个漏报按基线钉成空集合 + `test_holdout10_hits_are_stable`；**十批 112 份里只有 holdout10 未消耗，对外数字改引** `eval/results/rules-holdout10-baseline-20261030.json`；全量 **406 测试**；阶段 4 第 9 轮：**先按 holdout8 基线只修那五处**（`version: 8`→9：`R-INC-001` `(?:for|on) the Seller's account` / `R-DIS-003` 跨句 `refer` / `R-PAY-001` “收到全部价款后再装运” / `R-DIS-004` 中文“不服裁决向法院上诉” / `R-INP-002` 立即检验与当日通知），修后 holdout8 `11/0/0`、holdout1–7 全 FP=0、主集 `hit_counts` 与 v8 逐条相同；**再新写中英混合 holdout9（H89–H100，12 份：5 英 / 7 中）+ gold**（11 个现象 / 11 条文本规则，H99/H100 干净对照），在 `version: 9` 规则上**只跑盲测基线、不改规则** → `TP=6 FP=0 FN=5 TN=121`，**P=1.00 / R=0.545 / F1=0.706**（合同级 `5/0/5`）；五个漏报全是刻意构造的未覆盖写法：H89 FOB 下“价格已含至目的港运费”、H90 `may instead elect … decided by the courts`、H91 中文“确认收款后方可发运”、H92 “请求重新审理”、H93 中文数字“二十四小时”；H99/H100 零触发；五个漏报按基线钉成空集合 + `test_holdout9_hits_are_stable`；**九批 100 份里只有 holdout9 未消耗，对外数字改引** `eval/results/rules-holdout9-baseline-20261029.json`；全量 **405 测试**；阶段 4 第 8 轮：用户选“先写 holdout8 再报新泛化数字”，因此**新写中英混合留出集 holdout8（H77–H88，12 份：5 英 / 7 中）+ gold**（11 个现象 / 11 条文本规则，H87/H88 干净对照），在 `version: 8` 规则上**只跑盲测基线、不改规则** → `TP=6 FP=0 FN=5 TN=121`，**P=1.00 / R=0.545 / F1=0.706**（合同级 `5/0/5`）；五个漏报全是刻意构造的未覆盖写法：H77 `The ocean freight … is on the Seller's account`、H78 `refer the dispute to the courts`、H79 中文“七个工作日内付清全部货款”、H80 “仲裁庭的裁决…收到裁决书之日起…提起上诉”、H83 `inspect immediately upon discharge`；H87/H88 零触发；五个漏报按基线钉成空集合 + `test_holdout8_hits_are_stable`；**八批 88 份里只有 holdout8 未消耗，对外数字改引这一份基线**；全量 **404 测试**；阶段 4 第 7 轮第二步：**按 holdout7 盲测基线修四处写法**，规则 `version: 7`→**8** —— `R-INC-001` 卖方账上运费迂回语态、`R-DIS-003` 跨句或裁或审（`award`/新条标题守卫）、`R-PAY-001` 中文“全部价款”（排除分期）、`R-DIS-004` `bring the matter before the courts`；每处先探针（7 批 76 份 + 主集 50 份 + 样例）确认零新误报；修后 holdout7 `11/0/0`（H75/H76 仍零触发）、holdout1–6 全 FP=0、主集 `hit_counts` 与 v7 逐条相同；`test_holdout7_hits_are_stable` 先失败点名 H65/H66/H67/H69 再翻表降级；阶段 4 第 7 轮第一步：用户明确“先做 holdout7 盲测基线”，因此**只写集 + 只跑基线、当轮不改规则**——新建中英混合 holdout7（H65–H76，12 份）+ gold（11 现象 / 11 条规则，H75/H76 干净对照），基线 `TP=7 FP=0 FN=4 TN=121` → **P=1.00 / R=0.636 / F1=0.778**，漏报 H65（`for the Seller's account`）/H66（跨句或裁或审）/H67（中文“全部价款”）/H69（`bring the matter before the courts`），H75/H76 零触发；四个漏报先按基线钉成空集合；阶段 4 第 6 轮：**先写纯英文 holdout6（H53–H64，12 份）+ gold，再改规则**——盲测基线 P=1.00 / R=0.727 / F1=0.842（漏报 H53/H55/H61），随后修 `R-INC-001` 卖方付运费倒装、`R-DIS-003` 连接词后逗号、`R-PAY-001` entire/full … before shipment，规则 `version: 6`→**7**，holdout6 降级为回归集；测试改为“先按基线钉表 → 修后必然失败 → 再翻表”；阶段 4 第 5 轮 + 界面轮 16：**先写 holdout5（H41–H52，12 份）+ gold，再改规则**——盲测基线 P=1.00 / R=0.90 / F1=0.947（唯一漏报 H41，与 H39 同型），随后修 `R-DIS-004` 英文分支（modal 与动词之间允许插时间状语），holdout4/5 均降级为回归集；结果页新增“这份报告怎么读”（关闭 ISSUE-024）；新增 `DELETE /api/reviews` 批量清空（ISSUE-022 第 7 条解决）；界面轮 15：检索评测落地——100 题 gold 两层映射（95 题可评测 / 5 题语料未覆盖）+ ranking / production 双口径 + 点名条号/来源排序加权（lenient R@3 0.800→0.958、strict R@3 0.390→0.758），ADR-016，关闭 ISSUE-018、新增 ISSUE-033；界面轮 14：多智能体专家并行（付款 / 交付 / 争议）+ 只读工具层（4 个本地工具 + MCP stdio）+ 专家意见与 Agent 轨迹上屏 + 两个开关默认关闭；界面轮 13：上传上限 30 MB + 图片 PDF 本地 OCR + 4 个外部 Skill 包内置 + zip 导入 + 完整原文 + 条款去重；界面轮 12：配色三档 + Skill 工具/附件 + 头像裁剪 + 标签行 + 历史即时刷新 + 切分精度 + 左原文右意见独立滚动；界面轮 10：账户设置 B 端分区弹窗 + 主题色 5 套 + 字号三档 + 侧栏去掉昵称邮箱；界面轮 9：个人账户弹窗 + Skill 编辑 + 厂商 20；界面轮 8：Skill Markdown 导入 + 注册 not found 定位；界面轮 7：Skill 仓库独立页；界面轮 6：审查历史子目录 + 记录运维；界面轮 5：账号/记录/Skill/BYOK；界面轮 4：主区两屏；第四阶段第 4 轮：规则 version 5 + 第四批留出集）
> 当前状态：**第三阶段第 6 步完成（解释 + 质量门 + RAG + FastAPI）；界面轮 15 完成（按 ADR-016 落地检索评测：`eval/rag_gold.py` + `data/eval/rag_label_map.yaml` 把 `100问题.md` 的概念标签翻成 `source_id#section`，生成可 diff 的 `data/eval/gold_rag.json`（**95 题可评测 / 5 题语料未覆盖**，缺口不进分母）；`eval/run_rag_eval.py` 同时报 `ranking`（top-5 不过阈值）与 `production`（`RAG_TOP_K=3` / `RAG_MIN_SCORE=1.0`）× `lenient` / `strict`，结果落 `eval/results/rag-YYYYMMDD.json`；评测暴露“解读稿压过条文/条号不参与打分”后加**只改排序**的加权（点名条号 ×2.5、条文原文再 ×1.1、点名法律名 ×1.15，抽不出条号全 1.0）：lenient R@1 0.516→0.747 / R@3 0.800→0.958、strict R@1 0.158→0.305 / R@3 0.390→0.758；`app/services/chinese_numbers.py` 统一“第584条 ↔ 第五百八十四条”；**398 个测试通过**）；界面轮 14 完成（按 ADR-015 落地可选 Agent 层：`validate_extraction` 之后“付款 / 交付 / 争议”三个专家并行出参考意见（确定性路由、schema 无 `risk_level`、引文定位不到即丢弃），`rules`/人工确认之后插一次 `research_tools`（4 个本地只读工具 + MCP stdio/JSON-RPC 子集，零新依赖、`shell=False`、超时杀进程、无 LLM 走确定性检索）；专家意见与 Agent 轨迹上屏，专家块只用中性色；`AGENTS_ENABLED` / `TOOLS_ENABLED` 默认 false，关闭时与确定性主干逐字一致；`API_VERSION 1.1.0`）；界面轮 13 完成（上传上限 15→30 MB 且前后端同一配置源；图片/扫描 PDF 走本地 OCR（`pypdfium2` + `rapidocr-onnxruntime`，离线、只在无文本层时触发、≤20 页、只产文本不判级）；桌面 4 个外部 Skill 包复制进 `app/resources/skills/` 作 `builtin:*`（内置 Skill 7→11）；Skill 仓库支持 zip 包导入（不落盘、不执行）；“两个付款条件”双层去重（切分 + 展示）并为旧记录兜底；结果页合同名/Skill/审查重点/状态收成同一行标签；左栏新增“原文全文”tab 按原排版呈现）；界面轮 12 完成（配色改“白天/黑夜/跟随系统”三档，主题色 5 套下线；Skill 从一段提示词扩成“指令 + 5 个可声明工具 + 只读文本附件”；头像上传后先裁剪再存 128×128 JPEG；审查页顶部改标签行并删掉对话式长叙述；审查与确认后侧栏历史即时刷新；未命中规则改“这条没问题”的人话；条款切分修 4 类误切 + 短标题 + 前言标注；逐条审查左目录与原文、右意见与“采用修改/保留原文/撤销”，三块各自滚动）；界面轮 5 完成（账号体系 / 审查记录 / Skill 仓库 / BYOK 按 ADR-013 落地，侧栏 = 导航 + API 配置 + 接口文档 + 账号区）；上传仍先判断是不是合同（不是即 `not_contract`，不切条款/不抽取/不判级）；第四阶段第 1–10 轮进行中：规则 13 条（`version: 10`）、50 份模拟合同 + 21 个 silver gold 现象、三组评测指标、**十批留出集 112 份 / 97 个现象（九批 100 份已消耗，仅 holdout10 未消耗）**；**当前对外报数只引 holdout10 的盲测基线**（中英混合，规则 `version: 10`、改规则之前，12 份 / 11 个现象）：P=1.00 / R=0.545 / F1=0.706，漏报 H101/H102/H103/H104/H105 **尚未修**；holdout9 基线 P=1.00 / R=0.545 / F1=0.706（H89/H90/H91/H92/H93 已在 `version: 10` 修好，修后 `11/0/0` 只作回归）、holdout8 / holdout7 / holdout6 / holdout5 基线保留为历史记录；holdout1–9 均已降级为回归集，**下一步若按 holdout10 基线修五处（`version: 10`→11）后须再写 holdout11 才能报新数字**；阶段 4 第 6–10 轮把纪律写进测试（先按基线钉表 → 修后必然失败 → 再翻表降级），全量 **406 测试**；阶段 4 第 5 轮另完成结果页“这份报告怎么读”（关闭 ISSUE-024）与 `DELETE /api/reviews` 批量清空（ISSUE-022 第 7 条解决）；人工复核 silver gold（ISSUE-020）仍未完成
> 交接原则：任何新接手的人只读本文件 + `00_PROJECT_STATE.md` + `02_ARCHITECTURE_DECISIONS/README.md`，就能继续开发。

---

## 1. 项目是做什么的

面向“国际货物销售合同”的 AI 预审智能体。输入 PDF / DOCX / TXT 合同，输出结构化风险报告：

- 条款切分并保留页码、字符偏移；
- LLM 只做要素抽取与风险解释；
- Python 规则引擎唯一决定 `red / yellow / pass`；
- 红色风险触发 LangGraph `interrupt()`，人工确认后才出最终报告；
- 报告每条风险都有 `rule_id + reason + 原文引用 + 文件:页码:字符偏移`；
- 交付：侧栏导航壳 + 对话式主区（FastAPI 托管，给审查重点/附件/Skill → 查看风险点 → 人工确认 → 下载报告）+ 账号与审查记录 + BYOK 模型配置 + 命令行 + FastAPI 接口；Streamlit 备用。

硬约束来自根目录 `开发提示词.md`：技术栈 Python / LangGraph / Streamlit / FastAPI / Pydantic；规则决定等级，LLM 只抽取与解释；HITL 必须暂停/恢复；全部代码要解释清、能测试、边界明确。**2026-10-27 用户明确放开 RAG 与多智能体（ADR-007）**：允许 RAG、专家节点与 Supervisor 路由，但判级仍只由 Python 规则产生、HITL 仍必须真中断、证据仍必须可追溯；三个开关默认关闭（`RAG_ENABLED=false`、`AGENTS_ENABLED=false`、`TOOLS_ENABLED=false`，界面轮 14 按 ADR-015 实现了后两个）。训练模型、Docker、前端框架仍禁止——**主区两屏 + 侧栏导航壳用 HTML/CSS/JS 手写，未引入 React/Vue/npm/CDN，字体随包离线**（ADR-009 第 3、5 轮补充）。

---

## 2. 当前完成度

| 项 | 状态 | 证据 |
|---|---|---|
| GitHub 调研 | ✅ 完成 | `01_RESEARCH_LOG.md`，8 个仓库源码级分析 |
| 架构 ADR | ✅ 完成，全部已接受 | `02_ARCHITECTURE_DECISIONS/ADR-001~016` |
| 环境与依赖 | ✅ 完成 | `.venv`（Python 3.12.10）+ `requirements*.txt`；实际版本见 ADR-006 §6 |
| 业务代码（第 3 步） | ✅ 解析/切分/抽取/校验/规则可用 | `app/` |
| HITL（第 4 步） | ✅ 条件边 + `interrupt()` + checkpointer | `app/nodes/hitl.py`、`app/review_service.py`、`app/services/checkpointer.py` |
| 解释 / RAG（第 5 步） | ✅ 质量门 + BM25 + 真实语料 | `app/nodes/explain.py`、`app/services/rag.py`、`data/knowledge/` |
| API / UI（第 6 步） | ✅ FastAPI + pending 落盘 + Streamlit 备用 | `app/api.py`、`app/ui.py`、`app/report_markdown.py`、`app/services/pending_store.py` |
| B 端审查工作台（界面轮 2） | ✅ 四视图 + 本地字体 + 只读规则目录 | `app/web/index.html`、`app/web/styles.css`、`app/web/app.js`、`app/web/fonts/`；`GET /`、`GET /static/*`、`GET /api/rules`；`tests/test_web.py`（6 项）、`tests/test_api.py::test_rule_catalog_matches_definitions` |
| 账号 / 记录 / Skill / BYOK（界面轮 5） | ✅ 本地 SQLite + 密文盒 + 每审查模型运行时 | `app/services/accounts.py`、`app/services/secret_box.py`、`app/services/llm_providers.py`、`app/services/skill_catalog.py`、`app/services/llm.py`（`LLMRuntime` / `review_llm_scope`）；`tests/test_accounts.py`（28 项）；`API_VERSION 1.0.0` |
| 阶段 4 第 10 轮第二步（新写 holdout10 + 新泛化基线） | ✅ 只写集 + 只跑一次基线，**规则 `version: 10` 一条不动**；五个漏报按基线钉成空集合 | `data/contracts_holdout10/H101–H112.md`（12 份：5 英 / 7 中）、`data/eval/gold_holdout10.json`（11 现象 / 11 条文本规则 + H111/H112 干净对照）、`eval/results/rules-holdout10-baseline-20261030.json`（**当前唯一可对外引用**：`TP=6 FP=0 FN=5 TN=121`，P=1.00 / R=0.545 / F1=0.706，漏报 H101/H102/H103/H104/H105）；`tests/test_rules.py`（`HOLDOUT10_DIR` + `EXPECTED_HOLDOUT10_HITS` + `test_holdout10_hits_are_stable`，五个漏报先写空集合）；全量 **406 passed** |
| 阶段 4 第 10 轮第一步（按 holdout9 基线修五处，`version: 10`） | ✅ 只修基线暴露的五处，探针先验；修后只作回归 | `app/rules/definitions.yaml`（`version: 10`：`R-INC-001` 1.5 价格已含运费 / `R-DIS-003` 1.4 instead 式选择权 / `R-PAY-001` 1.3 确认收款后发运 / `R-DIS-004` 1.5 中文“请求重新审理” / `R-INP-002` 1.4 中文数词期限）、`tests/test_rules.py`（五个漏报翻成 H89/H90/H91/H92/H93）、`tests/test_api.py`（`ruleset_version == 10`）、`eval/results/rules-holdout9-v10-20261030.json`（11/0/0，仅回归）；全量 **406 passed** |
| 阶段 4 第 9 轮第二步（新写 holdout9 + 新泛化基线） | ✅ 只写集 + 只跑基线，**规则 `version: 9` 一条不动**；五个漏报按基线钉成空集合；第 10 轮已按该批基线修完，本批降级为回归集 | `data/contracts_holdout9/H89–H100.md`（12 份：5 英 / 7 中）、`data/eval/gold_holdout9.json`（11 现象 / 11 条文本规则 + H99/H100 干净对照）、`eval/results/rules-holdout9-baseline-20261029.json`（**历史基线、已消耗**：`TP=6 FP=0 FN=5 TN=121`，P=1.00 / R=0.545 / F1=0.706，漏报 H89/H90/H91/H92/H93）；`tests/test_rules.py`（`HOLDOUT9_DIR` + `EXPECTED_HOLDOUT9_HITS` + `test_holdout9_hits_are_stable`，五个漏报原为空集合、第 10 轮翻表）；全量 **405 passed** |
| 阶段 4 第 9 轮第一步（按 holdout8 基线修五处，`version: 9`） | ✅ 只修基线暴露的五处，探针先验；修后只作回归 | `app/rules/definitions.yaml`（`version: 9`：`R-INC-001` `(?:for|on) the Seller's account` 且保留 `at the Seller's expense/cost` / `R-DIS-003` 跨句 `\brefer` / `R-PAY-001` 中文“收到全部价款后再装运” / `R-DIS-004` 中文“不服裁决向法院上诉” / `R-INP-002` `immediately … upon discharge` + `on the same day`）、`tests/test_rules.py`（五个漏报翻成 H77/H78/H79/H80/H83）、`tests/test_api.py`（`ruleset_version == 9`）、`eval/results/rules-holdout8-v9-20261029.json`（11/0/0，仅回归）；全量 **405 passed** |
| 阶段 4 第 8 轮（新写 holdout8 + 新泛化基线） | ✅ 第 9 轮已按该批基线修完五处（`version: 9`），本批降级为回归集 | `data/contracts_holdout8/H77–H88.md`（12 份：5 英 / 7 中）、`data/eval/gold_holdout8.json`（11 现象 / 11 条文本规则 + H87/H88 干净对照）、`eval/results/rules-holdout8-baseline-20261029.json`（**历史基线、已消耗**：`TP=6 FP=0 FN=5 TN=121`，P=1.00 / R=0.545 / F1=0.706，漏报 H77/H78/H79/H80/H83）；`tests/test_rules.py`（`HOLDOUT8_DIR` + `EXPECTED_HOLDOUT8_HITS` + `test_holdout8_hits_are_stable`，五个漏报原为空集合、第 9 轮翻表）
| 阶段 4 第 7 轮第二步（按 holdout7 基线修四处，`version: 8`） | ✅ 只修基线暴露的四处，探针先验；修后只作回归 | `app/rules/definitions.yaml`（`version: 8`：`R-INC-001` 卖方账上运费 / `R-DIS-003` 跨句（`award` 守卫）/ `R-PAY-001` 中文“全部价款” / `R-DIS-004` `bring the matter`）、`tests/test_rules.py`（四个漏报翻成 H65/H66/H67/H69）、`tests/test_api.py`（`ruleset_version == 8`）、`eval/results/rules-holdout7-v8-20261029.json`（11/0/0，仅回归）；全量 **403 passed** |
| 阶段 4 第 7 轮第一步（中英混合 holdout7 盲测基线） | ✅ 只写集 + 只跑基线，**当轮不改规则**（规则仍 `version: 7`）；四个漏报按基线钉成空集合 | `data/contracts_holdout7/H65–H76.md`（12 份中英混合）、`data/eval/gold_holdout7.json`（11 现象 / 11 条文本规则 + H75/H76 干净对照）、`eval/results/rules-holdout7-baseline-20261029.json`（历史基线：`TP=7 FP=0 FN=4 TN=121`，P=1.00 / R=0.636 / F1=0.778，漏报 H65/H66/H67/H69）；`tests/test_rules.py`（`EXPECTED_HOLDOUT7_HITS` + `test_holdout7_hits_are_stable`，四个漏报先写空集合）；全量 **403 passed** |
| 阶段 4 第 6 轮（纯英文 holdout6 盲测 + 三处英文写法修复） | ✅ 先写集、先基线、再改规则；纪律写进测试 | `data/contracts_holdout6/H53–H64.md`（12 份全英文）、`data/eval/gold_holdout6.json`（11 现象 / 11 条文本规则 + H62/H63 干净对照）、`eval/results/rules-holdout6-baseline-20261028.json`（**唯一可对外引用**：P=1.00 / R=0.727 / F1=0.842，漏报 H53/H55/H61）、`eval/results/rules-holdout6-20261028.json`（修后 11/0/0，仅回归）；`app/rules/definitions.yaml`（`version: 7`：`R-INC-001` 英文倒装分支 / `R-DIS-003` `\s+or[,\s]\s*` / `R-PAY-001` entire … before shipment 正则）；`tests/test_rules.py`（`EXPECTED_HOLDOUT6_HITS` + `test_holdout6_hits_are_stable`，含“修前空集合 → 修后翻表”两步）；`tests/test_api.py`（`ruleset_version == 7`）；全量 **402 passed** |
| 阶段 4 第 5 轮 + 界面轮 16（holdout5 盲测 / H39 修复 / 报告导读 / 批量清空） | ✅ 先写集、再改规则；报告有导读；清空一次事务完成 | `data/contracts_holdout5/H41–H52.md`（12 份）、`data/eval/gold_holdout5.json`（10 现象 / 9 条规则 + H43/H52 干净对照）、`eval/results/rules-holdout5-baseline-20261028.json`（当时唯一可对外引用：P=1.00 / R=0.90 / F1=0.947，现为历史记录）、`eval/results/rules-holdout5-20261028.json`（修后，仅回归）；`app/rules/definitions.yaml`（`version: 6`）；`tests/test_rules.py`（`EXPECTED_HOLDOUT5_HITS` + `test_holdout5_hits_are_stable`，H39 断言翻为“必须命中”）；`app/web/app.js`（`LEGAL.guide` / `openGuide()` / 两处 `data-guide`）；`app/api.py`（`DELETE /api/reviews` + `ReviewPurgeResult`）、`app/services/accounts.py`（`delete_reviews`）；`tests/test_web.py`（报告导读）、`tests/test_accounts.py`（401 + 跨账号 + 幂等） |
| 检索评测（界面轮 15） | ✅ 100 题 → 95 题可评测（5 题语料未覆盖）；ranking / production × lenient / strict；只改排序的加权 | `eval/rag_gold.py`（`resolve_label` / `build_gold`）、`data/eval/rag_label_map.yaml`（27 个手判标签 + 12 条 gaps）、`data/eval/gold_rag.json`、`eval/rag_eval.py`（`score` / `_first_rank` / `_summarize`）、`eval/run_rag_eval.py`（`validate_gold` / `_rank` / `run`）、`app/services/chinese_numbers.py`（`to_chinese_number` / `from_chinese_number`）、`app/services/rag.py`（`_article_numbers` / `_query_boosts`）、`eval/results/rag-20261028.json`、`tests/test_rag_eval.py`（6 项）、`tests/test_rag_boost.py`（6 项）；全量 **398 passed** |
| 多智能体专家并行 + 只读工具层（界面轮 14） | ✅ 三个专家并行出参考意见（不判级）；本地 4 个只读工具 + MCP stdio；两个开关默认关闭 | `app/nodes/experts.py`（`EXPERT_SPECS` / `select_experts` / `route_experts` / `collect_expert_findings`）、`app/services/tools.py`（`ToolSpec` / `ToolRegistry` / `McpStdioClient` / `build_tool_registry` / `parse_mcp_servers`）、`app/nodes/research.py`（`research_tools` / `_plan` / `_fallback_plan` / `_execute`）、`app/graph.py`（并行 fan-out + `research_tools`）、`app/schemas.py`（`ExpertFinding` / `ExpertOpinion` / `ToolCallRecord` / `AgentTrace` + `operator.add` reducer）、`app/nodes/explain.py`（`<untrusted_experts>` / `<untrusted_tools>`）、`app/services/clause_review.py`（`_agent_trace`）、`app/nodes/report.py`、`app/web/app.js`（`expertBlocks` / `agentTraceBlock`）、`app/web/styles.css`（`.expert-*` / `.trace-*`）、`.env.example`、`tests/test_agents.py`（10 项）、`tests/test_tools.py`（23 项）、`tests/test_web.py`（+1）；全量 **386 passed** |
| 上传 30 MB + 图片 PDF OCR + 外部 Skill 包 + zip 导入 + 原文全文（界面轮 13） | ✅ 扫描件也能审查；内置 Skill 7→11；Skill 可传 zip；付款条件不再重复；左栏可看完整原文 | `app/services/ocr.py`（`ocr_available` / `ocr_pdf_pages`）、`app/nodes/ingest.py`（`MIN_PAGE_TEXT_CHARS` / `MIN_PDF_TEXT_CHARS` / `ocr_attempted` / `fail(message, extra_warnings)`）、`app/config.py`（`ocr_enabled` / `ocr_max_pages` / `ocr_render_scale`）、`app/resources/skills/`（4 个外部包）、`app/services/skill_catalog.py`（`_PACKAGE_SPECS` / `packaged_skills` / `parse_skill_package`）、`app/api.py`（`POST /api/skills/import`）、`app/nodes/segment.py`（`_merge_duplicate_headings`）、`app/services/clause_review.py`（`_display_title` / `_merge_adjacent_duplicates`）、`app/schemas.py`（`ClauseReviewList.contract_text`）、`app/web/app.js`（`MAX_BYTES` 30 MB / `renderContractFulltext` / `applyPaneMode`）、`app/web/index.html`（`.pane-tabs` / `#contract-fulltext` / zip 导入文案）、`app/web/styles.css`（`.pane-tabs` / `.contract-fulltext`）、`tests/test_ocr.py`（+5）、`tests/test_accounts.py`（+4）、`tests/test_segment.py`（+1）、`tests/test_clause_review.py`（+2）、`tests/test_web.py`（+1 并改写 2）；全量 **347 passed** |
| 配色三档 + Skill 工具/附件 + 头像裁剪 + 左原文右意见（界面轮 12） | ✅ 主题色下线；Skill 可声明 5 个工具、可挂只读文本附件；头像可拖动/缩放裁剪；标签行 + 三块独立滚动 | `app/web/index.html`（`[data-scheme-value]`、`#skill-tools` / `#skill-asset-pick` / `#skill-asset-input` / `#skill-asset-list`、`#avatar-crop-dialog`）、`app/web/app.js`（`resolvedScheme` / `applyPrefs` / `cropGeometry` / `cropResult` / `applyCrop` / `reviewChip` / `clauseListItem` / `renderClauseOrigin` / `keepClause` / `refreshHistory` / `loadSkillTools` / `renderToolChips` / `renderAssetList`）、`app/web/styles.css`（`html[data-scheme]`、`.chip-tag` / `.chip-wide`、`.workbench-grid` 三块独立滚动、`.clause-origin`、`.detail-actions`、`.pass-block`、`.tool-chip` / `.asset-*`、`.crop-stage`）、`app/services/skill_catalog.py`（`TOOL_CATALOG` / `SkillAsset` / `compose_focus`）、`app/services/accounts.py`（`tools` / `assets` 列 + `_clean_skill_*`）、`app/api.py`（`GET /api/skills/tools`）、`app/nodes/segment.py`（同行标题 / 字段黑名单 / 说明块 / 中英合并 / `_short_title`）、`app/services/clause_review.py`（`is_preamble`）；`tests/test_web.py`（+3 项、改写 3 项）、`tests/test_accounts.py`（+4 项）、`tests/test_segment.py`（+3 项）、`tests/test_clause_review.py`（+1 项）；全量 **334 passed** + CDP 冒烟 |
| 账户设置 B 端弹窗 + 侧栏收口（界面轮 10） | ✅ 左侧分区（个人信息 / 通用 / 数据管理 / 关于）+ 字号三档（主题色已在轮 12 换成三档配色）；侧栏不再显示昵称与邮箱 | `app/web/index.html`（`#account-dialog` 分区结构、`#account-line` 删除）、`app/web/app.js`（`setAccountPanel` / `loadAccountStats` / `loadAboutInfo` / `syncPrefControls` / `resetPrefs`、`prefs.scheme` / `prefs.font`）、`app/web/styles.css`（`.account-nav` / `.account-panel` / `.seg` / `--ui-text-scale` + `html[data-font]`、全量 `font-size` 换算）、`tests/test_web.py`（个人账户测试扩到分区与三档配色断言） |
| 个人账户 + Skill 编辑 + 紧凑 + 厂商 20 + 密码自动填充（界面轮 9） | ✅ 头像/昵称/系统设置/二次确认清数据；自建 Skill 可编辑；厂商 10→20 | `app/web/index.html`（`#account-row` / `#account-dialog` / `#llm-form` autocomplete）、`app/web/app.js`（`renderAvatar` / `askClear` / `runClear` / `fillSkillForm`；`squareThumbnail` 已在轮 12 换成裁剪弹窗）、`app/web/styles.css`（`.avatar` / `.account-confirm` / `.skill-head` / `.skill-detail`）、`app/services/accounts.py`（`avatar` 列 + `update_profile` + `update_skill` + `_clean_skill_fields`）、`app/api.py`（`PATCH /api/auth/profile`、`PATCH /api/skills/{id}`）、`app/services/llm_providers.py`（20 家）、`tests/test_accounts.py`（+7）、`tests/test_web.py`（+3） |
| Skill 导入 + 注册 not found 修复（界面轮 8） | ✅ Markdown / 文件夹批量导入；旧进程导致注册 404 已定位并重启 | `app/web/app.js`（`parseSkillMarkdown` / `readEntryFiles` / `filesFromDataTransfer` / `importSkillFiles`、`renderSkillsPage` 右栏导入卡片）、`app/web/styles.css`（`.dropzone` / `.import-log` / `.import-actions`）、`tests/test_web.py`（+1 项，共 19）；`README.md` 快速开始补“改后端必须重启、`openapi` 版本应为 1.0.0” |
| Skill 仓库独立页 + 自绘下拉 + 页脚贴右 + 输入区收窄（界面轮 7） | ✅ `#/skills` 页面 + listbox 下拉 + 页脚一行贴右 | `app/web/index.html`（删 `#skills-dialog`、`href="#/skills"`）、`app/web/app.js`（`renderSkillsPage` / `renderSkillSelect` / `toggleSkillMenu`）、`app/web/styles.css`（`.skills-grid` / `.tool-skill` / `.skill-menu` / `.sheet-foot` / 720px）、`tests/test_web.py`（+2 项） |
| 历史可运维 + Skill 归位 + 满屏（界面轮 6） | ✅ 侧栏子目录 + 改名/置顶/删除 + 定高弹窗 | `app/services/accounts.py`（`title`/`pinned` + `ALTER TABLE` 升级 + `rename/set_pinned/delete`）、`app/review_service.py`（`discard`）、`app/api.py`（`PATCH|DELETE /api/reviews/{id}`）、`app/web/*`；`tests/test_accounts.py`（+4 项）、`tests/test_web.py`（+3 项） |
| 主区极简 + 侧栏保留（界面轮 4） | ✅ 两屏：上传 → 风险点 | `app/web/index.html`、`app/web/app.js`、`app/web/styles.css`；侧栏/顶栏导航壳保留；hash 路由只留 `#/` 与 `#/review/{id}`；待确认态渲染 `approval.findings`；`tests/test_web.py`（10 项） |
| 文档类型闸门（界面轮 3） | ✅ 先判断是不是合同，不是就停 | `app/services/document_type.py`、`app/nodes/precheck.py`、`app/graph.py`（`ingest → precheck → segment | report`）；`status=not_contract`；`tests/test_document_type.py`（11 项）、`tests/test_api.py::test_non_contract_upload_is_not_reviewed`、`tests/test_web.py::test_runtime_internals_stay_out_of_the_ui` |
| 测试 | ✅ 406 个通过 | `tests/`；`pytest` 全绿；Fake LLM 无需 Key |
| 规则集 | ✅ 13 条 | `app/rules/definitions.yaml`（`version: 10`，三类措辞 + 保额邻近判定 + `R-DIS-004` 允许 modal 与动词间插时间状语 + 英文卖方付运费倒装 / 连接词后逗号 / `entire … before shipment` + 卖方账上运费迂回语态（`for|on` 与 `at … expense|cost` 两式）/ 跨句或裁或审（含 `refer`）/ 中文“全部价款”与“收全款再发货” / `bring the matter` 与中文“不服裁决上诉” / 立即检验与当日通知 + “价格已含运费” / instead 式选择权 / “确认收款后发运” / 中文“请求重新审理” / 中文数词期限）；6 条新规则各有语料命中集合回归（ADR-010） |
| 评测集 / 指标 | ⏳ 主集完成、**十批留出完成（九批已消耗，仅 holdout10 可报数）**、**检索评测已完成**、待复核 | `data/eval/gold_rules.json`（21 现象，silver）+ `gold_holdout{,2,3,4,5,6,7,8,9,10}.json`（7/9/7/9/10/11/11/11/11/11 现象）+ `eval/results/rules-*.json`；**holdout10 只引基线文件** `rules-holdout10-baseline-20261030.json`（P=1.00 / R=0.545 / F1=0.706，漏报 H101/H102/H103/H104/H105 **尚未修**）；holdout9 基线 `P=1.00 / R=0.545 / F1=0.706`（已在 v10 修好，修后 11/0/0 只作回归）、holdout8 / holdout7 / holdout6 / holdout5 基线为历史记录；**下一步若修完须新写 holdout11**；**检索**：`data/eval/gold_rag.json`（100 题 → 95 题可评测）+ `eval/results/rag-20261028.json`（lenient R@3 0.958 / strict R@3 0.758）；**silver gold 未经人工复核** |
| Git 仓库 | ✅ 已初始化 | `cf0fd63`、`71e8a9d`、`750cca3`、`625e9bd`、`e41d235`、`c7f24a9`、`6eaff8c`、`5dc05bd`、`c540259`、`eba67c0`、`892ddf2`、`302630a`、`84820f7`、`f9771e7`（界面轮 15）、`4f45ab1`（阶段 4 第 5 轮 + 界面轮 16）、`c57c53d`（阶段 4 第 6 轮）、`6052400`（第 6 轮版本残留修正）、`675db4a`（阶段 4 第 7 轮第一步）、`afc094f`（第 7 轮第二步 `version: 8`）、`d4a3783`（第 7 轮提交号记录）、`6206272`（阶段 4 第 8 轮：新写 holdout8 盲测基线，规则未改）、`ba413c6`（阶段 4 第 9 轮：按 holdout8 基线修五处（`version: 9`）+ 新写 holdout9 盲测基线，当前 HEAD） |

> 报数纪律（ADR-011 / 第 5–10 轮补充）：对外只引用 holdout10 的**盲测基线**（`eval/results/rules-holdout10-baseline-20261030.json`，12 份中英混合 / 11 个现象，规则 `version: 10`，P=1.00 / R=0.545 / F1=0.706），并注明“silver gold 待复核、样本 12 份、漏报 H101/H102/H103/H104/H105 尚未修”。主集（50 份）P/R=1.0 是**同分布**产物；holdout、holdout2、holdout3、holdout4、holdout5、holdout6、holdout7、holdout8、holdout9 九批都已被用于定位缺陷（“已消耗”），修复后即使 1.0 也只能当回归守卫；**下一步若按 holdout10 基线修完这五处，holdout10 也降级，新数字必须来自新写的 holdout11**。覆盖率 52.4%（主集 gold）仍是真实短板；留出集的 `coverage=1.0` 是平凡结果，不能与 recall 混读。

> 检索报数纪律（ADR-016）：只说“在 `100问题.md` 的 **95 题可评测**子集上的指标”，并同时给出口径（`ranking` 还是 `production`、`lenient` 还是 `strict`）；不能写成“线上召回率 0.958”，也不能把 lenient 与 strict、ranking 与 production 混着比。5 题语料未覆盖（#42/#69/#86/#87/#88）必须单独提，不能塞回分母。

### 2.1 架构决策速览（ADR-001~016）

| ADR | 结论 | 状态 |
|---|---|---|
| 001 图结构 | 确定性顺序主干 + 两个条件边（是否有 red / 是否 approve）+ 单一 HITL 门；不用 Supervisor/并行/单体 ReAct | **已接受**（两条条件边均已实现：`route_by_risk`、`route_after_human_review`；界面轮 14 按 ADR-015 增加**可选**专家并行，默认关闭，主干仍顺序） |
| 002 HITL | 节点内 `interrupt()` + checkpointer + `Command(resume=HitlDecision)`；审批前零业务写入；超时 → `unreviewed_red_risk`，绝不自动通过 | **已接受**（第 4 步已实现，回填见 ADR-002 §7） |
| 003 规则/LLM | 规则唯一判级；LLM 只抽 17 字段与解释；schema 禁止 `risk_level`；引文核验、越权表述拦截、失败兜底 | **已接受** |
| 004 持久化 | 运行用 `SqliteSaver`（同步，当前实现）/测试用 `InMemorySaver`；`thread_id=review_id`；pending/报告/审计分离；惰性超时 | **已接受**（ADR-004 原写 `AsyncSqliteSaver`，第 4 步实际用同步 `SqliteSaver`，见 ADR-002 §7） |
| 005 解析/证据 | pypdf + python-docx + TXT；canonical text + 页/全局偏移；`文件名:p页:start-end`；精确/空白规范化定位 | **已接受** |
| 006 环境 | Python 3.12 + LangGraph 1.2.17 等最新稳定依赖；OpenAI 兼容接口；无 Docker/Redis/Postgres | **已接受** |
| 007 范围变更 | 允许 RAG/多智能体/Supervisor（仅路由）；判级/HITL/证据边界不变；默认开关关闭 | **已接受**（2026-10-27；RAG 第 5 步已实现，多智能体界面轮 14 按 ADR-015 已实现） |
| 008 RAG/质量门 | 本地 BM25 + 中文二元组；`source_id#section` 白名单；Python 质量门拦截越权；无命中/配置错误降级 | **已接受**（第 5 步已实现） |
| 009 API/UI | API/UI 只依赖 `ReviewService`；pending 时间戳原子落盘；上传校验；Markdown 纯渲染；**第 2 轮补充：原生 Web 前端；第 3 轮补充：B 端工作台（framed-sheet + hash 路由四视图 + 本地 IBM Plex 字体 + 只读 `GET /api/rules`）；第 4 轮补充：移除侧栏“运行环境”块 + 非合同页，`API_VERSION` 0.9.0；第 5 轮补充：收成极简两屏（上传 / 风险点），待确认先展示审批载荷中的红色风险，下载走 `/report?format=markdown`**，Streamlit 降为备用 | **已接受**（第 6 步已实现；第 2–5 轮补充均已实现） |
| 010 规则扩充/评测 | 规则 7 → 13 条；新规则准入四关；模拟合同拆入 `data/contracts/`；评测只报触发情况 | **已接受**（2026-10-27 第 1 轮已实现） |
| 011 评测方法 | gold 三层（检索期望 / silver 规则 gold / 留出 gold）；三组指标；留出集发现漏报也不回改规则；**留出集一旦被用于定位缺陷即视为“已消耗”，只能作回归守卫**；报数纪律；第 4 轮补“保额邻近判定”与“测试钉住已知漏报”；第 5 轮补“先写集、先跑基线、再改规则，只引基线文件”；第 6 轮补“纯英文留出集”与“测试先钉基线、修后必然失败再翻表”；第 7 轮补“中英混合留出集”“跨句分支的 `award` 守卫与 200 字符窗口”以及“七批全部消耗后须新写 holdout8” | **已接受**（2026-10-27 第 2–4 轮、2026-10-28 第 5 轮、2026-10-29 第 6–7 轮已实现） |
| 012 类型闸门 | `ingest` 后 `precheck_document` 判定“是不是合同”；否 → `not_contract` 直接出报告，不切条款/不抽取/不判级/不触发 HITL | **已接受**（界面轮 3 已实现，`API_VERSION` 0.9.0） |
| 013 账号与 BYOK | 账号/会话/Skill/记录/模型配置落本地 SQLite（零新依赖）；口令 PBKDF2 + 会话只存 token 哈希；API Key 密文盒加密、接口只回尾号；`LLMRuntime` 按 `review_id` 登记 + `ContextVar` 作用域；**审查重点 / Skill 只进 `<untrusted_focus>`，不改等级** | **已接受**（界面轮 5 已实现，`API_VERSION` 1.0.0） |
| 014 OCR 与外部 Skill 包 | 上传上限 15→30 MB（单一配置源）；**只在 PDF 无文本层/单页少文本时**用 `pypdfium2` + `rapidocr-onnxruntime` 本地 OCR（离线、≤20 页、逐页降级），OCR 只进 `raw_text`、**不参与判级**；4 个外部 Skill 包复制进 `app/resources/skills/` 作 `builtin:*`；zip 导入只读文本、根目录 `SKILL.md` 必填、**不执行包内脚本**、`allowed-tools` 不映射 | **已接受**（界面轮 13 已实现） |
| 015 多智能体专家与只读工具层 | `validate_extraction` 之后**确定性路由**出“付款 / 交付 / 争议”三个专家并行出参考意见（schema **无 `risk_level`**、引文定位不到即丢弃、并行只写 reducer 字段）；`rules`/人工确认之后插一次 `research_tools`：4 个本地只读工具 + MCP stdio/JSON-RPC 子集（零新依赖、`shell=False`、超时杀进程），无 LLM 走确定性检索；**两个开关默认关闭，关闭时拓扑与结论和原来完全一致** | **已接受**（界面轮 14 已实现，`API_VERSION` 1.1.0） |
| 016 检索评测与条号加权 | `100问题.md` 的概念标签经“通用条号正则 + 人工 YAML”两层映射成 `source_id#section`，一个标签允许多条可接受片段（条文原文 / 英文原文 / 解读稿）；`gaps` 显式登记、**缺口不进分母**（95 / 100）；同时报 `ranking`（top-5、`min_score=0`）与 `production`（真实 `RAG_TOP_K`/`RAG_MIN_SCORE`）× `lenient` / `strict`，**禁止混读**；检索侧只做**排序加权**（点名条号 ×2.5、条文原文 ×1.1、点名来源 ×1.15），不打分新片段、不过滤、不改判级；gold 过期即失败 | **已接受**（界面轮 15 已实现） |

---

## 3. 环境准备

### 3.1 本机现状（2026-10-26 验证）

| 项 | 结果 |
|---|---|
| 系统 | Windows，PowerShell 5 |
| 默认 `python` | 3.14（`C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64`） |
| 可用的 3.12 | `py -3.12` → `C:\Users\lenovo\AppData\Local\Python\pythoncore-3.12-64\python.exe` |
| uv 自带 3.12 | `C:\Users\lenovo\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\python.exe` |
| GitHub API | 可访问（HTTP 200） |
| `git clone github.com:443` | 连接被重置；调研用 `codeload.github.com` 快照替代；**推送同理**（`github.com:443` 仍不通，`api.github.com` 与 `ssh.github.com:443` 可通） |
| GitHub 远端仓库 | `origin` = `ssh://git@ssh.github.com:443/lo-pei/agent-alex-contract-review.git`（private，默认分支 `master`）；本地 `core.sshCommand` 指向仓库 Deploy Key `~/.ssh/agent_alex_deploy`（只对该仓库有写权限，勿删；删了需重新加 key 才能推送） |
| `git push` 走法 | 直接 `git push` 即可（配好 `core.sshCommand` 后无需额外参数）；换机器时先 `ssh -i <key> -p 443 -T git@ssh.github.com` 验证 |
| PyPI | 可访问 |

### 3.2 版本决策（重要）

`开发提示词.md` 写“Python 3.9+”，但 2026-10-26 最新依赖的实际要求是：

| 包 | 最新版本 | requires-python |
|---|---|---|
| langgraph | 1.2.17 | ≥3.10 |
| langchain | 1.4.7 | ≥3.10 |
| langchain-openai | 1.7.2 | ≥3.10 |
| langgraph-checkpoint-sqlite | 3.1.2 | ≥3.10 |
| fastapi | 0.162.0 | ≥3.10 |
| uvicorn | 0.54.0 | ≥3.10 |
| streamlit | 1.66.1 | **≥3.11** |
| pydantic | 2.14.1 | ≥3.10 |
| python-docx | 1.2.0 | ≥3.9 |
| pypdf | 6.21.2 | ≥3.9 |
| pytest | 9.1.1 | ≥3.10 |
| ruff | 0.17.2 | ≥3.7 |

**结论：用 Python 3.12**（本机已装；用户已确认“按建议继续”）。如果必须严格支持 3.9，只能锁旧版本（LangGraph 0.2.x / Streamlit 旧版），会牺牲当前 API 与 HITL 文档能力，且需要额外兼容测试；不建议。该事项已关闭（ISSUE-004），决策记录在 `ADR-006-运行环境与依赖策略.md`。

### 3.3 初始化命令（已执行）

```powershell
cd "d:\A项目\Agent_Alex外贸合同智审助手"

# 1) 创建虚拟环境（用 3.12，不要用默认 3.14）
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip

# 2) 安装依赖（版本锁定在 requirements.txt / requirements-dev.txt）
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

# 3) 验证
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m app.graph_demo
```

实际安装结果（2026-10-26）：Python 3.12.10、LangGraph 1.2.17、Streamlit 1.66.1、FastAPI 0.162.0、Pydantic 2.14.1、pypdf 6.21.2、python-docx 1.2.0、PyYAML 6.0.3、pytest 9.1.1、ruff 0.17.2；无冲突。详见 ADR-006 §6。

> 注意：`pypdf` 是 BSD 许可；不要引入 PyMuPDF（AGPL/商业双许可）作为默认依赖。扫描件 OCR 不在 MVP 范围。

### 3.4 环境变量（`.env.example` 已提供，`.env` 尚未创建）

`.env.example` 已提交；真实 `.env` 尚未创建（没有 Key，不影响最小图与测试）。字段见下方模板。

```dotenv
# .env.example（不提交真实 Key）
LLM_PROVIDER=openai_compatible
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

# RAG（默认关闭）
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

MAX_UPLOAD_MB=30
MAX_CONTRACT_CHARS=200000
MAX_PAGES=200

# 图片 PDF 本地 OCR（ADR-014）
OCR_ENABLED=true
OCR_MAX_PAGES=20
OCR_RENDER_SCALE=2.2

# 账号 / 审查记录 / Skill / BYOK（ADR-013）
USER_DB_PATH=.data/app.sqlite
USER_SECRET_PATH=.data/secret.key
SESSION_TTL_DAYS=7
```

> 真实 `.env` 必须进 `.gitignore`；代码、日志、README 不得出现 Key。
> `.data/app.sqlite`（账号/会话/Skill/记录/密文 Key）与 `.data/secret.key`（主密钥）必须一起备份：**只备份库不备份主密钥，已保存的 API Key 无法解密**，界面会提示重新填写。

---

## 4. 目录现状（第 6 步已创建的部分）

```text
Agent_Alex外贸合同智审助手/
├─ 开发提示词.md
├─ requirements.txt / requirements-dev.txt
├─ pyproject.toml                 # ruff + pytest 配置
├─ .env.example                   # 已提供；真实 .env 未创建
├─ .gitignore
├─ README.md
├─ app/
│  ├─ __init__.py
│  ├─ config.py                   # 环境变量、路径、上限（CHECKPOINT_* / HITL_TIMEOUT_MINUTES / PENDING_DIR / UPLOAD_DIR / RAG_*）
│  ├─ schemas.py                  # State/Clause/Evidence/ExtractedFieldSet/RuleEvaluation/Explanation/Report/ApprovalPayload
│  ├─ graph.py                    # 8 节点 + 两条条件边 + 强制 checkpointer
│  ├─ review_service.py           # start/get/resume（幂等 + 惰性超时 + pending 落盘 + review_id RLock）
│  ├─ graph_demo.py               # CLI（SQLite 跨进程；--review-id/--decision）
│  ├─ api.py                      # FastAPI（上传/查询/决定/下载；错误码 400/404/409/413/422；托管 `/` 与 `/static`）
│  ├─ web/
│  │  ├─ index.html               # 原生 Web 前端：四步单页（上传 → 审查 → 人工确认 → 报告）
│  │  ├─ styles.css               # 设计令牌/深浅色/响应式/打印（无框架、无 CDN）
│  │  └─ app.js                   # 状态机/上传/轮询/审批表单/报告渲染/转义（不判级、不拼 Command）
│  ├─ ui.py                       # Streamlit（备用：上传 → 审批 → 报告 → 下载）
│  ├─ report_markdown.py          # ReviewReport → Markdown（纯渲染）
│  ├─ nodes/
│  │  ├─ ingest.py                # TXT/MD/PDF/DOCX → pages + canonical text + 全局偏移
│  │  ├─ segment.py               # 标题切分 + 合并 + 超长拆分 + 段落 fallback
│  │  ├─ extract.py               # LLM 17 字段抽取（唯一 LLM 抽取节点）
│  │  ├─ validate.py              # 引文核验 + 数值归一 + 一致性 → facts / to_verify
│  │  ├─ rules.py                 # 规则节点（唯一等级来源）
│  │  ├─ hitl.py                  # 审批载荷 + interrupt() + 决策校验 + 两条条件边
│  │  ├─ explain.py               # LLM 解释 + Python 质量门 + RAG 引用白名单 + 规则兜底
│  │  └─ report.py                # 报告汇总（跟随人工终态 + limitation）
│  ├─ rules/
│  │  ├─ definitions.yaml         # 13 条规则（11 文本 + 2 字段，version 5）
│  │  ├─ dsl.py                   # 白名单条件 DSL
│  │  └─ engine.py                # 加载/求值/证据/fail-closed/skipped
│  ├─ services/
│  │  ├─ llm.py                   # 结构化输出 + 1 次修复 + 异常类型 + get_llm()
│  │  ├─ evidence.py              # locate_quote（精确 → NFC/空白规范化）
│  │  ├─ checkpointer.py          # memory/sqlite 工厂 + JsonPlusSerializer 类型登记
│  │  ├─ pending_store.py         # pending 时间戳原子落盘 + review_id 白名单
│  │  └─ rag.py                   # BM25 + 中文二元组 + MD/DOCX 切分 + manifest 校验 + 缓存
│  └─ __main__.py                 # 计划（未创建）
├─ tests/
│  ├─ conftest.py
│  ├─ fakes.py                    # Fake LLM（无需 Key）
│  ├─ test_ingest.py / test_ingest_formats.py / test_segment.py
│  ├─ test_evidence.py / test_llm_service.py / test_extract.py / test_validate.py / test_rules.py
│  │  └─ test_rules.py 含 6 条新规则正反 fixture + 6 个英文/同义改写 + 6 个改写措辞 fixture + 50 份语料与十批留出的命中集合回归 + 样例零误报
│  ├─ test_eval_metrics.py        # 指标计算 + gold 完整性 + 留出自洽（11 个，纯计算，无需 Key）
│  ├─ test_hitl.py                # HITL 暂停/恢复/幂等/超时/载荷/非法决策（17 个）
│  ├─ test_explain.py             # 解释与质量门（13 个）
│  ├─ test_rag.py                 # BM25/manifest/DOCX/长段/缓存/真实语料（22 个）
│  ├─ test_pending_store.py       # 落盘/跨进程超时/损坏文件/非法 ID（11 个）
│  ├─ test_api.py                 # FastAPI 全流程与错误码（15 个）
│  ├─ test_web.py                 # 原生前端：入口/静态资源/无外链/不判级（5 个）
│  ├─ test_report_markdown.py     # Markdown 渲染（3 个）
│  ├─ test_ui.py                  # Streamlit 冒烟（1 个）
│  ├─ test_graph.py / test_graph_extraction.py
│  └─ fixtures/pdf_builder.py     # 纯标准库构造最小 PDF
├─ data/
│  ├─ samples/                    # 2 份自拟脱敏合同（TXT）
│  ├─ contracts/                  # 50 份模拟合同（由 eval/prepare_contracts.py 生成，可重建）
│  ├─ contracts_holdout/          # 8 份留出合同（H01–H08）→ 已消耗，回归守卫
│  ├─ contracts_holdout2/         # 12 份留出合同（H09–H20）→ 已消耗，回归守卫
│  ├─ contracts_holdout3/         # 8 份留出合同（H21–H28）→ 第 4 轮已消耗，回归守卫
│  ├─ contracts_holdout4/         # 12 份留出合同（H29–H40）→ 第 5 轮已消耗（H39 已修），回归守卫
│  ├─ contracts_holdout5/         # 12 份留出合同（H41–H52）→ 第 5 轮已消耗，回归守卫
│  ├─ contracts_holdout6/         # 12 份留出合同（H53–H64，纯英文）→ 第 6 轮已消耗，回归守卫
│  ├─ contracts_holdout7/         # 12 份留出合同（H65–H76，中英混合）→ 第 7 轮已消耗，回归守卫
│  ├─ contracts_holdout8/         # 12 份留出合同（H77–H88，中英混合）→ 第 9 轮已按该批基线修完，回归守卫
│  ├─ contracts_holdout9/         # 12 份留出合同（H89–H100，中英混合）→ 第 10 轮已按该批基线修完，回归守卫
│  ├─ contracts_holdout10/        # 12 份留出合同（H101–H112，中英混合）→ 第 10 轮盲测，**当前唯一可报数集；只引基线文件**
│  ├─ eval/gold_contracts.json    # 50 份 / 105 条“条款 → Q 编号 → 期望召回 → 干扰项”（检索期望）
│  ├─ eval/gold_rules.json        # silver gold：21 个风险现象（11 有规则 / 10 缺口）
│  ├─ eval/gold_holdout.json      # 留出 gold：7 个现象（H04 为干净对照）
│  ├─ eval/gold_holdout2.json     # 留出 gold：9 个现象（H10/H13/H20 为干净对照）
│  ├─ eval/gold_holdout3.json     # 留出 gold：7 个现象（H27/H28 为干净对照）
│  ├─ eval/gold_holdout4.json     # 留出 gold：9 个现象（H32/H34/H36 为干净对照）
│  ├─ eval/gold_holdout5.json     # 留出 gold：10 个现象 / 9 条规则（H43/H52 为干净对照）
│  ├─ eval/gold_holdout6.json     # 留出 gold：11 个现象 / 11 条文本规则（H62/H63 为干净对照）
│  ├─ eval/gold_holdout7.json     # 留出 gold：11 个现象 / 11 条文本规则（H75/H76 为干净对照），第 7 轮已消耗
│  ├─ eval/gold_holdout8.json     # 留出 gold：11 个现象 / 11 条文本规则（H87/H88 为干净对照），第 9 轮已消耗
│  ├─ eval/gold_holdout9.json     # 留出 gold：11 个现象 / 11 条文本规则（H99/H100 为干净对照），第 10 轮已消耗
│  ├─ eval/gold_holdout10.json    # 留出 gold：11 个现象 / 11 条文本规则（H111/H112 为干净对照），当前对外数字来源，待人工复核
│  └─ knowledge/                  # 真实语料 14 篇 + manifest；模拟合同1..6.md 为评测来源，不进 manifest
├─ eval/
│  ├─ prepare_contracts.py        # 拆分模拟合同 → data/contracts/ + gold
│  ├─ metrics.py                  # 指标纯计算（rule_level / contract_level / coverage）
│  ├─ run_eval.py                 # 规则级评测 + 指标 → eval/results/rules[-tag]-YYYYMMDD.json
│  ├─ rag_gold.py                 # 100问题.md → gold_rag.json（两层映射；--write 落盘）
│  ├─ rag_eval.py                 # 检索指标纯计算（recall@k / MRR / 分组 / miss 明细）
│  ├─ run_rag_eval.py             # 检索评测 → eval/results/rag-YYYYMMDD.json（ranking / production）
│  └─ results/                    # 评测结果
└─ docs/
   └─ devlog/                     # 本目录
```

> 标注“计划”的文件/目录**尚不存在**；不要按规划假设它们已可用。

---

## 5. 启动方式

| 形态 | 命令 | 状态 |
|---|---|---|
| 全链路（TXT，无 Key 走降级） | `.\.venv\Scripts\python.exe -m app.graph_demo` | ✅ 可用（风险样例停在人工确认） |
| 全链路（PDF/DOCX） | `.\.venv\Scripts\python.exe -m app.graph_demo path\to\contract.pdf` | ✅ 可用 |
| 报告 JSON | `.\.venv\Scripts\python.exe -m app.graph_demo --json` | ✅ 可用 |
| 恢复人工决定 | `.\.venv\Scripts\python.exe -m app.graph_demo --review-id <id> --decision approve --reviewer zhangsan` | ✅ 可用（SQLite 跨进程） |
| 超时语义 | `.\.venv\Scripts\python.exe -m app.graph_demo --review-id <id> --decision timeout` | ✅ 可用 → `unreviewed_red_risk` |
| 测试 | `.\.venv\Scripts\python.exe -m pytest` | ✅ 406 个通过 |
| 静态检查 | `.\.venv\Scripts\python.exe -m ruff check .` | ✅ 通过 |
| 命令行（统一入口） | `python -m app --file data/samples/contract.txt` | ⏳ 计划（`__main__.py` 未创建） |
| API | `.\.venv\Scripts\python.exe -m uvicorn app.api:create_app --factory --port 8000` | ✅ 可用（`/docs` 可试；默认 SQLite + 文件 pending） |
| **Web 前端（主界面）** | `.\.venv\Scripts\python.exe -m uvicorn app.api:create_app --factory --port 8000` → 打开 `http://127.0.0.1:8000/` | ✅ 可用（侧栏 = 导航 + API 配置 + 接口文档 + 账号区；主区两屏：上传合同 → 风险点；结果页 = 顶部**同一行标签**（合同名 / Skill / 审查重点 / 状态）+ 左栏“条款目录 / 原文全文”两个 tab + 右栏意见与“采用修改·保留原文·撤销”，三块各自滚动；结果页 URL 为 `#/review/{id}`；结果页两处“这份报告怎么读”打开七节静态说明 + 由 `GET /api/reviews/{id}/report?format=json` 的 `limitations` 补第八节；账号区“清空审查记录”走一次 `DELETE /api/reviews`） |
| Streamlit（备用） | `.\.venv\Scripts\python.exe -m streamlit run app/ui.py` | ✅ 可用（上传/审批/下载） |
| 拆合同 + gold | `.\.venv\Scripts\python.exe eval\prepare_contracts.py` | ✅ 可用（50 份合同 / 105 条映射） |
| 主集评测 | `.\.venv\Scripts\python.exe eval\run_eval.py` | ✅ 可用（无需 Key；含三组指标） |
| **对外报数（holdout10 基线，当前）** | `... eval\run_eval.py --contracts data\contracts_holdout10 --gold data\eval\gold_holdout10.json --gold-rules data\eval\gold_holdout10.json --tag holdout10-baseline` | ✅ 可用（**当前唯一可对外引用**：`rules-holdout10-baseline-20261030.json`，规则 `version: 10`、12 份 / 11 现象，P=1.00 / R=0.545 / F1=0.706，漏报 H101/H102/H103/H104/H105 **尚未修**；修完重跑出的 11/0/0 只作回归） |
| 历史基线（holdout9） | `... --contracts data\contracts_holdout9 --gold data\eval\gold_holdout9.json --gold-rules data\eval\gold_holdout9.json --tag holdout9-baseline` | ✅ 可用（`rules-holdout9-baseline-20261029.json`：P=1.00 / R=0.545 / F1=0.706，漏报 H89/H90/H91/H92/H93 已在 `version: 10` 修好，修后 11/0/0 只作回归） |
| 历史基线（holdout8） | `... --contracts data\contracts_holdout8 --gold data\eval\gold_holdout8.json --gold-rules data\eval\gold_holdout8.json --tag holdout8-baseline` | ✅ 可用（`rules-holdout8-baseline-20261029.json`：P=1.00 / R=0.545 / F1=0.706，漏报 H77/H78/H79/H80/H83 已在 `version: 9` 修好，修后 11/0/0 只作回归） |
| 历史基线（holdout7） | `... --contracts data\contracts_holdout7 --gold data\eval\gold_holdout7.json --gold-rules data\eval\gold_holdout7.json --tag holdout7-baseline` | ✅ 可用（`rules-holdout7-baseline-20261029.json`：P=1.00 / R=0.636 / F1=0.778，漏报 H65/H66/H67/H69 已在 `version: 8` 修好，修后 11/0/0 只作回归） |
| 回归守卫（已消耗样本） | `--contracts data\contracts_holdout{,2,3,4,5,6,7,8,9} --tag holdout{,2,3,4,5,6,7,8,9}` | ✅ 可用（结果不得对外报数；九批全部已消耗） |
| **检索 gold 重建** | `.\.venv\Scripts\python.exe -m eval.rag_gold --write` | ✅ 可用（`100问题.md` 或语料变动后必跑；不跑则 `pytest` 的 gold 过期守卫会失败） |
| **检索评测（ranking + production）** | `.\.venv\Scripts\python.exe -m eval.run_rag_eval` | ✅ 可用（无需 Key；输出 `eval/results/rag-YYYYMMDD.json`；`--tag` 可加后缀） |
| 检索评测（只跑指定 gold） | `... -m eval.run_rag_eval --gold data\eval\gold_rag.json --top-k 5` | ✅ 可用 |
| 全链路评测（含抽取/解释） | 计划 | ⏳ 未实现（需要 LLM Key；规则级 gold 待人工复核） |

> 标 ✅ 的命令已实际执行验证；标 ⏳ 的尚不可用。`--decision` 支持 `approve / reject / changes(request_changes) / timeout`；`--memory` 用内存 checkpointer（仅单进程调试）。API 必须用 `--factory`（`create_app` 是工厂函数，不是模块级 `app`）；多 worker 未支持（ISSUE-019）。

---

## 6. 已确认的设计底线

1. **规则唯一判级**：`red / yellow / pass` 只能由 Python 规则产生；LLM 输出（抽取/解释/专家）里不允许有 `risk_level` 字段。
2. **LLM 只做两件事**：抽取条款要素（缺失写 null）；解释风险与给建议（必须引用原文）。RAG/专家节点只能增强解释，不能新增或改写等级。
3. **HITL 真中断**：节点内 `interrupt()`；checkpointer 持久化；`Command(resume=HitlDecision)` 恢复；审批前零业务写入；超时不自动通过。
4. **失败显式降级**：LLM 失败 → 抽取降级/解释兜底；规则执行异常 → fail-closed 系统 red（`is_system_finding=true`，进入 HITL）；HITL 超时 → `unreviewed_red_risk`；RAG 无命中 → 退化为纯规则解释。
5. **证据可定位**：`文件:第N页:字符start-end`；LLM 引文必须精确出现在条款原文（仅允许空白/Unicode 规范化）；知识引用必须能定位到 `source_id#section`。
6. **抽取状态是一等状态**：`ok / degraded / skipped` 都必须进报告；`degraded` 时字段规则 `skipped`，不得把系统降级伪装成“合同缺少条款”。
7. **图结构**：确定性顺序主干；两个条件边只用于“是否有 red”“是否 approve”；单体 ReAct 禁用；Supervisor 仅白名单路由（ADR-007）；界面轮 14 起**可选**专家并行（ADR-015），默认关闭，主干顺序不变。
8. **持久化**：运行用 SQLite checkpointer，测试用内存；`thread_id=review_id`；pending 时间戳落盘 `.data/pending/<review_id>.json`；报告由 state 派生。
9. **RAG/多智能体/工具默认关闭**：`RAG_ENABLED=false`、`AGENTS_ENABLED=false`、`TOOLS_ENABLED=false`；开启后专家与工具也只用于解释/建议/补充材料，不得判级；并行分支只能写带 reducer 的字段（否则 `INVALID_CONCURRENT_GRAPH_UPDATE`）；MCP 只允许 `.env` 里配置的 stdio 命令，只读、超时杀进程。
10. **入口分层**：CLI / FastAPI / 原生 Web 前端 / Streamlit 全部只依赖 `ReviewService`；不拼 `Command(resume=...)`；前端/API/UI 都不判级（ADR-009 + 第 2 轮补充）。
11. **不引入**：Neo4j/GraphRAG、向量数据库、训练模型、Docker、React/Vue 及任何前端框架/npm 构建/CDN、Postgres/Redis、PyMuPDF 默认依赖、无许可证仓库代码。原生 Web 前端是手写 `HTML/CSS/JS`，由 FastAPI 托管。

---

## 7. 已知坑（务必先看）

| # | 坑 | 处理 |
|---|---|---|
| 1 | 默认 `python` 是 3.14，直接 `python -m venv` 会装不上/跑不稳 | 显式用 `py -3.12 -m venv .venv`，命令都用 `.venv\Scripts\python.exe` |
| 2 | `git clone github.com` 在本机被重置 | 依赖安装走 PyPI；拉参考仓库用 `codeload.github.com` tar.gz；不要反复重试 clone |
| 3 | LangGraph resume 会从 `interrupt()` 所在节点顶部重跑 | interrupt 之前只做纯读取；所有写库/外部调用放到 interrupt 之后 |
| 4 | MemorySaver 不跨进程持久化 | 演示/生产用 `sqlite_checkpointer()`（同步 `SqliteSaver`）；MemorySaver 只用于测试（`memory_checkpointer()`） |
| 5 | `interrupt_before` 与节点内 `interrupt()` 两种方案混用会混淆 | 本项目统一用节点内 `interrupt()`；不要同时用 `interrupt_before`（ADR-002） |
| 6 | 让 LLM 输出等级会导致不可回归 | 抽取/解释 schema 都不含 `risk_level`；Pydantic `extra="forbid"` |
| 7 | PDF 解析是最大不确定性 | 只支持文本型 PDF（pypdf）；扫描件明确提示“不支持/需 OCR”；DOCX 用 python-docx；TXT 直接读（ADR-005） |
| 8 | 条款切分错误会让后续全错 | 先写规则切分（条款编号/标题/段落 fallback），加 fixture 快照测试；LLM 不参与切分 |
| 9 | 规则执行异常被静默忽略会漏红风险 | fail-closed：生成系统 red finding（`is_system_finding=true`），进入 HITL；报告中单独分组，不伪装成合同风险 |
| 10 | CUAD 不能代表国际销售合同 | 自建 20–30 条条款级 gold；CUAD 只作方法参考 |
| 11 | 无 LICENSE 仓库不能复制代码 | zihan / Harvey / Sentinel 只借鉴设计；引用 Apache-2.0/MIT 代码需保留声明 |
| 12 | Star 数与质量无关 | 文档中不把 Star 当技术优势；只写代码可验证的行为 |
| 13 | 不要在 README/答辩写无出处的准确率 | 所有指标来自 `eval/results/*.json`，附模型、样本数、日期、命令 |
| 14 | Git 仓库已初始化（`cf0fd63`），新增文件前先看 `.gitignore` | 不要提交 `.venv/`、`.env`、`.data/`、`*.sqlite*`、缓存；每完成一步提交一次 |
| 15 | 同一 review 并发 resume 可能重复应用决策 | 按 `review_id` 加 `asyncio.Lock`；恢复前检查状态幂等（ADR-004） |
| 16 | SQLite WAL 在 Windows 上偶发文件锁 | 连接生命周期由 FastAPI lifespan 管理；关闭前 checkpoint；测试用内存 checkpointer |
| 17 | 解释 LLM 可能改写等级或给出越权结论 | 解释 schema 无等级字段；Quality Gate 拦截“合同无效/已批准/已签署”等表述；失败用规则理由兜底（ADR-003） |
| 18 | `AsyncSqliteSaver` 导入路径容易写错 | 必须 `from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver`；`from_conn_string` 是异步上下文管理器 |
| 19 | `langgraph-checkpoint-sqlite` 会带入 `sqlite-vec` 原生扩展 | 已确认有 Windows amd64 wheel；若安装失败，记录错误并评估改用同步 `SqliteSaver`（需改 ADR） |
| 20 | Pydantic state 的 `timings` 是整体替换，不是合并 | 每个节点返回 `{**state.timings, "xxx_ms": ...}`；不能只返回自己的那一条 |
| 21 | `Settings` 是 frozen dataclass，测试里不能直接改属性 | 用 `dataclasses.replace(settings, max_contract_chars=100)` 后 monkeypatch 模块级 `settings` |
| 22 | Pydantic 只把 `ValueError` 当校验失败；`re.error` 会直接冒泡 | 正则校验里 `except re.error` 转 `ValueError`，保证规则加载期报 `ValidationError` |
| 23 | 缺失条款类规则（如“未约定适用法律”）没有原文命中区间 | 报告显示“无原文证据”是预期行为；不要用模糊匹配伪造证据，HITL/UI 需明确标注 |
| 24 | 文本级“缺失关键词”规则可能被无关表述误命中 | 关键词表要窄；扩规则时先加 fixture/gold，再做误报回归 |
| 25 | pypdf 会提取页眉/页脚/水印，污染条款正文 | MVP 不过滤；规则关键词要窄；扩评测时统计页眉误命中 |
| 26 | PDF 表格/多栏会打乱列顺序 | 只在 `warnings` 提示；重要表格条款必须人工核对；不静默当正确 |
| 27 | 扫描件判定阈值是“总文本 < 50 字符” | 低文本量但真实的 PDF 会被判失败；错误信息要求用户提供可复制文本文件 |
| 28 | DOCX 没有真实页码，统一 `p1` | 报告 limitation 必须说明；不要伪造页码 |
| 29 | `is_heading` 对纯数字编号有三重约束 | 改正则时先跑 `test_body_line_starting_with_number_is_not_heading`，否则正文会被切成标题 |
| 30 | 条款数 > 200 会让整次审查 `status="failed"` | 不是 bug，是防静默截断；UI/API 要提示“拆分合同或调大 `MAX_PAGES`/上限” |
| 31 | PDF 测试 fixture 只支持 ASCII（Helvetica/WinAnsi） | 中文 PDF fixture 需嵌入 CJK 字体，暂未做；不要用 ASCII fixture 证明中文 PDF 可用 |
| 32 | “部分条款抽取成功”若算 `ok`，字段规则会把“没抽到”判成“合同缺条款” | `extraction_status` 只有**全量成功**才是 `ok`；部分覆盖/失败一律 `degraded`，字段规则 skipped |
| 33 | `extra="forbid"` 只挡未知字段，挡不住“字段给了但引文是编的” | 非 null 字段必须有 `quote` 且 `locate_quote` 成功；否则丢弃字段 + `to_verify`（宁缺勿假） |
| 34 | 逐字符 `unicodedata.normalize` 无法合成组合字符 | `locate_quote` 必须整簇规范化（基字符 + 组合符一起），并用起止索引表映射回原文 |
| 35 | 数值字段 LLM 会返回 `"USD 620,000"` 之类带单位文本 | 归一为 float 但检测到单位/币种残留 → `to_verify`；不静默当作可信金额 |
| 36 | 同一字段在多个条款出现且不一致 | 保留首个并 `to_verify`；不自动选“看起来更合理”的值，也不做汇率换算 |
| 37 | `tests/fakes.py` 的 Fake LLM 必须实现 `StructuredLLM` 协议（`model_id` + `invoke`） | 新节点依赖 LLM 时用同一协议，测试注入 `FakeLLM`，禁止在业务代码里写 if-test 分支 |
| 38 | `get_llm()` 是 `lru_cache(maxsize=1)`；测试改 `settings` 后必须 `cache_clear()` | 否则会一直用旧 Key/模型；已在 `test_llm_service.py` 用 try/finally 示范 |
| 39 | 条款数 > `MAX_EXTRACT_CLAUSES`（默认 40）时只抽部分条款 | 按“全量成功才算 ok”的规则，此时字段规则全部 skipped；长合同要么调大上限，要么接受跳过并在报告提示 |
| 40 | SQLite checkpoint 会告警“Deserializing unregistered type app.schemas.X ... will be blocked in a future version” | 必须用 `app/services/checkpointer.py` 的 `_serde()`（`JsonPlusSerializer(allowed_msgpack_modules=[...])`）登记 `app.schemas` 全部 Pydantic 类型；不要直接用裸 `SqliteSaver`/`InMemorySaver` |
| 41 | `SqliteSaver.from_conn_string()` 不接受 `serde` | 手动 `sqlite3.connect(path, check_same_thread=False)` → `SqliteSaver(conn, serde=_serde())`，并在 `finally` 关闭连接 |
| 42 | `invoke()` 暂停时返回值含 `__interrupt__` 键，直接 `ContractReviewState.model_validate(raw)` 会因 extra 字段失败 | 用 `{k: v for k, v in raw.items() if not k.startswith("__")}` 过滤后再校验 |
| 43 | 暂停时 `state.status` 仍是 `running`，不是 `awaiting_human` | `awaiting_human` 由 `ReviewService` 从 `snapshot.next` 派生；不要把状态机写成“节点返回 awaiting_human” |
| 44 | 已终态 review 再次 `resume` 会重跑图/重复生成报告 | `ReviewService.resume()` 先查 `snapshot.next`；不在 `human_review` 且状态属于 `FINAL_STATUSES` 时直接返回现有结果（幂等） |
| 45 | CLI 误把 checkpointer 传给 `ReviewService`（第一个参数是 compiled graph） | 正确写法 `ReviewService(build_graph(checkpointer=sqlite_checkpointer()))`；`SqliteSaver` 没有 `invoke` |
| 46 | `interrupt()` 抛出的暂停不是异常，不会让 CLI 非零退出 | CLI 需要显式判断 `awaiting_human` 并打印 `review_id` 与恢复命令；不要用“进程失败”表示等待审批 |
| 47 | ~~`ReviewService._requested_at` 仅存进程内存，重启后惰性超时失效~~ | 已修复（第 6 步）：`app/services/pending_store.py` 落盘 `.data/pending/<review_id>.json`；缺失/损坏一律不判超时（ISSUE-017） |
| 48 | 人工意见里的 `overrides` 可能引用不存在的 `rule_id` | 节点只产生 warning，不写入报告等级；规则等级永远不会被人工意见改写 |
| 49 | `uvicorn app.api:app` 会失败（模块里只有工厂函数 `create_app`） | 用 `--factory`：`uvicorn app.api:create_app --factory`；或在 `api.py` 末尾加模块级 `app`（本项目故意不加，避免测试共享全局状态） |
| 50 | Streamlit 的 `st.cache_resource` 会跨会话复用 checkpointer 连接 | 用 `atexit` 关闭 SQLite 连接；测试用 `streamlit.testing.v1.AppTest` 只跑首屏，不做多会话并发 |
| 51 | TestClient 必须配 `httpx`，上传必须配 `python-multipart` | 前者在 `requirements-dev.txt`，后者在 `requirements.txt`；缺任一会在测试/上传时直接报错 |
| 52 | FastAPI 里 `Path(...)` 与 `pathlib.Path` 同名冲突 | 别名导入 `from fastapi import Path as ApiPath`；`review_id` 用 `pattern` 校验，非法值走 422 |
| 53 | 用户上传的文件名可能含 `..\`/`../` 或控制字符 | `_safe_filename()` 同时按 `\` 与 `/` 取 basename、去不可打印字符、限制长度；落盘目录固定为 `.data/uploads/<新 uuid>/` |
| 54 | `.doc` 与 `.docx` 是两个不同格式 | `.docx` 用 python-docx；`.doc` 明确 400 并提示另存为 `.docx`（RAG manifest 同样拒绝 `.doc`） |
| 55 | DOCX 法条通常全是 `Normal` 样式，不能靠标题样式切分 | 按 `^第X条` 正则切分，编/章/节作上下文前缀；`目录` 行丢弃；section 用条文号做引用 |
| 56 | 英文 CISG 用 `***Article N***` 而非 Markdown 标题 | `_heading_of()` 同时识别 `#` 标题、`***...***` 与结构性加粗；新增格式先加测试再改正则 |
| 57 | 单条法规超过 1600 字符会让 BM25 与提示词失真 | `_chunk_text()` 按空行段落 + 句末标点二次切分；同一标题依次 `s2`、`s2-2` |
| 58 | 每次 API/UI 请求都重载 500KB 语料会很慢 | `load_knowledge_base` 按 `(目录, manifest+文件 mtime/size)` 缓存；语料变更自动重建，测试用独立目录避免污染 |
| 59 | ICC 官方写作 `Incoterms® 2020`，带注册商标 `®` | 检测版本号的正则必须允许 `[®™]`，否则会把“写了版本”判成“没写版本”（真实误报 40/50，见 ADR-010） |
| 60 | 新规则容易“看起来合理、实际满语料误报” | 每条新规则先在 `data/contracts/` 上跑命中集合，命中集合写进 `EXPECTED_CORPUS_HITS` 回归测试；再跑两份样例确认零误报 |
| 61 | `data/contracts/` 是生成物，不是用户原始语料 | 用 `eval/prepare_contracts.py` 重建；不要手改单份合同，否则 gold 与原文会不一致 |
| 62 | “CIF 没写保险条款”不等于缺陷（Incoterms 默认规则补位） | `R-INS-001` 只在“约定了投保但没写保额/比例”时触发；新增保险类规则前先确认是否与默认规则重复 |
| 63 | 规则数量变化会让多处硬编码断言失败 | 新增/删除规则时同步 `test_load_default_rules`、`test_graph.py` 的规则数断言与文档中的“N 条规则” |
| 64 | 模拟合同自带映射摘要是“检索期望”，不是规则判级 gold | 不要用 `gold_contracts.json` 直接算规则 precision；规则级 gold 另存 `gold_rules.json`，检索评测另做（ISSUE-018） |
| 65 | 用“规则设计时的同一批合同”算出的 P/R 必然接近 1.0 | 同分布指标只能当回归守卫；对外报数必须用**未参与规则设计**的留出集（ADR-011） |
| 66 | 留出集上发现漏报后，本能是立刻改正则 | 改了就不再是留出集，指标会虚高；正确做法是记录漏报 → 下轮改规则 → **另写新留出集**重验（ISSUE-021） |
| 67 | 中文规则的正则常把关键词语序写死（“运费由卖方”） | 实际写作“费用由卖方承担并预付”就漏检；规则要么放宽语序，要么用 `contains_any` + 距离约束 |
| 68 | 英文合同可能“碰巧命中”中文规则（靠 `insurance` 等英文词） | 碰巧命中不能算英文支持；H02 就是这样过的，补英文表达时不要因此以为已覆盖 |
| 69 | 指标零分母时返回 0.0 会误导 | 返回 `None`（JSON `null`），并在报告里说明“无正例，不计算 P/R” |
| 70 | 字段规则在评测里恒为 skipped | `gold_rules.json` 用 `unscored_rules` 显式排除，否则会把“降级”算成“漏报” |
| 71 | `contains_any: [CIF]` 会命中 `Pacific` / `specification` 里的子串 | 英文缩写一律用“前后非英文字母”边界（如 `(?<![A-Za-z])(?:CIF)(?![A-Za-z])`），但允许紧跟中文（`FOB上海`）；本轮因此修掉一个真实误报（H13） |
| 72 | 跨条款正则的距离窗口会被小标题/空行吃掉 | 窗口要按实测留余量（H19 的 FOB→freight 实测 210，200 不够）；把实测距离写进规则注释，避免下轮又踩 |
| 73 | 留出集的 `coverage` 恒为 1.0（gold 每条现象都标了 rule_id） | 覆盖率只在设计集上有信息量；留出集必须把 `coverage` 与 `recall` 分开看，`run_eval` 已打印提示 |
| 74 | 修完漏报后“指标变 1.0”很容易被当成泛化能力提升 | 只要那批样本被用来定位过缺陷，它就是回归集；对外数字必须来自**下一批新写**的样本（ADR-011 第 3 轮补充） |
| 75 | `none_of` 里的“已写保额”若用全文级正则，合同任意 “40% of contract price” 都会压制 `R-INS-001` | 金额/比例必须与保险关键字**邻近**（同句、±60/40 字符）才算“已写保额”；窗口是启发式，改规则时先用 H29/H34/H36 三项正反样本回归 |
| 76 | 已知漏报若顺手修掉，会悄悄把唯一的报数集变成回归集 | 用测试**钉住**期望集合：holdout4 的 H39 曾断言“必须漏报”，本轮修好后同一测试翻为“必须命中”，强制作者同时更新期望、把旧集降级、另写新集（holdout5），再做新基线（ADR-011 第 5 轮） |
| 77 | 中文并列写法不止“或 / 或者”（还有“亦可 / 也可以 / 仍有权 / 可选择”） | 判决类规则必须先穷举连接词，再用“非该语义”的干净条款（仅可撤销裁决、仅可执行裁决）做反例回归 |
| 78 | 想上 React/Vue + Vite 做前端，但项目禁止前端框架，且会引入 npm/构建/联网依赖 | 用 `app/web/` 的 `HTML/CSS/JS` 手写单页，FastAPI 用 `FileResponse` + `StaticFiles` 托管；`app.js` 不写死 host/端口 |
| 79 | 前端若把后端文本直接塞进 `innerHTML`，合同里的 `<script>` 会被执行 | 所有字段先过 `esc()` 再拼模板；新增渲染点必须复用同一个转义函数（`tests/test_web.py` 会检查外链与判级，但 XSS 靠代码评审） |
| 80 | 浏览器里“顺手”算等级或拼 `Command(resume=...)` 会绕过 HITL/判级边界 | 等级只来自 `ReviewSummary`；审批只 POST `/api/reviews/{id}/decisions`；测试用正则钉住不得给 `risk_level` / `overall_level` 赋值 |
| 81 | Streamlit 提示“已运行”但浏览器打不开（8501 未监听/端口被占/`--server.address` 不对） | 显式 `--server.port 8501 --server.address 127.0.0.1 --server.headless true`，再用 `GET /_stcore/health` 验证；主界面已改为 FastAPI `/`（8000），Streamlit 仅备用 |
| 82 | 工作台需要“规则集”页，但正则 / `condition` / DSL 绝不能下发浏览器 | 只读 `GET /api/rules` 返回 `RuleSummary` 白名单（`rule_id/title/category/risk_level/reason/suggestion/requires_extraction` + 集合版本），Pydantic `extra="forbid"`；新增展示字段要同步改模型与前端，禁止把 YAML 直接序列化给前端 |
| 83 | Windows 下 `mimetypes` 可能没有 `.woff2` 映射，字体被当 `application/octet-stream` 送出去 | `app/api.py` 启动时 `mimetypes.add_type("font/woff2", ".woff2")`；`tests/test_web.py::test_local_fonts_are_served` 断言 `content-type` 以 `font/` 开头 + `OFL.txt` 可读 |
| 84 | Google Fonts 的“静态字重” latin 子集可能返回同一个可变字体文件（三份 SHA256 相同） | 先用哈希比对再落盘；本项目只保留 `ibm-plex-sans-var.woff2`（`font-weight: 100 700`）+ Mono 400/500，避免仓库里堆三份同样的二进制 |
| 85 | `@font-face` 少了 `font-display` / 权重范围写错，会让离线环境回落到系统字体且“看不出错” | 可变字体显式写 `font-weight: 100 700`；`font-display: swap`；`tests/test_web.py` 断言 CSS 里存在 `/static/fonts/` 与 `@font-face`，防止有人误改回 CDN |
| 86 | 窄屏抽屉只用 `transform: translateX(-102%)` 收起时，链接仍在可访问树里，键盘能 Tab 到屏幕外 | 收起态同时 `visibility: hidden`，`[data-open="true"]` 再 `visible`；这个真实缺陷是被 taste-skill 的 `ragged-row` 告警“顺带”暴露出来的（它把屏幕外侧栏当成了同排卡片） |
| 87 | 规则目录表在 390px 五列并排会挤成一字一换行 | `@media (max-width: 900px)` 把 `.rules-table` 改成堆叠条目（`display: block` + 首行三元信息 + “处理建议”小标题），不做横向滚动；“窄屏堆叠 + 宽屏表格”要用同一个 DOM，别复制两份 |
| 88 | 任意文本都能命中规则关键词，于是论文/法规也被“审查”出风险 | 入口先过 `precheck_document`（`classify_document`），不是合同 → `not_contract` 直接出“未执行审查”报告；判否时 `clauses=[]`、不抽取、不判级、不触发 HITL（ADR-012） |
| 89 | 闸门的抬头正则若在全文中搜，会把正文“货物符合合同约定”当成标题 | `_extract_title()` 只看开头 12 个非空行，行长 ≤48，且排除标点句与 `本合同/符合合同/根据合同` 等正文用语；改词表时先跑 90 份合同语料回归 |
| 90 | 合同编号正则若在“去空白文本”上匹配，`合同编号：C47` 会取不到值 | 在原文上匹配并捕获**第二组（值）**；`合同编号/合同号/订单号/协议编号` 与 `Contract No./P.O. No.` 两套写法都要覆盖 |
| 91 | `not_contract` 是新终态，忘了登记会导致人工决定把图再跑一遍 | 必须同时加入 `ReviewStatus` Literal、`ReviewService.FINAL_STATUSES`、`report_markdown.STATUS_LABELS`、`ui.py` 状态映射与前端 `STATUSES`；漏一处就会出现“已停止但还能提交决定” |
| 92 | 界面里展示接口版本 / 规则集 / checkpoint / RAG 开关，业务用户看不懂也解决不了问题 | 侧栏只留 `/docs`；`test_runtime_internals_stay_out_of_the_ui` 钉住 `运行环境`/`rt-*`/`.runtime` 不得回到页面；需要排查时看 `/health`，不占业务界面 |
| 93 | 内容少的页面（“不是合同”页）会让 sheet 只占半屏、浮在中间 | `.app` 用 `grid-template-rows: auto minmax(min-content, 1fr)` + `align-items: stretch`，让 `main` 撑满剩余高度；不要用 `min-height` 硬编码 |
| 94 | PowerShell 里用 `-replace` / `Replace()` 改中文与多行 Markdown，容易产生字面 `\n` 或引号解析错误 | 改文档优先用 Edit 工具做**精确整行替换**；改完用 `Select-String` 复核目标行，避免出现 `\n   -` 这类脏字符 |
| 95 | 动态渲染出来的 `<input type="file">` 在脚本启动时还不存在，缓存成 `dom.fileInput` 会是 `undefined`，点“选择合同”直接抛错、按钮像坏了一样 | 事件里现取：`dom.view.querySelector("#file-input")?.click()`；凡是“渲染后才存在的节点”都不要缓存进 `dom`（`test_web.py::test_header_pick_button_targets_rendered_input` 已钉住） |
| 96 | 检索写在 `get_llm()` 成功之后，没配 Key 时直接 return——RAG 开着也永远看不到引用，用户以为知识库没生效 | `explain_risks` 必须**先加载知识库、再判断 LLM**；LLM 不可用时也检索，把 `source_id#section` 挂到规则兜底（`source="rule"`，等级与正文不变），并在摘要写明“未参与解释与判级” |
| 97 | 改了 `index.html` / `app.js` 的类名，却把旧选择器留在 `styles.css`，页面会“裸奔”或错位 | 改结构必须同步改样式；本轮保留 `.app/.sidebar/.topbar/.sheet` 壳，主区换成 `.drop/.headline/.lead/.risks/.risk/.tag/.why/.confirm/.down`，并保留 `:root` / `@font-face`；改完跑 `test_web.py` + 真实截图复核 |
| 98 | 待确认态 `report` 是 `None`，只读 `report.findings` 会先显示“0 处风险”，用户没看到风险点就被要求确认 | 待确认时用 `ReviewSummary.approval.findings / findings_total / quotes / citations`（审批载荷，只含 red）；`awaiting_human=false` 且 `report` 存在时才读报告 |
| 99 | 结果页“下载报告”写成 `/api/reviews/{id}?format=markdown`，拿到的是审查 JSON 而不是 Markdown 报告 | 报告接口是 `GET /api/reviews/{id}/report?format=markdown`；`tests/test_web.py` 已断言脚本包含该路径 |
| 100 | hash 路由下任何 `href="#xxx"` 都会触发 `hashchange`，跳转链接 `#main` 会被当成未知路由重渲染成首页 | 跳转链接点击时 `preventDefault()` 再 `focus()`；新增锚点前先确认不会进入 `route()` |
| 101 | Edge headless `--screenshot` 异步写文件，命令返回后立刻 `Test-Path` 可能为 False；`--window-size=390` 会被浏览器最小窗口宽度裁切，看起来像横向溢出 | 截图后 `Start-Sleep 2–3` 再读文件；窄屏验证用 500px 或 CDP 设备仿真，不要把 390 的裁切误判成 CSS 溢出 |
| 102 | “页面信息太多”≠“页面元素都删掉”：曾把侧栏、面包屑、顶栏一并拆掉，用户立刻要求“原来的侧边栏保留，仅右侧主体内容做变更” | 界面改动先区分**导航壳**（侧栏/顶栏：定位、导航、服务状态）与**业务主区**（结论与证据）；精简只动主区，导航壳保留原结构，只删对应视图已不存在的死链 |
| 103 | 用 CDP 断言 `getComputedStyle(el).display` 时，flex 容器里的 `inline-flex` 按钮会被 blockify 成 `flex`；照文档写 `inline-flex` 会误判失败 | 断言前想清父容器布局：`.topbar` 是 flex，汉堡按钮计算值就是 `flex`；同理 headless 默认视口不是 `--window-size`，需 `Emulation.setDeviceMetricsOverride` 显式设宽 |
| 104 | 把“审查重点 / 附件 / Skill”塞进侧栏，用户看的是 Codex/Harness 那种**主体对话输入区** | 导航壳（侧栏）只放导航/账号/API 配置/接口文档；输入区放 `#view` 的 `.chat`（标题 + `.composer-box`：textarea + 工具行 + 圆形发送键），Enter 发送、Shift+Enter 换行；`tests/test_web.py::test_review_focus_lives_in_main_composer_not_sidebar` 钉住两侧 |
| 105 | 侧栏同时放“登录 / 注册”两个入口，且弹窗内切换 tab 时高度跳动（昵称字段出现/消失） | 侧栏只留“登录”；注册放登录弹窗的 tab；`.auth-extra{min-height:62px}` 固定占位，注册显示昵称、登录显示等高提示框 `#auth-switch-hint`；用 CDP 量两种模式的弹窗尺寸必须一致（实测 460×458） |
| 106 | 法务条款用一长段 `<p>` + 大行距，看起来像“免责声明墙”，没人读 | `LEGAL.privacy/terms` 存结构化数组，渲染成 `<h3><span class="legal-no">01</span>标题</h3><p>正文</p>`：编号用 `padStart(2,"0")`、正文 13.5px、行高 1.62；改文案只改常量，不写死 HTML |
| 107 | `uvicorn app.api:app` 直接报 `Attribute "app" not found in module "app.api"`，前端/CDP 全部连不上 | `app/api.py` 只有工厂 `create_app`，必须 `uvicorn app.api:create_app --factory`；写冒烟脚本时先等 `/health` 返回再断言 |
| 108 | 用三段短句当“合同”做 HTTP 冒烟，会被文档类型闸门判成 `not_contract`，后续 `awaiting_human`/报告断言全挂 | 冒烟必须用完整合同（`data/samples/sample_sales_contract.txt`）；闸门判否时 `approval=None`、`report.findings=[]`，不要把这当成接口坏了 |
| 109 | PowerShell 里 here-string + `curl.exe` 做 multipart/cookie 冒烟，`"@ |` 同行、引号转义极易报“string is missing the terminator” | 冒烟脚本改用 Python `httpx.Client`（自动管 cookie）+ `sys.exit(1)` 断言；`@'…'@` 必须独占一行，且用 `Set-Content -Encoding utf8` |
| 110 | CDP `Runtime.evaluate` 报 `'Runtime.evaluate' wasn't found`，或取值报 `reading 'value' of undefined` | `send()` 时必须带 `sessionId`（`Target.attachToTarget` 后取）；`send()` 已返回 `message.result`，再按 `response.result.value` 取，别多解构一层 |
| 111 | 把用户 API Key 放进 `ContractReviewState` / 函数默认参数，会随 checkpoint 落盘、进日志 | 用 `LLMRuntime` 按 `review_id` 登记 + `with review_llm_scope(...)` 包住 `graph.invoke()`；`get_llm()` 优先级“本次审查配置 → 环境默认 → `LLMNotConfigured` 降级”；终态 `_finish()` 清理运行时 |
| 112 | 主密钥被删/换后，解密失败若静默回退到环境 Key，会变成“用错模型还要用户付钱” | `SecretBoxError` → 500 并提示“主密钥已变更，请在 API 配置里重新填写 Key”；测试 `test_rotated_master_key_reports_actionable_error` 钉住 |
| 113 | 冒烟脚本、截图、临时 sqlite 散落在 `.tmp-shots/` 未忽略，容易被 `git add .` 带进仓库 | `.gitignore` 增加 `.tmp-shots/`；临时库用环境变量指到该目录（`USER_DB_PATH`/`CHECKPOINT_SQLITE_PATH`/`PENDING_DIR`/`UPLOAD_DIR`），不要动真实 `.data/` |
| 114 | 登录弹窗里给“注册态”预留 `min-height:62px` 的包裹层，登录时那块空着，邮箱与密码之间出现 98px 大空隙 | 不要用“留白占位”等高；直接删掉包裹层，用 `#auth-dialog .dialog-body{min-height:396px; justify-content:center}` 让两种模式等高，表单字段回到统一的 `gap:10px`（实测邮箱→密码 34px，含标签） |
| 115 | 定高的常量靠目测会翻车（先写 300px，注册态 body 实际 396px，切 tab 时弹窗从 460×385 跳到 460×453） | 先用 CDP `Page.captureScreenshot` 或 `dialog-body` 的 `getBoundingClientRect()` 量出**较高那个模式**的高度，再把它写成常量；`tests/test_web.py` 钉住 `min-height: 396px`，改文案/加字段时要同步重量 |
| 116 | `review_records` 已上线后直接改建表语句，老库用户不会获得新列，`ORDER BY pinned` 直接报 `no such column` | `_init_schema()` 末尾用 `PRAGMA table_info(review_records)` 判断列是否存在，缺则 `ALTER TABLE ... ADD COLUMN`；`_record_from_row()` 用 `row.keys()` 兼容缺列，别假设 `sqlite3.Row` 一定有 |
| 117 | 删历史记录只删索引行，checkpoint / pending 时间戳 / 上传文件仍留在磁盘，列表“空了”但占空间、且旧 review_id 还能被 resume | `ReviewService.discard(review_id)` 清 `_pending`、`clear_llm_runtime`、尽力 `checkpointer.delete_thread`（无此方法/失败就静默），API 再 `shutil.rmtree(upload_root/review_id, ignore_errors=True)`；删除接口返回 204，越权与不存在统一 404，避免探测别人的 review_id |
| 118 | 侧栏子目录里的记录行每行带“置顶/改名/删除”，给每个按钮单独 `addEventListener` 会在每次刷新列表后泄漏/失效 | 事件委托：`#history-list` 上监听 `click` + `submit`，用 `event.target.closest("[data-pin],[data-rename],[data-delete]")` 分发；改名是行内 `<form>`，必须 `preventDefault()` 再 `PATCH` JSON |
| 119 | 480px 窄屏下把 `.composer-tools .send{margin-left:0}` 会把发送键贴到下拉框左边，看起来像误触 | 工具行换行后用 `margin-left:auto` 让发送键靠右（第二行右端）；窄屏改动要 CDP 实测 `overflow-x` 与按钮坐标，不要只看截图 |
| 120 | 原生 `<select>` 的下拉弹层由浏览器绘制，字体/圆角/间距与页面不一致，选项里也放不下“推荐 / 我的 / 管理”这类辅助信息，看起来“很丑且难对齐” | 改成自绘 combo：胶囊触发器（`aria-haspopup="listbox"` / `aria-expanded` / `aria-controls`）+ `ul[role="listbox"]` + `button[role="option"][aria-selected]`；必须补 ↑↓、Esc、点外收起（document 只绑一次，否则每次重渲染都会叠加监听） |
| 121 | 下拉菜单用 `right:0` 贴住胶囊右边缘，窄屏工具行换行后胶囊靠左，菜单会算出负的 `left`（CDP 实测 `menuLeft=-104`，被裁掉） | ≤640px 的媒体查询里改成 `left:0; right:auto` 并收窄 `width: min(252px, calc(100vw - 48px))`；改完用 CDP 断言 `menuLeft >= 0 && menuRight <= innerWidth` |
| 122 | 下拉 `max-height` 写小了（286px）会让 8 个选项出现一条细滚动条，视觉上像“组件坏了” | 用 `scrollHeight > clientHeight` 断言“无滚动条”，再按实测高度给 `max-height`（当前 336px 一次放下 8 项） |
| 123 | 页面底部政策链接“没贴右”的根因不是对齐，而是 `.sheet-foot` 上残留 `max-width: var(--content)`（820px）；同时 `padding-top:16px` + `line-height:1.6` 把页脚撑得很高 | 页脚属于画布宽度：`width:100%; max-width:none`，只给 `.foot-links{margin-left:auto}` 贴右；高度靠 `padding-top:8px` + `font-size:11.5px` + `line-height:1.45` 收到一行（实测 26px）；不要用 `position:fixed`（会脱离白纸压住内容） |
| 124 | 页面点“注册”显示 **not found**，很容易误判成前端路径写错 | 先看**运行中的进程**：`GET /openapi.json` 的 `info.version` 不是 1.0.0（例如 0.9.0）就说明 8000 端口是旧代码，旧版本只有 `/api/reviews`、`/api/rules`、`/health`，没有 `/api/auth/*` → 注册必然 404。uvicorn 没加 `--reload`，改后端必须手动重启；重启后 `version=1.0.0`、`GET /api/auth/me` 应 200 |
| 125 | 往 `.skills-grid`（2 列）里直接追加第三个子元素（导入卡片）会**掉到第二行第一列**，右栏表单下方出现一大片空白 | `grid-template-columns` 只定义列，多余子元素按行自动摆放；必须把“表单 + 导入卡片”包进同一个 `.skills-column.skills-side` 容器（再补 `.skills-side{gap:14px}`），而不是继续往 grid 里塞子节点 |
| 126 | API 配置里点 Key 输入框，浏览器弹出“快捷填入已保存的账号密码” | 浏览器按“`<form>` 里有 `type=password`”判定为登录表单。修复：表单 `autocomplete="off"` + Key 输入 **`autocomplete="new-password"`**（关键，浏览器当作“设置新密码”就不会列凭据/提示保存）+ `name="llm_api_key"` + `data-lpignore="true"` + `data-form-type="other"`；同时给厂商/地址/模型加 `autocomplete="off"`。不要改成 `type=text`（Key 会明文露在屏幕上） |
| 127 | 给 `users` 表加列后，老库（`.data/app.sqlite`）启动就报 `no such column: avatar` | 建表语句只对新库生效；必须写 `_ensure_user_columns()`：`PRAGMA table_info(users)` 取现有列 → 缺就 `ALTER TABLE users ADD COLUMN avatar TEXT NOT NULL DEFAULT ''`；`_user_from_row` 也按 `"avatar" in row.keys()` 容错。迁移函数要在 `commit()` 之前、`__init__` 里调用 |
| 128 | 账户设置弹窗写了 `.account-dialog{width:min(760px,...)}` 仍然只有 460px 宽 | `.dialog{width:460px}` 在前、`.account-dialog` 在后，但**单类选择器优先级相同**，谁后写谁赢——这里实际是 `.dialog` 声明更靠后/更高优先级。改成 `.dialog.account-dialog` 提高特异性，并在 640px 媒体查询里同样带上 `.dialog`；改完用 CDP 断言 `rect.width >= 720` |
| 129 | 字号“小/标准/大”要能全局生效，但样式表里全是写死的 `font-size: 12.5px` | 在 `:root` 加 `--ui-text-scale: 1`，用脚本把所有 `font-size: Npx` 批量改成 `calc(Npx * var(--ui-text-scale, 1))`（只动字号、不动 padding/宽度/图标），再用 `html[data-font="sm"|"lg"]` 改倍率；坑：别把 `font-size` 写进 `font:` 简写，否则倍率不生效 |
| 130 | 弹窗里的 Skill 表单点了“保存”毫无反应 | 弹窗是 `index.html` 的静态节点，在 `#view` 之外；原来 `bindSkills()` 把 `click/submit/change/drop/keydown` 挂在 `dom.view` 上，根本收不到。凡静态弹窗的交互，委托必须挂 `document`（只绑一次，用 id / `data-*` 过滤），且不要随页面重渲染重复绑定 |
| 131 | 自定义弹窗宽度写了也不生效（仍 460px） | `.dialog{width:460px}` 与 `.account-dialog` / `.skill-dialog` 都是单类选择器，特异性相同、后写者赢；必须写 `.dialog.skill-dialog`（两个类）才能压过默认宽度，媒体查询里也带上 `.dialog` |
| 132 | 切换条款时整页被 `scrollIntoView` 顶跑 | 条款列表自身是滚动容器，`scrollIntoView` 会连带滚动外层页面；改成按 `getBoundingClientRect()` 差值直接调 `list.scrollTop`（只动列表） |
| 133 | 合同级问题全部画成红标，明明只有 1 处黄色也显示红 | 组内等级要按最严重一条取（有 red 才 red，否则 yellow），并且这个等级只能来自 `finding.risk_level`，不能在 `renderWorkbench()` 里重新判断 |
| 134 | 流式输出结束后，逐条审查分屏被对话挤到屏幕外，用户以为“没做逐条审查” | 流式回调里 `box.hidden = false` 后判断 `getBoundingClientRect().top > innerHeight - 120` 再 `scrollIntoView({block:"start"})`；不要无条件滚，否则短对话也会跳 |
| 135 | 导出 PDF 中文变方块/乱码 | `reportlab` 默认 `Helvetica` 没有中文字形；必须 `pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))` 并给 Paragraph 设置 `fontName`，同时用 `escape()` 处理 `&<>`、把 `\n` 换成 `<br/>`；`requirements.txt` 里要写 `reportlab==4.4.4` |
| 136 | 导出文件名中文被截断成乱码 | `Content-Disposition` 只写 `filename=中文.docx` 时多数浏览器按 latin-1 处理；要同时给 ASCII 兜底名与 RFC5987 形式 `filename*=UTF-8''<quote(name, safe="")>`，前端优先解 `filename*` |
| 137 | 三个并行专家各自写 `degraded_steps` / `timings`，跑图直接报 `INVALID_CONCURRENT_GRAPH_UPDATE` | LangGraph 并行分支**只能写带 reducer 的字段**：`expert_findings` / `expert_notes` / `expert_route` 用 `Annotated[list[T], operator.add]`；`expert_status` / `degraded_steps` / `warnings` 统一由汇合节点 `collect_expert_findings` 单点写 |
| 138 | 并行分支的 append 顺序不稳定，前端“专家顺序”每次都不一样 | 展示层不要直接用 `state.expert_route`：`_agent_trace()` 与 `collect_expert_findings()` 都按 `EXPERT_ORDER` 归一；测试也按同一顺序比较，别断言原始列表相等 |
| 139 | 给专家 schema 留个“置信度 / 建议等级”字段，看起来更专业，实际会让 LLM 变相判级 | `ExpertDraft` / `ExpertOpinion` 一律 `extra="forbid"` 且**不含 `risk_level`**；引文必须 `locate_quote` 命中，否则整条丢弃并记 `expert:<id>:quote_not_found` |
| 140 | 工具“调用成功”却让审查挂掉，或模型编了个不存在的工具名就真的执行 | `ToolRegistry.call()` **永不抛异常**，统一转 `ok=False` 轨迹；`_execute()` 只执行注册表里的名字，白名单外只记“未注册的工具（白名单外，不执行）” |
| 141 | MCP 用 `shell=True` 拼命令字符串，等于把 `.env` 配置变成任意命令执行 | `subprocess.Popen(list(argv), shell=False)`；命令只来自 `.env` 的 `MCP_SERVERS`；单行 ≤1 MB、初始化 15 s、调用按 `MCP_TIMEOUT_SECONDS` 超时 `kill()`；不可达只注册 `<server>/unavailable` 占位工具 |
| 142 | 本地无 LLM Key 时 `TOOLS_ENABLED=true` 看起来“什么都没发生”，演示像是没做工具调用 | `_fallback_plan()` 用第一条 red/yellow 的规则标题作检索词调 `find_clause` / `search_knowledge`，并写 `research_tools:deterministic_plan` + warning，明确“不是模型规划的” |
| 143 | 专家意见用红/黄/绿渲染，用户直接当成风险等级，规则判级被绕过 | 专家块只用中性色（`--muted/--faint/--border/--raised`），并明写“专家意见只作补充参考，不代表风险等级”；`test_web.py` 断言 `.expert-block` 内不得出现语义色变量 |
| 144 | 英文 `either party may, within 45 days …, bring an action` 被漏报——原正则要求 `may|shall` **紧跟**动作动词，而这里插了时间状语且状语前是**逗号** | modal 与动词之间放宽为 `\s*[^.]{0,80}?`（`\s*` 而非 `\s+`，逗号也能过）；同时保留“裁决的法定执行 / 申请撤销”不误报（H43 干净对照）；改完必须用 holdout4 的 H39 + holdout5 的 H41 双向回归 |
| 145 | “用留出集修规则”看起来最省事，但一改就毁掉唯一能对外报数的样本 | 顺序固定：**写新集 → 写 gold → 先跑基线 → 才改规则 → 修后只做回归**；对外永远引用基线文件，修后 1.0 不作为泛化证据；`tests/test_rules.py` 用期望集合 + 干净对照把这条钉住 |
| 146 | 前端清空历史按条循环 `DELETE /api/reviews/{id}`，中途失败会留下“删了一半”的状态，还给服务端制造 N 次事务 | 新增 `DELETE /api/reviews`：单事务只删本账号行、返回 `{deleted:N}`，再顺带 `service.discard()` 与 `rmtree(upload_root/<id>)`；测试覆盖未登录 401、跨账号隔离、二次清空幂等 |
| 147 | “这份报告怎么读”若把覆盖范围/局限写死在前端，后端 `limitations` 一改就前后不一致 | 前端只写**稳定的七节**（等级来源、三档含义、证据、专家不判级、工具只读、边界、使用顺序），动态部分拉 `GET /api/reviews/{id}/report?format=json` 的 `limitations` 追加为第八节；拉取失败静默降级为七节 |
| 148 | 英文 `FOB` 下“The Seller shall arrange and pay for the ocean freight”被漏报——`R-INC-001` 英文侧只认 `freight … paid by the seller`，认不出“卖方 + 付运费动词 + 运费名词”的倒装 | 新增第二条英文分支（`seller … arrange and pay for\|pay for\|prepay\|bear\|defray … ocean/sea freight\|freight\|carriage`，间隔限定 40/24 字符且不跨句）；**刻意不收裸 `pay`**，否则“Seller 安排运输 + Buyer 付运费”的正常 FOB 会误报 |
| 149 | 英文 `… arbitration … or, at the Buyer's option, by proceedings in the courts` 被漏报——`R-DIS-003` 用 `\s+or\s+`，而连接词后是逗号（与 `may,` 同属标点缺陷） | 放宽为 `\s+or[,\s]\s*`：保留前面必须有空白的限制（不吃 `arbitrator/order/for` 里的 `or`），只允许紧跟逗号后再接内容 |
| 150 | 英文 `pay the entire contract price before shipment` 被漏报——`R-PAY-001` 只认 5 个固定短语 | 加正则：`entire\|full\|whole\|100% of the` + `price/value/amount/payment` + 80 字符内 `in advance\|before shipment/delivery/dispatch\|prior to shipment\|upon signing`；限定词只收“全部”，正常分期（`the balance … before shipment`）不误报 |
| 151 | 修规则时容易“顺手”把漏报修掉却忘了样本已经降级，导致对外数字变成用测试集调参的结果 | `test_holdout6_hits_are_stable` **先按基线把三个漏报写成空集合**（跑通即基线快照）；修完再跑必然失败并点名 H53/H55/H61，此时才翻表并注明“本批已降级、只引基线文件”——把顺序钉死在测试里 |
| 152 | 用户说“先做 holdout7 盲测基线”，若同一轮顺手把漏报也修了，基线文件会立刻与代码不一致，对外数字就说不清是“规则水平”还是“修复前旧状态” | 第 7 轮**只做前两步**（写集 + 跑基线），规则保持 `version: 7`；`EXPECTED_HOLDOUT7_HITS` 把四个漏报写成空集合，跑通即基线快照；修规则、翻表、升版本留到第二步单独提交 |
| 153 | 新留出集写得太像旧集（沿用同一句式），基线会虚高，测不出泛化 | 每批先列“本批要测的新写法”，再据此写合同：holdout7 专挑 `for the Seller's account`（迂回语态）、仲裁句与法院句**分属两句**（跨句）、中文“一次性支付…全部价款”、`bring the matter before the courts`；holdout8 再换一轮：`is on the Seller's account`（介词短语）、`refer the dispute to the courts`、中文“付清全部货款”、`仲裁庭的裁决 + 收到裁决书之日起`、`immediately upon discharge` |
| 154 | 七批样本全部消耗后，容易“用旧基线报新代码”或干脆不报 | 用户选“先写 holdout8 再报新泛化数字”：**只写集 + 只跑基线，规则一条不动**，新基线文件 `rules-holdout8-baseline-20261029.json` 唯一对应 `version: 8`；`test_holdout8_hits_are_stable` 把五个漏报写成空集合，修规则那天必然失败并点名——把“降级”交给测试而不是记忆 |
| 155 | 新批次若挑“规则已经能认”的写法，R 会虚高（例如 0.9+），但没诊断价值 | holdout8 刻意五处都选 `version: 8` 没覆盖的写法，基线 R=0.545 **低于** holdout7 的 0.636，并在日志/ADR 里写明“这是设计使然，诚实报低才有诊断价值” |
| 156 | 修规则时“换个更宽的写法”容易把老分支挤掉（例如把 `at the Seller's expense` 整段替换成 `for the Seller's account`） | 数字没变也属于**悄悄丢能力**。改法：新旧分支并列成 `(?:(?:for\|on) … account\|at … (?:expense\|cost))`，并重跑九批 + 主集确认 `hit_counts` 逐条不变；本轮 `R-INC-001` 就出现过这次小反复 |
| 157 | 第 9 轮五处都修好后，holdout8 不再可报数；若图省事直接拿“修后 11/0/0”当新数字，等于用调参集报数 | 严格按两步：修完 holdout8 **立即降级**，另写 holdout9 并**只跑基线**（规则 `version: 9` 一条不动）；对外数字只引 `rules-holdout9-baseline-20261029.json`；holdout9 五个漏报同样先写空集合，等下一轮修时才翻表 |
| 158 | 临时探针脚本若不加 `re.IGNORECASE`，得到的“只命中目标合同”结论会和引擎不一致（引擎是大小写不敏感的） | 探针统一用 `re.IGNORECASE`，与 `app/rules/engine.py` 同一口径；本轮五处候选都按引擎口径重跑后才落进 YAML（`FOB/EXW/FCA`、`The price … Inclusive` 这类大小写差异不会再骗过探针） |
| 159 | 第 10 轮五处都修好后，holdout9 不再可报数；若直接写“修后 11/0/0”当新数字，等于拿调参集报数 | 同样两步：修完 holdout9 **立即降级**，另写 holdout10 并**只跑一次基线**（规则 `version: 10` 一条不动）；对外数字只引 `rules-holdout10-baseline-20261030.json`（UTC 命名，本地生成于 2026-10-31）；holdout10 五个漏报同样先写空集合，等下一轮修时才翻表 |
| 160 | `R-DIS-003` 的跨句守卫用“仲裁句到法院句之间不得出现 `award`”来区分“裁决后起诉”，但 H90 的仲裁句**本身就含 `award`**，新写法被守卫拦住 | 不放松守卫（那会把 H39/H41 的“裁决后起诉”误吃成或裁或审），而是**单列一条 instead 分支**：只在 `may/shall/can/could … instead/alternatively … elect/choose/opt/have … court/litigate` 这种“选择权”语义里命中，与跨句分支互不干扰 |

---

## 8. 参考资料（按可信度排序）

| 优先级 | 资料 | 用途 |
|---|---|---|
| 1 | 本项目 `docs/devlog/01_RESEARCH_LOG.md` | 8 个仓库的事实、证据文件/行号、借鉴与不借鉴清单 |
| 2 | `开发提示词.md` | 需求、技术约束、禁止事项、交付要求 |
| 3 | aurelien-henrion/contract-agent（MIT） | 双 schema、Python 复核、HITL 安全写入门、脚本化 LLM 测试 |
| 4 | laolaola278-dev/enterprise-contract-review-agent（Apache-2.0） | 分页/字符偏移、citation、审计、确定性评测 |
| 5 | Harvey-cream/Langchain_DG（无 LICENSE） | 只读设计：Quality Gate、证据精确定位、等级下限、越权拦截 |
| 6 | zihan154896-jpg/intelligent-contract-review（无 LICENSE） | 只读设计：结构化修复重试、checkpointer 工厂、降级、Badcase |
| 7 | bcefghj/multi-agent-contract-review（Apache-2.0） | 规则 DSL 框架；**其 HITL 与 94% 指标不要照搬** |

---

## 9. 本次调研的第三方代码使用声明

- 没有把任何第三方仓库的源代码复制进本项目。
- 后续若复用 Apache-2.0 / MIT 代码，必须在文件头注明来源仓库、文件路径、许可证，并在 `README.md` 的“第三方代码与许可”一节列出。
- zihan / Harvey / Sentinel 无 LICENSE，**禁止复制代码**，只能按设计思想重写。

---

## 10. 下一步交接动作

1. ~~等用户确认 ADR-001 ~ ADR-005~~ ✅ 已确认（2026-10-26，全部“已接受”）。
2. ~~创建 `.venv`、安装依赖、`.gitignore`、git init~~ ✅ 已完成（Python 3.12.10，提交 `cf0fd63`）。
3. ~~最小图 ingest → segment → rules → report 跑通~~ ✅ 已完成（45 个测试通过）。
4. 下一步按顺序：
   - ~~**第 2 步**：`ingest` 接入 PDF（pypdf）/DOCX（python-docx）；`segment` 加标题识别、超长条款拆分、完整 `clause_type` 表；补 PDF/DOCX fixture。~~ ✅ 已完成（2026-10-26，63 个测试）。
   - ~~**第 3 步**：`app/services/llm.py` + `services/evidence.py` + `nodes/extract.py` + `nodes/validate.py`；Fake LLM 测试，无需 Key。~~ ✅ 已完成（2026-10-26，115 个测试；规则 5 → 7 条）。
   - ~~**第 4 步**：`route_by_risk` 条件边 + `interrupt()` + checkpointer（测试 `InMemorySaver`，运行 `SqliteSaver`）+ HITL 测试。~~ ✅ 已完成（2026-10-27，131 个测试；14 个 HITL 测试；SQLite 跨进程实测）。
   - ~~**第 5 步**：`nodes/explain.py` + Quality Gate + 报告合并；RAG MVP（BM25/字符 n-gram，默认 `RAG_ENABLED=false`）。~~ ✅ 已完成（2026-10-27，160 个测试）。
   - ~~**第 6 步**：FastAPI + Streamlit（上传、运行、展示/确认、下载；`.data/pending` 落盘 + 锁）。~~ ✅ 已完成（2026-10-27，197 个测试；真实语料 14 篇接入）。
   - **第四阶段第 1 轮（已完成，2026-10-27）**：规则 7 → 13 条（ADR-010）；50 份模拟合同拆入 `data/contracts/`；`eval/run_eval.py` 跑出触发基线（11/50 命中）；209 个测试通过。
   - **第四阶段第 2 轮（已完成，2026-10-27）**：`data/eval/gold_rules.json`（21 现象，silver）+ `data/contracts_holdout/H01–H08` + `data/eval/gold_holdout.json`；`eval/metrics.py` 三组指标；`run_eval.py` 支持 `--tag`；**留出集 P=1.00 / R=0.714 / F1=0.833，暴露 2 个漏报**；220 个测试通过（ADR-011）。
   - **第四阶段第 3 轮（已完成，2026-10-27）**：规则 `version: 4` 补英文/同义改写（`R-DIS-003/004`、`R-INC-001`、`R-INS-001`、`R-INP-002`），并修掉“子串误命中（Pacific→CIF）”与“运费窗口截断”两处缺陷；新写 `holdout2`（H09–H20，12 份）与 `holdout3`（H21–H28，8 份）；**holdout3 盲测 P=1.00 / R=0.571 / F1=0.727**，暴露 3 个措辞漏报；228 个测试通过。
   - **第四阶段第 4 轮（已完成，2026-10-27）**：规则 `version: 5` 修三类措辞（“亦可”类并列、“卖方负责支付…运费”、英文数词 `thirty-six (36) hours`）+ `R-INS-001` 保额从全文级收窄为**保险语境邻近**；新写 `holdout4`（H29–H40，12 份）；**holdout4 盲测 P=1.00 / R=0.889 / F1=0.941**，仅剩 H39 漏报（modal 与动词间插时间状语，**故意不修**，测试已钉住）；holdout3 回归 7/0/0；236 个测试通过。
   - **界面轮 1（已完成，2026-10-27）**：`app/web/`（`index.html` + `styles.css` + `app.js`）原生单页，FastAPI 托管 `GET /` 与 `/static`；四步（上传 → 审查 → 人工确认 → 报告）；无框架/无 CDN/无构建；241 个测试通过。
   - **界面轮 2（已完成，2026-10-27）**：按外部方法论 `Leonxlnx/taste-skill`（`references/app-screens.md`）重做成 **B 端审查工作台**——`aside.sidebar`（工作台 / 当前审查 / 复核报告 / 规则集 + 运行环境块）+ `header.topbar`（面包屑 + 服务在线）+ `main.sheet`（framed-sheet 画布）；hash 路由四视图；本地 IBM Plex 字体（`app/web/fonts/`，含 `OFL.txt`，零 CDN）；新增只读 `GET /api/rules`（`API_VERSION` 0.7.0 → 0.8.0，`RuleSummary/RuleCatalog` 白名单投影，不返回正则/DSL）；`tests/test_web.py` 6 项 + `tests/test_api.py::test_rule_catalog_matches_definitions`；真实浏览器 1440/768/390 四页 **0 FAIL / 0 WARN**；243 个测试通过。
   - **界面轮 3（已完成，2026-10-27）**：用户上传论文被当成合同跑完整审查 → 新增**文档类型闸门**（ADR-012）：`ingest_document` 后插 `precheck_document`，`classify_document` 用“抬头 / 合同编号 / 买卖双方 / 编号条款 / 交易要素 / 签署语”打分（阈值 4），叠加论文与法规反向信号；不是合同 → `status=not_contract` → 直接 `build_report`，**不切条款、不抽取、不判级、不触发 HITL**。契约侧 `DocumentCheck{is_contract, confidence, reasons, hints}` + `ReviewSummary.document_check` + `API_VERSION` 0.9.0 + `ReviewService.FINAL_STATUSES` 纳入 `not_contract`；前端新增“不是合同”页（判定依据 / 下一步 / 重新选择文件），工作台流水线 5 → 6 步。同时按用户要求**移除侧栏“运行环境”块**（接口版本 / 规则集 / checkpoint / RAG 开关），只留 `/docs` 入口。实测：论文 PDF 判否（0.98、0 findings）；5 个语料目录 90 份合同 0 误杀；257 个测试通过。
   - **界面轮 3 补充（已完成，2026-10-27）**：修复顶部“选择合同”按钮点了没反应（`#file-input` 是渲染时生成的，启动时缓存 `dom.fileInput` 为 `undefined`，改为 `dom.view.querySelector("#file-input")?.click()`，并加静态回归测试）；按用户要求在本机 `.env` 开启 RAG（`RAG_ENABLED=true`，知识库 1834 个片段可检索），并把检索移到 LLM 判断之前——**没配 Key 也能在报告里看到“知识引用”**（解释正文仍回退规则理由、`source="rule"`、等级不变），见 ADR-008 §6。
   - **界面轮 4（已完成，2026-10-27）**：用户要求“原来的侧边栏保留，仅右侧主体内容做变更” → 主区收成两屏（`#/` 上传合同、`#/review/{id}` 风险点），删除流水线/规则集/KPI/抽取要素/待核对/复核记录与 `#/workbench`、`#/rules`；待确认态改为用 `approval.findings` 先展示红色风险；下载链接改指 `/report?format=markdown`；261 个测试通过。
   - **界面轮 5（已完成，2026-10-27，ADR-013）**：账号/审查记录/Skill 仓库/BYOK + 右侧对话式首屏。
     - 后端：`app/services/accounts.py`（本地 SQLite 五表，PBKDF2 口令，会话只存 token 哈希，跨账号 404）、`secret_box.py`（`v1:` 密文盒 + `.data/secret.key`）、`llm_providers.py`（9 个厂商目录）、`skill_catalog.py`（7 个内置 Skill + `compose_focus`）、`llm.py`（`LLMRuntime` / `review_llm_scope` / `probe_llm`）；`POST /api/reviews` 增加 `focus / skill_id / reference`，`ReviewSummary.focus/skill_name`、`ReviewReport.focus/skill`；`API_VERSION 1.0.0`。
     - 前端：审查重点/附件/Skill 移到 `#view` 的对话式 `.composer-box`（Enter 发送、Shift+Enter 换行、拖拽）；侧栏只留登录入口（注册在弹窗 tab 内、`.auth-extra` 等高）；底部免责一行 + 右下角隐私条款/使用政策弹窗（`01…` 编号、13.5px/1.62）；新增 API 配置、Skill 仓库、我的审查三个弹窗。
     - 验证：`pytest` 288 通过；`ruff` / `node --check` 通过；HTTP 端到端 34 项（注册→Skill→带 focus 上传→approve→Markdown→记录→BYOK 密文→退出→跨账号 404）全过；CDP 11 项（对话式首屏、弹窗等高 460×458、政策编号、480px 无溢出）全过。
   - **界面轮 6（已完成，2026-10-27）**：历史可运维 + Skill 入口归位 + 满屏 + 弹窗定高。
     - 后端：`review_records` 加 `title / pinned`（`PRAGMA` + `ALTER TABLE` 平滑升级）；`list_reviews()` 改 `pinned DESC, created_at DESC`；新增 `PATCH /api/reviews/{id}`（改名 / 置顶，空串恢复文件名、截断 60 字）与 `DELETE /api/reviews/{id}`（204）；`ReviewService.discard()` 连带清 pending / 运行时 / checkpoint；`record()` 在暂停时写 `awaiting_human`（原来误写 `running`）。
     - 前端：删掉首屏三行说明；主区 `.view` 满宽 + `.chat` 垂直居中 + 输入区 880px；Skill 下拉 = 内置 + 自建 + 固定末项“Skill 仓库…”（选它打开侧栏仓库，默认 `builtin:full`）；“当前审查”→“审查历史”侧栏折叠子目录（改名 / 置顶 / 删除，事件委托）；侧栏底部新增 Skill 仓库入口（带数量）；登录/注册共用定高弹窗（460×453、body 396/396）并必须手勾同意（默认不勾选）。
     - 验证：`pytest` 295 通过；`ruff` / `node --check` 通过；CDP 26 项（铺满 1432/1440、下拉 8 项末项 `__repo__`、同意未勾被拦、gap 34px、弹窗 460×453、子目录改名/置顶/删除、480px 无溢出）全过。
   - **界面轮 7（已完成，2026-10-27）**：仓库独立页 + 自绘下拉 + 页脚贴右 + 输入区收窄。
     - 前端：删除 `#skills-dialog`，侧栏入口改 `href="#/skills"`，新增 `renderSkillsPage()`（推荐 7 / 我的 / 新建，两栏 `.skills-grid`，操作走 `#view` 事件委托）；原生 `<select>` 换成胶囊触发器 + `ul[role="listbox"]`（12px 卡片、`aria-selected`、↑↓/Esc/点外收起、末项“Skill 仓库… · 管理”、`max-height:336px` 无滚动条、≤640px 左对齐）；`.sheet-foot` 去掉 820px 上限改 `width:100%`、`padding-top:8px`、字号 11.5/行高 1.45（实测高 26px），`.foot-links{margin-left:auto}` 贴右；`.composer-box` 880→720、textarea 56→44。
     - 验证：`pytest` **297 通过**（新增 2 项前端测试）；`ruff` / `node --check` 通过；CDP 20 项（输入区 720、页脚右边缘 1399/1432、页脚 26px、政策链接贴右、下拉 8 项无滚动条、仓库页 0 个 dialog、480 菜单不越界）全过。
   - **界面轮 8（已完成，2026-10-27）**：注册 not found 根因 + Skill 导入。
     - 诊断：8000 端口是旧进程（`/openapi.json` 版本 **0.9.0**，无 `/api/auth/*`），前端点注册必然 404；停止旧 PID → `uvicorn app.api:create_app --factory --port 8000` 重启 → `version=1.0.0`、`GET /api/auth/me` 200。
     - 前端：`#/skills` 右栏新增“从 Markdown 导入”——`.dropzone`（可聚焦、Enter/空格触发）+“选择 .md 文件”（`accept` + `multiple`）+“选择文件夹”（`webkitdirectory`），拖拽文件夹用 `webkitGetAsEntry()` 递归 `readEntries()`；`parseSkillMarkdown()` 读 frontmatter（`name`/`description`/`instruction`）→ 一级标题 → 文件名 → 首段；长度 40/160/1000 与服务端对齐、超长截断；逐条 `POST /api/skills`（只发三字段，`extra="forbid"`）、同名跳过、单次 30 个 / 单文件 200 KB、未登录拦截并弹登录、结果落到 `.import-log`（ok/bad/skip）。
     - 验证：`pytest` **298 通过**（`tests/test_web.py` 19 项）；`ruff` / `node --check` 通过；CDP 10 项（拖拽高亮、2 md 建成 2 Skill 且 txt 被过滤、frontmatter 生效、侧栏计数 +1、同名跳过、未登录被拦、480 无溢出）全过。
   - **界面轮 9（已完成，2026-10-28）**：个人账户弹窗 + Skill 查看/编辑 + 仓库紧凑化 + 厂商扩容 + 阻止密码自动填充。
     - 仓库页删掉 `page-head` 说明段；列表项改成一行（名称 + 标签 + 折叠箭头 + 使用，`.skill-head` / `.skill-toggle` / `.skill-detail`，行高 36px），点名称展开说明、审查重点与操作；“编辑”把内容填进右栏（标题“编辑我的 Skill”、按钮“保存修改”、出现“取消”），提交 `PATCH /api/skills/{id}`；推荐 Skill 只读，点“存为我的”预填后仍 `POST`。
     - 右栏收紧：`.panel` 12/13px、`.field-compact` 输入 30px、textarea 68px、`.btn-compact` 30px、卡片 gap 10px；实测表单 ~318px、导入 ~171px。
     - 个人账户：侧栏 `.account-row`（退出登录 + 26px 圆形头像）→ `#account-dialog`（62px 头像 + 更换/移除、昵称、只读邮箱、减少动效 / 自动聚焦、清除本机缓存 / 清空审查记录）；两个清除动作都先展开红色确认条；“清空审查记录”先取数量、0 条直接提示不需要清除；头像在浏览器 `squareThumbnail(file, 128)` 压成 128×128 JPEG 后 `PATCH /api/auth/profile`。
     - 后端：`users.avatar` 列 + `_ensure_user_columns()` 老库升级；`PATCH /api/auth/profile`（`display_name` ≤40、`avatar` 仅 data URL ≤400k）；`PATCH /api/skills/{id}`（`builtin:*` → 400 “另存为我的”，跨账号 404，未登录 401，`_clean_skill_fields()` 与新建共用）；厂商目录 10→20（Gemini/xAI/Groq/Mistral/Together/火山/千帆/混元/MiniMax/阶跃/LM Studio）。
     - API 配置表单：`autocomplete="off"` + Key 输入 `autocomplete="new-password"` + `name="llm_api_key"` + `data-lpignore` + `data-form-type="other"`，解决“点 Key 输入框弹出浏览器快捷填入账号密码”。
     - 验证：`pytest` **308 通过**（`tests/test_accounts.py` 35 项、`tests/test_web.py` 22 项）；`ruff` / `node --check` 通过；CDP 冒烟全过（头像入口位置/弹窗/改名/动效关/两处二次确认/128×128 头像/列表折叠与编辑改名/推荐“存为我的”/紧凑尺寸/厂商 ≥20/`new-password`）；截图 `skills-compact.png`、`account-dialog.png`。
   - **界面轮 10（已完成，2026-10-28）**：账户设置改成 B 端分区弹窗 + 侧栏不再显示昵称/邮箱。
     - 侧栏：删掉 `#account-line`（连同 `accountLine`、`.account-line` / `.account-name` / `.account-mail` 样式），左下角只留“退出登录 + 26px 圆形头像”；`renderAccount()` 不再把昵称/邮箱拼进侧栏。
     - 弹窗：`.dialog.account-dialog` 760×560（窄屏 `calc(100vw - 16px)` 且分区导航转顶部横向标签）；左侧 `[data-account-panel]` 四个分区（个人信息 / 通用 / 数据管理 / 关于），右侧 `[data-account-section]` 面板 `hidden` 切换，↑↓ 键可移；`setAccountPanel()` 在“数据管理”按需拉 `/api/reviews?limit=500` 与本地自建 Skill 数，在“关于”拉 `/health` 版本。
     - 通用：主题色 5 套（松石绿 / 靛青 / 石墨 / 陶土 / 绛紫，只换 `--accent`，风险红黄绿不动；深色媒体查询里给同色系亮版），字号 小/标准/大（`--ui-text-scale` = 0.94/1/1.1，全量 `font-size` 换 `calc(... * var(--ui-text-scale))`，布局尺寸不变），保留“减少动效 / 自动聚焦”，新增“恢复默认外观”。（**界面轮 12 已把主题色换成“白天 / 黑夜 / 跟随系统”三档**，`--accent` 不再可调。）
     - 数据管理：两个统计卡 + 两档清除（本机缓存 / 清空审查记录），清除仍先出红色确认条；个人信息补“注册时间”只读字段与姓名/邮箱摘要；关于区放版本、条款政策入口与数据位置。
     - 验证：`pytest` **308 通过**（`tests/test_web.py` 22 项，个人账户测试改为分区断言并断言侧栏不再有 `#account-line`）；`ruff` / `node --check` 通过；CDP 21 项全过、`exceptions: []`（弹窗 760×560、左侧导航 164px、4 分区切换、主题色切到靛青后 `--accent=#3a4f9b` 且写进 `alex.prefs`、字号大档标题 23→25.3px 且小字也同步、数据统计 0/0、空记录“不需要清除”、确认条可取消、关于版本 1.0.0、关窗后偏好保留、重开回到“个人信息”、480px 导航转横向且无横向溢出）。
   - **界面轮 11（已完成，2026-10-28）**：推荐 Skill 方块 + 新建/导入弹窗 + 对话式逐条审查与修订导出 + 退出中断确认。
     - Skill 仓库：`skillTile()` 生成 `.skill-tiles`（`repeat(auto-fill, minmax(122px,1fr))`、`aspect-ratio:1/1`、卡内 2 行名称 + 2 行说明 + 右下角“使用”胶囊），推荐区不再是一行长矩形；页头 `.skills-head` 右上角放 `#skill-new-open` / `#skill-import-open`，右栏 `.skills-grid` / `.skills-side` / `.skill-form` 全部删除；新建与导入改成 `index.html` 静态弹窗 `#skill-new-dialog` / `#skill-import-dialog`（编辑自建 Skill 复用同一弹窗走 `PATCH`，推荐“存为我的”只是预填）；因为弹窗在 `#view` 外，`bindSkills()` 的事件委托全部改到 `document`。
     - 后端：`app/schemas.py` 加 `ClauseFinding` / `ClauseReview` / `ClauseReviewList`；新增 `app/services/clause_review.py`（`build_clause_reviews()` 只聚合图状态，条款等级 = `red > yellow > pass`，`pass` = 规则未命中；`REVISION_TEMPLATES` 14 条示例条款 + `REVISION_NOTE`，红前黄后、按 `rule_id` 去重；无条款归属的规则进 `contract_findings`）与 `app/services/clause_export.py`（DOCX 用 `python-docx`、PDF 用 `reportlab` 内置 `STSong-Light`，三节 + 免责声明，内存生成）；新增 `GET /api/reviews/{id}/clauses` 与 `POST /api/reviews/{id}/export`（`format: docx|pdf` + 已更正条款；`ExportError`→400；`Content-Disposition` 带 RFC5987 中文名；沿用 `authorize()` 归属校验）；`requirements.txt` 加 `reportlab==4.4.4`。
     - 前端结果页：`.review-shell`（用户气泡 + 助手气泡 `#ai-stream` + `#approval-slot` + `#workbench`）；`chatNarrative()` 拼真实数据、`streamText()` 18ms/3 字逐段写入（`prefs.motion` 直出、`stopStream()` 清理），结束时展开工作台并（必要时）滚到分屏；`.workbench-grid` 左 `#clause-list`（序号 / 名称 / 等级 / 已更正✓ + 首行“※ 全合同”）、右 `#clause-detail`（原文 / 意见 / 建议 / 依据 / 引文 / 可编辑修订 / 一键更正 / 撤销）；`data-apply-all` 批量套用，`state.corrections` 只在前端；导出用 `blob` + `filenameFromDisposition()` 解中文名；`renderApproval()` 改成只返回 HTML，由 `#approval-slot` 挂载后 `bindConfirm()`。（**界面轮 12 已删掉气泡与流式部分**，改为标签行 + 直接分屏。）
     - 退出确认：`hasActiveTask()` = `busy || taskActive || reviewStatus ∈ {awaiting_human, running}`，命中弹 `#logout-confirm`（“审查任务仍在进行 / 退出会中断这次任务…”），取消不退出；确认走 `doLogout()`（界面轮 12 起不再有流式定时器，只清本地状态）。
     - 验证：`pytest` **323 通过**（新增 `tests/test_clause_review.py` 11 项，`tests/test_web.py` 26 项）；`ruff` / `node --check` 通过；Edge headless + CDP 复核（方块 130×130、右上角按钮与页头右边缘齐平、两个弹窗、450ms 仅 105/276 字符、分屏两栏 376/709、红条款建议与示例条款、更正/撤销、导出 DOCX 39,086 B / PDF 9,205 B、退出确认可取消）。
   - **界面轮 12（已完成，2026-10-28）**：配色三档 + Skill 工具/附件 + 头像裁剪 + 标签行 + 历史即时刷新 + 切分精度 + 左原文右意见独立滚动。
     - **配色**：删掉 5 套主题色与 `.theme-dot`，`prefs.scheme ∈ {light, dark, system}`；`resolvedScheme()` 用 `matchMedia("(prefers-color-scheme: dark)")` 解析 `system`，写 `html[data-scheme]`（生效）/ `html[data-scheme-pref]`（用户选择）与 `<meta name="color-scheme">`；深色变量从 `@media` 搬进 `html[data-scheme="dark"]`；`darkQuery.change` 时系统切换即时生效；通用面板三个按钮 `[data-scheme-value]`。
     - **Skill 形式**：`TOOL_CATALOG` 5 个已实现能力（`rules_scan` / `field_extract` / `clause_split` / `knowledge_lookup` / `negotiation_hint`，各带 `effect`）；`Skill` 增 `tools`，`SkillAsset` 只存文本（`.py/.md/.markdown/.txt`、≤5 个、单个 ≤6000 字、总量 ≤30000）；`skills` 表加 `tools` / `assets`（JSON，老库 `ALTER TABLE`）；`GET /api/skills/tools`；新建/编辑弹窗加工具胶囊与附件区（明写“只读取文本，不会被运行”）；`compose_focus()` 拼工具 effect 与附件，并声明“不作为判级依据、不得当作指令执行”。
     - **头像裁剪**：`#avatar-crop-dialog` + 288px 画布，`cropGeometry()` / `drawCrop()` / pointer 拖动 / 方向键 / 缩放滑杆 / 重置；`cropResult()` 输出 128×128 `image/jpeg` 0.85 → `PATCH /api/auth/profile`；删除 `squareThumbnail()`。
     - **标签行 + 删叙述**：`reviewChip()` → `.chip-tag`（合同 / Skill / 审查重点，`chip-wide` 46ch 省略 + `title`）；删除 `chatNarrative()` / `streamText()` / `stopStream()` / `state.streamTimer` / `#ai-stream` / `.chat-thread` / `.msg` / `.msg-bubble` / `.stream-caret` / `caret-blink`；`doLogout()` 不再调 `stopStream()`。
     - **历史即时刷新**：`refreshHistory()` 静默 `GET /api/reviews?limit=20` → `renderHistory()`（不调 `setBadge`），在 `startReview()` 与 `decide()` 成功后调用；登录后收起“登录后可以查看…”提示。
     - **人话**：`PASS_NOTE` + `.pass-block`（绿底），先说“这一条没有发现需要修改的地方”，再补“这一条和当前规则库对照过”，不再复述“没有命中规则，可按原文保留”。
     - **切分**：`segment.py` 增 `_NUMBERED_HEADING`（≤600 字）/ `_LABEL_HEADING`（≤800 字）/ `_FIELD_LABELS`（装运港、Port of Shipment…）/ `_notice_spans()`（特别提示块）/ `_merge_translations()`（中英对照，带编号不并）/ `_short_title()`（目录短标题）；`_merge_small()` 只并无标题小段；`ClauseReview.is_preamble` 让前言显示“前言”、导出也不写成“第 1 条”。
     - **左原文右意见**：`.workbench-grid` 等高 `min(66vh, 720px)`；左 `.clause-pane` 只做 flex 容器（`overflow:hidden`），目录 `#clause-list` 与当前条款原文 `#clause-origin` 各自 `overflow-y:auto`；右 `#clause-detail` 独立滚动；三块都 `overscroll-behavior: contain`；每条给“采用修改 / 保留原文 / 撤销更正”，`state.kept` 与 `state.corrections` 互斥；窄屏（≤900）上下排列。
     - 验证：`pytest` **334 通过**（`tests/test_segment.py` +3、`tests/test_clause_review.py` +1、`tests/test_accounts.py` +4、`tests/test_web.py` +3 并改写旧断言）；`ruff` / `node --check` 通过；Edge headless + CDP 复核（三档配色落 `html[data-scheme]`、Skill 弹窗 5 个工具胶囊、头像裁剪保存为 JPEG data URL、真实上传后左目录 + 左原文 + 右意见、640 高视口下右栏滚 141px 时左栏与整页保持 0、采用/保留状态正确）。
   - **界面轮 13（已完成，2026-10-28）**：30 MB 上传 + 图片 PDF OCR + 4 个外部 Skill 包 + zip 导入 + 付款条件去重 + 同一行标签 + 完整原文。
     - **上传上限**：`MAX_UPLOAD_MB` 默认 15 → 30（`app/config.py`、`.env`、`.env.example`）；前端 `MAX_BYTES = 30 * 1024 * 1024`、错误文案与首屏 `.composer-hint` 同步；API `limit_bytes` 与 Streamlit `settings.max_upload_mb` 共用同一配置，测试钉住“30 MB”。
     - **OCR**：新增 `app/services/ocr.py`（`pypdfium2` 渲染 + `rapidocr-onnxruntime`，进程内复用引擎 + 锁，单页失败跳过）；`app/nodes/ingest.py` 只在**整份文本 < 50 字**（全页）或**单页 < 10 字**（补该页）时触发，`targets[:ocr_max_pages]`，超出与失败都写 warning；`OcrError` → `fail(str(exc), warnings)`；OCR 文本只进 `raw_text`，**不判级**；`tests/test_ocr.py` 5 项（图片 PDF 走 OCR、文本 PDF 不调、失败降级、开关关闭、依赖缺失）。
     - **外部 Skill 包**：4 个桌面包复制到 `app/resources/skills/{letter-of-credit-reviewer,xiaping-export-contract,xiaolv-export-contract,ai-contract-risk-officer}`；`skill_catalog.py` 用 `_PACKAGE_SPECS` 声明 `builtin:*` 四个 id，`instruction` 为提炼稿（≤1000 字），`_package_assets()` 把原 `SKILL.md` 放第一位、references 按固定优先级排序（≤5 个 × 6000 字，超长标“（节选）”）；内置 Skill 7 → 11。
     - **zip 导入**：`parse_skill_package(raw)` 找最浅 `SKILL.md`、解析 frontmatter 的 `name/description/tags`，正文作 instruction；只收 `.py/.md/.markdown/.txt`；拒绝非 zip / 缺 `SKILL.md` / >8 MB / 解压 >40 MB / >200 条目 / 单文件 >200 KB；**内存解析、不落盘、不执行**；`POST /api/skills/import`（需登录，201，返回 `{skill, warnings, files}`）；测试用 `raise SystemExit` 的 `check.py` 证明未被执行。
     - **两个付款条件**：根因是旧切分把 `5. 付款条件： Payment:` 后面的英文段又切成一条标题、并吞掉后 4 条；修法两层——`segment._merge_duplicate_headings()`（切分时相邻同名合并、偏移连续）+ `clause_review._merge_adjacent_duplicates()`（展示层兜底旧记录，文本拼接、意见按红→黄合并、等级仍由原 findings 推出、合并后重排 `index`）；`_display_title()` 把旧长标题截成“编号 + 主题词”。
     - **同一行标签**：结果页删 `.review-head-main` / `.file-line`，合同文件名、Skill、审查重点、状态全部进 `#review-chips`；`.review-chips .status-chip{margin-left:0}`。
     - **完整原文**：`ClauseReviewList.contract_text = state.raw_text`；左栏 `.pane-tabs`（**条款目录**默认 / **原文全文**），`renderContractFulltext()` 按 `\n\n` 分段、段内 `\n` → `<br>`，自己 `overflow-y:auto` + `overscroll-behavior:contain`；`applyPaneMode()` 只切左栏，不影响右栏意见。
     - 验证：`pytest` **347 通过**（`tests/test_ocr.py` +5、`tests/test_accounts.py` +4、`tests/test_segment.py` +1、`tests/test_clause_review.py` +2、`tests/test_web.py` +1 并改写 2）；`ruff` / `node --check` 通过；真实图片 PDF OCR 4.9 s（`SALES CONTRACT / 2.PAYMENT TERMS / 100% T/T IN ADVANCE / 3.DELIVERY:CIF HAMBURG`）；`4b82dd…` 旧记录 7→6 条且只剩一个“5. 付款条件”；`0bbbf1…` 15 条 + `contract_text` 7552 字。
   - **界面轮 14（已完成，2026-10-28，ADR-015）**：多智能体专家并行 + 只读工具层（本地工具 / MCP），默认关闭。
     - **专家并行**：`app/nodes/experts.py` 三个 `ExpertSpec`（`payment` / `delivery` / `dispute`，各带 `clause_types` + 中英关键词 + `instruction`）；`select_experts()` 纯 Python 按条款类型/关键词路由，无命中跑全部（召回优先）；`route_experts()` 在开关关闭/`status=failed`/无条款时直接返回 `evaluate_rules`；`validate_extraction` 用条件边返回专家节点列表 → LangGraph 并行 fan-out → `collect_expert_findings` 汇合 → `evaluate_rules`。
     - **并行写安全**：`ContractReviewState.expert_findings / expert_notes / expert_route` 用 `Annotated[list, operator.add]`；每个专家 `finish()` 只回这三类字段；`expert_status`（`skipped/ok/degraded`）/ `degraded_steps` / `warnings` 由汇合节点单点写；展示层按 `EXPERT_ORDER` 归一顺序。
     - **不判级**：`ExpertDraft` / `ExpertOpinion` 均 `extra="forbid"` 且**没有 `risk_level`**；引文必须 `locate_quote` 命中（否则丢弃 + `expert:<id>:quote_not_found`）；无 Key → `:not_configured`，异常 → `:failed`，都只写 `expert_notes`。
     - **工具层**：`app/services/tools.py` 的 `ToolRegistry`（白名单、`call()` 永不抛异常、参数 200 字 / 摘要 400 字截断）注册 4 个本地只读工具（`contract_outline` / `find_clause` / `read_field` / `search_knowledge`，后者受 `RAG_ENABLED` 控制）；`McpStdioClient` 手写 `initialize → tools/list → tools/call`（`shell=False`、单行 ≤1 MB、超时 `kill()`、不可达注册 `<server>/unavailable`），零新依赖。
     - **节点**：`app/nodes/research.py` 的 `research_tools` 插在 `evaluate_rules`（或人工确认）之后、`explain_risks` 之前；`ToolPlan` 1 次规划、`min(MAX_TOOL_CALLS, 3)` 次执行；未注册工具只记 `ok=False`；**无 LLM 时 `_fallback_plan()`** 用第一条红/黄规则标题做确定性检索并写 warning。
     - **解释与状态**：`explain.py` system prompt 增第 9/10 条，user prompt 增 `<untrusted_experts>` / `<untrusted_tools>`（结束标签转义），引用白名单扩成“本条 RAG 命中 ∪ 工具 citation”；`ClauseReviewList.agent_trace`（`_agent_trace` 过滤 + 归一）+ `ReviewReport.expert_findings / tool_calls`。
     - **前端**：`expertBlocks(clauseId)` 渲染“参考 · {专家}”（`topic/detail/quote/citation/suggestion` + 明写“不代表风险等级”），`agentTraceBlock()` 用 `<details>` 折叠轨迹（专家 / 状态 / **降级原因翻成人话** / 工具成败 / 调用次数与合计耗时 / 引用）；`.expert-*` 只用中性色，测试断言 `.expert-block` 不含语义色变量。
     - **报告与导出**：`report_markdown.py` 加“专家参考意见（不参与判级）”“工具调用记录”两节；`clause_export.py` 的 DOCX / PDF 加“四、专家参考意见（不参与判级）”“五、工具调用记录”（取自 `ClauseReviewList.agent_trace`，失败调用也留错误原因）。`AgentTrace.expert_notes` 透出 `expert:<id>:not_configured / :failed / :quote_not_found`（去重），前端翻成“未配置模型 / 执行失败 / 引文未能在原文定位”。
     - **配置**：`Settings` 新增 `agents_enabled=False` / `tools_enabled=False` / `mcp_servers=""` / `mcp_timeout_seconds=10.0` / `max_tool_calls=3`；`.env.example` 带 JSON 示例；`/health` 返回两个开关；`API_VERSION` 1.0.0 → **1.1.0**。
     - 验证：`pytest` **386 通过**（`tests/test_agents.py` 12 项、`tests/test_tools.py` 23 项含伪 MCP 服务器、`tests/test_web.py` +1）；`ruff` / `node --check` 通过；开/关专家对照测试确认 `rule_id` 与 `overall_level` 完全一致。
   - **界面轮 15（已完成，2026-10-28，ADR-016）**：检索评测落地（ISSUE-018 关闭）。
     - **gold 两层映射**：`eval/rag_gold.py` 用 `CISG-N` / `CC-N` / `LAW-N` / `JI-CC-N` 通用条号正则 + `data/eval/rag_label_map.yaml`（27 个手判标签、12 条 `gaps`）把 `100问题.md` 翻成 `source_id#section`；一个标签允许多条可接受片段（`CISG-ZH#s27` / `CISG-EN#s26` / `CISG-KEY#s25`），`strict` 剔解读稿、`lenient` 保留；`gaps` 命中的题标 `unresolved` **不进分母** → **95 题可评测 / 5 题未覆盖**；生成物 `data/eval/gold_rag.json` 带 `generated_at` 与 `corpus.chunk_count`。
     - **指标与口径**：`eval/rag_eval.py` 纯计算（`recall_at` / `mrr` / `rank_histogram` / `by_group` / `misses_beyond_k` / `not_top1`）；`eval/run_rag_eval.py` 同时跑 `ranking`（top-5、`min_score=0`）与 `production`（`RAG_TOP_K=3` / `RAG_MIN_SCORE=1.0`），结果落 `eval/results/rag-20261028.json`；gold 过期直接 `exit 3`，测试 `test_committed_gold_matches_current_corpus` 重建比对。
     - **加权（只改排序）**：`app/services/rag.py` 的 `_article_numbers()` / `_query_boosts()`，点名条号 ×2.5、条文原文再 ×1.1、点名来源 ×1.15；条号正则支持 `第39(2)条` / `第49(1)(b)条` / `第2条第2款`；抽不出条号全 1.0（与原 BM25 一致，有断言）。
     - **数字互转单一实现**：新建 `app/services/chinese_numbers.py`（`to_chinese_number` / `from_chinese_number`，`NumberFormatError`），检索与 gold 共用。
     - 验证：`pytest` **398 通过**（`tests/test_rag_eval.py` 6 项、`tests/test_rag_boost.py` 6 项）；`ruff` / `node --check` 通过；指标 lenient R@1 0.516→**0.747** / R@3 0.800→**0.958**、strict R@1 0.158→**0.305** / R@3 0.390→**0.758**；剩 4 题语义指代登记 ISSUE-033。
   - **阶段 4 第 5 轮 + 界面轮 16（已完成，2026-10-28）**：holdout5 盲测 + H39 修复 + 报告导读 + 批量清空。
     - **先写集**：`data/contracts_holdout5/`（H41–H52，12 份）+ `data/eval/gold_holdout5.json`（10 现象 / 9 条规则；H43“仅可依法申请撤销裁决”、H52 全合规为干净对照）；刻意换写法：英文 `may, within forty-five (45) days …, bring an action`、中文“仲裁裁决作出后…仍可提起诉讼”、英文 `At the option of the Buyer … or … the courts`、`within forty-eight (48) hours after discharge`。
     - **先跑基线**：`eval/results/rules-holdout5-baseline-20261028.json` → `TP=9 FP=0 FN=1 TN=122`，**P=1.00 / R=0.90 / F1=0.947**（唯一漏报 H41，与 H39 同型）；**这份基线是 holdout5 唯一可对外引用的数字**。
     - **才改规则**：`R-DIS-004` 英文分支 `\s+(?:may|shall|can|could)\s+` → `\s*[^.]{0,80}?`（状语前是逗号，必须 `\s*`）；规则 `version: 5` → **6**；修后 holdout5 `10/0/0`、holdout4 `9/0/0`（H39 进期望表）、holdout1–3 与主集 50 份仍全 1.0，无新误报。
     - **纪律固化**：`tests/test_rules.py` 新增 `EXPECTED_HOLDOUT5_HITS` + `test_holdout5_hits_are_stable()`（逐规则比集合，H43/H52 断言零命中）；原“H39 必须漏报”翻为“必须命中”。
     - **报告导读**：`app/web/app.js` 的 `LEGAL.guide` 七节（等级只有规则能给 / 三档含义 / 证据怎么读 / “参考 · 专家”不是等级 / Agent 轨迹与工具调用 / 这份报告不能说明什么 / 建议的使用顺序）+ `openGuide()` 用 `/report?format=json` 的 `limitations` 追加第八节；结果页两处入口（动作区 + “仅下载报告”分支）；关闭 ISSUE-024。
     - **批量清空**：`app/api.py` 的 `DELETE /api/reviews`（`ReviewPurgeResult{deleted}`）+ `accounts.delete_reviews()` 单事务按 owner 删；随后 `service.discard()` 与 `rmtree(upload_root/<id>)`；前端改成一次请求；ISSUE-022 第 7 条解决。
     - 验证：`pytest` **401 通过**（`tests/test_accounts.py` +1 覆盖 401 / 跨账号 / 幂等，`tests/test_web.py` +1 覆盖导读文案与动态节）；`ruff check app tests eval`、`node --check app/web/app.js` 通过。
   - **阶段 4 第 6 轮（已完成，2026-10-29）**：纯英文 holdout6 盲测 + 三处英文写法修复。
     - **先写集**：`data/contracts_holdout6/`（H53–H64，12 份**全英文正文**）+ `data/eval/gold_holdout6.json`（11 现象覆盖 11 条文本规则，含 R-PAY-002 / R-DIS-002 两个“条款缺失型”；H62、H63 为干净对照）。
     - **先跑基线**：`eval/results/rules-holdout6-baseline-20261028.json` → `TP=8 FP=0 FN=3 TN=121`，**P=1.00 / R=0.727 / F1=0.842**（漏报 H53/H55/H61）；**这份基线是 holdout6 唯一可对外引用的数字**。
     - **才改规则**（`version: 6` → **7**）：`R-INC-001` 增英文倒装分支（`seller … arrange and pay for|pay for|prepay|bear|defray … ocean/sea freight|freight|carriage`，不收裸 `pay`）；`R-DIS-003` 的 `\s+or\s+` → `\s+or[,\s]\s*`；`R-PAY-001` 增 `entire|full|whole|100% of the … price/amount/payment … in advance|before shipment|prior to shipment|upon signing`。
     - **修后只作回归**：holdout6 `11/0/0`（H62/H63 仍零触发）、holdout5 `10/0/0`、holdout4 `9/0/0`、holdout3 `7/0/0`、holdout2 `9/0/0`、holdout1 `7/0/0`；主集 50 份 `11/0/0` 且命中分布与 `version: 6` **逐条相同**（无新误报）。
     - **纪律固化（本轮升级）**：`tests/test_rules.py` 新增 `EXPECTED_HOLDOUT6_HITS` + `test_holdout6_hits_are_stable()`，**先按基线把三个漏报写成空集合**（跑通即基线快照），修完再跑必然失败并点名 H53/H55/H61，此时才翻表并注明“本批已降级、只引基线文件”。
     - 验证：`pytest` **402 通过**；`ruff check app tests eval`、`node --check app/web/app.js` 通过；`tests/test_api.py` 的 `ruleset_version` 断言 6→7。
   - **阶段 4 第 7 轮第一步（已完成，2026-10-29）**：中英混合 holdout7 盲测基线（**当轮不改规则**）。
     - **先写集**：`data/contracts_holdout7/`（H65–H76，12 份**中英混合**）+ `data/eval/gold_holdout7.json`（11 现象 / 11 条文本规则；H75、H76 为干净对照）；刻意选四种与现有正则形态不同的写法：H65 `The ocean freight … shall be for the Seller's account`、H66 仲裁句与法院句**分属两句**、H67 中文“装运前一次性支付合同项下全部价款”、H69 `bring the matter before the courts`。
     - **只跑基线（未改规则，`version` 仍 7）**：`eval/results/rules-holdout7-baseline-20261029.json` → `TP=7 FP=0 FN=4 TN=121`，**P=1.00 / R=0.636 / F1=0.778**，合同级 `TP=6 FP=0 FN=4`，漏报 H65/H66/H67/H69；**这份基线是 holdout7 唯一可对外引用的数字**。
     - **纪律固化**：`tests/test_rules.py` 新增 `EXPECTED_HOLDOUT7_HITS` + `test_holdout7_hits_are_stable()`，四个漏报先写成**空集合**（跑通即基线快照）；第二步修完规则后该测试必然失败并点名，届时才翻表降级。
     - 验证：`pytest` **403 通过**；`ruff check app tests eval`、`node --check app/web/app.js` 通过。
   - **阶段 4 第 7 轮第二步（已完成，2026-10-29，规则 `version: 8`）**：按基线只修四处写法。
     - **先探针后改规则**：候选正则先在临时脚本跑 **7 批留出集 76 份 + 主集 50 份 + 2 份样例**；第一次探针发现 `R-DIS-003` 跨句候选在 holdout4 H39 / holdout5 H41（“裁决后起诉”）上也命中，会制造新假阳性 → 加 tempered-dot 守卫（中间禁用 `award` 与新条标题）。
     - **四处修法**：`R-INC-001`（1.2→1.3）卖方账上运费 `for the Seller's account / at the Seller's expense`；`R-DIS-003`（1.1→1.2）跨句或裁或审；`R-PAY-001`（1.0→1.1）中文“装运前一次性付全部价款”（排除“全部价款的 30%”）；`R-DIS-004`（1.2→1.3）`bring the matter before the courts`。
     - **纪律**：改完先跑规则测试，**只有** `test_holdout7_hits_are_stable` 失败并点名 H65/H66/H67/H69（其余 55 个规则测试全绿），才翻表降级。
     - **修后只作回归**：holdout7 `11/0/0`（H75/H76 仍零触发）、holdout1–6 全 FP=0、主集 `hit_counts` 与 v7 逐条相同；`tests/test_api.py` 断言 `ruleset_version == 8`；验证 `pytest` **403 通过**、`ruff check app tests eval`、`node --check app/web/app.js` 通过。
   - **阶段 4 第 9 轮第一步（已完成，2026-10-29，规则 `version: 9`）**：只按 holdout8 基线修那五处，多一处不改。
     - **五处修法**：`R-INC-001`（1.3→1.4）迂回语态扩成 `(?:(?:for|on) … account|at … (?:expense|cost))` 并**保留**旧分支；`R-DIS-003`（1.2→1.3）跨句动词表补 `\brefer[a-z]*`（`\b` 防 `prefer`）；`R-PAY-001`（1.1→1.2）加“收到/收讫 + 全部价款/货款 + 后/再 + 装运”；`R-DIS-004`（1.3→1.4）加中文“不服 + 向…法院 + 上诉/起诉/诉讼”（不收撤销裁决这类法定救济）；`R-INP-002`（1.2→1.3）加 `immediately/forthwith/promptly … upon discharge` 与 `on the same day`。
     - **先探针后落 YAML**：候选正则同时跑九批留出集 100 份 + 主集 50 份，只保留“只命中目标合同”的写法（`re.IGNORECASE` 与引擎一致）；跑完即删临时脚本。
     - **纪律**：`test_holdout8_hits_are_stable` 先失败并点名 H77/H78/H79/H80/H83（其余规则测试全绿），才把空集合翻成“必须命中”。
     - **修后只作回归**：holdout8 `11/0/0`（H87/H88 仍零触发）、holdout1–7 全 FP=0、主集 `hit_counts` 与 v8 逐条相同（`R-INS-001:1,R-INP-002:1,R-INC-001:1,R-INC-002:1,R-PAY-002:5,R-DIS-003:1,R-DIS-004:1`）；`tests/test_api.py` 断言 `ruleset_version == 9`。
   - **阶段 4 第 9 轮第二步（已完成，2026-10-29）**：新写 holdout9 盲测基线，**当轮不改规则**。
     - **写集**：`data/contracts_holdout9/`（H89–H100，12 份：5 英 / 7 中）+ `data/eval/gold_holdout9.json`（11 现象 / 11 条文本规则；H99、H100 为干净对照）；刻意选 `version: 9` 仍未覆盖的写法：H89 FOB 下“价格已含至目的港运费”、H90 `may instead elect … decided by the courts`、H91 中文“确认收款后方可发运”、H92 “请求重新审理”、H93 中文数字“二十四小时”。
     - **只跑基线（`version: 9` 不动）**：`eval/results/rules-holdout9-baseline-20261029.json` → `TP=6 FP=0 FN=5 TN=121`，**P=1.00 / R=0.545 / F1=0.706**，合同级 `5/0/5`，漏报 H89/H90/H91/H92/H93，H99/H100 零触发；**这份基线是 holdout9 唯一可对外引用的数字**。
     - **纪律固化**：`tests/test_rules.py` 新增 `HOLDOUT9_DIR` + `EXPECTED_HOLDOUT9_HITS`（五个漏报**空集合** = 基线快照）+ `test_holdout9_hits_are_stable`（含 H99/H100 零触发断言）；规则测试 57 → 58。
     - 验证：`pytest -q --override-ini addopts=` **405 passed（154.90s）**；`ruff check app tests eval` All checks passed；`node --check app/web/app.js` OK。
   - **阶段 4 第 10 轮第一步（已完成，2026-10-31，规则 `version: 10`）**：只按 holdout9 基线修那五处，多一处不改。
     - **五处修法**：`R-INC-001`（1.4→1.5）加“价格已含运费”分支（`FOB/EXW/FCA … price … inclusive of … freight`）；`R-DIS-003`（1.3→1.4）加 instead 式选择权分支（因原跨句守卫被 `award` 拦住，单列）；`R-PAY-001`（1.2→1.3）加“全部/全额价款 + 确认收款后 + 发运”；`R-DIS-004`（1.4→1.5）加中文“请求重新审理/再审/重新仲裁”；`R-INP-002`（1.3→1.4）补中文数词期限（限“小时 + 检验/通知/异议”）。
     - **先探针后落 YAML**：候选正则同时跑九批留出集 100 份 + 主集 50 份 + 2 份样例，统一 `re.IGNORECASE`（与引擎一致），只保留“只命中目标合同”的写法；跑完即删临时脚本。
     - **纪律**：`test_holdout9_hits_are_stable` 先失败并点名 H89/H90/H91/H92/H93（其余规则测试全绿），才把空集合翻成“必须命中”。
     - **修后只作回归**：holdout9 `11/0/0`（H99/H100 仍零触发）、holdout1–8 全 FP=0、主集 `hit_counts` 与 v9 逐条相同；`tests/test_api.py` 断言 `ruleset_version == 10`。
   - **阶段 4 第 10 轮第二步（已完成，2026-10-31）**：新写 holdout10 盲测基线，**当轮不改规则、只跑一次**。
     - **写集**：`data/contracts_holdout10/`（H101–H112，12 份：5 英 / 7 中，版式混入销售确认书 / 采购订单 / 长条款）+ `data/eval/gold_holdout10.json`（11 现象 / 11 条文本规则；H111、H112 为干净对照）；刻意选 `version: 10` 仍未覆盖的写法：H101 FOB 下 `all costs of carriage … shall be defrayed by the Seller`、H102 `In lieu of arbitration … seek a ruling … from the High Court`、H103 中文“款项全额到账后方安排装运”、H104 “申请对裁决的实体问题进行复审”、H105 检验期限“两个工作日”。
     - **只跑基线（`version: 10` 不动）**：`eval/results/rules-holdout10-baseline-20261030.json` → `TP=6 FP=0 FN=5 TN=121`，**P=1.00 / R=0.545 / F1=0.706**，合同级 `5/0/5`，漏报 H101/H102/H103/H104/H105，H111/H112 零触发；**这份基线是 holdout10 唯一可对外引用的数字**（UTC 命名，本地生成于 2026-10-31）。
     - **纪律固化**：`tests/test_rules.py` 新增 `HOLDOUT10_DIR` + `EXPECTED_HOLDOUT10_HITS`（五个漏报**空集合** = 基线快照）+ `test_holdout10_hits_are_stable`（含 H111/H112 零触发断言）；规则测试 58 → 59。
     - 验证：`pytest -q --override-ini addopts=` **406 passed**；`ruff check app tests eval` All checks passed；`node --check app/web/app.js` OK。
   - **下一步（第四阶段）**：
     - ~~修 H39（`R-DIS-004` modal 与动词之间放宽为 `[^.]{0,80}?`），另写 holdout5（8–12 份）再报数~~ ✅ 阶段 4 第 5 轮已完成（先写集、先基线、再改规则，`version: 6`；holdout4/5 均降级为回归集）；
     - ~~先写 holdout6（纯英文）重跑基线再改规则~~ ✅ 阶段 4 第 6 轮已完成（`version: 7`；holdout6 盲测基线 R=0.727，修后 1.0 只作回归）；
     - ~~再要提升规则泛化，先写 holdout7（中英混合，专攻被动语态与跨句写法）重跑基线~~ ✅ 阶段 4 第 7 轮**第一步**已完成（基线 R=0.636，漏报 H65/H66/H67/H69，**当轮未修规则**）；
     - ~~**第 7 轮第二步**：按 holdout7 基线修四处写法~~ ✅ 阶段 4 第 7 轮第二步已完成（`version: 8`，holdout7 降级为回归集）；
     - ~~**写 holdout8**（七批已全部消耗）：先跑盲测基线再决定修什么~~ ✅ 阶段 4 第 8 轮已完成（中英混合 H77–H88，规则 `version: 8` 一条不动，基线 P=1.00 / R=0.545 / F1=0.706，漏报 H77/H78/H79/H80/H83 按纪律钉成空集合）；
     - ~~**第 9 轮第一步**：按 holdout8 基线只修那五处（`version: 8`→9）~~ ✅ 已完成（holdout8 `11/0/0` 后降级为回归集，holdout1–7 全 FP=0，主集命中分布不变）；
     - ~~**第 9 轮第二步**：新写中英混合 holdout9 + gold，只跑盲测基线~~ ✅ 已完成（`version: 9` 一条不动，P=1.00 / R=0.545 / F1=0.706，漏报 H89/H90/H91/H92/H93 按纪律钉成空集合，`rules-holdout9-baseline-20261029.json` 为当前唯一对外数字）；
     - ~~**第 9 轮下一步**：按 holdout9 基线只修那五处，再写 holdout10~~ ✅ 阶段 4 第 10 轮已完成（`version: 10`，holdout9 修后 `11/0/0` 降级；holdout10 基线 P=1.00 / R=0.545 / F1=0.706，漏报 H101–H105 按纪律钉成空集合，`rules-holdout10-baseline-20261030.json` 为当前唯一对外数字）；
     - **第 10 轮下一步（按顺序，勿跳步）**：①若继续按 holdout10 基线只修那五处写法（FOB 下 `all costs of carriage … shall be defrayed by the Seller` / `In lieu of arbitration … seek a ruling` / 中文“款项全额到账后方安排装运” / “申请对裁决的实体问题进行复审” / “两个工作日”），拿 `test_holdout10_hits_are_stable` 先失败点名再翻表，规则 `version: 10`→11；②修完 holdout10 即降级为回归集，**新对外数字必须来自新写的 holdout11**；③或转做规则缺口 / silver gold 复核 / 检索查询改写（边际收益可能更高）；
     - 人工复核 21 个 silver 现象 + 十批留出的 97 个现象（7+9+7+9+10+11+11+11+11+11），silver 升 gold（ISSUE-020）；
     - 补规则缺口：不可抗力缺失、检验条款缺失、责任上限、质保期（ISSUE-009，主集覆盖率 52.4%）；
     - ~~RAG 检索评测：先做 `100问题.md` → manifest 映射（ISSUE-018），再调 `RAG_TOP_K`/`RAG_MIN_SCORE`~~ ✅ 界面轮 15 已按 ADR-016 完成（95 题可评测；ranking/production × lenient/strict；只改排序的条号/来源加权）；剩余 4 题语义指代与同义改写见 ISSUE-033——**下一步若要提升，先做查询改写，不要直接调权重**；
     - 语料授权与 `effective_date` 复核（ISSUE-015）；多智能体已在界面轮 14 按 ADR-015 落地（专家并行 + 只读工具层，默认关闭），真实外部 API（制裁名单 / 汇率 / HS 编码）仍待接（ISSUE-032）。
6. 每完成一个阶段：更新 `00_PROJECT_STATE.md`、写当日 `03_DEV_LOGS/YYYY-MM-DD.md`、更新本文件的“当前完成度/已知坑”、更新 `05_OPEN_ISSUES.md`。

---

## 11. RAG / 多智能体边界（ADR-007）

| 允许 | 禁止 |
|---|---|
| 本地知识检索增强解释/建议（BM25、字符 n-gram） | 用 RAG 结果决定 `red / yellow / pass` |
| 知识引用格式 `source_id#section` | 引用未登记/无授权的文档 |
| 专家节点补充解释（付款/交付/争议），并行 fan-out | 专家改级、新增 red/yellow、越权给法律结论 |
| 只读工具（4 个本地 + MCP stdio）为解释补材料 | 工具改合同、写库、改等级；执行未注册/白名单外工具 |
| 前端展示后端返回的等级、解释与专家参考意见 | 前端自行判级、前端拼 `Command(resume=...)`、前端调用 LLM |
| Supervisor 白名单路由（现为 `select_experts()` 确定性路由） | Supervisor 判级、自由规划、动态生成节点 |
| 开关控制（`AGENTS_ENABLED` / `TOOLS_ENABLED` 默认关闭） | 默认开启、隐式联网调用 embedding 服务、`shell=True` 跑 MCP |

默认行为：`RAG_ENABLED=false` 时 `explain` 只用规则 `reason` + 合同原文；RAG 无命中时必须退化为纯规则解释，并在 `limitations` 说明“未使用知识库”。`AGENTS_ENABLED=false` 时三个专家节点不进图、`expert_status="skipped"`；`TOOLS_ENABLED=false` 时 `research_tools` 是零副作用空节点——两者关闭时拓扑与结论和原来逐字一致。

**为什么默认关闭**（用户界面轮 3 问过）：RAG 只增强**解释**、不参与判级；知识库没就绪时开启，会让“检索不到”被误读成“没有风险”。开启方式：`.env` 里 `RAG_ENABLED=true`（本机 `.env` 已开启，`GET /health` 的 `rag_enabled` 为 true）；查当前值：`GET /health` 的 `rag_enabled`。界面轮 3 已按用户要求把该开关从侧栏移除，业务界面不再展示实现细节。

> 注意：`explain_risks` **先检索、再判断 LLM**。模型不可用时解释正文仍回退规则理由（`source="rule"`），但该条风险会带上检索到的 `source_id#section`（界面显示为“知识引用”），并在摘要里写明“知识引用仅按检索结果列出，未参与解释与判级”。没配 `LLM_API_KEY` 也能看到引用，只是没有模型生成的解释文字。
