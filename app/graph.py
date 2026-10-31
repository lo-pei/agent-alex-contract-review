"""LangGraph 图组装（ADR-001、ADR-002、ADR-003、ADR-012、ADR-015）。

角色：确定性主干 + 可选的专家并行分支 / 工具检索
`ingest → precheck（是不是合同）→ segment → extract → validate
 → [专家并行：付款 / 交付 / 争议] → rules → (research_tools)?
 → (human_review)? → explain_risks → report`。
依赖：`app/nodes/*`、`app/schemas.py`。
约束：
- `precheck_document` 用确定性规则判断上传对象是不是合同；不是合同就**不进入判级**，
  直接生成“未执行审查”的报告（论文/法规不会被当成合同审查）；
- `extract`/`explain` 是“可降级站”：未配置 LLM 时抽取降级、解释回退规则理由，图不中断；
- `human_review` 用 `interrupt()` 真暂停，因此**编译时必须注入 checkpointer**（缺失直接报错，
  不允许静默退化成伪 HITL）；
- 条件边只看规则等级与人工决定：任一 red 才进人工确认；只有 approve 才做 LLM 解释；
- 专家分支与工具节点默认关闭（`AGENTS_ENABLED` / `TOOLS_ENABLED`），关闭时拓扑等价于
  原来的确定性主干；专家并行只通过带 reducer 的字段回传（ADR-015）。
用法：
    graph = build_graph(checkpointer=memory_checkpointer())
    state = graph.invoke(initial_state, config={"configurable": {"thread_id": review_id}})
    # 暂停后
    state = graph.invoke(Command(resume=decision.model_dump()), config)
"""

from __future__ import annotations

from typing import Any

from langgraph.errors import GraphBubbleUp
from langgraph.graph import END, START, StateGraph

from app.nodes.experts import (
    collect_expert_findings,
    expert_delivery,
    expert_dispute,
    expert_payment,
    route_experts,
)
from app.nodes.explain import explain_risks
from app.nodes.extract import extract_fields
from app.nodes.hitl import human_review, route_after_human_review, route_by_risk
from app.nodes.ingest import ingest_document
from app.nodes.precheck import precheck_document, route_after_precheck
from app.nodes.report import build_report
from app.nodes.research import research_tools
from app.nodes.rules import evaluate_rules_node
from app.nodes.segment import segment_clauses
from app.nodes.validate import validate_extraction
from app.schemas import ContractReviewState
from app.services.progress import progress_store

_EXPERT_LABELS = {True: "已给出参考意见", False: "未启用"}


def _summary_of_node(node: str, updates: object) -> str:
    """把节点返回的更新摘成一句人话（只复述数量/状态，不推断风险）。"""
    data = updates if isinstance(updates, dict) else {}
    if node == "ingest_document":
        if data.get("status") == "failed":
            return "文件读取失败"
        pages = data.get("pages") or []
        text = data.get("raw_text") or ""
        return f"{len(pages)} 页 · {len(text)} 字符"
    if node == "precheck_document":
        check = data.get("document_check")
        if check is None:
            return "解析已失败，跳过类型判断"
        return (
            "判定为合同，继续审查"
            if getattr(check, "is_contract", False)
            else "判定不是合同，已停止判级"
        )
    if node == "segment_clauses":
        return f"切成 {len(data.get('clauses') or [])} 条"
    if node == "extract_fields":
        return {
            "ok": "抽取完成",
            "degraded": "已降级（字段规则将跳过）",
            "skipped": "未执行",
        }.get(data.get("extraction_status", ""), "")
    if node == "validate_extraction":
        return {
            "ok": "引文定位通过",
            "degraded": "引文未能定位，已降级",
            "skipped": "未执行",
        }.get(data.get("extraction_status", ""), "")
    if node.startswith("expert_") or node == "collect_expert_findings":
        return _EXPERT_LABELS.get(
            data.get("expert_status") == "ok",
            str(data.get("expert_status") or ""),
        )
    if node == "evaluate_rules":
        evaluations = data.get("rule_evaluations") or []
        red = sum(
            1
            for item in evaluations
            if getattr(item, "risk_level", "") == "red"
            and not getattr(item, "is_system_finding", False)
        )
        yellow = sum(
            1
            for item in evaluations
            if getattr(item, "risk_level", "") == "yellow"
            and not getattr(item, "skipped", False)
        )
        return f"命中红色 {red} 条 · 黄色 {yellow} 条"
    if node == "research_tools":
        calls = data.get("tool_calls") or []
        return f"工具调用 {len(calls)} 次" if calls else "未调用工具"
    if node == "human_review":
        return "已收到人工决定"
    if node == "explain_risks":
        return {
            "ok": "解释生成完成",
            "fallback": "解释回退为规则理由",
            "skipped": "无风险需要解释",
        }.get(data.get("explanation_status", ""), "")
    if node == "build_report":
        return "报告已生成"
    return ""


def _tracked(node: str, func):
    """给节点套一层“过程记录”：开始写 running，结束写耗时与摘要。

    只写进程内事件表（`app/services/progress.py`），不改 state、不写 checkpoint，
    因此对判级、幂等与超时语义零影响。`interrupt()` 抛出的 `GraphBubbleUp`
    记为“等待”，继续向上抛给 LangGraph 处理。
    """

    def run(state: ContractReviewState) -> Any:
        review_id = getattr(state, "review_id", "")
        if not review_id and isinstance(state, dict):
            review_id = state.get("review_id", "")
        store = progress_store()
        store.begin(review_id, node)
        try:
            updates = func(state)
        except GraphBubbleUp:
            store.finish(review_id, node, status="waiting", detail="等待人工确认")
            raise
        except Exception as exc:  # noqa: BLE001 - 记下失败原因后原样抛出
            store.finish(review_id, node, status="failed", detail=type(exc).__name__)
            raise
        store.finish(review_id, node, detail=_summary_of_node(node, updates))
        return updates

    run.__name__ = node
    return run


def build_graph(checkpointer: object | None = None):
    """编译图。HITL 必需 checkpointer：传 `InMemorySaver`（测试）或 `SqliteSaver`（运行）。"""
    if checkpointer is None:
        raise ValueError(
            "human_review 使用 interrupt()，编译图必须注入 checkpointer；"
            "测试用 app.services.checkpointer.memory_checkpointer()，运行用 sqlite_checkpointer()。"
        )

    builder = StateGraph(ContractReviewState)

    builder.add_node("ingest_document", _tracked("ingest_document", ingest_document))
    builder.add_node("precheck_document", _tracked("precheck_document", precheck_document))
    builder.add_node("segment_clauses", _tracked("segment_clauses", segment_clauses))
    builder.add_node("extract_fields", _tracked("extract_fields", extract_fields))
    builder.add_node("validate_extraction", _tracked("validate_extraction", validate_extraction))
    builder.add_node("expert_payment", _tracked("expert_payment", expert_payment))
    builder.add_node("expert_delivery", _tracked("expert_delivery", expert_delivery))
    builder.add_node("expert_dispute", _tracked("expert_dispute", expert_dispute))
    builder.add_node(
        "collect_expert_findings",
        _tracked("collect_expert_findings", collect_expert_findings),
    )
    builder.add_node("evaluate_rules", _tracked("evaluate_rules", evaluate_rules_node))
    builder.add_node("research_tools", _tracked("research_tools", research_tools))
    builder.add_node("human_review", _tracked("human_review", human_review))
    builder.add_node("explain_risks", _tracked("explain_risks", explain_risks))
    builder.add_node("build_report", _tracked("build_report", build_report))

    builder.add_edge(START, "ingest_document")
    builder.add_edge("ingest_document", "precheck_document")
    builder.add_conditional_edges(
        "precheck_document",
        route_after_precheck,
        {"segment_clauses": "segment_clauses", "build_report": "build_report"},
    )
    builder.add_edge("segment_clauses", "extract_fields")
    builder.add_edge("extract_fields", "validate_extraction")
    # 专家并行：返回列表时 LangGraph 并行启动多个分支；关闭开关时直接进规则
    builder.add_conditional_edges(
        "validate_extraction",
        route_experts,
        [
            "expert_payment",
            "expert_delivery",
            "expert_dispute",
            "evaluate_rules",
        ],
    )
    builder.add_edge("expert_payment", "collect_expert_findings")
    builder.add_edge("expert_delivery", "collect_expert_findings")
    builder.add_edge("expert_dispute", "collect_expert_findings")
    builder.add_edge("collect_expert_findings", "evaluate_rules")
    builder.add_conditional_edges(
        "evaluate_rules",
        route_by_risk,
        {
            "human_review": "human_review",
            "explain_risks": "research_tools",
            "build_report": "build_report",
        },
    )
    builder.add_conditional_edges(
        "human_review",
        route_after_human_review,
        {"explain_risks": "research_tools", "build_report": "build_report"},
    )
    builder.add_edge("research_tools", "explain_risks")
    builder.add_edge("explain_risks", "build_report")
    builder.add_edge("build_report", END)

    return builder.compile(checkpointer=checkpointer)

