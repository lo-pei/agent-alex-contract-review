"""图演示入口：`python -m app.graph_demo [合同路径] [--decision ...] [--json]`。

角色：阶段 3/4 的“跑通验证”：环境、图编译、节点串联、抽取降级、规则、HITL 暂停与恢复。
依赖：`app/review_service.py`、`app/services/checkpointer.py`、`data/samples/*`。
说明：
- 默认用 SQLite checkpointer（`.data/checkpoints.sqlite`），因此暂停后可跨进程恢复；
- 红色风险会**真的暂停**并打印审批载荷；用 `--review-id` + `--decision` 恢复；
- 超时必须显式传 `--decision timeout`，不存在“自动通过”；
- 没有配置 `LLM_API_KEY` 时抽取自动降级，字段规则 skipped，这是预期的降级路径。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.graph import build_graph
from app.review_service import ReviewRun, ReviewService
from app.schemas import ContractReviewState, HitlDecision, format_citation
from app.services.checkpointer import open_checkpointer, sqlite_checkpointer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SAMPLE = PROJECT_ROOT / "data" / "samples" / "sample_sales_contract.txt"

DECISION_LABELS = {
    "approve": "approve",
    "reject": "reject",
    "changes": "request_changes",
    "request_changes": "request_changes",
    "timeout": "timeout",
}


def run_review(
    path: Path | str,
    *,
    decision: HitlDecision | None = None,
) -> ContractReviewState:
    """测试/脚本用：内存 checkpointer 跑一次，可选恢复人工决定，返回最终 state。"""
    service = ReviewService.in_memory()
    run = service.start(path)
    if run.awaiting_human and decision is not None:
        run = service.resume(run.review_id, decision)
    if run.state is None:  # pragma: no cover - 防御性，ReviewRun 始终带 state
        raise RuntimeError("审查未返回状态")
    return run.state


def _print_state(state: ContractReviewState) -> None:
    print(f"合同文件：{state.source_filename}")
    print(f"审查编号：{state.review_id}")
    print(f"条款数量：{len(state.clauses)}")
    print(f"总体等级：{state.overall_level}")
    print(f"审查状态：{state.status}")
    print(f"要素抽取：{state.extraction_status}", end="")
    if state.extraction_model:
        print(f"（模型 {state.extraction_model}，prompt {state.prompt_version}）")
    else:
        print()
    print(f"风险解释：{state.explanation_status}", end="")
    if state.explanation_model:
        print(
            f"（模型 {state.explanation_model}，prompt {state.explanation_prompt_version}）"
        )
    else:
        print()
    if state.facts:
        print("抽取字段：")
        for field, value in state.facts.items():
            evidence = state.fact_evidence.get(field)
            citation = (
                f"（{format_citation(state.source_filename, evidence)}）" if evidence else ""
            )
            print(f"  - {field}: {value!r}{citation}")
    if state.to_verify:
        print("待人工核对：")
        for item in state.to_verify:
            where = f"[{item.clause_id}] " if item.clause_id else ""
            print(f"  - {where}{item.field}: {item.reason}")
    if state.errors:
        print("错误：")
        for error in state.errors:
            print(f"  - {error}")
    if state.warnings:
        print("提示：")
        for warning in state.warnings:
            print(f"  - {warning}")
    if state.hitl:
        print(
            "人工决定："
            f"{state.hitl.action}（复核人 {state.hitl.reviewer}"
            + (f"，意见：{state.hitl.comment}" if state.hitl.comment else "")
            + "）"
        )
    report = state.report
    if report:
        print(f"摘要：{report.summary}")
        if report.findings:
            print("风险项：")
            for finding in report.findings:
                tag = "系统" if finding.is_system_finding else "合同"
                print(f"  [{finding.risk_level}][{tag}] {finding.rule_id} {finding.reason}")
                for citation in finding.citations:
                    print(f"      依据：{citation}")
                if finding.explanation_summary:
                    source = "模型" if finding.explanation_source == "llm" else "规则"
                    print(f"      解释（{source}）：{finding.explanation_summary}")
                    if finding.explanation_citation:
                        print(f"      解释依据：{finding.explanation_citation}")
                for citation in finding.knowledge_citations:
                    print(f"      知识：{citation}")
                if finding.suggestion:
                    print(f"      建议：{finding.suggestion}")
        print("规则版本：" + report.rule_engine_version)
        print(f"解释版本：{report.explanation_prompt_version}（{report.explanation_status}）")
    print(f"耗时(ms)：{state.timings}")


def _print_approval(run: ReviewRun) -> None:
    payload = run.approval
    print("\n=== 等待人工确认（图已暂停，未生成报告） ===")
    if payload is None:  # pragma: no cover - 暂停时必有载荷
        print("（未取到审批载荷）")
        return
    print(f"红色风险：{payload.findings_total} 条（展示 {len(payload.findings)} 条）")
    for finding in payload.findings:
        tag = "系统" if finding.is_system_finding else "合同"
        print(f"  [{tag}] {finding.rule_id} {finding.title}")
        print(f"      理由：{finding.reason}")
        if finding.suggestion:
            print(f"      建议：{finding.suggestion}")
        for citation in finding.citations:
            print(f"      依据：{citation}")
        for quote in finding.quotes[:1]:
            print(f"      原文：{quote}")
    if payload.to_verify:
        print("待核对：" + "；".join(payload.to_verify[:5]))
    print(f"\n{payload.instructions}")
    print(
        "恢复命令：python -m app.graph_demo "
        f"--review-id {run.review_id} --decision approve|reject|changes|timeout"
    )
    print(f"本次审查编号：{run.review_id}")


def _parse_decision(args: argparse.Namespace) -> HitlDecision:
    action = DECISION_LABELS[args.decision]
    return HitlDecision(
        action=action,
        reviewer=args.reviewer,
        comment=args.comment,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="运行合同审查图（含 HITL 真暂停）")
    parser.add_argument("contract", nargs="?", default=str(DEFAULT_SAMPLE), help="合同文件路径")
    parser.add_argument("--json", action="store_true", help="输出 ReviewRun JSON")
    parser.add_argument("--review-id", help="恢复已有审查（与 --decision 一起用）")
    parser.add_argument(
        "--decision",
        choices=sorted(DECISION_LABELS),
        help="人工决定：approve / reject / changes / timeout",
    )
    parser.add_argument("--reviewer", default="cli-reviewer", help="复核人标识")
    parser.add_argument("--comment", default=None, help="复核意见")
    parser.add_argument(
        "--memory",
        action="store_true",
        help="使用内存 checkpointer（暂停后无法跨进程恢复，仅用于快速演示）",
    )
    args = parser.parse_args(argv)

    if args.decision and not args.review_id:
        parser.error("--decision 需要与 --review-id 一起使用（先运行一次拿到审查编号）")

    context = open_checkpointer("memory") if args.memory else sqlite_checkpointer()
    with context as saver:
        service = ReviewService(build_graph(checkpointer=saver))
        if args.decision:
            run = service.resume(args.review_id, _parse_decision(args))
        else:
            run = service.start(args.contract)

    if args.json:
        print(json.dumps(run.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 0 if run.status != "failed" else 1

    if run.state is not None:
        _print_state(run.state)
    if run.awaiting_human:
        _print_approval(run)
        return 0
    return 0 if run.status != "failed" else 1


if __name__ == "__main__":
    sys.exit(main())
