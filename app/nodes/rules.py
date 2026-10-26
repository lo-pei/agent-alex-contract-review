"""`evaluate_rules` 节点：调用规则引擎，产出唯一风险等级。

角色：图的第三站，**等级唯一来源**（ADR-003）。
依赖：`app/rules/engine.py`、`app/schemas.py`。
约束：
- 输入为空/文件失败 → 不跑规则，`overall_level="unknown"`；
- 规则文件加载失败 → 直接抛异常（启动期配置错误，不允许零规则出报告）；
- 单条规则异常 → 引擎内 fail-closed 成系统 red，节点不吞掉。
"""

from __future__ import annotations

from functools import lru_cache
from time import perf_counter

from app.rules.engine import RuleDefinition, evaluate_rules, load_rules, overall_level
from app.schemas import ContractReviewState


@lru_cache(maxsize=1)
def get_rules() -> tuple[RuleDefinition, ...]:
    """规则只加载一次；加载失败直接抛出，让问题在启动/首次运行暴露。"""
    return tuple(load_rules())


def evaluate_rules_node(state: ContractReviewState) -> dict:
    started = perf_counter()

    def finish(**updates: object) -> dict:
        return {
            **updates,
            "timings": {
                **state.timings,
                "evaluate_rules_ms": round((perf_counter() - started) * 1000, 2),
            },
        }

    if state.status == "failed" or not state.raw_text.strip():
        return finish(rule_evaluations=[], overall_level="unknown")

    rules = list(get_rules())
    evaluations = evaluate_rules(rules, state.clauses, state.raw_text, facts={})
    level = overall_level(evaluations)

    degraded = list(state.degraded_steps)
    if any(e.is_system_finding for e in evaluations):
        degraded.append("evaluate_rules:rule_execution_error")

    return finish(
        rule_evaluations=evaluations,
        overall_level=level,
        degraded_steps=degraded,
    )
