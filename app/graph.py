"""LangGraph 图组装（ADR-001）。

角色：把 ingest → segment → extract → validate → rules → report 串成确定性顺序主干；
HITL 条件边在下一阶段加入。
依赖：`app/nodes/*`、`app/schemas.py`。
约束：`extract`/`validate` 是“可降级站”，不是必需站——未配置 LLM 时抽取降级为
`extraction_status="degraded"`，字段规则跳过，文本规则照常执行，图不中断。
用法：
    graph = build_graph()
    state = graph.invoke(initial_state, config={"configurable": {"thread_id": review_id}})
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.nodes.extract import extract_fields
from app.nodes.ingest import ingest_document
from app.nodes.report import build_report
from app.nodes.rules import evaluate_rules_node
from app.nodes.segment import segment_clauses
from app.nodes.validate import validate_extraction
from app.schemas import ContractReviewState


def build_graph(checkpointer: object | None = None):
    """编译图。传 `InMemorySaver` 可用于测试/演示；生产用 `AsyncSqliteSaver`（下一阶段）。"""
    builder = StateGraph(ContractReviewState)

    builder.add_node("ingest_document", ingest_document)
    builder.add_node("segment_clauses", segment_clauses)
    builder.add_node("extract_fields", extract_fields)
    builder.add_node("validate_extraction", validate_extraction)
    builder.add_node("evaluate_rules", evaluate_rules_node)
    builder.add_node("build_report", build_report)

    builder.add_edge(START, "ingest_document")
    builder.add_edge("ingest_document", "segment_clauses")
    builder.add_edge("segment_clauses", "extract_fields")
    builder.add_edge("extract_fields", "validate_extraction")
    builder.add_edge("validate_extraction", "evaluate_rules")
    builder.add_edge("evaluate_rules", "build_report")
    builder.add_edge("build_report", END)

    return builder.compile(checkpointer=checkpointer)
