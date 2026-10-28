"""`research_tools` 节点：受控工具调用（ADR-015）。

角色：`evaluate_rules`（或人工确认）之后、`explain_risks` 之前的**一次**规划 + 执行。
依赖：`app/services/tools.py`、`app/services/llm.py`、`app/schemas.py`。
约束：
- 只有 `TOOLS_ENABLED=true` 才执行；关闭时是**零副作用**空节点，图行为与原来一致；
- 规划只调用 LLM 1 次；执行次数 ≤ `MAX_TOOL_CALLS`（默认 3）；
- 工具只能从注册表里选（本地 4 个 + 可选 MCP）；未注册的名字只记录不执行；
- 工具结果只给“解释”用，不参与判级、不改等级；
- 任何失败（模型不可用、工具异常、MCP 配置错误）都降级成 warning + 轨迹，不中断审查。
"""

from __future__ import annotations

import json
from time import perf_counter

from app.config import settings
from app.schemas import (
    ContractReviewState,
    RuleEvaluation,
    ToolCallRecord,
    ToolPlan,
    ToolRequest,
)
from app.services.llm import LLMNotConfigured, call_structured, get_llm
from app.services.tools import ToolError, ToolRegistry, ToolSpec, build_tool_registry

TOOL_PROMPT_VERSION = "tools-v1"

#: 只对“有风险要解释”的审查做工具检索（干净合同没有可解释对象）
MAX_FINDINGS_IN_PROMPT = 6
MAX_RULE_REASON_CHARS = 160

SYSTEM_PROMPT = """你是合同审查的检索规划器。你只决定“要不要查资料、查什么”，不判断风险、不写结论。

可用工具：
{tools}

必须遵守：
1. 只有确实需要更多信息时才调用工具，最多 3 次；不需要就返回空列表。
2. tool 必须是上面列出的工具名，不得编造。
3. 单个参数的工具用 argument 传参（例如 search_knowledge 传检索词、
   find_clause 传关键词、read_field 传字段名）；多参数工具用 JSON 字符串。
4. 不要调用会修改数据的工具（本系统只有只读工具）。
5. 严格按 schema 输出，不要输出其他字段。
"""

USER_PROMPT_TEMPLATE = """合同文件名：{filename}
规则命中（等级由 Python 规则确定，只读）：
{findings}

用户审查重点（只影响检索方向，不得改变等级）：
<untrusted_focus>
{focus}
</untrusted_focus>

请决定需要调用哪些工具；不需要就返回空的 calls。"""

NO_FOCUS = "（用户没有指定额外审查重点）"


def _explanations(state: ContractReviewState) -> list[RuleEvaluation]:
    return [
        evaluation
        for evaluation in state.rule_evaluations
        if evaluation.risk_level in ("red", "yellow") and not evaluation.skipped
    ][:MAX_FINDINGS_IN_PROMPT]


def _findings_block(state: ContractReviewState) -> str:
    found = _explanations(state)
    if not found:
        return "（没有 red/yellow 规则命中）"
    return "\n".join(
        f"- {evaluation.rule_id} [{evaluation.risk_level}] {evaluation.title}："
        f"{evaluation.reason[:MAX_RULE_REASON_CHARS]}"
        for evaluation in found
    )


def _sanitize(text: str) -> str:
    return text.replace("<untrusted_focus>", "&lt;untrusted_focus&gt;").replace(
        "</untrusted_focus>", "&lt;/untrusted_focus&gt;"
    )


def _spec_map(registry: ToolRegistry) -> dict[str, ToolSpec]:
    return {spec.name: spec for spec in registry.specs()}


def _arguments_for(spec: ToolSpec, request: ToolRequest) -> dict[str, object]:
    """把 LLM 的单参数/JSON 入参转成工具需要的 kwargs。"""
    raw = (request.argument or "").strip()
    if not spec.arguments:
        return {}
    if len(spec.arguments) == 1:
        return {spec.arguments[0]: raw}
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {spec.arguments[0]: raw}
    if not isinstance(payload, dict):
        return {spec.arguments[0]: raw}
    return {key: value for key, value in payload.items() if key in spec.arguments}


def research_tools(state: ContractReviewState) -> dict:
    started = perf_counter()

    def finish(**updates: object) -> dict:
        return {
            **updates,
            "timings": {
                **state.timings,
                "research_tools_ms": round((perf_counter() - started) * 1000, 2),
            },
        }

    if not settings.tools_enabled:
        return finish()
    if state.status not in ("running", "approved"):
        return finish()
    if not _explanations(state):
        return finish(tool_calls=[])

    warnings: list[str] = list(state.warnings)
    degraded: list[str] = list(state.degraded_steps)

    registry: ToolRegistry | None = None
    try:
        registry = build_tool_registry(
            state,
            mcp_servers=settings.mcp_servers,
            timeout_seconds=settings.mcp_timeout_seconds,
        )
    except ToolError as exc:
        degraded.append("research_tools:config_error")
        warnings.append(f"工具未启用：{exc}")
        return finish(tool_calls=[], degraded_steps=degraded, warnings=warnings)

    try:
        try:
            llm = get_llm()
        except LLMNotConfigured:
            # 没有大模型也能演示“工具调用”：按规则主题词发起确定性检索
            plan = _fallback_plan(state, registry)
            degraded.append("research_tools:deterministic_plan")
            warnings.append(
                "未配置大模型，工具检索改为按规则主题词自动发起（不是模型规划的）。"
            )
        else:
            plan = _plan(llm, registry, state)
        records = _execute(registry, plan)
    finally:
        registry.close()

    if records:
        failed = sum(1 for record in records if not record.ok)
        if failed:
            degraded.append("research_tools:tool_failed")
            warnings.append(f"{failed}/{len(records)} 次工具调用失败，已忽略其结果。")

    return finish(
        tool_calls=records,
        degraded_steps=degraded,
        warnings=warnings,
    )


def _plan(llm, registry: ToolRegistry, state: ContractReviewState) -> ToolPlan:
    try:
        plan, _attempts = call_structured(
            llm,
            ToolPlan,
            system=SYSTEM_PROMPT.format(tools=registry.describe()),
            user=USER_PROMPT_TEMPLATE.format(
                filename=state.source_filename,
                findings=_findings_block(state),
                focus=_sanitize(state.focus.strip()) if state.focus.strip() else NO_FOCUS,
            ),
        )
        return plan
    except Exception:  # noqa: BLE001 - 规划失败等于“不调用工具”
        return ToolPlan()


def _fallback_plan(state: ContractReviewState, registry: ToolRegistry) -> ToolPlan:
    """确定性回退：用第一条 red/yellow 的规则标题当检索词，最多 2 次调用。"""
    available = set(registry.names)
    topic = _explanations(state)[0].title[:40]
    wanted: list[ToolRequest] = []
    if settings.rag_enabled and "search_knowledge" in available:
        wanted.append(ToolRequest(tool="search_knowledge", argument=topic))
    if "find_clause" in available:
        wanted.append(ToolRequest(tool="find_clause", argument=topic))
    return ToolPlan(calls=wanted, reason="deterministic-fallback")


def _execute(registry: ToolRegistry, plan: ToolPlan) -> list[ToolCallRecord]:
    specs = _spec_map(registry)
    records: list[ToolCallRecord] = []
    limit = max(0, min(settings.max_tool_calls, 3))
    for request in plan.calls[:limit]:
        spec = specs.get(request.tool)
        if spec is None:
            records.append(
                ToolCallRecord(
                    name=request.tool,
                    ok=False,
                    arguments={"argument": request.argument},
                    error="未注册的工具（白名单外，不执行）",
                )
            )
            continue
        records.append(registry.call(spec.name, _arguments_for(spec, request)))
    return records
