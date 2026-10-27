# ADR-008：RAG MVP（本地 BM25 检索）与解释质量门

- 状态：**已接受（2026-10-27）**
- 日期：2026-10-27
- 决策人：用户 + Trae AI
- 关联：ADR-003（规则/LLM 边界）、ADR-007（范围变更：允许 RAG）、ISSUE-015（语料与授权）

## 1. 背景

ADR-007 允许 RAG，但约束很硬：

- 等级只能来自 Python 规则；
- 引用必须可追溯（`source_id#section`）；
- 无命中/配置错误必须降级，不能阻塞报告；
- 比赛环境需要离线可跑、可测试、无额外服务依赖。

同时真实知识语料（ISSUE-015）尚未提供，因此第一步只能做“可替换的检索骨架 + 示例语料”。

## 2. 选项

| 方案 | 优点 | 缺点 | 结论 |
|---|---|---|---|
| A. 向量库（FAISS/Chroma）+ embedding API | 语义召回好 | 新增依赖与服务；离线/无 Key 不可用；成本与延迟不可控；难以解释为何召回 | 不选（MVP） |
| B. Neo4j / GraphRAG | 关系推理强 | 依赖重、建设周期长，与 10 天 MVP 不匹配 | 不选 |
| C. 纯 LLM“凭记忆答” | 实现最快 | 不可追溯、会编造条文；违反证据边界 | **禁止** |
| D. 本地词法检索（BM25）+ 中文二元组 | 零网络、零新依赖、可解释、可测试 | 语义泛化弱；同义改写召回差 | **采用（MVP）** |

## 3. 决策

### 3.1 检索

- 英文按词、中文按“单字 + 二元组”切分（不引入分词库）；
- BM25（`k1=1.5, b=0.75`）+ **相对阈值**：只保留得分 ≥ 最高分 25% 的片段，避免长尾噪声进提示词；
- `RAG_TOP_K`（默认 3）、`RAG_MIN_SCORE`（默认 1.0，绝对下限）；
- 语料规模在几十份文档内时全量常驻内存，加载一次，无索引持久化。

### 3.2 语料与元数据

- `data/knowledge/manifest.yaml`，`version: 1`，每条必须有
  `source_id / title / publisher / version / jurisdiction / effective_date / language / file / license`；
- `source_id` 必须字母开头（合法引用锚点）；`effective_date` 必须 `YYYY-MM-DD`；
- 文件只能是 `.md/.txt`、必须 UTF-8、必须在语料目录内（拒绝 `..` 与绝对路径）；
- 未知字段、重复 `source_id`、空 `documents` 一律报错——**宁可启动失败，不让无授权/无版本文本入库**。

### 3.3 引用

- 片段按 Markdown 标题切分，编号 `s1, s2, ...`；
- 对外唯一格式 `source_id#section`（如 `EX-INCOTERMS#s3`）；
- 质量门只接受“本条风险**实际检索到**的片段”作为引用；模型引用了未检索到的片段 → 丢弃并告警；
- 报告里的知识引用与合同原文引用分字段展示（`citations` vs `knowledge_citations`），不合并。

### 3.4 解释质量门（Python）

对每条 LLM 解释执行，任一不通过即回退规则理由：

| 检查 | 失败代码 |
|---|---|
| `rule_id` 必须是本次要求解释的规则 | `rule_id` |
| `clause_id` 必须属于该规则命中的条款 | `clause_id` |
| `summary` 非空 | `empty_summary` |
| 禁止“合同无效/有效/已批准/已签署/无风险/建议直接签署/等级为…”等越权表述 | `forbidden:<code>` |
| `quote` 必须能在对应条款原文精确定位（仅空白/NFC 规范化） | `quote_not_found` |
| 知识引用必须是实际检索到的 `citation` | 丢弃该引用 + warning |
| schema 无 `risk_level` | Pydantic `extra="forbid"` |

模型失败、未配置、质量门失败都**只影响该条**，其余风险继续解释；整体状态标 `fallback`，报告 limitation 明示。

### 3.5 执行时机

- 只有 `approved` 或“无红快速通道（`running`）”才调用解释；
- `rejected / changes_requested / unreviewed_red_risk / failed` 直接出报告，`explanation_status="skipped"`；
- 没有任何 red/yellow（或字段规则被 `skipped`）时不调用 LLM。

## 4. 后果

**正面**

- 零新依赖、离线可跑，`pytest` 可覆盖全部路径；
- 每条解释都能落到“规则 + 合同原文 + 知识片段”三元证据；
- 知识库不可用/未命中时报告仍完整，只是标注未使用知识库。

**代价 / 风险**

- 词法检索对同义改写（“适用法律” vs “准据法”）召回有限，需靠真实语料与评测集调 `top_k/min_score`；
- 示例语料是项目自拟，**不能**作为法律依据对外引用；
- 每条约 1 次额外 LLM 调用（4 条风险 ≈ 4 次），成本与延迟随风险条数线性增长（上限 20 条）。

**后续**

- 语料到位后补 50 条检索 query 评测（recall@k、引用正确率）；
- 若词法召回不足，再评估“BM25 + 本地小向量模型”，但仍不得引入外部 embedding 服务（保持离线）；
- 阶段 B 的专家节点只能复用本 ADR 的解释/引用约束。

## 5. 证据

- `app/services/rag.py`、`app/nodes/explain.py`
- `tests/test_rag.py`（15 个）、`tests/test_explain.py`（13 个）
- `data/knowledge/manifest.yaml` + 3 份示例语料
- 实测：`R-DIS-002` → `EX-CN-CONTRACT#s3`（仲裁与管辖）、`R-TRD-001` → `EX-INCOTERMS#s2`（贸易术语与版本）
