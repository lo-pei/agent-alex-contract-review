# RAG 与多智能体：需要你准备的资料清单

> 更新时间：2026-10-27
> 对应决策：[ADR-007 范围变更](./02_ARCHITECTURE_DECISIONS/ADR-007-范围变更-RAG与多智能体.md)
> 用途：为第 5 步（解释 + RAG）与阶段 B（专家智能体）准备语料与评测数据。
> 原则：**资料缺失不阻塞当前代码**；但 RAG 上线前必须先有“最小可开工集”，否则解释只能引用规则理由，不能引用法条。

---

## 0. 一句话结论

最小需要 **4 类知识文档 + 1 份元数据清单 + 10 条检索问题 + 20–30 份脱敏合同 gold**。
其余（完整法条库、术语表、改写对照、长合同）越多越好，但不是开工前提。

---

## 1. RAG 知识库（最重要）

### 1.1 必需（MVP 最小集）

| 优先级 | 资料 | 用途 | 建议格式 | 关键元数据 |
|---|---|---|---|---|
| P0 | Incoterms 2020 术语摘要（FOB/CIF/CFR/EXW/FCA 等 5–7 条即可） | 判断贸易术语版本缺失、费用/风险划分建议 | Markdown（中文摘要 + 英文原文关键句） | 版本=2020、发布机构=ICC、来源 |
| P0 | CISG（联合国国际货物销售合同公约）中英对照，重点：第 25/35/38/39/45/74 条 | 根本违约、检验期限、损害赔偿 | Markdown/TXT | 法域=UN、生效年份 |
| P0 | 中国《民法典》合同编 + 涉外民事关系法律适用法（摘录） | 适用法律缺失、争议解决建议 | Markdown（条款号 + 原文） | 法域=CN、版本年份 |
| P0 | 公司内部“风险红线清单 + 审批 checklist” | 与规则集对齐的建议、人工复核提示 | Markdown / 表格 | 发布部门、版本、生效日期 |
| P1 | UCP 600（信用证）重点条款 | 付款方式建议（L/C 场景） | Markdown 摘要 | 版本=600、ICC |
| P1 | 主要仲裁机构规则摘要（CIETAC / SIAC / HKIAC / ICC） | 仲裁条款建议（机构/规则/地点/语言） | Markdown | 机构、规则版本 |
| P2 | 出口管制/制裁/反腐败合规指引（中国商务部 + 主要目标市场） | 合规条款缺失提示 | Markdown | 发布机构、年份、法域 |
| P2 | 行业模板（按你的主营品类，如纺织/机械/化工/农产品） | 条款比对（缺失/偏差） | DOCX / Markdown | 品类、内部版本 |

> 说明：**不要**把付费标准（如完整 ISO 标准、付费数据库条文）直接全文入库分发；用“条款摘要 + 来源引用”即可。授权问题见第 5 节。

### 1.2 每个文档必须带的元数据

`data/knowledge/manifest.yaml` 是唯一登记处，示例：

```yaml
documents:
  - source_id: incoterms2020
    title: Incoterms 2020 关键术语摘要
    publisher: ICC
    version: "2020"
    jurisdiction: INT
    effective_date: 2020-01-01
    language: zh-en
    file: incoterms/incoterms2020_summary.md
    license: internal-reference-only   # 必填：public-domain / internal-reference-only / licensed
    citation_hint: "按“术语名 + 条款号”引用"
  - source_id: cisg
    title: 联合国国际货物销售合同公约
    publisher: UNCITRAL
    version: "1980"
    jurisdiction: UN
    effective_date: 1988-01-01
    language: zh-en
    file: cisg/cisg_zh_en.md
    license: public-domain
```

缺 `source_id / version / jurisdiction / license` 的文档**不允许入库**（报告里无法引用，也无法判断能不能用）。

### 1.3 切分要求

- 按“章节 / 条款号”切分，**不要**按固定字数乱切；
- 每段 200–800 字，保留条款号（如 `CISG Art. 35`、`Incoterms 2020 FOB A4`）；
- 表格类（如责任对照）保留表头；
- 中英混排文档，中英各自成段，避免一段里两种语言混切。

---

## 2. 检索评测（决定“能不能说 RAG 有用”）

### 2.1 最少 10 条，建议 50 条

| 字段 | 说明 |
|---|---|
| `query` | 审查场景里的真实问题，如“FOB 未写版本有什么风险？” |
| `expected_source_ids` | 应命中的文档（可多个） |
| `expected_sections` | 应命中的条款号（可选，但强烈建议） |
| `notes` | 为什么这条是标准答案 |

示例：

```yaml
queries:
  - query: FOB 未注明 Incoterms 版本会怎样？
    expected_source_ids: [incoterms2020]
    expected_sections: ["FOB"]
    notes: 费用与风险转移点依赖版本，必须提示补版本
  - query: 买方 30 天检验期是否合理？
    expected_source_ids: [cisg]
    expected_sections: ["Art. 38", "Art. 39"]
```

评测口径（会写进报告，不允许“凭感觉说准”）：

- `Recall@5`：应命中文档是否在前 5 条；
- `Citation Precision`：解释里引用的 `source_id#section` 是否真实存在；
- `No-hit rate`：检索不到时是否正确退化为规则理由（不编造法条）。

### 2.2 需要你确认的评测集规模

- 默认：**10 条先开工，50 条做正式评测**；
- 若你能提供真实业务问题（客服/法务常问的 50 个问题），优先用真实问题。

---

## 3. 多智能体所需资料

多智能体不是“多写几个 prompt”，而是要把**角色边界**和**判据**写清楚。

| 资料 | 用途 | 是否必需 |
|---|---|---|
| 现有审批流程（谁审、审什么、卡在哪一步） | 决定 HITL 与专家节点的分工 | 必需（口述即可，我整理成文档） |
| 内部风险红线清单（哪类条款一律不接受） | `PolicyChecker` 的判据 | 必需 |
| 历史“问题条款 → 修改后条款”对照 30–50 组 | 训练/评测“建议质量”，不是训练模型 | 强烈建议 |
| 常见谈判让步顺序（哪些能让、哪些不能让） | 建议措辞分级（强/弱建议） | 可选 |
| 品类模板合同（每品类 1 份） | `ClauseComparator` 的比对基准 | 建议（与 P2 行业模板同一份） |

多智能体角色默认草案（你可以直接改）：

| 角色 | 负责 | 不负责 |
|---|---|---|
| Extractor | 抽 17 字段 + 原文引文 | 判风险 |
| ClauseComparator | 与模板比对，指出缺失/偏差 | 定等级 |
| PolicyChecker | 对照内部红线，指出候选命中 | 定等级 |
| Explainer | 用规则结果 + 原文 + 知识片段写解释与建议 | 新增规则、改等级 |
| Supervisor（可选） | 只路由到上述白名单节点 | 产出结论、批准 |

---

## 4. 合同与 gold（规则/抽取/解释共用）

已在 ISSUE-005 记录，这里合并列出：

- **20–30 份脱敏合同**：
  - 10–15 份常见销售合同（中英各半）；
  - 3–5 份长合同（>40 条款，用于长合同覆盖评测）；
  - 2 份扫描件/复杂版式（用于验证“明确报错”而不是假装成功）；
  - 2–3 份“干净合同”（应全 pass，用于误报率）。
- **条款级 gold**：每份合同标注 `(clause_id, rule_id, 期望等级)`；允许“规则未覆盖”标注为 `uncovered`。
- **字段 gold**：17 字段的期望值 + 是否允许 null。
- **解释 gold（可选）**：每条红色风险期望引用的原文片段（用引文是否命中来评，不评文采）。

脱敏要求：公司名、金额、联系人、银行账号替换；保留条款结构与行业术语。

---

## 5. 合规与授权（必须确认）

| 事项 | 需要你确认 |
|---|---|
| 合同文本能否发送到外部 LLM（数据出境/保密） | 能 / 不能 / 仅脱敏后可以 |
| 知识库文档的版权与授权 | 每份文档在 `manifest.yaml` 标 `license`；付费标准只做摘要引用 |
| 是否允许把内部红线清单写进代码仓库 | 允许 / 只放本地不入库（放 `data/knowledge/internal/` 并 gitignore） |
| 报告对外分享时的脱敏要求 | 是否需要自动遮盖金额/公司名 |

> 默认策略：内部资料放 `data/knowledge/internal/` 并在 `.gitignore` 排除；对外报告只引用 `source_id#section`，不粘贴大段原文。

---

## 6. 目录与格式约定

```text
data/
  knowledge/
    manifest.yaml                 # 唯一登记处（见 1.2）
    incoterms/*.md
    cisg/*.md
    cn_law/*.md
    arbitration/*.md
    internal/*.md                 # 默认 gitignore
  eval/
    contracts/                    # 20–30 份脱敏合同（txt/md/pdf/docx）
    gold/
      rules.yaml                  # (contract, clause_id, rule_id, expected_level)
      fields.yaml                 # 17 字段 gold
    retrieval_queries.yaml        # 见 2.1
```

`gold/rules.yaml` 示例：

```yaml
contracts:
  - file: contracts/sales_zh_01.txt
    labels:
      - clause_id: C003
        rule_id: R-PAY-001
        expected_level: red
      - clause_id: C007
        rule_id: R-DLV-001
        expected_level: yellow
    uncovered: [C009]   # 规则集未覆盖，但人工认为有风险
```

---

## 7. 最小可开工集（建议先给这些，其他后补）

| # | 资料 | 数量 | 我拿到后做什么 |
|---|---|---|---|
| 1 | Incoterms 2020 摘要（FOB/CIF/EXW/FCA/CFR） | 1 份 Markdown | 建 `incoterms2020` 文档 + 切分 + 检索 |
| 2 | CISG 中英（重点 6 条） | 1 份 | 建 `cisg` 文档；解释可引用 “Art. 35” |
| 3 | 民法典合同编 + 法律适用法摘录 | 1 份 | 建 `cn_law` 文档 |
| 4 | 内部风险红线清单 | 1 份 | 建 `internal_policy` 文档 + `PolicyChecker` 判据 |
| 5 | 检索问题 | 10 条 | 建 `retrieval_queries.yaml`，先跑 Recall@5 |
| 6 | 脱敏合同 | 5 份起（目标 20–30） | 建 gold 骨架，跑规则评测 |

拿到 1–5 就可以开始第 5 步的 RAG MVP；第 6 项决定评测数字，不影响代码开工。

---

## 8. 你可以先不提供的

- 不需要你写代码或 prompt；
- 不需要你整理成数据库；
- 不需要提供真实未脱敏合同；
- 不需要购买向量数据库/云服务；
- 不需要提供完整法律意见（我们只做“提示 + 引用”，不做法律结论）。

---

## 9. 我这边会先做的默认动作（无需你确认）

1. `RAG_ENABLED=false`、`AGENTS_ENABLED=false` 默认关闭，保证现有行为不变；
2. 先实现 BM25/字符 n-gram 检索（零新依赖、离线可跑），不引入外部向量库；
3. 知识引用统一格式 `source_id#section`，报告中与规则理由分开呈现；
4. 检索不到时解释退化为规则理由，不编造法条；
5. 专家节点输出只做“候选问题”，不改规则等级；失败进 `degraded_steps`。

> 如果以上默认与你的预期不符，在第 5 步开始前告诉我即可。
