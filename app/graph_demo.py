"""最小图演示入口（无 LLM）：`python -m app.graph_demo [合同路径] [--json]`。

角色：阶段 3 第 1 步的“跑通验证”：环境、图编译、节点串联、规则引擎、报告。
依赖：`app/graph.py`、`app/schemas.py`、`data/samples/*`。
"""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver

from app.graph import build_graph
from app.schemas import ContractReviewState

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SAMPLE = PROJECT_ROOT / "data" / "samples" / "sample_sales_contract.txt"


def run_review(path: Path) -> ContractReviewState:
    graph = build_graph(checkpointer=InMemorySaver())
    initial = ContractReviewState(
        review_id=uuid.uuid4().hex,
        source_filename=path.name,
        source_path=str(path),
    )
    result = graph.invoke(
        initial.model_dump(),
        config={"configurable": {"thread_id": initial.review_id}},
    )
    return ContractReviewState.model_validate(result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="运行最小合同审查图（无 LLM）")
    parser.add_argument("contract", nargs="?", default=str(DEFAULT_SAMPLE), help="合同文件路径")
    parser.add_argument("--json", action="store_true", help="只输出报告 JSON")
    args = parser.parse_args(argv)

    path = Path(args.contract)
    state = run_review(path)
    report = state.report

    if args.json:
        payload = report.model_dump(mode="json") if report else {}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if state.status != "failed" else 1

    print(f"合同文件：{state.source_filename}")
    print(f"审查编号：{state.review_id}")
    print(f"条款数量：{len(state.clauses)}")
    print(f"总体等级：{state.overall_level}")
    print(f"审查状态：{state.status}")
    if state.errors:
        print("错误：")
        for error in state.errors:
            print(f"  - {error}")
    if state.warnings:
        print("提示：")
        for warning in state.warnings:
            print(f"  - {warning}")
    if report:
        print(f"摘要：{report.summary}")
        if report.findings:
            print("风险项：")
            for finding in report.findings:
                tag = "系统" if finding.is_system_finding else "合同"
                print(f"  [{finding.risk_level}][{tag}] {finding.rule_id} {finding.reason}")
                for citation in finding.citations:
                    print(f"      依据：{citation}")
                if finding.suggestion:
                    print(f"      建议：{finding.suggestion}")
        print("规则版本：" + report.rule_engine_version)
    print(f"耗时(ms)：{state.timings}")
    return 0 if state.status != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
