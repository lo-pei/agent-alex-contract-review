"""逐条审查视图：把规则结果按条款聚合，并给出“修改后的条款”示例。

角色：`GET /api/reviews/{id}/clauses` 的组装层，供前端左右分屏逐条展示与一键更正。
约束：
- **不重新判级**：`risk_level` 直接沿用 `RuleEvaluation`（red/yellow），未命中的条款为 `pass`；
- 修订文本是**示例条款**，带 `___` 占位，前端必须标注“请按实际交易填写”，不能伪装成法律意见；
- 只消费图状态中的规则结果与解释结果，不调用 LLM、不读写文件；
- 同一规则引用多条条款时，每条都展示该规则（人工仍可逐条判断）。
"""

from __future__ import annotations

import re

from app.config import settings
from app.nodes.experts import EXPERT_ORDER
from app.schemas import (
    AgentTrace,
    ClauseFinding,
    ClauseReview,
    ClauseReviewList,
    ContractReviewState,
    ExpertFinding,
    ExplanationResult,
    RuleEvaluation,
)

#: 每条规则对应的“修改后的条款”示例；没有列出的规则只给文字建议。
REVISION_TEMPLATES: dict[str, str] = {
    "R-TRD-001": (
        "本合同采用 ___（例如 FOB Shanghai）贸易术语，适用 Incoterms® 2020；"
        "风险转移与费用划分以该版本为准。"
    ),
    "R-PAY-001": (
        "买方应于合同生效后 10 个工作日内支付合同总价的 30% 作为预付款；"
        "余款 70% 于卖方提交提单副本后 15 个工作日内以电汇（T/T）支付。"
    ),
    "R-PAY-002": (
        "买方应以电汇（T/T）支付货款：合同生效后 30 日内支付 30% 预付款，"
        "装运前凭提单副本支付余款 70%；逾期付款按年利率 ___% 计息。"
    ),
    "R-DLV-001": (
        "卖方应于 ___ 年 __ 月 __ 日前完成装运，并在装运后 3 个工作日内向买方提供"
        "提单、商业发票与装箱单。"
    ),
    "R-INP-001": (
        "买方应在装运前委托 ___（例如 SGS）按 ___（例如 ISO 2859-1）进行抽样检验，"
        "检验费用由 ___ 承担，检验证书作为付款单据之一。"
    ),
    "R-DIS-001": "本合同的订立、效力、解释与履行均适用中华人民共和国法律。",
    "R-DIS-002": (
        "因本合同引起或与本合同有关的争议，双方应友好协商；协商不成的，"
        "提交中国国际经济贸易仲裁委员会（CIETAC）按其现行仲裁规则在 ___ 仲裁，"
        "仲裁裁决为终局的，对双方均有约束力。"
    ),
    "R-DIS-003": (
        "因本合同引起的争议提交中国国际经济贸易仲裁委员会（CIETAC）按其现行仲裁规则仲裁，"
        "仲裁裁决为终局的，对双方均有约束力；任何一方不得就同一争议再向法院起诉。"
    ),
    "R-DIS-004": (
        "仲裁裁决为终局的，对双方均有约束力；任何一方不得在仲裁裁决作出后再就同一争议"
        "向法院起诉。"
    ),
    "R-INS-001": (
        "卖方应按发票金额的 110% 投保 ___（例如 Institute Cargo Clauses (A)），"
        "保险单随装运单据提交，受益人为买方。"
    ),
    "R-INC-001": (
        "双方确认以贸易术语 ___（例如 FOB Shanghai, Incoterms® 2020）作为风险与费用划分依据；"
        "主运费由 ___ 承担，与该术语不一致的约定以本条款为准。"
    ),
    "R-INC-002": (
        "整箱集装箱货物建议改用 ___（例如 FCA Shanghai, Incoterms® 2020），"
        "由卖方在集装箱堆场将货物交给承运人，风险自此转移给买方。"
    ),
    "R-INP-002": (
        "买方应在收到货物后 ___ 个工作日内完成检验并书面通知卖方；"
        "易腐货物可另行约定更短期限，但不得少于 ___ 个工作小时。"
    ),
}

#: 修订文本统一的边界说明（前端原样展示，避免把示例当结论）。
REVISION_NOTE = "示例条款：下划线处需按实际交易条件填写，签署前请专业人士复核。"


def _explanation_map(explanations: list[ExplanationResult]) -> dict[str, ExplanationResult]:
    """同一规则可能有多条解释；逐条视图只取第一条（报告里仍保留全部）。"""
    result: dict[str, ExplanationResult] = {}
    for item in explanations:
        result.setdefault(item.rule_id, item)
    return result


def _quotes(evaluation: RuleEvaluation) -> list[str]:
    seen: list[str] = []
    for evidence in evaluation.evidence:
        quote = (evidence.quote or "").strip()
        if quote and quote not in seen:
            seen.append(quote)
        if len(seen) >= 3:
            break
    return seen


def _finding(
    evaluation: RuleEvaluation,
    explanation: ExplanationResult | None,
) -> ClauseFinding:
    knowledge = list(explanation.knowledge_citations) if explanation is not None else []
    return ClauseFinding(
        rule_id=evaluation.rule_id,
        title=evaluation.title,
        # 只搬规则等级，不在这里做任何判断（ADR-003）
        risk_level="red" if evaluation.risk_level == "red" else "yellow",
        reason=evaluation.reason,
        suggestion=evaluation.suggestion,
        explanation_summary=explanation.summary if explanation is not None else None,
        explanation_quote=explanation.quote if explanation is not None else None,
        explanation_citation=explanation.citation if explanation is not None else None,
        knowledge_citations=knowledge,
        quotes=_quotes(evaluation),
    )


def _active_evaluations(state: ContractReviewState) -> list[RuleEvaluation]:
    return [
        evaluation
        for evaluation in state.rule_evaluations
        if not evaluation.skipped and evaluation.risk_level in {"red", "yellow"}
    ]


def _by_severity(findings: list[ClauseFinding]) -> list[ClauseFinding]:
    """展示顺序：红在前、黄在后（只调整顺序，不改变任何等级）。"""
    return sorted(findings, key=lambda item: 0 if item.risk_level == "red" else 1)


def _revised_text(findings: list[ClauseFinding]) -> tuple[str | None, str | None]:
    """按“红在前、黄在后”拼接示例条款；没有模板时返回 (None, None)。"""
    ordered = _by_severity(findings)
    blocks: list[str] = []
    seen_rules: set[str] = set()
    for finding in ordered:
        if finding.rule_id in seen_rules:
            continue
        template = REVISION_TEMPLATES.get(finding.rule_id)
        if not template:
            continue
        seen_rules.add(finding.rule_id)
        blocks.append(template)
    if not blocks:
        return None, None
    return "\n\n".join(blocks), REVISION_NOTE


_TITLE_NUMBER_RE = re.compile(r"^\s*(\d{1,3})\s*[.、]\s*")


def _display_title(title: str) -> str:
    """目录短标题：旧版切分存了整行标题（含冒号后的正文），展示时只留主题词。"""
    stripped = " ".join((title or "").split())
    if not stripped:
        return ""
    number = ""
    rest = stripped
    match = _TITLE_NUMBER_RE.match(stripped)
    if match:
        number = f"{match.group(1)}."
        rest = stripped[match.end() :]
    head = rest.split("：", 1)[0].split(":", 1)[0].strip()
    if head and len(head) <= 16:
        return f"{number} {head}".strip()
    return stripped


def _heading_key(title: str) -> str:
    """标题归一键：去掉编号、冒号后的正文与空白，用来识别重复标题。"""
    text = _TITLE_NUMBER_RE.sub("", (title or "").strip())
    text = text.split("：", 1)[0].split(":", 1)[0]
    return re.sub(r"\s+", "", text).casefold()


def _merge_adjacent_duplicates(clauses: list[ClauseReview]) -> list[ClauseReview]:
    """相邻且同名（去掉编号/空格后）的条款合成一条展示。

    旧版切分会把同一标题的英文译文段也切成一条，导致目录出现两个“付款条件”。
    这里只做展示层合并：文本拼接、意见合并、等级仍按原有规则结果计算。
    """
    merged: list[ClauseReview] = []
    for clause in clauses:
        previous = merged[-1] if merged else None
        if (
            previous is not None
            and not previous.is_preamble
            and not clause.is_preamble
            and _heading_key(previous.title)
            and _heading_key(previous.title) == _heading_key(clause.title)
        ):
            previous.text = (previous.text.rstrip() + "\n\n" + clause.text.lstrip()).strip()
            previous.findings = _by_severity(previous.findings + clause.findings)
            red = any(item.risk_level == "red" for item in previous.findings)
            yellow = any(item.risk_level == "yellow" for item in previous.findings)
            previous.risk_level = "red" if red else "yellow" if yellow else "pass"
            previous.revised_text, previous.revision_note = _revised_text(previous.findings)
            continue
        merged.append(clause)
    return merged


def build_clause_reviews(
    state: ContractReviewState,
    *,
    awaiting_human: bool = False,
) -> ClauseReviewList:
    """把一次审查的规则结果整理成“逐条审查”数据。

    `awaiting_human=True` 时报告还没生成，但规则结果已经可以逐条展示（审批前预览）。
    """
    explanations = _explanation_map(state.explanations)
    active = _active_evaluations(state)
    known_clause_ids = {clause.clause_id for clause in state.clauses}

    by_clause: dict[str, list[ClauseFinding]] = {}
    contract_findings: list[ClauseFinding] = []
    for evaluation in active:
        finding = _finding(evaluation, explanations.get(evaluation.rule_id))
        targets = [cid for cid in evaluation.clause_ids if cid in known_clause_ids]
        if not targets:
            contract_findings.append(finding)
            continue
        for clause_id in targets:
            by_clause.setdefault(clause_id, []).append(finding)

    clauses: list[ClauseReview] = []
    for index, clause in enumerate(state.clauses, start=1):
        findings = _by_severity(by_clause.get(clause.clause_id, []))
        red = any(item.risk_level == "red" for item in findings)
        yellow = any(item.risk_level == "yellow" for item in findings)
        level = "red" if red else "yellow" if yellow else "pass"
        revised, note = _revised_text(findings)
        # 前言单独标注：前端显示“前言”，导出也不写成“第 1 条”
        is_preamble = clause.clause_type == "preamble"
        clauses.append(
            ClauseReview(
                clause_id=clause.clause_id,
                index=index,
                title="前言" if is_preamble else _display_title(clause.title),
                text=clause.text,
                page=clause.page,
                risk_level=level,
                is_preamble=is_preamble,
                findings=findings,
                revised_text=revised,
                revision_note=note,
            )
        )

    # 旧版切分（或译文重复标题）可能留下同名的相邻条款：只在展示层合并，不改等级来源
    clauses = _merge_adjacent_duplicates(clauses)
    for position, clause in enumerate(clauses, start=1):
        clause.index = position
    revised_count = sum(1 for clause in clauses if clause.revised_text)

    contract_revised, contract_note = _revised_text(contract_findings)
    if contract_revised:
        revised_count += 1
    # 合同级问题也提供一条“建议新增条款”的修订文本，前端单独展示
    limitations = [
        "逐条审查只展示规则覆盖到的问题；修改建议是示例文本，不构成法律意见。",
        "红色风险需要人工确认后才会生成正式报告；未确认时不会改变等级。",
    ]
    if state.extraction_status != "ok":
        limitations.append("本次抽取未完全成功，依赖字段的规则可能被跳过（skipped）。")

    return ClauseReviewList(
        review_id=state.review_id,
        source_filename=state.source_filename,
        status=state.status,
        overall_level=state.overall_level,
        awaiting_human=awaiting_human,
        clauses=clauses,
        contract_text=state.raw_text,
        contract_findings=_by_severity(contract_findings),
        contract_revised_text=contract_revised,
        contract_revision_note=contract_note,
        revised_count=revised_count,
        limitations=limitations,
        agent_trace=_agent_trace(state),
    )


def _agent_trace(state: ContractReviewState) -> AgentTrace:
    """逐条审查页的 Agent 轨迹（ADR-015）；未启用专家/工具时返回空轨迹。"""
    findings: list[ExpertFinding] = []
    known = {clause.clause_id for clause in state.clauses}
    for finding in state.expert_findings:
        if finding.clause_id is not None and finding.clause_id not in known:
            continue
        findings.append(finding)
    route = [
        expert_id
        for expert_id in EXPERT_ORDER
        if expert_id in set(state.expert_route)
    ]
    return AgentTrace(
        agents_enabled=settings.agents_enabled,
        tools_enabled=settings.tools_enabled,
        experts=route,
        expert_status=state.expert_status,
        expert_notes=_expert_notes(state),
        expert_findings=findings,
        tool_calls=list(state.tool_calls),
    )


def _expert_notes(state: ContractReviewState) -> list[str]:
    """降级原因去重（并行 append 顺序不稳，同一专家也可能重复写）。"""
    notes: list[str] = []
    for note in state.expert_notes:
        if note not in notes:
            notes.append(note)
    return notes
