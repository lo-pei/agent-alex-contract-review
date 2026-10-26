"""LangGraph 图组装（ADR-001）。

角色：把 ingest → segment → rules → report 串成确定性顺序主干；HITL 条件边在下一阶段加入。
依赖：`app/nodes/*`、`app/schemas.py`。
用法：
    graph = build_graph()
    state = graph.invoke(initial_state, config={"configurable": {"thread_id": review_id}})
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.nodes.ingest import ingest_document
from app.nodes.report import build_report
from app.nodes.rules import evaluate_rules_node
from app.nodes.segment import segment_clauses
from app.schemas import ContractReviewState


def build_graph(checkpointer: object | None = None):
    """编译最小图。传 `InMemorySaver` 可用于测试/演示；生产用 `AsyncSqliteSaver`（下一阶段）。"""
    builder = StateGraph(ContractReviewState)

    builder.add_node("ingest_document", ingest_document)
    builder.add_node("segment_clauses", segment_clauses)
    builder.add_node("evaluate_rules", evaluate_rules_node)
    builder.add_node("build_report", build_report)

    builder.add_edge(START, "ingest_document")
    builder.add_edge("ingest_document", "segment_clauses")
    builder.add_edge("segment_clauses", "evaluate_rules")
    builder.add_edge("evaluate_rules", "build_report")
    builder.add_edge("build_report", END)

    return builder.compile(checkpointer=checkpointer)
