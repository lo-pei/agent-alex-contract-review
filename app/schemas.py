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
]


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


class HitlDecision(BaseModel):
    """人工审批决定（ADR-002）。超时绝不映射为 approve。"""

    model_config = ConfigDict(extra="forbid")

    action: Literal["approve", "request_changes", "reject", "timeout"]
    reviewer: str = Field(min_length=1, max_length=64)
    comment: str | None = Field(default=None, max_length=2000)
    overrides: dict[str, str] = Field(default_factory=dict)


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
    explanation_grounded: bool = False
    is_system_finding: bool = False


class ReviewReport(BaseModel):
    """对外输出报告（阶段 3 第 1 步只包含规则结果，无 LLM 解释）。"""

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

    # LLM 抽取（阶段 3 后续步骤实现）
    extraction_status: Literal["ok", "degraded", "skipped"] = "skipped"
    to_verify: list[ToVerifyItem] = Field(default_factory=list)

    # 规则（唯一等级来源）
    rule_evaluations: list[RuleEvaluation] = Field(default_factory=list)
    overall_level: OverallLevel = "unknown"

    # HITL
    status: ReviewStatus = "running"
    hitl: HitlDecision | None = None

    # 解释与报告
    explanation_status: Literal["ok", "fallback", "skipped"] = "skipped"
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
