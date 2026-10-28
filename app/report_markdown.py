"""把 `ReviewReport` 渲染成 Markdown（API/UI 下载用）。

角色：对外交付的可读报告；内容完全来自 `ReviewReport`，不新增任何判断。
依赖：`app/schemas.py`。
约束：
- 不重算风险等级，也不改写摘要/限制；
- 所有文本做 Markdown 转义（表格单元格、正文换行），避免合同原文破坏排版；
- 解释缺失时明确写“未提供”，不伪装成已解释。
"""

from __future__ import annotations

from app.schemas import ReviewReport

LEVEL_LABELS = {
    "red": "红色",
    "yellow": "黄色",
    "pass": "通过",
    "unknown": "未知",
}

STATUS_LABELS = {
    "approved": "已人工确认（approve）",
    "rejected": "已拒绝（reject）",
    "changes_requested": "要求修改（request_changes）",
    "unreviewed_red_risk": "未获人工确认（超时/无效决策）",
    "completed": "审查完成",
    "failed": "审查失败",
    "not_contract": "未执行审查（不是合同）",
    "running": "审查中（等待人工确认）",
}

EXPLANATION_LABELS = {
    "ok": "模型解释（已通过质量门）",
    "fallback": "规则理由兜底（模型不可用或未通过质量门）",
    "skipped": "未执行解释",
}

ACTION_LABELS = {
    "approve": "批准",
    "reject": "拒绝",
    "request_changes": "要求修改",
    "timeout": "超时未确认",
}

SOURCE_LABELS = {"llm": "模型", "rule": "规则", "none": "未提供"}


def _text(value: object) -> str:
    """正文转义：折叠换行，避免列表/引用结构被合同原文打断。"""
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def _cell(value: object) -> str:
    return _text(value).replace("|", "\\|")


def _level(report: ReviewReport) -> str:
    return LEVEL_LABELS.get(report.overall_level, report.overall_level)


def _finding_lines(index: int, finding) -> list[str]:
    tag = "系统" if finding.is_system_finding else "合同"
    title = LEVEL_LABELS.get(finding.risk_level, finding.risk_level)
    lines = [
        f"### {index}. [{title}][{tag}] {finding.rule_id}",
        "",
        f"- 理由：{_text(finding.reason)}",
    ]
    if finding.clause_ids:
        lines.append(f"- 相关条款：{', '.join(finding.clause_ids)}")
    if finding.citations:
        lines.append("- 原文依据：" + "；".join(f"`{citation}`" for citation in finding.citations))
    if finding.explanation_summary:
        source = SOURCE_LABELS.get(finding.explanation_source, finding.explanation_source)
        grounded = "已定位" if finding.explanation_grounded else "未定位"
        lines.append(f"- 解释（{source}，引文{grounded}）：{_text(finding.explanation_summary)}")
        if finding.explanation_quote:
            lines.append(f"  - 原文摘录：{_text(finding.explanation_quote)}")
        if finding.explanation_citation:
            lines.append(f"  - 解释依据：`{finding.explanation_citation}`")
    else:
        lines.append("- 解释：未提供（未执行解释或该风险无需解释）")
    if finding.knowledge_citations:
        lines.append(
            "- 知识引用：" + "；".join(f"`{item}`" for item in finding.knowledge_citations)
        )
    if finding.suggestion:
        lines.append(f"- 建议：{_text(finding.suggestion)}")
    lines.append("")
    return lines


def _expert_lines(report: ReviewReport) -> list[str]:
    """专家参考意见：只作补充材料，明写不参与判级（ADR-015）。"""
    lines = [
        "## 专家参考意见（不参与判级）",
        "",
        "> 由付款 / 交付 / 争议三个专家并行给出，只作补充参考；"
        "风险等级仍只由 Python 规则判定，专家意见不改变上方任何一条等级。",
        "",
    ]
    if not report.expert_findings:
        lines.extend(
            ["本次未产生可用的专家意见（未启用专家，或模型不可用 / 引文未能在原文定位）。", ""]
        )
        return lines
    for index, finding in enumerate(report.expert_findings, start=1):
        title = finding.expert_title or finding.expert
        where = f"[{finding.clause_title or finding.clause_id}] " if (
            finding.clause_title or finding.clause_id
        ) else ""
        lines.append(f"### {index}. {_text(title)} · {_text(finding.topic)}")
        lines.append("")
        lines.append(f"- 条款：{where or '全合同'}（专家 `{finding.expert}`）")
        lines.append(f"- 说明：{_text(finding.detail)}")
        if finding.quote:
            lines.append(f"- 原文摘录：{_text(finding.quote)}")
        if finding.citation:
            lines.append(f"- 位置：`{finding.citation}`")
        if not finding.grounded:
            lines.append("- 定位：引文未能在原文唯一定位，仅供人工核对")
        if finding.suggestion:
            lines.append(f"- 建议：{_text(finding.suggestion)}")
        lines.append("")
    return lines


def _tool_lines(report: ReviewReport) -> list[str]:
    """工具调用轨迹：成败、参数、摘要、引用都留痕（ADR-015）。"""
    lines = ["## 工具调用记录", ""]
    if not report.tool_calls:
        lines.extend(["本次未调用工具（未启用工具层）。", ""])
        return lines
    lines.extend(
        [
            "| # | 工具 | 结果 | 耗时 | 参数 | 摘要 / 错误 | 引用 |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for index, call in enumerate(report.tool_calls, start=1):
        name = call.title or call.name
        result = "成功" if call.ok else "失败"
        arguments = (
            "；".join(f"{key}={_cell(value)}" for key, value in call.arguments.items()) or "—"
        )
        detail = _cell(call.error or call.summary) or "—"
        citations = "；".join(f"`{item}`" for item in call.citations) or "—"
        lines.append(
            f"| {index} | {_cell(name)} `{_cell(call.name)}` | {result} | "
            f"{call.elapsed_ms:.0f} ms | {arguments} | {detail} | {citations} |"
        )
    lines.append("")
    return lines


def render_report_markdown(report: ReviewReport) -> str:
    """生成完整 Markdown 报告（UTF-8 文本）。"""
    lines: list[str] = [
        f"# 合同审查报告 · {_text(report.source_filename)}",
        "",
        f"- 审查编号：`{report.review_id}`",
        f"- 生成时间：{report.generated_at.isoformat()}",
        f"- 总体等级：**{_level(report)}**（仅由 Python 规则判定）",
        f"- 审查状态：{STATUS_LABELS.get(report.status, report.status)}",
        f"- 风险条数：红色 {sum(1 for f in report.findings if f.risk_level == 'red')} 条，"
        f"黄色 {sum(1 for f in report.findings if f.risk_level == 'yellow')} 条",
        f"- 风险解释："
        f"{EXPLANATION_LABELS.get(report.explanation_status, report.explanation_status)}",
        "",
        "## 摘要",
        "",
        _text(report.summary) or "（无摘要）",
        "",
        "## 风险清单",
        "",
    ]

    if report.findings:
        for index, finding in enumerate(report.findings, start=1):
            lines.extend(_finding_lines(index, finding))
    else:
        lines.extend(["未命中任何风险规则（不代表合同没有风险，见文末限制）。", ""])

    lines.extend(_expert_lines(report))
    lines.extend(_tool_lines(report))

    lines.extend(["## 抽取要素", ""])
    if report.extracted_fields:
        lines.extend(["| 字段 | 值 |", "| --- | --- |"])
        for field, value in report.extracted_fields.items():
            lines.append(f"| {_cell(field)} | {_cell(value) if value is not None else '（空）'} |")
    else:
        lines.append("本次未得到可用的抽取字段（模型未配置、降级或合同无可抽取条款）。")
    lines.append("")

    lines.extend(["## 待人工核对", ""])
    if report.to_verify:
        for item in report.to_verify:
            where = f"[{item.clause_id}] " if item.clause_id else ""
            lines.append(f"- {where}{_text(item.field)}：{_text(item.reason)}")
    else:
        lines.append("无。")
    lines.append("")

    lines.extend(["## 人工复核", ""])
    if report.hitl is None:
        lines.append("本次无需人工确认，或尚未提交人工决定。")
    else:
        action = ACTION_LABELS.get(report.hitl.action, report.hitl.action)
        lines.append(f"- 决定：{action}")
        lines.append(f"- 复核人：{_text(report.hitl.reviewer)}")
        if report.hitl.comment:
            lines.append(f"- 意见：{_text(report.hitl.comment)}")
        if report.hitl.overrides:
            overrides = "；".join(
                f"`{key}` → {_text(value)}" for key, value in report.hitl.overrides.items()
            )
            lines.append(f"- 字段覆盖：{overrides}")
        lines.append("")
        lines.append("人工决定只记录复核结论，不改写规则判定的风险等级。")
    lines.append("")

    lines.extend(["## 限制与免责", ""])
    for limitation in report.limitations:
        lines.append(f"- {_text(limitation)}")
    lines.append("")

    lines.extend(
        [
            "## 版本信息",
            "",
            f"- 规则引擎：`{report.rule_engine_version}`",
            f"- 抽取 prompt：`{report.prompt_version}`",
            f"- 抽取模型：`{report.model_id or '未使用'}`",
            f"- 解释 prompt：`{report.explanation_prompt_version}`",
            f"- 解释模型：`{report.explanation_model or '未使用'}`",
            "",
        ]
    )
    return "\n".join(lines)
