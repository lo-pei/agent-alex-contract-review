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


def build_graph(checkpointer: object | None = None):
    """编译图。HITL 必需 checkpointer：传 `InMemorySaver`（测试）或 `SqliteSaver`（运行）。"""
    if checkpointer is None:
        raise ValueError(
            "human_review 使用 interrupt()，编译图必须注入 checkpointer；"
            "测试用 app.services.checkpointer.memory_checkpointer()，运行用 sqlite_checkpointer()。"
        )

    builder = StateGraph(ContractReviewState)

    builder.add_node("ingest_document", ingest_document)
    builder.add_node("precheck_document", precheck_document)
    builder.add_node("segment_clauses", segment_clauses)
    builder.add_node("extract_fields", extract_fields)
    builder.add_node("validate_extraction", validate_extraction)
    builder.add_node("expert_payment", expert_payment)
    builder.add_node("expert_delivery", expert_delivery)
    builder.add_node("expert_dispute", expert_dispute)
    builder.add_node("collect_expert_findings", collect_expert_findings)
    builder.add_node("evaluate_rules", evaluate_rules_node)
    builder.add_node("research_tools", research_tools)
    builder.add_node("human_review", human_review)
    builder.add_node("explain_risks", explain_risks)
    builder.add_node("build_report", build_report)

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

