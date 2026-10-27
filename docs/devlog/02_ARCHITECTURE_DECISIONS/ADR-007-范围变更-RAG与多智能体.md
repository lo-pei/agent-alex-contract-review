# ADR-007：范围变更——允许 RAG 与多智能体

- 状态：**已接受（2026-10-27，用户明确指示「可以做 rag 和多 agent」）**
- 日期：2026-10-27
- 决策人：用户 + Trae AI
- 关联：`开发提示词.md`（原硬约束）、ADR-001、ADR-002、ADR-003、ADR-006、`06_RAG与多智能体资料清单.md`
- 影响范围：`app/services/rag.py`（计划）、`app/nodes/explain.py`（计划）、`app/nodes/agents/*`（计划）、依赖与评测

---

## 1. 背景

`开发提示词.md` 原硬约束写明「禁止 RAG 知识库、禁止多智能体、禁止 Supervisor」。这条约束的初衷是防止 10 天 MVP 失控：多智能体容易变成无人可解释的自由对话循环，RAG 容易把不可追溯的“知识”混进判级。

用户在 2026-10-27 明确放开：可以做 RAG 与多智能体。本节记录**放开什么、不放开什么**，以及引入顺序，避免“顺手加个 Agent”破坏已经验证的边界。

---

## 2. 决策

### 2.1 放开的部分

| 能力 | 结论 | 允许的用法 |
|---|---|---|
| RAG 知识库 | ✅ 允许 | 为**解释/建议/条款比对**提供可引用的法规、惯例、内部政策片段 |
| 多智能体 | ✅ 允许 | 多个**角色明确、输出有 schema、可单独测试**的专家节点，用确定性编排串联 |
| Supervisor | ✅ 允许（受限） | 只做**路由**：从白名单里选择下一个专家节点；不产生文字结论、不改等级、不写报告 |

### 2.2 不放开的部分（不可变边界）

1. **风险等级仍只由 Python 规则产生**：`red/yellow/pass` 只出现在 `app/rules/*` 与报告；RAG 检索结果、专家智能体、Supervisor 都不得输出或改写等级。
2. **HITL 仍是红色风险的唯一出口**：`interrupt()` + checkpointer + `Command(resume=...)` 不变；任何智能体都不得自动批准。
3. **证据可追溯**：
   - 合同引用仍是 `文件名:p页:start-end`，必须能 `locate_quote`；
   - 知识引用必须是 `source_id#section`（文档 ID + 章节/页码），带版本与法域；
   - 没有 `source_id` 的“知识”不得进入报告。
4. **不引入不可控循环**：禁止无上限的 agent 对话、禁止 `while True` 自我反思；每个专家节点最多调用 LLM 1 次（+1 次修复重试）。
5. **不引入额外基础设施**：仍需单机可跑，不引入 Docker、外部向量数据库服务、消息队列；向量索引落地为本地文件 / SQLite。
6. **不训练模型**：RAG 只用现成 embedding 或纯检索（BM25/关键词），不做微调。

### 2.3 与 `开发提示词.md` 的关系

- 本条是**用户显式授权**的范围变更，优先于原文档的“禁止 RAG / 多智能体”；
- 其余硬约束（Python + LangGraph + Streamlit + FastAPI + Pydantic、规则唯一判级、真 HITL、异常降级、可追溯、可测试）**继续有效**；
- `开发提示词.md` 为只读需求文档，不改写；变更记录以本 ADR 为准。

---

## 3. 引入方式（分阶段，可回退）

```text
阶段 A（第 5 步）：RAG 检索服务 + 解释节点
  rules(Python) ──► explain(LLM + RAG 引用) ──► report
  影响面：只影响“建议/解释”文本，不影响 findings 的 rule_id / risk_level

阶段 B（第 6 步之后）：多智能体专家评审
  validate ──► [clause_compare | policy_check | explain] ──► rules ──► HITL ──► report
  影响面：专家节点只产出“候选问题/引用”，是否构成风险仍由规则 YAML 决定
```

### 3.1 阶段 A：RAG（解释辅助）

- 检索对象：`data/knowledge/` 下的法规、惯例、内部政策（见资料清单）；
- 检索实现优先级：
  1. **BM25 / 字符 n-gram 关键词检索**（纯 Python，零新依赖，可离线）——MVP 先用；
  2. 若召回不足，再评估本地向量（`sqlite-vec` 已可安装）或现成 embedding API；
- 输出契约（新增 schema，计划）：

```python
class KnowledgeChunk(BaseModel):
    source_id: str          # 如 "incoterms2020"
    title: str
    version: str            # 如 "2020"
    jurisdiction: str       # 如 "ICC" / "CN" / "UN"
    section: str            # 条款号/章节
    text: str
    score: float

class KnowledgeCitation(BaseModel):
    source_id: str
    section: str
    version: str
    jurisdiction: str
```

- 解释节点必须把检索片段放在 `<untrusted_knowledge>` 分隔符中，同样做转义；
- **RAG 片段只能支持“建议”，不能作为“风险等级”依据**；报告同时展示 `rule.reason` 与知识引用，二者不合并成一个结论；
- 检索不到 → `knowledge_citations=[]`，解释退化为规则 `reason` 兜底，不编造法条。

### 3.2 阶段 B：多智能体（专家节点）

| 角色 | 输入 | 输出（schema） | 禁止 |
|---|---|---|---|
| `Extractor`（已有） | 条款原文 | 17 字段 + quote | 输出等级 |
| `ClauseComparator` | 条款 + 模板/知识片段 | 缺失/偏差候选（`clause_id` + 引用 + 说明） | 直接下结论为 red |
| `PolicyChecker` | 合同全文 + 内部红线清单 | 命中的红线候选（`policy_id` + 引用） | 改写规则等级 |
| `Explainer`（第 5 步） | 规则结果 + 条款原文 + 知识片段 | `RiskExplanation`（quote 必须可定位） | 新增 `rule_id`、越权结论 |

编排规则：

- 固定顺序优先，不用“自由对话式 Supervisor”；
- 若使用 Supervisor，只允许在 `{clause_compare, policy_check, explain}` 三个白名单节点中选择，且选择结果写进 `degraded_steps` 便于审计；
- 专家节点失败 → 记录 `degraded_steps`，主流程继续，报告参与项标记“专家未执行”；
- 所有专家输出必须经 Pydantic 校验 + 引文定位；不合格直接丢弃。

### 3.3 开关（默认关闭）

```text
RAG_ENABLED=false        # 关闭时：解释只用规则 reason，不检索
AGENTS_ENABLED=false     # 关闭时：只有确定性主干（当前行为）
```

关闭时行为必须与第 4 步完全一致，且有测试覆盖（回归保护）。

---

## 4. 被否决的做法

| 做法 | 否决原因 |
|---|---|
| 让 RAG 片段参与判级 / 由 LLM 综合“知识 + 合同”给等级 | 破坏规则唯一判级，无法回归 |
| 多智能体自由对话（AutoGen/CrewAI 式） | 输出不可预测、成本不可控、无法写确定性测试 |
| Supervisor 拥有“通过/拒绝”权限 | 绕过 HITL，违反硬约束 |
| 引入外部向量数据库/托管服务 | 单机演示与离线复现困难；增加部署依赖 |
| 把付费标准全文入库并分发 | 版权/授权风险；只允许引用与摘要（见资料清单） |
| RAG 检索不到时让 LLM“凭常识补法条” | 幻觉法条，不可追溯，必须禁止 |

---

## 5. 后果

### 正面

- 解释与建议可以引用真实法规/惯例，报告更有说服力；
- 专家节点职责单一，可分别测试与关闭；
- RAG/多智能体是**加法**，不改变已验证的判级与 HITL 语义。

### 代价与风险

- 知识库质量与授权成为新的前置条件（ISSUE-015）；
- 检索错配会带来“引用不相关”的解释，需要检索评测（query gold）；
- 多智能体增加延迟与成本，需限制节点数与单节点 1 次调用；
- prompt injection 面扩大：知识文档也可能是不可信输入，需分隔符 + schema + 引文校验；
- 评测复杂度上升：必须分别报告规则、抽取、解释、检索四层指标。

### 必须补的测试（后续步骤）

| 测试 | 断言 |
|---|---|
| `test_rag_disabled_by_default` | 默认不检索，报告无知识引用 |
| `test_rag_citations_are_registered` | 每条知识引用都能在 manifest 中找到 `source_id`/版本/法域 |
| `test_rag_no_hit_falls_back` | 检索为空 → 用规则 reason 兜底，不编造 |
| `test_agents_cannot_override_rule_level` | 专家输出被篡改时，报告等级仍等于规则等级 |
| `test_supervisor_whitelist` | Supervisor 只能选白名单节点，越界即报错/降级 |

---

## 6. 证据

- 用户指令：2026-10-27「注意，可以做rag和多agent，我需要准备哪些资料，然后继续第四步」；
- `开发提示词.md` 原硬约束（禁止 RAG / 多智能体 / Supervisor）与本 ADR 的差异说明见 §2.3；
- 资料与授权清单：`docs/devlog/06_RAG与多智能体资料清单.md`；
- 现有边界实现：`app/rules/engine.py`（唯一判级）、`app/nodes/hitl.py`（`interrupt()`）、`app/services/evidence.py`（引文定位）。
