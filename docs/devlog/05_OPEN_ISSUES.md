# 待解决问题 / 风险登记

> 更新时间：2026-10-29（阶段 4 第 9 轮：**先按 holdout8 基线只修那五处（`version: 8`→9），再新写中英混合留出集 holdout9（H89–H100，12 份：5 英 / 7 中）+ gold（11 个现象 / 11 条规则，H99/H100 干净对照），只跑基线、不改规则** → `TP=6 FP=0 FN=5 TN=121`，**P=1.00 / R=0.545 / F1=0.706**（合同级 `5/0/5`），漏报 H89（FOB 下“价格已含至目的港运费”）/H90（`may instead elect … decided by the courts`）/H91（中文“确认收款后方可发运”）/H92（“请求重新审理”）/H93（中文数字“二十四小时”），H99/H100 零触发；五个漏报按基线钉成空集合（`test_holdout9_hits_are_stable`），**九批中只有 holdout9 未消耗，对外数字改引这一份基线**；阶段 4 第 8 轮：**新写中英混合留出集 holdout8（H77–H88，12 份：5 英 / 7 中）+ gold（11 个现象 / 11 条规则，H87/H88 干净对照）**，在 `version: 8` 规则上**只跑盲测基线、不改规则** → `TP=6 FP=0 FN=5 TN=121`，**P=1.00 / R=0.545 / F1=0.706**（合同级 `5/0/5`），漏报全部是刻意构造的未覆盖写法：H77 `The ocean freight … is on the Seller's account`、H78 `refer the dispute to the courts`、H79 中文“七个工作日内付清全部货款”、H80 “仲裁庭的裁决…收到裁决书之日起…提起上诉”、H83 `inspect immediately upon discharge`；H87/H88 零触发；五个漏报按基线钉成空集合（`test_holdout8_hits_are_stable`），**八批中只有 holdout8 未消耗，对外数字改引这一份基线**；阶段 4 第 7 轮第二步：**按 holdout7 基线修四处写法**，规则 `version: 7`→**8** —— `R-INC-001` 卖方账上运费迂回语态、`R-DIS-003` 跨句或裁或审（`award`/新条标题守卫）、`R-PAY-001` 中文“全部价款”（排除分期）、`R-DIS-004` `bring the matter before the courts`；修后 holdout7 `11/0/0`（H75/H76 仍零触发）、holdout1–6 全 FP=0、主集 `hit_counts` 与 v7 逐条相同；`test_holdout7_hits_are_stable` 先失败点名 H65/H66/H67/H69 再翻表降级；**七批样本全部消耗，对外仍只引 holdout7 基线**；阶段 4 第 7 轮第一步：新写**中英混合**留出集 holdout7（H65–H76，12 份）+ gold（11 个现象 / 11 条规则，H75/H76 干净对照），**只跑盲测基线、不改规则** → `TP=7 FP=0 FN=4 TN=121`，P=1.00 / R=0.636 / F1=0.778，漏报 H65（`for the Seller's account`）/H66（跨句或裁或审）/H67（中文“全部价款”）/H69（`bring the matter before the courts`），四个漏报已按基线钉成空集合；阶段 4 第 6 轮：先写**纯英文**留出集 holdout6（H53–H64，12 份）+ gold（11 个现象 / 11 条规则，H62/H63 干净对照），改规则之前跑基线 → P=1.00 / R=0.727 / F1=0.842（漏报 H53/H55/H61），随后修 `R-INC-001` 卖方付运费倒装、`R-DIS-003` 连接词后逗号、`R-PAY-001` entire/full … before shipment，规则 `version: 7`，holdout6 降级为回归集；测试改为“先按基线钉表 → 修后必然失败 → 再翻表”；阶段 4 第 5 轮 + 界面轮 16：修 holdout4 暴露的 H39（英文情态动词与动词之间插时间状语）并另写 holdout5（H41–H52）做盲测基线 P=1.00 / R=0.90 / F1=0.947，规则 `version: 6`，holdout4 降级为回归集；结果页新增“这份报告怎么读”（关闭 ISSUE-024）；新增 `DELETE /api/reviews` 批量清空（ISSUE-022 第 7 条解决）；界面轮 15：检索评测落地——100 题 gold 映射 + 两套口径 + 点名条号/来源加权，ADR-016，关闭 ISSUE-018、新增 ISSUE-033；界面轮 14：多智能体专家并行 + 只读工具层（本地工具 / MCP），ADR-015，关闭 ISSUE-016、新增 ISSUE-032；界面轮 13：上传上限 15→30 MB + 图片 PDF 本地 OCR + 4 个外部 Skill 包内置 + zip 导入 + 两个付款条件双层去重 + 完整原文；界面轮 12：主题色下线改三档配色 + Skill 工具与文本附件 + 头像裁剪 + 标签行 + 历史即时刷新 + 条款切分精度 + 左原文右意见独立滚动；界面轮 10：账户设置改成 B 端分区弹窗（个人信息 / 通用 / 数据管理 / 关于）+ 主题色 5 套 + 界面字号三档 + 侧栏不再显示昵称/邮箱；界面轮 9：个人账户弹窗（头像/昵称/系统设置/二次确认清数据）+ Skill 查看与编辑 + 仓库紧凑化 + 厂商 10→20 + 阻止密码自动填充；界面轮 8：注册 not found 根因（旧进程 0.9.0）+ Skill 支持 Markdown/文件夹导入；界面轮 7：Skill 仓库独立页 + 自绘下拉 + 页脚贴右/降高 + 输入区收窄；界面轮 6：审查历史子目录 + 记录改名/置顶/删除 + 侧栏 Skill 仓库 + 满屏 + 弹窗定高；界面轮 5：账号 / 审查记录 / Skill / BYOK；界面轮 4：侧栏保留 + 主区两屏；第四阶段第 4 轮：规则 version 5 + 保额邻近判定 + 第四批留出集）
> 状态标记：`[OPEN]` 待处理 / `[CLOSED]` 已解决 / `[DEFERRED]` 本阶段不处理
> 规则：未决事项不写进代码；影响架构的必须先拍板，再进第二阶段。
> 本轮变化：阶段 4 第 9 轮（ISSUE-021 第 7 步）——两步走，顺序不能换：
> ①**只修 holdout8 基线点名的五处**（`version: 8`→9）：`R-INC-001` 迂回语态扩成 `(?:for|on) the Seller's
> account`（同时保留 `at the Seller's expense/cost`）、`R-DIS-003` 跨句动词表补 `\brefer`、`R-PAY-001`
> 加“收到/收讫 + 全部价款/货款 + 后/再 + 装运”、`R-DIS-004` 加中文“不服 + 向…法院 + 上诉/起诉/诉讼”
> （不收撤销裁决这类法定救济）、`R-INP-002` 加 `immediately/forthwith/promptly … upon discharge` 与
> `on the same day`；每处先探针（九批 100 份 + 主集 50 份）确认只命中目标合同；修后 holdout8 `11/0/0`
> （H87/H88 仍零触发）、holdout1–7 全 `FP=0`、主集 `hit_counts` 与 v8 逐条相同；
> `test_holdout8_hits_are_stable` 先失败点名 H77/H78/H79/H80/H83 再翻表降级。
> ②**再新写 holdout9**（`data/contracts_holdout9/`，H89–H100，12 份：5 英 / 7 中）+
> `data/eval/gold_holdout9.json`（11 个现象 / 11 条文本规则，H99/H100 干净对照），在 `version: 9` 上
> **只跑基线、不改规则**：`TP=6 FP=0 FN=5 TN=121` → **P=1.00 / R=0.545 / F1=0.706**（合同级 `5/0/5`），
> 漏报 H89/H90/H91/H92/H93（全部是刻意构造的 `version: 9` 未覆盖写法），H99/H100 零触发；
> 五个漏报按纪律钉成空集合（跑通 = 基线快照）+ `test_holdout9_hits_are_stable`；
> **九批 100 份里只有 holdout9 未消耗，对外数字改引**
> `eval/results/rules-holdout9-baseline-20261029.json`；下一步按这五处修规则（`version: 9`→10），
> holdout9 随即降级，再报数须写 holdout10。
> 阶段 4 第 8 轮（ISSUE-021 第 6 步）——用户选“先写 holdout8 再报新泛化数字”，所以那一轮
> **只写集 + 只跑基线，规则 `version: 8` 一条不动**：
> 新写 `data/contracts_holdout8/`（H77–H88，12 份：5 英 / 7 中）+ `data/eval/gold_holdout8.json`
> （11 个现象 / 11 条文本规则，H87/H88 干净对照）；基线 `TP=6 FP=0 FN=5 TN=121` →
> **P=1.00 / R=0.545 / F1=0.706**（合同级 `5/0/5`），漏报 H77/H78/H79/H80/H83（全部是刻意构造的
> `version: 8` 未覆盖写法），H87/H88 零触发；五个漏报按纪律钉成空集合（跑通 = 基线快照）+
> `test_holdout8_hits_are_stable`；**八批 88 份里只有 holdout8 未消耗，对外数字改引**
> `eval/results/rules-holdout8-baseline-20261029.json`（该批第 9 轮已修完并消耗，现只作回归）。
> 阶段 4 第 7 轮第二步（ISSUE-021 第 5 步完成）——按第一步钉下的盲测基线**只修四处**：
> `R-INC-001` 加 `FOB/EXW/FCA … freight … shall be for the Seller's account / at the Seller's expense`；
> `R-DIS-003` 加**跨句**分支（仲裁句句号后再起一句法院句），中间用 tempered-dot 守卫禁止出现
> `award` 与新条标题（否则 holdout4 H39 / holdout5 H41 的“裁决后起诉”会被误吃成或裁或审）；
> `R-PAY-001` 加中文“装运/发货/交货/出运前 … 一次性/全额支付 … 全部/全额价款”（末尾负向断言排除“全部价款的 30%”）；
> `R-DIS-004` 在既有英文分支内补 `bring the matter/dispute/case before/to the courts`；
> 每处都先跑临时探针（7 批留出集 76 份 + 主集 50 份 + 2 份样例）确认只命中目标合同才写进 YAML；
> 规则 `version: 7` → **8**，`test_holdout7_hits_are_stable` 先按纪律失败点名 H65/H66/H67/H69、再翻表降级；
> 修后 holdout7 `11/0/0`（H75/H76 仍零触发）、holdout1–6 全 FP=0、主集 `hit_counts` 与 v7 逐条相同（**无新误报**），
> **holdout7 至此全部消耗，对外仍只引基线文件** `eval/results/rules-holdout7-baseline-20261029.json`。
> 阶段 4 第 7 轮第一步（ISSUE-021 第 5 步上半）——用户明确“先做 holdout7 盲测基线”，所以当时
> **只写集 + 跑基线，不改规则**：新写 `data/contracts_holdout7/`（H65–H76，12 份**中英混合**）+
> `data/eval/gold_holdout7.json`（11 个现象 / 11 条规则，H75/H76 为干净对照），刻意选四种新写法：
> H65 `the ocean freight … shall be for the Seller's account`、H66 仲裁句与法院句**分属两句**、
> H67 中文“装运前一次性支付合同项下全部价款”、H69 `bring the matter before the courts`；
> 基线 → `TP=7 FP=0 FN=4 TN=121`，**P=1.00 / R=0.636 / F1=0.778**，合同级 `6/0/4`，H75/H76 零触发；
> 结果文件 `eval/results/rules-holdout7-baseline-20261029.json`（**唯一可对外引用**）；
> `test_holdout7_hits_are_stable` 先按基线把四个漏报写成**空集合**（跑通 = 基线快照），
> 第二步修规则后必然失败并点名 H65/H66/H67/H69；当时规则仍是 `version: 7`（第二步才升 8）。
> 阶段 4 第 6 轮（ISSUE-021 第 4 步）——上一轮把“已知漏报清零”之后，按 ADR-011 的纪律
> **先写一批纯英文留出集 holdout6（H53–H64，12 份）+ gold（11 个现象 / 11 条规则）**，
> 改规则之前跑基线：`TP=8 FP=0 FN=3` → **P=1.00 / R=0.727 / F1=0.842**，漏报 H53（FOB 下
> `Seller shall arrange and pay for the ocean freight` 倒装）、H55（`or, at the Buyer's option, by proceedings …`
> 连接词后带逗号）、H61（`pay the entire contract price before shipment` 未写 in advance）；
> 随后修三处（`R-INC-001` 增英文倒装分支、`R-DIS-003` 的 `\s+or\s+` → `\s+or[,\s]\s*`、
> `R-PAY-001` 增 entire/full/whole/100% of the … before shipment 正则），规则 `version: 6` → **7**；
> 修后 holdout6 = 11/0/0、holdout5/holdout4/holdout1–3 仍 1.0、主集 50 份命中分布与 v6 逐条相同（**无新误报**），
> 但**对外只引基线文件** `eval/results/rules-holdout6-baseline-20261028.json`；holdout6 同时降级为回归集。
> 纪律升级：`test_holdout6_hits_are_stable` **先按基线把三个漏报写成空集合**（跑通即基线快照），
> 修完后该测试**必然失败**并点名 H53/H55/H61，此时才翻表降级——把“先写集、再改规则”钉在测试里。
> 阶段 4 第 5 轮 + 界面轮 16（ISSUE-021 第 3 步）——holdout4 的 H39 是“英文情态动词与动词之间
> 插入时间状语”（`may, within 30 days …, commence proceedings`），按纪律先**另写 holdout5（H41–H52，12 份）**
> 做盲测基线（**P=1.00 / R=0.90 / F1=0.947**，唯一漏报 H41，只差一个 `\s+` → `\s*` 的写法），
> 再改 `R-DIS-004` 的英文分支（`\s*[^.]{0,80}?`），规则 `version: 5` → **6**；
> 修后 holdout5 = 1.0、holdout4 = 1.0、holdout1–3 仍 1.0、主集 50 份 TP=11 FP=0 FN=0（**无新误报**），
> 但**对外只引基线文件** `eval/results/rules-holdout5-baseline-20261028.json`；holdout4/5 同时降级为回归集。
> 界面轮 16 两处小改进：①结果页新增“这份报告怎么读”（等级来源、专家不判级、工具只读、覆盖边界，
> 并追加后端 `limitations`）→ **关闭 ISSUE-024**；②新增 `DELETE /api/reviews`（一次请求、只删本账号、
> 顺手清 checkpoint 与上传目录）替代前端逐条删除 → ISSUE-022 第 7 条解决，其余仍 OPEN。
> 界面轮 15 做**检索评测**（ISSUE-018，ADR-016）——把 `100问题.md` 的概念标签
> （`CISG-25` / `INC-CIF A5` / `JI-CC-1`）通过 `data/eval/rag_label_map.yaml` + 通用条号解析
> 翻成语料真实 citation（`CISG-ZH#s27` / `INCOTERMS-2020#s12` / `SPC-CONTRACT-2023#第一条`），
> 生成可 diff 的 `data/eval/gold_rag.json`（**95 题可评测 / 5 题语料未覆盖**，未覆盖的不进分母）；
> 新增 `eval/run_rag_eval.py`，同时报两套口径：`ranking`（top-5 不过阈值，看排序）与
> `production`（`RAG_TOP_K`/`RAG_MIN_SCORE` 实际配置，看线上会不会返回空），并把
> `lenient`（条文原文或解读稿）与 `strict`（只认条文原文）分开报；
> 评测暴露“问第 584 条却让解读稿压过条文”后，按证据加了**排序加权**
> （点名条号 ×2.5、条文原文再 ×1.1、点名法律名 ×1.15，抽不出条号就不猜、不过滤不清空）：
> lenient **R@1 0.516→0.747、R@3 0.800→0.958、MRR 0.667→0.849**，
> strict **R@1 0.158→0.305、R@3 0.390→0.758**；`app/services/chinese_numbers.py` 统一
> “第584条 ↔ 第五百八十四条”的互转（检索与 gold 共用一份，避免评测命中而线上不命中）；
> **关闭 ISSUE-018**，**新增 ISSUE-033**（剩余 4 道语义指代题、同义改写与跨语言提问仍靠词法检索）。
> 界面轮 14 回应“离 agent 越走越远”——按 **ADR-015** 真正加了一层 Agent 能力，同时守住“规则唯一判级”：①**多智能体专家并行**（`app/nodes/experts.py`）：`validate_extraction` 之后按 `clause_type` + 关键词**确定性路由**出“付款 / 交付 / 争议”三个专家，LangGraph 并行 fan-out，汇合后进 `evaluate_rules`；专家输出 `ExpertOpinion`/`ExpertDraft` **没有 `risk_level`**、引文必须能在条款原文定位（否则丢弃并记 `quote_not_found`），失败/无 Key 只写 `expert_notes`；并行分支只写带 `operator.add` 的字段，`degraded_steps`/`warnings` 由汇合节点单点写（避免并发写冲突）；**关闭 ISSUE-016**；②**只读工具层**（`app/services/tools.py` + `app/nodes/research.py`）：`rules` 之后插一次 `research_tools`，4 个本地工具（条款目录 / 关键词定位 / 字段回读 / 知识检索）+ **MCP stdio JSON-RPC 子集**（`initialize → tools/list → tools/call`，零新依赖、`shell=False`、超时杀进程、单行 ≤1 MB、服务器只来自 `.env`）；LLM 规划 ≤3 次，**无 LLM 时退化为确定性检索**（离线也能演示）；白名单外的调用只记 `ok=False` 不执行；每次调用留 `ToolCallRecord`（参数/摘要截断、耗时、成败、引用）；③解释侧新增 `<untrusted_experts>` / `<untrusted_tools>` 两段数据区并做结束标签转义，引用白名单扩成“本条 RAG 命中 ∪ 工具返回的 citation”；④逐条审查页新增“参考 · 专家”区块（**中性色，明确写“不代表风险等级”**）与折叠的“Agent 轨迹”；⑤两个开关 `AGENTS_ENABLED` / `TOOLS_ENABLED` 默认 `false`，关闭时拓扑与结论和原来**完全一致**（有对照测试）；`API_VERSION` 1.0.0 → **1.1.0**；**新增 ISSUE-032**（额外调用成本、MCP 信任边界、真实外部 API 未接）。界面轮 13 按 5 条反馈做：①**上传上限 15→30 MB**（`MAX_UPLOAD_MB` 单一配置源，前端 `MAX_BYTES`、错误文案、首屏提示同步，测试钉住）；②**图片 PDF 本地 OCR**——`pypdfium2` 渲染 + `rapidocr-onnxruntime`（离线 ONNX），只在整份 PDF 文本 < 50 字或单页 < 10 字时触发，≤20 页、逐页降级，OCR 文本只进 `raw_text`、**不参与判级**（**新增 ISSUE-030**）；③桌面 4 个外部 Skill 包复制进 `app/resources/skills/` 作 `builtin:*`，`instruction` 提炼关注方向、原 `SKILL.md` 与 references 作只读附件（**新增 ISSUE-031**：来源/授权未确认、正文截断到 6000 字）；④“两个付款条件”定位为旧切分把双语标题后的英文段再切成一条并吞掉后 4 条 → 切分侧 `_merge_duplicate_headings()` + 展示侧 `_merge_adjacent_duplicates()` 双层合并（旧记录不重跑也能修正）；结果页合同名 / Skill / 审查重点 / 状态收成**同一行标签**；左栏新增**原文全文** tab（`contract_text` 一次返回，按 `\n\n` 分段、段内 `<br>`，保持原文件排版，不再机械拆分）；⑤**zip Skill 包导入**——根目录 `SKILL.md` 必填、只收文本、内存解析不落盘、**包内脚本不执行**、`allowed-tools` 不映射（`POST /api/skills/import`）。界面轮 12 把**主题色 5 套下线**（用户反馈“改不了”），改成 **白天 / 黑夜 / 跟随系统** 三档（`html[data-scheme]` + `matchMedia`，深色变量从 `@media` 搬进属性选择器）；Skill 从“一段提示词”扩成 **指令 + 5 个可声明工具 + 只读文本附件**（`.py/.md/.txt`，≤5 个 / ≤6000 字，新增 `GET /api/skills/tools`，**绝不执行**）——**新增 ISSUE-029**（工具只影响 focus 文案、附件不执行且存在提示注入面）；头像上传后进 `#avatar-crop-dialog` 自己拖动/缩放再存 128×128 JPEG（服务端仍不重新编码，归 ISSUE-025）；审查页顶部改为**标签行**并删掉整段对话式叙述（**ISSUE-027 关闭**）；`refreshHistory()` 让审查/确认后侧栏历史立即更新（无推送，归 ISSUE-022）；未命中规则改“这一条没有发现需要修改的地方”；`segment.py` 修 4 类误切 + 目录短标题 + 前言标注；逐条审查左目录与原文、右意见与“采用修改/保留原文/撤销”，三块各自滚动。界面轮 10 把账户弹窗改成 **B 端设置形态**（左侧分区导航“个人信息 / 通用 / 数据管理 / 关于”，右侧面板切换；弹窗 760×560，窄屏导航转横向），通用区新增**主题色 5 套**（只换 `--accent`，风险语义色不动）与**界面字号 小/标准/大**（`--ui-text-scale` + 全量 `font-size: calc(...)`），个人信息补只读注册时间，数据管理加两张统计卡，关于区显示版本与政策入口；侧栏左下角**删掉昵称/邮箱**，只留“退出登录 + 头像”——**ISSUE-025** 补“偏好只在本机、无手动深色开关”，**ISSUE-022** 补“设置面板只做前端偏好、统计按需拉取”。界面轮 9 把 Skill 仓库列表改成**一行折叠**（点名称展开审查重点）、自建 Skill 可 `PATCH /api/skills/{id}` 编辑（推荐只读、可“存为我的”），右栏面板收紧凑；侧栏“退出登录”右侧加**圆形头像** → `#account-dialog`（换头像 / 改昵称 / 减少动效 / 自动聚焦 / 清除本机缓存 / 清空审查记录，两个清除动作都二次确认）；头像压成 128×128 JPEG 存 data URL（`users.avatar` 列 + 老库 `ALTER TABLE`）；厂商目录 10→20；API 配置 Key 输入改 `autocomplete="new-password"` 等属性，解决“点输入框弹出浏览器快捷填入账号密码”——**ISSUE-025** 补“无改密码/注销账号、头像不做服务端重编码”，**ISSUE-022** 补“清空记录逐条 DELETE、无批量接口”。界面轮 8 定位“注册显示 not found”是 **8000 端口跑着旧进程**（`openapi` 0.9.0，无 `/api/auth/*`）→ 重启为 1.0.0；并给 Skill 仓库加“从 Markdown 导入”（拖拽文件/文件夹 + 两个选择入口，前端解析 frontmatter/标题/首段，逐条 `POST /api/skills`，同名跳过、单次 30 个 / 单文件 200 KB）。**新增 ISSUE-026**（开发服务未开 `--reload`，前后端版本可能错位）。界面轮 7 把 Skill 仓库从弹窗改为独立页面 `#/skills`、原生 select 换成自绘 listbox、页脚铺满并贴右降高、输入区 880→720。界面轮 6 把“当前审查”改成侧栏“审查历史”子目录（记录可改名/置顶/删除，`PATCH|DELETE /api/reviews/{id}`），Skill 仓库入口收到侧栏、下拉末项固定为仓库，主区铺满屏幕，登录弹窗定高且登录/注册都必须手勾同意；**ISSUE-025** 补“同意条款未留痕（`consent_version`/`consent_at`）”与“删记录只清本机痕迹”；界面轮 5 按 ADR-013 增加账号、审查记录、Skill 仓库与 BYOK（**ISSUE-025**：账号/密钥的运维边界——密码找回、登录限流、主密钥备份、Cookie `Secure`、多 worker 运行时）；ISSUE-024 仍待做“这份报告怎么读”；ISSUE-021/020/009 与上轮一致（H39 故意不修、silver gold 待复核、覆盖率 52.4%）。
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
| ISSUE-015 | OPEN | P1 | RAG 知识库授权与检索评测未确认 | 真实语料已入库（14 篇，含 DOCX 条文切分）；**检索评测已按 ADR-016 落地**（ISSUE-018 关闭）；剩下确认对外引用授权 |
| ISSUE-016 | CLOSED | P2 | 多智能体专家角色与编排范围未定 | 界面轮 14 按 ADR-015 落地：付款 / 交付 / 争议三个并行专家 + 确定性白名单路由（不是聊天式 Supervisor）；专家 schema 无 `risk_level`、引文定位不到即丢弃；默认关闭 |
| ISSUE-017 | CLOSED | P2 | HITL pending 时间戳只在进程内存 | 已落盘 `.data/pending/<review_id>.json`，跨进程超时判定有测试 |
| ISSUE-018 | CLOSED | — | 检索评测问题集的 source_id 与 manifest 不一致 | 界面轮 15 按 ADR-016 落地：`data/eval/rag_label_map.yaml` + `eval/rag_gold.py` 生成 `gold_rag.json`（95 题可评测 / 5 题语料未覆盖），`eval/run_rag_eval.py` 报 ranking / production × lenient / strict 四组指标；lenient R@3 0.800→0.958、strict R@3 0.390→0.758（点名条号/来源加权） |
| ISSUE-019 | OPEN | P2 | 并发锁仅进程内、上传/报告文件无清理策略 | 单机演示可接受；多进程部署前需换文件锁/数据库并加保留期 |
| ISSUE-020 | OPEN | P1 | 规则级 gold、留出合同集与模拟合同数量不符 | silver gold（21 现象）+ 九批留出集（100 份 / 86 个现象）已就位；**待人工复核**，且用户所称 60 份实为 50 份 |
| ISSUE-021 | OPEN | P1 | 规则对英文条款与同义改写漏报 | 已修六轮（version 4 → 5 → 6 → 7 → 8 → **9**）：英文/同义改写、子串误命中、窗口截断、保额全文级判定、3 类措辞、情态动词后插时间状语、卖方付运费倒装 / 连接词后逗号 / entire … before shipment、卖方账上运费迂回语态 / 跨句或裁或审 / 中文“全部价款” / `bring the matter`，以及 `on the Seller's account` / 跨句 `refer` / “收全款再发货” / 中文“不服裁决向法院上诉” / 立即检验与当日通知；holdout1–8 全部消耗为回归集；**当前对外数字来自 holdout9 盲测基线** P=1.00 / R=0.545 / F1=0.706（9 批 100 份中仅 holdout9 未消耗），五个漏报 H89/H90/H91/H92/H93 未修，下一批须写 holdout10 |
| ISSUE-022 | OPEN | P2 | 主区交互无自动化测试、待确认态依赖审批载荷口径、历史列表无分页、清空记录逐条删、偏好只在本地 | `tests/test_web.py` 覆盖加载/无外链/本地字体/不判级/侧栏保留且主区无工作台内容/待确认先展示规则风险/Skill 末项仓库/历史子目录工具/同意默认不勾选/Markdown 导入入口/Skill 行折叠与编辑/账户设置四分区与侧栏无昵称邮箱/LLM 表单不自填充/标签行与左右分栏/Skill 工具与附件/历史即时刷新/目录编号/**报告怎么读**；**清空记录已改批量接口**（`DELETE /api/reviews`，一次请求、只删本账号、顺手清 checkpoint 与上传目录）；上传、抽屉、确认、改名置顶删除、账户分区切换、拖拽裁剪、独立滚动仍靠真实浏览器 + CDP 冒烟；`approval` 只含 red，黄色风险只在确认后的报告出现；历史只取 20 条且是**前端主动重取**（无推送）；导入上限与同名跳过只在前端执行，服务端仅校验长度；配色/字号/动效只写 `localStorage`，统计卡按需拉 `GET /api/reviews?limit=500`，无设置表与统计接口 |
| ISSUE-023 | OPEN | P1 | 文档类型闸门边界：召回优先、非中英合同可能误拒、阈值需真实语料调参 | 闸门只判“是不是合同”，不判类型、不判风险；误拒/误放率无统计口径；扫描件已在 `ingest` 用本地 OCR 补文本（ADR-014），但 OCR 也失败时仍只能按“过短”拒绝并提示人工核对 |
| ISSUE-024 | CLOSED | — | 主区不再展示规则目录与报告全貌，用户无法自助判断“规则覆盖到哪” | 界面轮 16 在结果页加“这份报告怎么读”（逐条审查动作区 + 仅下载报告分支都有入口）：规则是唯一等级来源、三档含义、证据怎么读、专家不是等级、工具只读、覆盖边界（13 条规则 / 主集覆盖率 52.4%）；后端 `ReviewReport.limitations` 由 `GET /api/reviews/{id}/report?format=json` 追加渲染，不在前端写死；仍不新增主区视图 |
| ISSUE-025 | OPEN | P1 | 账号与密钥的运维边界（找回密码、注销账号、登录限流、主密钥备份、Cookie `Secure`、多 worker、同意留痕、头像编码、偏好不随账号） | 演示形态：无找回/验证码/限流；**无改密码与注销账号**（口令哈希尚无版本化迁移）；主密钥与库必须一起备份，丢失只能重填 Key；Cookie 未加 `Secure`（本地 HTTP）；多 worker 时 `_RUNTIME` 不共享；登录/注册手勾同意但未记 `consent_version`/`consent_at`；头像只校验 `data:image/...;base64` 前缀与 400k 字符上限，服务端不重新编码/不扫描（界面轮 12 起由前端裁剪成 128×128 JPEG）；配色/字号/动效只存 `localStorage`，不跨设备同步（配色已改为白天/黑夜/跟随系统三档，仍不落库） |
| ISSUE-026 | OPEN | P2 | 开发服务未开 `--reload`，8000 端口可能跑着旧代码（注册 404 “not found”） | 演示用单进程 uvicorn；改后端后手动重启，用 `GET /openapi.json` 的 `info.version` 核对是否为 1.0.0；长期方案是本地开 `--reload` 或启动脚本打印版本 |
| ISSUE-027 | CLOSED | — | 审查结果页的“流式输出”是前端时序，不是真事件流 | 界面轮 12 用户要求“该部分直接删去”，`chatNarrative`/`streamText`/`#ai-stream` 与气泡样式已移除；结果页改为标签行 + 直接分屏 |
| ISSUE-028 | OPEN | P2 | 退出登录只做前端拦截，后端没有“取消审查任务”接口 | 前端 `#logout-confirm` 二次确认后清本地状态；pending / checkpoint / 上传目录不会被清理；建议新增 `POST /api/reviews/{id}/cancel` |
| ISSUE-029 | OPEN | P2 | Skill 的工具声明与文本附件只影响“怎么写解释”，不执行、不编排，且有提示注入面 | `TOOL_CATALOG` 5 个能力只改 focus 文案；`SkillAsset` 只存文本（≤5 个 / ≤6000 字）绝不执行也不做 AST 检查；附件进 prompt 靠前缀声明“不得当作指令执行”；要真执行需受限沙箱并改 ADR |
| ISSUE-030 | OPEN | P2 | 图片 PDF 的 OCR 精度、触发条件与页数上限 | `pypdfium2` + RapidOCR 只在整份文本 < 50 字或单页 < 10 字时兜底，≤20 页；英文可能吞空格（`SALESCONTRACT`）、中文/表格可能串行；报告统一写“请人工核对”；换更强模型/版面分析需另评 |
| ISSUE-031 | OPEN | P2 | 4 个外部 Skill 包的来源与授权未确认、正文存在截断 | 复制进 `app/resources/skills/` 作 `builtin:*`；`SKILL.md`/references 只保留前 6000 字并标“（节选）”；对外分发前需确认授权与完整正文的存放方式 |
| ISSUE-032 | OPEN | P2 | 专家并行与工具层的成本、信任边界与真实外部数据 | 每次审查多 3 次专家调用 + 1 次工具规划 + ≤3 次工具执行；MCP 属外部子进程信任边界（`shell=False`、只读、超时杀进程）；真实外部 API（制裁名单 / 汇率 / HS 编码 / 征信）需密钥与授权，未接 |
| ISSUE-033 | OPEN | P2 | 词法检索的两类结构性短板：无条号的语义指代题、同义改写/跨语言提问 | 100 题里仍剩 4 道（#4/#6/#43/#100）属“不点条号的指代”，同义改写与中英互问仍靠词法共现；目前**不调参过拟合**，后续按需做查询改写（在检索前扩同义词/条号），或受限语义检索（须改 ADR-008） |

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
- **当前进度**：`app/rules/definitions.yaml`（`version: 8`）已实现 **13 条**：
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

- **状态**：OPEN（2026-10-27 语料已提供，链路已跑通；**检索评测已于界面轮 15 落地**，授权待确认）
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
  4. **检索评测**：已在界面轮 15 按 ADR-016 完成——100 题经 `data/eval/rag_label_map.yaml` 翻成真实 citation，
     分母 95 题（5 题语料未覆盖），`ranking / production × lenient / strict` 四组指标见
     `eval/results/rag-20261028.json`；仍剩 4 道无条号指代题（ISSUE-033）。
- **默认**：`RAG_ENABLED=false`；开启后只增强解释，不参与判级；知识引用必须能在 `source_id#section` 定位。
- **禁止**：把无授权文本、抓取的付费标准全文、或模型记忆当成知识库引用。

---

## ISSUE-016 · 多智能体专家角色与编排范围未定

- **状态**：CLOSED（2026-10-28 界面轮 14，ADR-015）
- **优先级**：P2
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
- **解决方式（界面轮 14）**：用户“时间还有很多”，明确要真正的 Agent 能力，按 ADR-015 落地 **三个专家**：
  1. `app/nodes/experts.py`：`payment / delivery / dispute` 三个并行分支，路由由 `select_experts` 用
     `clause_type + 关键词` 确定性选择（等价于“Supervisor 只做路由”，但零 LLM 成本、可单测）；
  2. `ExpertOpinion` / `ExpertDraft` 的 `extra="forbid"` 且**没有 `risk_level`**（`test_expert_draft_schema_forbids_risk_level`）；
     引文必须 `locate_quote` 命中，否则丢弃并记 `expert:<id>:quote_not_found`；
  3. 并行分支只写带 `operator.add` 的字段，`degraded_steps` / `warnings` / `expert_status` 由
     `collect_expert_findings` 单点写，避免并发写冲突；
  4. 开 / 关专家时 `rule_id` 与 `overall_level` 完全一致（`test_expert_findings_are_grounded_and_do_not_change_level`）；
  5. 逐条审查页新增“参考 · 专家”区块（中性色、明确写“不代表风险等级”）与折叠的“Agent 轨迹”。
- **仍未解决**：专家资料（“问题条款→改写”对照、让步顺序、品类模板）仍需用户提供；成本与外部数据见 ISSUE-032。
- **证据**：`app/nodes/experts.py`、`app/graph.py`、`tests/test_agents.py`、ADR-015。

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

- **状态**：CLOSED（界面轮 15，ADR-016）
- **优先级**：P1（影响 RAG 检索评测与任何“召回率”数字）
- **现象**：`data/knowledge/100问题.md` 的 100 条 query 使用 `CISG-25`、`CISG-39(2)`、`INC`、`LAW`、`CC`、`JI`、`RISK` 等命名，而 manifest 的 `source_id` 是 `CISG-ZH / CISG-EN / CISG-KEY / INCOTERMS-2020 / CN-CIVIL-CODE / CN-LAW-APPLICATION / SPC-* / RISK-REDLINE`；section 也是自然语言描述而非 `sN` / `第X条`。
- **影响**：直接跑评测会把“正确命中”误判为“未命中”，无法给出可信召回率。
- **建议方向**：
  1. 建立映射表（query # → `expected_source_ids` + `expected_sections`），人工确认 20–30 条高置信样本先跑；
  2. 检索结果允许“多命中”，评测按 `source_id` 与条文号（docx）或章节语义（md）匹配；
  3. 评测结果写入 `eval/results/*.json`，含 `RAG_TOP_K` / `RAG_MIN_SCORE` / 语料版本。
- **禁止**：在映射完成前宣称“RAG 召回率 X%”。

- **解决方式（界面轮 15，ADR-016）**：
  1. **两层映射**：概念标签（`CISG-25` / `INC-CIF A5` / `JI-CC-1`）先由 `eval/rag_gold.py`
     用通用条号正则（`CISG-N` / `CC-N` / `LAW-N` / `JI-CC-N`）转成语料真实条号，
     人工判断的部分（Incoterms 主题标题、红线清单条目等 27 个标签）落在
     `data/eval/rag_label_map.yaml`，两者都写成 `source_id#section` 形式；
  2. **一个标签 → 多条可接受片段**：中文原文 / 英文原文 / 解读稿都算命中，
     生成物 `data/eval/gold_rag.json` 可 diff、可复核，并带 `generated_at` 与语料 `chunk_count`；
  3. **语料缺口不进分母**：`gaps` 显式登记（如 CLOUT 未收录），含缺口标签且无任何可定位片段的题
     单独标“语料未覆盖”，因此分母是 **95 题**而不是 100 题（5 题：#42/#69/#86/#87/#88）；
  4. **两套口径分开报**：`ranking`（top-5、`min_score=0`，看排序能力）与
     `production`（真实 `RAG_TOP_K` / `RAG_MIN_SCORE`，看线上会不会返回空），
     `lenient`（条文或解读稿）与 `strict`（只认条文原文）分开，**禁止混读**；
  5. **gold 过期守卫**：`tests/test_rag_eval.py::test_committed_gold_matches_current_corpus`
     用当前语料重建 gold 与提交物比对，语料或题目一改就失败，避免“旧 gold 报新数”。
- **实测（`eval/results/rag-20261028.json`）**：
  - ranking lenient：R@1 0.516→**0.747**、R@3 0.800→**0.958**、R@5 0.874→**0.979**、MRR 0.667→**0.849**；
  - ranking strict：R@1 0.158→**0.305**、R@3 0.390→**0.758**、R@5 0.537→**0.821**、MRR 0.290→**0.524**；
  - production（`top_k=3` / `min_score=1.0`）：lenient 与 ranking 前三位一致，说明加权没有把线上结果挤空。
  - 加权只改排序（点名条号 ×2.5、条文原文再 ×1.1、点名法律名 ×1.15），不打分新片段、不过滤、不改判级；
    抽不出条号时全 1.0，退化为原 BM25。
- **残余**：仍剩 4 道无条号的语义指代题（#4/#6/#43/#100），归 **ISSUE-033**。
- **证据**：`eval/rag_gold.py`、`eval/rag_eval.py`、`eval/run_rag_eval.py`、`data/eval/rag_label_map.yaml`、
  `data/eval/gold_rag.json`、`app/services/chinese_numbers.py`、`app/services/rag.py`、
  `tests/test_rag_eval.py`（6 项）、`tests/test_rag_boost.py`（6 项）、ADR-016。

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

- **状态**：OPEN（已修五轮：`version: 4` 补英文/同义改写，`version: 5` 补三类措辞 + 保额邻近判定，`version: 6` 补“情态动词后插时间状语”，`version: 7` 补三处英文写法，`version: 8` 补四处中英写法；第 8 轮新写 holdout8 后**又暴露五处写法漏报（H77/H78/H79/H80/H83）尚未修**，八批中仅 holdout8 未消耗，下一步按基线修时升 9、修完须再写 holdout9）
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
- **第 3 步已完成（2026-10-28 第 5 轮，规则 `version: 6`）**：
  1. **先写留出集再改规则**：新建 `data/contracts_holdout5/`（H41–H52，12 份，与 C01–C50、holdout1–4 均不重复）+
     `data/eval/gold_holdout5.json`（10 个现象，覆盖 9 条规则）。刻意换措辞：英文“may, within forty-five (45) days …,
     bring an action”、中文“仲裁裁决作出后，任何一方仍可…提起诉讼”、英文“At the option of the Buyer … or … the courts”、
     “within forty-eight (48) hours after discharge”；
  2. **盲测基线（改规则之前）**：`eval/results/rules-holdout5-baseline-20261028.json` →
     **TP=9 FP=0 FN=1，P=1.00 / R=0.90 / F1=0.947**，唯一漏报 **H41**；干净对照 H43（英文“仅可依法申请撤销裁决”）与
     H52（全条款合规）都正确 pass；
  3. **定位**：H41 与 H39 同型——`R-DIS-004` 英文分支原本要求 `may|shall` 后**紧跟**空白再跟动词，
     而真实写法是 `may` + 逗号 + 时间状语 + 动词；
  4. **修法（最小改动）**：`\s+(?:may|shall|can|could)\s+` → `\s+(?:may|shall|can|could)\s*[^.]{0,80}?`，
     保留“裁决的法定执行（`may be enforced`）/ 申请撤销（`set aside`）”不误报；`version: "1.1"` → `"1.2"`，规则集 `5` → `6`；
  5. **修后**（只作回归守卫）：holdout5 = 10/0/0、holdout4 = 9/0/0（H39 已进表）、holdout1–3 仍 1.0、
     主集 50 份 TP=11 FP=0 FN=0（**无新误报**）。
- **第 4 步已完成（2026-10-29 第 6 轮，规则 `version: 7`；ADR-011 第 6 轮补充）**：
  1. **先写纯英文留出集**：新建 `data/contracts_holdout6/`（H53–H64，12 份全英文正文）+
     `data/eval/gold_holdout6.json`（11 个现象覆盖 11 条文本规则，含两条“条款缺失型”；H62/H63 为干净对照）；
  2. **盲测基线（改规则之前）**：`eval/results/rules-holdout6-baseline-20261028.json` →
     `TP=8 FP=0 FN=3 TN=121`，**P=1.00 / R=0.727 / F1=0.842**，漏报 **H53 / H55 / H61**；H62/H63 零触发；
  3. **三处缺陷与修法**：
     | 漏报 | 根因 | 修法 |
     |---|---|---|
     | H53 | `R-INC-001` 英文侧只认 `freight … paid by the seller`，认不出 `The Seller shall arrange and pay for the ocean freight` 这种“动词在前”的写法 | 新增第二条英文分支：术语后 260 字符内 `seller … (arrange and pay for\|pay for\|prepay\|bear\|defray) … (ocean/sea freight\|freight\|carriage)`；**不收裸 `pay`**，避免把“Seller 安排运输 + Buyer 付运费”的正常 FOB 误判 |
     | H55 | `R-DIS-003` 英文分支用 `\s+or\s+`，而真实写法是 `or, at the Buyer's option`（连接词后带逗号）——与上一轮 `may,` 同属标点缺陷 | `\s+or\s+` → `\s+or[,\s]\s*` |
     | H61 | `R-PAY-001` 只认 5 个固定短语，认不出 `pay the entire contract price before shipment` | 加正则：`(entire\|full\|whole\|100% of the …) … price/value/amount … 80 字符内 … (in advance\|before shipment/delivery/dispatch\|prior to shipment\|upon signing)`；限定词只收“全部”，正常分期不误报 |
  4. **修后**（只作回归守卫）：holdout6 = 11/0/0、holdout5 = 10/0/0、holdout4 = 9/0/0、holdout1–3 仍 1.0、
     主集 50 份 TP=11 FP=0 FN=0 且命中分布与 `version: 6` **逐条相同**（无新误报）；样例合同仍零命中。
  5. **纪律升级**：`test_holdout6_hits_are_stable` 先按基线把三个漏报写成**空集合**（跑通 = 基线快照），
     修完再跑**必然失败**并报出 H53/H55/H61；此时才翻表并注明“本批已降级、对外只引基线文件”。
- **第 7 步已完成（2026-10-29 第 9 轮；ADR-011 第 9 轮补充）**——两步走，先修后写，一步不跳：
  1. **只修 holdout8 基线点名的五处**（`version: 8`→9），每处先在临时探针里跑九批 100 份 + 主集 50 份：
     | 漏报 | 修法 | 反向守卫 |
     |---|---|---|
     | H77 | `R-INC-001`（1.3→1.4）把迂回语态扩成 `(?:for\|on) the Seller's account`，**并保留** `at the Seller's expense/cost` | 不收 `for the Buyer's account` / `at the Seller's risk` |
     | H78 | `R-DIS-003`（1.2→1.3）跨句动词表补 `\brefer` | `\b` 防 `prefer`；`award` 与新条标题守卫仍生效 |
     | H79 | `R-PAY-001`（1.1→1.2）加 `(?:收到\|收讫)…(?:全部\|全额)(?:价款\|货款\|款项)…(?:后\|再)…(?:装运\|发货\|出运\|交货)` | 不认“收到 30% 预付款后发货”；不认“全部价款的 30%” |
     | H80 | `R-DIS-004`（1.3→1.4）加中文 `不服…向…法院…(?:上诉\|起诉\|诉讼)` | 不收“申请撤销裁决”（法定救济，holdout4 H32 / holdout5 H52） |
     | H83 | `R-INP-002`（1.2→1.3）加 `inspect…immediately/forthwith/promptly…upon discharge/arrival/…` 与 `notify…on the same day` | 不认 `within 14 days after arrival` 这类正常期限 |
     修后 holdout8 `11/0/0`（H87/H88 仍零触发）、holdout1–7 全 FP=0、主集 `hit_counts` 与 v8 逐条相同；
     `test_holdout8_hits_are_stable` 先失败点名 H77/H78/H79/H80/H83 再翻表；`ruleset_version` 断言改 9。
  2. **再写 holdout9 并只跑基线**：新建 `data/contracts_holdout9/`（H89–H100，12 份：5 英 / 7 中）+
     `data/eval/gold_holdout9.json`（11 个现象 / 11 条文本规则，H99/H100 干净对照），刻意五处：
     | 合同 | 写法 | 规则 | 为什么仍可能漏 |
     |---|---|---|---|
     | H89 | FOB 下 `The price is inclusive of all freight charges up to Jebel Ali` | R-INC-001 | 是“价格已含运费”，不是“卖方付/记卖方账上” |
     | H90 | 裁决终局后 `Either party may instead elect to have any dispute decided by the courts` | R-DIS-003 | 动词是 `elect/decided`，不在动词表 |
     | H91 | 中文 `全部合同价款一次性汇入…卖方确认收款后方可发运` | R-PAY-001 | 用“收款”，不是“收到/收讫…全部货款” |
     | H92 | 中文 `任何一方均可向有管辖权的人民法院请求重新审理` | R-DIS-004 | 不是上诉/起诉/诉讼 |
     | H93 | 检验期限写成中文数字 `二十四小时` | R-INP-002 | 规则只认阿拉伯数字 |
     其余覆盖既有能力：H94（CIF 无保额）、H95（FOB + FCL）、H96（`DDP` 无版本）、H97（简式确认书，无付款 + 无争议解决）、H98（无适用法律）。
  3. **盲测基线（规则 `version: 9`，改规则之前）**：`eval/results/rules-holdout9-baseline-20261029.json` →
     `TP=6 FP=0 FN=5 TN=121`，**P=1.00 / R=0.545 / F1=0.706**；合同级 `TP=5 FP=0 FN=5 TN=2`；
     漏报 **H89 / H90 / H91 / H92 / H93**；干净对照 H99/H100 零触发。
  4. **纪律**：`test_holdout9_hits_are_stable` + `EXPECTED_HOLDOUT9_HITS` 把五个漏报先写成**空集合**（跑通 = 基线快照）；
     规则测试 57 → 58，全量 **405 测试**。
  5. **未做**：本轮没有再修 holdout9 这五处（修完即消耗），也未动 ISSUE-020/009/033。
- **第 5 步已完成（2026-10-29 第 7 轮第一/二步；ADR-011 第 7 轮补充）**——上半 = 只写集 + 只跑基线（1–3），下半 = 按基线修四处（4）：
  1. **先写中英混合留出集**：新建 `data/contracts_holdout7/`（H65–H76，12 份）+ `data/eval/gold_holdout7.json`
     （11 个现象 / 11 条文本规则，H75/H76 为干净对照），刻意选四种与现有正则形态不同的写法：
     | 合同 | 写法 | 规则 | 为什么可能漏 |
     |---|---|---|---|
     | H65 | `The ocean freight … shall be for the Seller's account` | R-INC-001 | 现有分支只认 `paid/borne by the Seller`，不认“记在卖方账上” |
     | H66 | 仲裁句 `… under the HKIAC Rules.` + 法院句 `If the dispute has not been resolved …, either party may commence proceedings in the courts …` **分属两句** | R-DIS-003 | 现有英文正则用 `[^.]` 拦跨句，同句内也没有 ` or ` |
     | H67 | 中文 `买方应于装运前一次性支付合同项下全部价款` | R-PAY-001 | 现有中文只认“全额预付/预付全款” |
     | H69 | `a party … may, within ninety (90) days …, bring the matter before the courts` | R-DIS-004 | 现有分支只认 `bring an action/suit/proceedings` |
  2. **盲测基线（规则 version 7，改规则之前）**：`eval/results/rules-holdout7-baseline-20261029.json` →
     `TP=7 FP=0 FN=4 TN=121`，**P=1.00 / R=0.636 / F1=0.778**；合同级 `TP=6 FP=0 FN=4 TN=2`，
     `false_negative_contracts = [H65, H66, H67, H69]`；干净对照 H75/H76 **零触发**（无新误报）；
  3. **纪律**：`test_holdout7_hits_are_stable` 把这四个漏报先写成**空集合**（跑通 = 基线快照），
     第二步修完规则后该测试必然失败并点名，届时才翻表降级；当时 `version` 仍是 7。
  4. **第二步（2026-10-29 第 7 轮第二步，规则 `version: 8`）**：只修这四处，每处**先跑临时探针**
     （7 批留出集 76 份 + 主集 50 份 + 2 份样例）确认只命中目标合同才写进 YAML；
     | 漏报 | 修法 | 反向守卫 |
     |---|---|---|
     | H65 | `R-INC-001`（1.2→1.3）加 `(FOB\|EXW\|FCA) … freight/carriage … shall be / is / to be for the Seller's account \| at the Seller's expense` | 不收 `for the Buyer's account`、`at the Seller's risk` |
     | H66 | `R-DIS-003`（1.1→1.2）加**跨句**分支：`arbitrat…` 句号后再起一句含 `either party / a party / the Buyer/Seller … commence/bring/file/initiate/sue/litigate … court` | 中间 tempered-dot 守卫**禁止 `award` 与新条标题**（`第X条` / `Article N` / `Clause N`），否则 holdout4 H39 / holdout5 H41 会被误吃 |
     | H67 | `R-PAY-001`（1.0→1.1）加中文“装运/发货/交货/出运前 … 一次性/全额支付 … 全部/全额价款” | 末尾负向断言排除“全部价款的 30%”这类分期写法 |
     | H69 | `R-DIS-004`（1.2→1.3）在既有英文分支内补 `bring the matter/dispute/case before/to the courts` | `enforced in any court` / `set aside` 不算 |
     改完后先跑 `pytest tests/test_rules.py`：**只有** `test_holdout7_hits_are_stable` 失败并点名
     H65/H66/H67/H69（其余 55 个规则测试全绿），确认失败原因就是“四个漏报进来了”，才翻表降级；
     修后 holdout7 = `11/0/0`（H75/H76 仍零触发）、holdout1–6 全 FP=0、主集 `11/0/0` 且 `hit_counts`
     与 v7 逐条相同（**无新误报**）；`tests/test_api.py` 断言 `ruleset_version == 8`；全量 **403 测试**。
     跨句分支是**启发式 200 字符窗口**，不是“同一 clause 内匹配”，这条边界写进 ADR-011。
- **第 6 步已完成上半（2026-10-29 第 8 轮；ADR-011 第 8 轮补充）——只写集 + 只跑基线，规则 `version: 8` 一条不动**：
  1. **先写中英混合留出集**：新建 `data/contracts_holdout8/`（H77–H88，12 份：5 英 / 7 中）+ `data/eval/gold_holdout8.json`
     （11 个现象 / 11 条文本规则，H87/H88 为干净对照），刻意构造五处 `version: 8` 未覆盖的写法（每类只放一处）：
     | 合同 | 写法 | 规则 | 为什么可能漏 |
     |---|---|---|---|
     | H77 | `The ocean freight … is on the Seller's account` | R-INC-001 | 上轮只补 `shall be for / at … expense`，不认 `is on …` 这种介词短语 |
     | H78 | 裁决终局后又写 `the Buyer may refer the dispute to the courts` | R-DIS-003 | 动词表没有 `refer`，且跨句 |
     | H79 | 中文 `签订后七个工作日内付清全部货款` | R-PAY-001 | 无“一次性/装运前”，现有中文分支不认“付清全部货款” |
     | H80 | `仲裁庭的裁决为终局裁决…可以在收到裁决书之日起三十日内向…法院提起上诉` | R-DIS-004 | 上轮用的是“仲裁裁决…后”，这里换成“仲裁庭的裁决”+“收到裁决书之日起” |
     | H83 | `inspect the Goods immediately upon discharge` / `notified … on the same day` | R-INP-002 | 只认“N hours/days after arrival”，不认“立即/当日” |
     其余覆盖既有能力：H81（`DAP` 无版本）、H82（FOB + FCL）、H84（CIF 无保额）、H85（简式确认书，无付款 + 无争议解决）、H86（无适用法律）。
  2. **盲测基线（规则 version 8，改规则之前）**：`eval/results/rules-holdout8-baseline-20261029.json` →
     `TP=6 FP=0 FN=5 TN=121`，**P=1.00 / R=0.545 / F1=0.706**；合同级 `TP=5 FP=0 FN=5 TN=2`；
     漏报 **H77 / H78 / H79 / H80 / H83**；干净对照 H87/H88 **零触发**。
     （R=0.545 低于 holdout7 的 0.636 是设计使然：五处都刻意挑了没覆盖的写法。）
  3. **纪律**：`test_holdout8_hits_are_stable` + `EXPECTED_HOLDOUT8_HITS` 把这五个漏报先写成**空集合**（跑通 = 基线快照），
     下一步修完规则后该测试必然失败并点名这五份合同，届时才翻表降级；规则测试 56 → 57，全量 **404 测试**。
  4. **未做**：本轮**没有**改任何规则（`version` 仍 8），也没有动 ISSUE-020/009/033。
- **修复的两处真实缺陷（holdout2 暴露，第 3 轮）**：
  | 缺陷 | 现象 | 修复 |
  |---|---|---|
  | 子串误命中 | `contains_any: [CIF, CIP]` 命中 “Pa**cif**ic / speci**fic**ation” → H13 误报 | 四条术语规则改用“前后非英文字母”边界（允许“FOB上海”） |
  | 距离窗口截断 | `R-INC-001` 200 字符窗口被“Freight and Charges”小标题吃掉 → H19 漏报 | 窗口放宽到 260，实测距离写进注释 |
- **当前指标口径（九批样本分工见 ADR-011 第 5/6/7/8/9 轮补充）**：
  | 样本 | 份数 | 结果 | 可否对外报数 |
  |---|---|---|---|
  | `data/contracts`（C01–C50） | 50 | TP=11 FP=0 FN=0（同分布；version 9 命中分布与 v6/v7/v8 逐条相同） | ❌ 回归守卫 |
  | `holdout`（H01–H08） | 8 | 修复后 TP=7 FP=0 FN=0 | ❌ 已消耗 |
  | `holdout2`（H09–H20） | 12 | 修复前 TP=8 FP=1 FN=1（P=R=0.889）；修复后 9/0/0 | ❌ 已消耗，回归守卫 |
  | `holdout3`（H21–H28） | 8 | 修复前 4/0/3（R=0.571）；**修复后 7/0/0** | ❌ 已消耗，回归守卫 |
  | `holdout4`（H29–H40） | 12 | 修复前 TP=8/0/1 → P=1.00 / R=0.889 / F1=0.941；**修复后 9/0/0** | ❌ 已消耗，回归守卫 |
  | `holdout5`（H41–H52） | 12 | 修复前 TP=9 FP=0 FN=1 → P=1.00 / R=0.90 / F1=0.947；修复后 10/0/0 | ❌ 已消耗，回归守卫 |
  | `holdout6`（H53–H64，纯英文） | 12 | 修复前 TP=8 FP=0 FN=3 → P=1.00 / R=0.727 / F1=0.842（漏报 H53/H55/H61）；修复后 11/0/0 | ❌ 已消耗，回归守卫 |
  | **`holdout7`（H65–H76，中英混合）** | 12 | 基线 TP=7 FP=0 FN=4 → P=1.00 / R=0.636 / F1=0.778（漏报 H65/H66/H67/H69，`version: 8` 已修）；修复后 11/0/0 | ❌ 已消耗（历史基线） |
  | **`holdout8`（H77–H88，中英混合）** | 12 | 基线 TP=6 FP=0 FN=5 → P=1.00 / R=0.545 / F1=0.706（漏报 H77/H78/H79/H80/H83，`version: 9` 已修）；修复后 11/0/0 | ❌ 已消耗（历史基线） |
  | **`holdout9`（H89–H100，中英混合）** | 12 | **基线 TP=6 FP=0 FN=5 → P=1.00 / R=0.545 / F1=0.706**（漏报 H89/H90/H91/H92/H93，**尚未修**）；H99/H100 干净对照零触发 | ✅ **当前唯一对外数字，只引基线文件** |
- **holdout6 暴露的 3 个漏报（第 6 轮已修）**：
  1. H53：`FOB Qingdao` + `The Seller shall arrange and pay for the ocean freight from Qingdao to Bremen, and the freight cost is included in the price` —— FOB 下本应由买方付主运费，**且规则认不出“动词在前”的写法**；
  2. H55：`shall be settled by arbitration in Singapore under the SIAC Rules or, at the Buyer's option, by proceedings in the courts of Singapore` —— 或裁或审，连接词后带逗号；
  3. H61：`The Buyer shall pay the entire contract price before shipment` —— 全额预付的同义句，原规则只认 `payment in advance` 等 5 个短语。
  修法见上（第 4 步第 3 点）。**注意**：三处都是“已知句式缺陷”，不是为这 12 份定制；干净对照 H62/H63 与主集 50 份均无新误报。
- **当前对外报数**：规则级 `P=1.00 / R=0.545 / F1=0.706`（holdout8 **基线**文件，12 份中英混合 / 11 个现象，规则 `version: 8`），
  并注明“silver gold 待复核、12 份、漏报 H77/H78/H79/H80/H83 尚未修”；
  holdout7 的基线 `P=1.00 / R=0.636 / F1=0.778`、holdout6 的 `P=1.00 / R=0.727 / F1=0.842` 与 holdout5 的 `P=1.00 / R=0.90 / F1=0.947` 一并作为历史记录。
  任何修后的 1.0 **不得**当作泛化指标引用（这些数据已用于定位缺陷）；八批 88 份中仅 holdout8 未消耗，下一步按基线修完即消耗，再报数须写 holdout9。
- **下一步**：
  1. **第 8 轮已写 holdout8 并跑基线**（`version: 8` 规则不动）：`TP=6 FP=0 FN=5` → P=1.00 / R=0.545 / F1=0.706，五个漏报按纪律钉成空集合 + `test_holdout8_hits_are_stable`；
  2. **按 holdout8 基线修这五处**：H77 介词短语 `is on the Seller's account`（`R-INC-001`）、H78 `refer the dispute to the courts`（`R-DIS-003`，动词表缺 `refer`）、H79 中文“付清全部货款”（`R-PAY-001`，无“一次性/装运前”）、H80 “仲裁庭的裁决…收到裁决书之日起…提起上诉”（`R-DIS-004`）、H83 `immediately upon discharge / on the same day`（`R-INP-002`）；每处先探针（八批 88 份 + 主集 50 份 + 样例），修完 `version: 8`→9 并翻表降级；
  3. 每条规则都对“法定救济 / 正常条款”保留反向样例，防止放宽后误报（H43/H62/H63/H75/H76/H87/H88 就是这类对照）；
  4. 保额邻近窗口是启发式（60/40 字符）、跨句分支是 200 字符窗口，仍可能失效，holdout9 继续覆盖换语种/版式。
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
  7. ~~个人账户的“清空审查记录”没有批量接口，由前端先 `GET /api/reviews?limit=500` 再逐条 `DELETE`~~ **已解决（界面轮 16）**：新增 `DELETE /api/reviews`，服务端在事务内只删本账号的行、返回删除条数，并顺手清掉对应的 checkpoint 与上传目录（前端不再发 N 次请求，也消除了“清到一半失败”的中间态）。
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
  3. **扫描件/OCR（界面轮 13 起已缓解）**：图片型 PDF 会先在 `ingest` 走本地 OCR（ADR-014）再进闸门，但 OCR 可能串行、吞空格，闸门仍只看文本、不猜内容；OCR 也拿不到文本时仍按“正文去空白 < 120 字”判否；
  4. **只判“是不是合同”**：不区分合同类型（国际货物销售 / 国内买卖 / 服务合同），所有通过的文档都按同一套 13 条外贸规则审查；
  5. **阈值与词表缺少真实语料校准**：目前只有 90 份模拟合同 + 论文/法规各一份真实样本，误拒率与误放率都没有统计口径。
- **默认建议**：
  - 收集真实上传失败案例（尤其是“像合同的非合同”）作为 `data/eval` 的闸门评测集，分别统计**误拒率**（真实合同被判否）与**误放率**，两者口径分开报；
  - 语言扩展按需加词表（德/法/日），但保持“召回优先”，不要为了提高精度而把阈值抬到 5；
  - 若未来引入合同类型字段，应作为 `DocumentCheck` 的**附加信息**，不得改变“规则唯一判级”与“闸门不判风险”的边界；
  - 扫描件 OCR 已于界面轮 13 落地（ADR-014，`app/services/ocr.py`），但闸门本身仍只判它拿到的文本、不猜内容；OCR 精度问题见 ISSUE-030。
- **证据**：`app/services/document_type.py`、`app/nodes/precheck.py`、`tests/test_document_type.py`、ADR-012、交接文档已知坑 88–91。

---

## ISSUE-024 · 主区不再展示规则目录，用户无法自助理解“覆盖到哪”

- **状态**：CLOSED（界面轮 16）
- **优先级**：P2
- **背景**：界面轮 4 删除了 `#/rules` 规则集视图（含侧栏入口），主区只剩上传与风险点；规则覆盖范围、抽取状态、解释来源、limitations 都只在 Markdown 报告里。
- **问题**：用户看到“没有发现规则覆盖的风险点”时，容易理解成“合同没问题”，而真实含义是“13 条规则没命中”；页面上没有任何入口解释这一点。
- **解决方式（界面轮 16）**：
  1. 结果页两处都有入口（逐条审查的动作区“这份报告怎么读”、仅下载报告的分支同名链接），复用已有的 `#legal-dialog`，**不新增主区视图**；
  2. 静态七节固定讲四件事：**等级只有规则能给**（13 条规则 / 三档含义）、**证据怎么读**（`source_id#section`、引用必须能在原文定位）、**“参考 · 专家”不是等级**（中性色、0 条时说明降级原因）、**这份报告不能说明什么**（覆盖率 52.4%、10 类无规则、OCR 需人工核对、检索指标不外推）；
  3. **不写死后端事实**：`openGuide()` 再拉 `GET /api/reviews/{id}/report?format=json`，把真实的 `limitations` 追加为第八节；报告尚未生成（待确认）时请求失败，保持静态说明即可；
  4. 规则目录接口 `GET /api/rules` 继续保留给第三方与 `/docs`，页面仍不消费。
- **默认建议（后续如需继续）**：把“本次命中了哪几条规则 / 哪些主题没覆盖”做成结构化字段（现在只在 `limitations` 文本里），前端就能渲染成对照表而不是段落。
- **证据**：`app/web/app.js`（`LEGAL.guide` / `openGuide()` / `data-guide` 两处入口）、`app/nodes/report.py`（`limitations`）、`tests/test_web.py::test_report_guide_dialog_explains_what_report_means`、ADR-009 第 5 轮补充“代价与边界”。

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

- **状态**：**CLOSED**（界面轮 12：用户要求“该部分直接删去”，整套流式叙述已移除）
- **优先级**：P2
- **背景**：界面轮 11 用户要求“以对话框对话的形式流式输出返回审查结果和审查报告”。当时实现是：先 `POST /api/reviews`（同步跑完图，遇 HITL 暂停）拿到真实结果，再 `GET /clauses` / `/report`，最后由前端 `streamText()` 每 18ms 写 3 个字符铺开。
- **决策（界面轮 12）**：删除 `chatNarrative()` / `streamText()` / `stopStream()` / `state.streamTimer` / `#ai-stream` 与 `.chat-thread` / `.msg` / `.msg-bubble` / `.stream-caret` 样式；结果页改为“顶部标签行（合同 / Skill / 审查重点）+ 直接分屏”。理由：真实进度本来就没有事件流支撑，前端节奏反而会让人误以为“还在跑”；而且那段长叙述把内部过程讲给用户听，挤掉了真正要看的条款与意见。
- **保留的部分**：后端 `POST /api/reviews` 仍是同步阻塞（遇 HITL 暂停），这属于既有架构；若将来要做真进度，按下面的建议拆成“提交任务 + SSE”即可，与本次删除不冲突。
- **若将来要做真事件流**：
  - 把 `POST /api/reviews` 拆成“提交任务（返回 review_id + 202）+ 事件流”，用 SSE（`text/event-stream`，FastAPI `StreamingResponse`）按节点推 `stage` / `clause` / `finding` / `done`，前端 `EventSource` 消费；HITL 仍走 `interrupt()`，事件流只推“等待人工确认”；
  - 不要把前端动画当进度上报。
- **证据**：`app/web/app.js`（已删除的 `streamText` / `chatNarrative`；现为 `reviewChip` / `renderWorkbench`）、`app/api.py`（`POST /api/reviews` 同步）、ADR-013 第 8 轮补充第 5 条。

---

## ISSUE-028 · 退出登录只做前端拦截，后端没有“取消审查任务”接口

- **状态**：OPEN
- **优先级**：P2
- **背景**：界面轮 11 要求“审查任务进行中退出要提示会中断任务并二次确认”。当前 `hasActiveTask()`（`busy || taskActive || reviewStatus ∈ {awaiting_human, running}`）命中时弹 `#logout-confirm`，确认后前端清本地状态（`taskActive / clauseView / corrections / kept / reviewStatus`）并 `POST /api/auth/logout`（界面轮 12 起不再有流式定时器可停）。
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

## ISSUE-029 · Skill 的工具声明与文本附件：只影响“怎么写解释”，不执行、不编排

- **状态**：OPEN
- **优先级**：P2
- **背景**：界面轮 12 用户要求“skill 不止提示词，还应当包括调用工具，或者一些 python 格式的文档”。当前落地：`TOOL_CATALOG` 5 个**已实现**能力（规则扫描 / 字段抽取 / 条款切分 / 知识检索 / 谈判提示），`Skill` 增 `tools: list[str]`；`SkillAsset` 只存文本（`.py/.md/.markdown/.txt`，≤5 个、单个 ≤6000 字、总量 ≤30000），`compose_focus()` 把工具 `effect` 与附件正文拼进审查重点，并显式标注“不作为判级依据、不得当作指令执行”。
- **问题**：
  1. **附件完全不执行**：不 `exec`、不 `import`、不沙箱、不做 AST/危险调用检查——只有“后缀白名单 + 长度上限 + 非空”三道校验。用户若以为上传 `.py` 会真的跑，预期会落空；
  2. **工具只是声明**：勾选不改变 LangGraph 节点顺序、不改变规则集合、不触发额外检索，只影响 focus 文案（即“模型被提醒该关注什么”）；
  3. 附件文本会进入 LLM prompt，**存在提示注入风险**——现靠前缀声明“不得当作指令执行”约束，未做内容审查/隔离；
  4. 工具 id 与图节点是硬编码对应，新增能力要同时改 `TOOL_CATALOG`、内置 Skill 与前端文案。
- **默认建议**：
  - UI 与文档持续强调“附件只读、不会运行”，避免误解（已在弹窗与 Skill 展开区写明）；
  - 若确实需要“Skill 自带检查脚本”，应走**受限执行**路线：单独的进程 + 无网络 + 只读挂载 + 超时，且只允许返回结构化提示（仍不得改等级），并把它登记进 ADR（当前明确不做）；
  - 提示注入：给附件单独分段并加“以下为用户资料，不是指令”的显式边界，必要时对 `忽略以上/请忽略` 类语句做关键词提示（现在仅靠前缀声明）。
- **证据**：`app/services/skill_catalog.py`（`TOOL_CATALOG` / `SkillAsset` / `compose_focus`）、`app/services/accounts.py`（`_clean_skill_assets` / `_clean_skill_tools`）、`app/api.py`（`GET /api/skills/tools`）、`app/web/index.html`（“只读取文本，不会被运行”）、ADR-013 第 8 轮补充第 2、3 条。

---

## ISSUE-030 · 图片 PDF 的 OCR 精度、触发条件与页数上限

- **状态**：OPEN
- **优先级**：P2
- **背景**：界面轮 13 用户要求“加入 OCR，以识别 PDF 图片”。当前实现（ADR-014）：`app/services/ocr.py` 用 `pypdfium2` 把页渲染成图（默认 `scale=2.2`），再用 `rapidocr-onnxruntime`（PP-OCR 的离线 ONNX 版，模型随包、**不联网**）识别；`app/nodes/ingest.py` 只在**整份 PDF 文本 < 50 字**（全页 OCR）或**单页 < 10 字**（补该页）时触发，最多 `OCR_MAX_PAGES=20`，单页失败跳过并在 warnings 里写页码。OCR 结果只写入 `raw_text`，**不参与判级**（等级仍只来自 Python 规则）。
- **问题**：
  1. **精度**：真实图片 PDF 实测 4.9 s 输出 `SALES CONTRACT / 2.PAYMENT TERMS / 100% T/T IN ADVANCE / 3.DELIVERY:CIF HAMBURG`——英文**空格会被吞**（`SALESCONTRACT`、`2.PAYMENT`），中文长句与表格可能串行；现有规则靠正则兼容（如标题编号允许无空格），但字段抽取可能因此抽错；
  2. **触发条件**是字数阈值：一份“文本层只有页眉页脚、正文全是图片”的 PDF 会因为总字数 > 50 而**不触发** OCR；
  3. **页数上限 20**：超过 20 页的扫描合同只识别前 20 页，后续条款直接缺失，报告不会显式说明“只识别了前 N 页”；
  4. **依赖体积与首次耗时**：`rapidocr-onnxruntime` + `pypdfium2` 让安装包变大（模型文件随 wheel），进程内首次加载有额外秒级延迟（已做进程内复用 + 锁）；
  5. **质量提示只有一句**：报告固定写“识别结果可能有错字或串行，重要条款请人工核对”，没有逐页置信度。
- **默认建议**：
  - 触发条件从“全文 < 50 字”改为**按页判定**（单页 < 10 字即补 OCR），并在 `settings` 里给出开关，避免“页眉页脚合同”漏识别；
  - 超过 `OCR_MAX_PAGES` 时在 warnings / 报告里显式写“仅识别前 20 页”，让用户知道范围；
  - 若要做得更准，评估版面分析（表格/分栏）或更强模型，但必须保持**离线 + 本地**，并重新评估体积与耗时；
  - 不把 OCR 置信度当作判级依据；需要时只作为“请人工核对”的提示强度。
- **证据**：`app/services/ocr.py`、`app/nodes/ingest.py`（`MIN_PAGE_TEXT_CHARS` / `MIN_PDF_TEXT_CHARS` / `ocr_attempted`）、`app/config.py`（`OCR_ENABLED` / `OCR_MAX_PAGES` / `OCR_RENDER_SCALE`）、`tests/test_ocr.py`、ADR-014。

---

## ISSUE-031 · 4 个外部 Skill 包的来源与授权未确认、正文存在截断

- **状态**：OPEN
- **优先级**：P2
- **背景**：界面轮 13 用户把桌面 4 个外部 Skill 包（`letter-of-credit-reviewer`、面向中国中小外贸企业的进出口合同快速审查技能（虾评平台）、外贸合同快审·小律同学AI（华为云）、`ai-contract-risk-officer`）要求“纳入 Skill 仓库”。当前做法：整包复制到 `app/resources/skills/`，`skill_catalog.py` 以 `_PACKAGE_SPECS` 声明为 `builtin:lc-reviewer` / `builtin:xiaping-fast-review` / `builtin:xiaolv-fast-review` / `builtin:risk-officer`；`instruction` 是**人工提炼的关注方向**（≤1000 字），原 `SKILL.md` 放附件第一位、references 按 `payment-terms → incoterms-2020 → risk-matrix → compliance-checklist → report-template → arbitration-institutions` 排序，最多 5 个 × 6000 字。
- **问题**：
  1. **来源与授权**：4 个包是用户桌面上的第三方 Skill，仓库里没有 LICENSE 记录；随项目对外分发前必须确认可再分发（延续 ISSUE-008 的“无 LICENSE 不复用代码”政策）；
  2. **正文截断**：references 超过 6000 字会截断并标“（节选）”，用户点开附件看到的是**不完整正文**；`SKILL.md` 也走同一上限；
  3. **instruction 与原文可能漂移**：`instruction` 是提炼稿，原文更新后不会自动同步，需要人工重写 `_PACKAGE_SPECS`；
  4. **更新方式只有复制**：没有“从 zip 覆盖内置包”的路径（zip 导入只创建**用户自建** Skill，不改 `builtin:*`）；
  5. `allowed-tools` 等原包声明**不映射**到本项目工具目录（只写 warning），用户若期待原包能力会被降级。
- **默认建议**：
  - 对外分发前补齐 4 个包的**来源与授权说明**（`app/resources/skills/<slug>/SOURCE.md` 或项目 `NOTICE`），不可确认就改成“演示占位、不随包分发”；
  - 附件上限按需提高（例如单文件 20000 字）或在 UI 提供“下载原始 `SKILL.md`”，避免“节选”误导；
  - 原包升级时用脚本重新提炼 `instruction`，并在 `_PACKAGE_SPECS` 记录版本号与提炼日期；
  - 保留“内置只读、用户不可改”的边界；用户要改就“存为我的”复制一份。
- **证据**：`app/resources/skills/`（4 个包目录）、`app/services/skill_catalog.py`（`_PACKAGE_SPECS` / `_package_assets` / `packaged_skills`）、`tests/test_accounts.py`（`test_packaged_external_skills_are_builtin`）、ADR-014。

---

## ISSUE-032 · 专家并行与工具层的成本、信任边界与真实外部数据

- **状态**：OPEN
- **优先级**：P2
- **背景**：界面轮 14 按 ADR-015 加入“三个并行专家 + 只读工具层（本地工具 / MCP）”。这套能力**默认关闭**
  （`AGENTS_ENABLED=false`、`TOOLS_ENABLED=false`），打开后才会产生额外调用与外部进程。
- **问题**：
  1. **成本不可见**：一次审查会多 3 次专家调用（每个专家 1 次）+ 1 次工具规划 + ≤3 次工具执行；
     UI 没有显示“本次额外调用 N 次 / 约多少 token”，用户开开关后可能被账单吓到；
  2. **MCP 是外部子进程**：虽然 `shell=False`、参数白名单、单行 ≤1 MB、超时杀进程、只注册只读工具，
     但服务器本身来自 `.env`（运维配置），它返回的内容会被拼进解释提示词——仍属信任边界，
     与 `SkillAsset` 的“绝不执行”不同（这里是真的跑进程）；
  3. **真实外部数据未接**：制裁名单、汇率、HS 编码、企业征信都需密钥与用户授权，且与 ADR-006
     “单机、无额外基础设施、可离线复现”冲突；当前只留 `McpToolClient` 接口；
  4. **专家质量依赖模型常识**：没有“问题条款→改写”对照、让步顺序、品类模板，专家意见会比较泛；
  5. **专家之间的交互被刻意去掉**：并行分支不能互相追问（拓扑固定），如果将来要“专家辩论”，
     必须新写 ADR 并解决成本 / 可测性。
- **默认建议**：
  - UI 上显示“本次额外 N 次模型调用”，并在设置里说明开启后的成本；
  - MCP 只允许运维在 `.env` 配置、只连本地命令；若将来允许远端，必须加超时、限流、内容过滤与审计日志；
  - 真实外部 API 按“先离线数据（如 OpenSanctions 离线包）→ 再接在线”的顺序推进，每次接入都要
    用户给出授权范围；
  - 专家资料由用户提供后再补 prompt 与 fixture，不靠模型自由发挥。
- **证据**：`app/services/tools.py`（MCP 客户端与白名单）、`app/nodes/experts.py`、`app/nodes/research.py`、
  `tests/test_tools.py`（伪 MCP 服务器）、`tests/test_agents.py`、ADR-015。

---

## ISSUE-033 · 词法检索的两类结构性短板（无条号指代、同义改写/跨语言）

- **状态**：OPEN
- **优先级**：P2（当前 R@3 已可用，属于“继续提升”而非“不能用”）
- **现象**：
  1. `100问题.md` 里有 4 道题**不点条号**、靠上位指代（如“根本违约与解除是什么关系”），
     加权机制对它们无效，仍未进 top-5；
  2. BM25 + 字符 n-gram 只能靠**词面共现**，用户把“适用法律”写成“准据法”、
     用英文问中文条文、或换一套同义措辞时，召回会明显下降。
- **影响**：演示时若用户不按题库措辞提问，引用命中率低于评测数字；不影响判级（规则唯一判级）。
- **默认建议**：
  - 先做**查询改写**（检索前把条号/法律名/术语补进 query），仍是确定性、可测试、离线的；
  - 不做“调参到过拟合”：权重与阈值只有在**新留出集**上复现收益才改；
  - 若确需语义检索，必须新写 ADR 并守住“离线可跑、零外部 embedding 服务、引用可追溯”，
    不能顺手违反 ADR-008 的边界。
- **证据**：`eval/results/rag-20261028.json`（`misses_beyond_k` / `not_top1` 字段）、
  `tests/test_rag_eval.py`、`tests/test_rag_boost.py`、ADR-016。

---

## 本阶段不处理（DEFERRED）

| 事项 | 原因 |
|---|---|
| 多语言 UI | Streamlit 中文界面即可 |
| 多租户 / RBAC / SSO | 本地单账号登录已实现（ADR-013）；不做组织隔离、角色权限矩阵与企业单点登录 |
| 数据库/Redis/消息队列 | 规则与报告用本地文件 + SQLite checkpointer 足够 |
| 知识图谱 / GraphRAG | RAG 已放开（ADR-007），但图数据库与实体关系抽取不在 MVP；先做 BM25/字符 n-gram 检索 |
| 向量数据库 / 外部 embedding 服务 | 增加依赖与成本；MVP 用本地词法检索即可 |
| Supervisor 判级 / 专家改级 | 违反“规则唯一判级”，永远不会做 |
| 微调模型 | 禁止训练模型；用规则 + 结构化输出 |
| Docker 部署 | 明确禁止；本地 Streamlit/FastAPI 演示 |
