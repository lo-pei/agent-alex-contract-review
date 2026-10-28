"""全局 Pydantic schema：状态、条款、证据、规则结果、报告。

角色：所有节点与模块共享的数据契约（ADR-001 §3.6、ADR-003 §3.5、ADR-005 §3）。
依赖：无项目内依赖；被 `app/nodes/*`、`app/rules/*`、`app/graph.py` 引用。
约束：
- 等级字段 `risk_level` 只允许出现在规则/报告侧，LLM 抽取与解释 schema 中禁止出现（ADR-003）。
- 所有 schema `extra="forbid"`，防止 LLM 或节点悄悄塞入未定义字段。
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RiskLevel = Literal["red", "yellow", "pass"]
OverallLevel = Literal["red", "yellow", "pass", "unknown"]

ReviewStatus = Literal[
    "running",
    "awaiting_human",
    "approved",
    "rejected",
    "changes_requested",
    "completed",
    "unreviewed_red_risk",
    "failed",
    #: 上传的文件没有被识别为合同（论文/法规/说明书等）：**不进入规则审查，也不产出风险结论**
    "not_contract",
]


class DocumentCheck(BaseModel):
    """文档类型闸门的判定结果（确定性规则，可解释）。

    `is_contract=False` 时图会在 `precheck_document` 处直接结束，
    只产出“未执行审查”的报告，避免把论文当成合同去判风险。
    """

    model_config = ConfigDict(extra="forbid")

    is_contract: bool
    confidence: float = Field(ge=0, le=1)
    #: 面向用户/审计的判定依据（已排序，可直接展示）
    reasons: list[str] = Field(default_factory=list)
    #: 判否时的下一步建议
    hints: list[str] = Field(default_factory=list)


class Page(BaseModel):
    """canonical text 中的一页（TXT/DOCX 固定为 1 页）。"""

    model_config = ConfigDict(extra="forbid")

    page_number: int = Field(ge=1)
    text: str
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)


class Clause(BaseModel):
    """条款：`text` 为 canonical_text 的 [start, end) 切片，含标题。"""

    model_config = ConfigDict(extra="forbid")

    clause_id: str
    title: str = ""
    text: str
    page: int = Field(default=1, ge=1)
    start: int = Field(default=0, ge=0)
    end: int = Field(default=0, ge=0)
    clause_type: str | None = None


class Evidence(BaseModel):
    """原文证据。`grounded=True` 表示 quote 已在原文精确/规范化定位。"""

    model_config = ConfigDict(extra="forbid")

    quote: str
    start: int | None = Field(default=None, ge=0)
    end: int | None = Field(default=None, ge=0)
    page: int | None = Field(default=None, ge=1)
    clause_id: str | None = None
    grounded: bool = False


class ToVerifyItem(BaseModel):
    """需要人工核对的事项（抽取/校验阶段产生）。"""

    model_config = ConfigDict(extra="forbid")

    field: str
    reason: str
    clause_id: str | None = None


class RuleEvaluation(BaseModel):
    """单条规则的执行结果。触发 → red/yellow；未触发 → pass。"""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    title: str
    risk_level: RiskLevel
    reason: str
    suggestion: str | None = None
    clause_ids: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    requires_human: bool = False
    is_system_finding: bool = False
    # 抽取不可用时字段规则被跳过（不是 pass，也不是触发）；评测应单独统计
    skipped: bool = False


# ---------- LLM 抽取契约（ADR-003 §3.7） ----------

#: MVP 的 17 个合同级字段；新增字段必须先改这里 + 测试 + prompt
EXTRACTED_FIELDS: tuple[str, ...] = (
    "seller",
    "buyer",
    "goods_description",
    "quantity",
    "unit_price",
    "total_amount",
    "currency",
    "incoterms",
    "incoterms_version",
    "delivery_date",
    "payment_method",
    "payment_terms",
    "inspection_standard",
    "warranty_period",
    "liability_cap",
    "governing_law",
    "dispute_resolution",
)

#: 需要归一化为数字的字段（规则 NumericLt/NumericGt 依赖）
NUMERIC_FIELDS: tuple[str, ...] = ("unit_price", "total_amount")


class FieldValue(BaseModel):
    """LLM 对单个字段的抽取结果：未提及 → value/quote 都为 null。"""

    model_config = ConfigDict(extra="forbid")

    value: str | int | float | None = None
    quote: str | None = Field(default=None, max_length=1000)


def _empty_field() -> FieldValue:
    return FieldValue()


class ExtractedFieldSet(BaseModel):
    """显式 17 字段（不用自由 dict），schema 中**没有** risk_level/confidence。"""

    model_config = ConfigDict(extra="forbid")

    seller: FieldValue = Field(default_factory=_empty_field)
    buyer: FieldValue = Field(default_factory=_empty_field)
    goods_description: FieldValue = Field(default_factory=_empty_field)
    quantity: FieldValue = Field(default_factory=_empty_field)
    unit_price: FieldValue = Field(default_factory=_empty_field)
    total_amount: FieldValue = Field(default_factory=_empty_field)
    currency: FieldValue = Field(default_factory=_empty_field)
    incoterms: FieldValue = Field(default_factory=_empty_field)
    incoterms_version: FieldValue = Field(default_factory=_empty_field)
    delivery_date: FieldValue = Field(default_factory=_empty_field)
    payment_method: FieldValue = Field(default_factory=_empty_field)
    payment_terms: FieldValue = Field(default_factory=_empty_field)
    inspection_standard: FieldValue = Field(default_factory=_empty_field)
    warranty_period: FieldValue = Field(default_factory=_empty_field)
    liability_cap: FieldValue = Field(default_factory=_empty_field)
    governing_law: FieldValue = Field(default_factory=_empty_field)
    dispute_resolution: FieldValue = Field(default_factory=_empty_field)


class ClauseExtraction(BaseModel):
    """单条款抽取结果（原始或已校验，节点不同语义不同）。"""

    model_config = ConfigDict(extra="forbid")

    clause_id: str
    fields: ExtractedFieldSet


class HitlDecision(BaseModel):
    """人工审批决定（ADR-002）。超时绝不映射为 approve。"""

    model_config = ConfigDict(extra="forbid")

    action: Literal["approve", "request_changes", "reject", "timeout"]
    reviewer: str = Field(min_length=1, max_length=64)
    comment: str | None = Field(default=None, max_length=2000)
    overrides: dict[str, str] = Field(default_factory=dict)


class ApprovalFinding(BaseModel):
    """审批载荷中的一条红色风险（只来自规则结果，不含 LLM 解释）。"""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    title: str
    risk_level: Literal["red"] = "red"
    reason: str
    suggestion: str | None = None
    clause_ids: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    #: 原文片段（截断），供人工在审批页核对
    quotes: list[str] = Field(default_factory=list)
    is_system_finding: bool = False


class ApprovalPayload(BaseModel):
    """`interrupt()` 的审批载荷（ADR-002 §3.2）。

    约束：不含 LLM 解释、不含“建议通过/拒绝”、不含时间戳（时间戳由 API 侧写入，
    保证节点 resume 重跑时载荷稳定）。
    """

    model_config = ConfigDict(extra="forbid")

    type: Literal["red_risk_approval"] = "red_risk_approval"
    review_id: str
    source_filename: str
    overall_level: OverallLevel
    findings: list[ApprovalFinding] = Field(default_factory=list)
    #: 红色风险总数（`findings` 最多展示 20 条）
    findings_total: int = 0
    truncated: int = 0
    extraction_status: Literal["ok", "degraded", "skipped"] = "skipped"
    extraction_summary: dict[str, str | int | float | None] = Field(default_factory=dict)
    to_verify: list[str] = Field(default_factory=list)
    instructions: str = (
        "请确认以上红色风险是否属实。可批准（approve）、要求修改（request_changes）"
        "或拒绝（reject）；超时将被标记为未确认，绝不自动通过。"
    )


class RiskExplanation(BaseModel):
    """LLM 对单条规则结果的解释契约（ADR-003 §3.8）：**没有** `risk_level`。"""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    clause_id: str | None = None
    summary: str = Field(min_length=1, max_length=300)
    #: 必须从条款原文原样复制；无对应条款时可为 null
    quote: str | None = Field(default=None, max_length=500)
    recommendation: str | None = Field(default=None, max_length=300)
    #: 只能引用检索结果中给出的 citation（`source_id#section`）
    knowledge_refs: list[str] = Field(default_factory=list, max_length=3)


class ExplanationResult(BaseModel):
    """质量门校验后的解释；报告只消费这个结构，不直接消费 LLM 输出。"""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    summary: str
    quote: str | None = None
    #: quote 定位到的 `文件名:p页:start-end`（可定位时才有）
    citation: str | None = None
    recommendation: str | None = None
    #: 所展示 quote 是否已在原文定位（规则兜底时也可能为 True）
    grounded: bool = False
    source: Literal["llm", "rule"] = "rule"
    knowledge_citations: list[str] = Field(default_factory=list)


class ReportFinding(BaseModel):
    """报告中的一条风险（仅非 pass 的规则结果）。"""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    risk_level: Literal["red", "yellow"]
    reason: str
    suggestion: str | None
    clause_ids: list[str]
    citations: list[str]
    explanation_summary: str | None = None
    explanation_quote: str | None = None
    explanation_grounded: bool = False
    explanation_citation: str | None = None
    explanation_source: Literal["llm", "rule", "none"] = "none"
    knowledge_citations: list[str] = Field(default_factory=list)
    is_system_finding: bool = False


class ClauseFinding(BaseModel):
    """逐条审查视图中的一条风险：等级沿用规则结果，不重新判级。"""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    title: str
    risk_level: Literal["red", "yellow"]
    reason: str
    suggestion: str | None = None
    explanation_summary: str | None = None
    explanation_quote: str | None = None
    explanation_citation: str | None = None
    knowledge_citations: list[str] = Field(default_factory=list)
    quotes: list[str] = Field(default_factory=list)


class ClauseReview(BaseModel):
    """单条款的审查视图：原文、命中的规则、可套用的修订示例。"""

    model_config = ConfigDict(extra="forbid")

    clause_id: str
    index: int = Field(ge=1)
    title: str = ""
    text: str
    page: int = Field(default=1, ge=1)
    risk_level: Literal["red", "yellow", "pass"] = "pass"
    findings: list[ClauseFinding] = Field(default_factory=list)
    #: 规则给出的“修改后的条款”示例；没有命中规则时为 None
    revised_text: str | None = None
    revision_note: str | None = None


class ClauseReviewList(BaseModel):
    """`GET /api/reviews/{id}/clauses` 的响应。"""

    model_config = ConfigDict(extra="forbid")

    review_id: str
    source_filename: str
    status: ReviewStatus
    overall_level: OverallLevel
    awaiting_human: bool = False
    clauses: list[ClauseReview] = Field(default_factory=list)
    #: 不指向具体条款的风险（例如“未约定适用法律”），作为“全合同”一组展示
    contract_findings: list[ClauseFinding] = Field(default_factory=list)
    #: 针对合同级问题给出的“建议新增条款”示例
    contract_revised_text: str | None = None
    contract_revision_note: str | None = None
    revised_count: int = 0
    limitations: list[str] = Field(default_factory=list)


class ReviewReport(BaseModel):
    """对外输出报告（规则结果 + 人工决定 + 可选 LLM 解释）。"""

    model_config = ConfigDict(extra="forbid")

    review_id: str
    source_filename: str
    generated_at: datetime
    overall_level: OverallLevel
    status: ReviewStatus
    summary: str
    findings: list[ReportFinding] = Field(default_factory=list)
    extracted_fields: dict[str, str | int | float | None] = Field(default_factory=dict)
    to_verify: list[ToVerifyItem] = Field(default_factory=list)
    hitl: HitlDecision | None = None
    limitations: list[str] = Field(default_factory=list)
    rule_engine_version: str
    prompt_version: str = "n/a"
    model_id: str | None = None
    explanation_status: Literal["ok", "fallback", "skipped"] = "skipped"
    explanation_model: str | None = None
    explanation_prompt_version: str = "n/a"
    #: 用户指定的审查重点（指令 + Skill + 参考材料）；只影响解释措辞，不改变等级
    focus: str | None = None
    #: 本次使用的 Skill 名称（内置推荐或用户自建）
    skill: str | None = None


class ContractReviewState(BaseModel):
    """LangGraph 全局状态（ADR-001 §3.6 的最小实现）。

    阶段 3 第 1 步尚未包含 LLM 相关字段（extractions/explanations），
    后续节点加入时按 ADR 追加，不改变已有字段语义。
    """

    model_config = ConfigDict(extra="forbid")

    # 版本与标识
    schema_version: int = 1
    review_id: str
    source_filename: str
    source_sha256: str = ""
    media_type: Literal["pdf", "docx", "text"] = "text"
    # 本地/上传暂存路径；只用于读文件，不写入报告
    source_path: str | None = None

    # ingest / segment
    pages: list[Page] = Field(default_factory=list)
    raw_text: str = ""
    warnings: list[str] = Field(default_factory=list)
    clauses: list[Clause] = Field(default_factory=list)
    #: 文档类型闸门结果（是不是合同）；None 表示尚未判定
    document_check: DocumentCheck | None = None

    # LLM 抽取（`extract_fields`）+ Python 校验（`validate_extraction`）
    extraction_status: Literal["ok", "degraded", "skipped"] = "skipped"
    extractions: list[ClauseExtraction] = Field(default_factory=list)
    # 校验后的合同级事实（只包含引文已定位的字段）
    facts: dict[str, str | int | float | None] = Field(default_factory=dict)
    fact_evidence: dict[str, Evidence] = Field(default_factory=dict)
    to_verify: list[ToVerifyItem] = Field(default_factory=list)
    extraction_model: str | None = None
    prompt_version: str = "n/a"

    # 规则（唯一等级来源）
    rule_evaluations: list[RuleEvaluation] = Field(default_factory=list)
    overall_level: OverallLevel = "unknown"

    # 用户审查重点（ADR-013）：只作为解释背景，任何节点都不得据此调用判级
    focus: str = ""
    skill_id: str | None = None
    skill_name: str | None = None

    # HITL
    status: ReviewStatus = "running"
    hitl: HitlDecision | None = None

    # 解释与报告
    explanation_status: Literal["ok", "fallback", "skipped"] = "skipped"
    explanations: list[ExplanationResult] = Field(default_factory=list)
    explanation_model: str | None = None
    explanation_prompt_version: str = "n/a"
    report: ReviewReport | None = None

    # 可观测性
    degraded_steps: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    timings: dict[str, float] = Field(default_factory=dict)


def format_citation(filename: str, evidence: Evidence) -> str:
    """`文件名:p页:start-end`（ADR-005 §3.4）；无法定位时返回“无原文证据”。"""
    if not evidence.grounded or evidence.start is None or evidence.end is None:
        return "无原文证据"
    page = evidence.page if evidence.page is not None else 1
    return f"{filename}:p{page}:{evidence.start}-{evidence.end}"
