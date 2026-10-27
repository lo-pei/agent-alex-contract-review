"""规则引擎：加载 YAML 规则定义，对合同文本/事实求值（ADR-003 §3.3–3.6）。

角色：唯一的风险等级来源（纯 Python，无 LLM、无 I/O 以外的副作用）。
依赖：`app/rules/dsl.py`、`app/schemas.py`、`app/rules/definitions.yaml`。
约束：
- 每条规则只产生一条 `RuleEvaluation`（触发 → red/yellow，未触发 → pass）；
- 规则加载失败 → 启动失败（不允许零规则运行）；
- 单条规则执行异常 → 系统 red（`is_system_finding=True`），进入后续 HITL；
- 依赖字段缺失 → yellow + `requires_human=True`，不静默 pass。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from app.rules.dsl import Condition, MatchSpan, evaluate_condition
from app.schemas import Clause, Evidence, RuleEvaluation

RULE_ENGINE_VERSION = "0.1.0"
DEFAULT_RULES_PATH = Path(__file__).with_name("definitions.yaml")
_MAX_EVIDENCE_PER_RULE = 5


class RuleDefinition(BaseModel):
    """单条规则的 YAML 契约（ADR-003 §3.3）。"""

    model_config = ConfigDict(extra="forbid")

    rule_id: str = Field(pattern=r"^R-[A-Z]{3}-\d{3}$")
    title: str = Field(min_length=1)
    category: Literal[
        "trade_term",
        "payment",
        "delivery",
        "inspection",
        "warranty",
        "liability",
        "dispute",
        "force_majeure",
        "compliance",
        "preamble",
    ]
    risk_level: Literal["red", "yellow"]
    reason: str = Field(min_length=1)
    suggestion: str = Field(min_length=1)
    requires_fields: list[str] = Field(default_factory=list)
    #: 依赖 LLM 抽取字段；抽取不可用（未配置/失败）时跳过而不是误报
    requires_extraction: bool = False
    condition: Condition
    source: str = Field(min_length=1)
    version: str | None = None


class RuleSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    rules: list[RuleDefinition] = Field(min_length=1)


def load_rule_set(path: Path | str = DEFAULT_RULES_PATH) -> RuleSet:
    """加载并校验规则文件（含集合级 `version`）；任何问题都抛异常（不静默降级）。"""
    rules_path = Path(path)
    if not rules_path.is_file():
        raise FileNotFoundError(f"规则文件不存在：{rules_path}")
    data = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    rule_set = RuleSet.model_validate(data)
    seen: set[str] = set()
    for rule in rule_set.rules:
        if rule.rule_id in seen:
            raise ValueError(f"规则 rule_id 重复：{rule.rule_id}")
        seen.add(rule.rule_id)
    return rule_set


def load_rules(path: Path | str = DEFAULT_RULES_PATH) -> list[RuleDefinition]:
    """只取规则列表（调用方不关心集合版本时使用）。"""
    return load_rule_set(path).rules


def _evidence_from_spans(
    spans: tuple[MatchSpan, ...], clauses: list[Clause], text: str
) -> tuple[list[Evidence], list[str]]:
    evidence: list[Evidence] = []
    clause_ids: list[str] = []
    for span in spans[:_MAX_EVIDENCE_PER_RULE]:
        quote = text[span.start : span.end]
        if not quote.strip():
            continue
        clause = next((c for c in clauses if c.start <= span.start < c.end), None)
        evidence.append(
            Evidence(
                quote=quote,
                start=span.start,
                end=span.end,
                page=clause.page if clause else 1,
                clause_id=clause.clause_id if clause else None,
                grounded=clause is not None,
            )
        )
        if clause and clause.clause_id not in clause_ids:
            clause_ids.append(clause.clause_id)
    return evidence, clause_ids


def evaluate_rules(
    rules: list[RuleDefinition],
    clauses: list[Clause],
    text: str,
    facts: dict[str, Any] | None = None,
    *,
    extraction_available: bool = True,
) -> list[RuleEvaluation]:
    """执行全部规则。

    `text` 是 canonical_text（与 `Clause.start/end` 同一坐标系），用于证据偏移回填。
    `facts` 是抽取并校验后的合同级字段。
    `extraction_available=False`（未配置 LLM / 抽取失败）时，字段规则标记为 `skipped`，
    不产出黄色误报，也不静默算 pass（评测可单独统计跳过率）。
    """
    facts = facts or {}
    if not rules:
        raise ValueError("规则集为空：不允许在不执行任何规则的情况下出报告")

    evaluations: list[RuleEvaluation] = []
    for rule in rules:
        try:
            if rule.requires_extraction and not extraction_available:
                evaluations.append(
                    RuleEvaluation(
                        rule_id=rule.rule_id,
                        title=rule.title,
                        risk_level="pass",
                        reason="要素抽取不可用，该字段规则未执行（不计入 pass/触发）。",
                        suggestion=None,
                        skipped=True,
                    )
                )
                continue

            missing = [f for f in rule.requires_fields if facts.get(f) in (None, "")]
            if missing:
                evaluations.append(
                    RuleEvaluation(
                        rule_id=rule.rule_id,
                        title=rule.title,
                        risk_level="yellow",
                        reason=(f"缺少字段 {', '.join(missing)}，规则无法判定，需人工确认。"),
                        suggestion=rule.suggestion,
                        requires_human=True,
                    )
                )
                continue

            outcome = evaluate_condition(rule.condition, text, facts)
            if not outcome.triggered:
                evaluations.append(
                    RuleEvaluation(
                        rule_id=rule.rule_id,
                        title=rule.title,
                        risk_level="pass",
                        reason="规则条件未触发。",
                        suggestion=None,
                    )
                )
                continue

            evidence, clause_ids = _evidence_from_spans(outcome.spans, clauses, text)
            evaluations.append(
                RuleEvaluation(
                    rule_id=rule.rule_id,
                    title=rule.title,
                    risk_level=rule.risk_level,
                    reason=rule.reason,
                    suggestion=rule.suggestion,
                    clause_ids=clause_ids,
                    evidence=evidence,
                    requires_human=rule.risk_level == "red",
                )
            )
        except Exception as exc:  # noqa: BLE001 - 规则异常必须 fail-closed
            evaluations.append(
                RuleEvaluation(
                    rule_id=rule.rule_id,
                    title=rule.title,
                    risk_level="red",
                    reason=f"规则执行异常（{type(exc).__name__}: {exc}），需人工确认。",
                    suggestion=None,
                    requires_human=True,
                    is_system_finding=True,
                )
            )
    return evaluations


def overall_level(evaluations: list[RuleEvaluation]) -> Literal["red", "yellow", "pass"]:
    """聚合等级：任一 red → red；否则任一 yellow → yellow；否则 pass。"""
    levels = {e.risk_level for e in evaluations}
    if "red" in levels:
        return "red"
    if "yellow" in levels:
        return "yellow"
    return "pass"
