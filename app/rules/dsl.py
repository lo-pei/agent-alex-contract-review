"""规则条件 DSL：白名单条件对象的定义与求值（ADR-003 §3.4）。

角色：把 YAML 中的条件解析成 Pydantic 对象，并在合同文本/合同事实上求值。
依赖：仅标准库 + pydantic；被 `app/rules/engine.py` 引用。
约束：
- 不使用 `eval` / `exec` / 动态 import；
- 文本匹配不区分大小写；返回命中区间，供引擎回填 Evidence 偏移；
- 条件缺陷（正则非法）在加载期报错，运行期异常由引擎转成系统 red。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _ConditionBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ContainsAny(_ConditionBase):
    type: Literal["contains_any"] = "contains_any"
    keywords: list[str] = Field(min_length=1)


class ContainsAll(_ConditionBase):
    type: Literal["contains_all"] = "contains_all"
    keywords: list[str] = Field(min_length=1)


class RegexMatch(_ConditionBase):
    type: Literal["regex_match"] = "regex_match"
    pattern: str = Field(min_length=1)

    @field_validator("pattern")
    @classmethod
    def _pattern_compiles(cls, value: str) -> str:
        try:
            re.compile(value)
        except re.error as exc:  # 非法正则在规则加载期失败，不在运行时静默跳过
            raise ValueError(f"非法正则：{exc}") from exc
        return value


class FieldEquals(_ConditionBase):
    type: Literal["field_equals"] = "field_equals"
    field: str
    value: str | int | float


class FieldIn(_ConditionBase):
    type: Literal["field_in"] = "field_in"
    field: str
    values: list[str] = Field(min_length=1)


class FieldMissing(_ConditionBase):
    type: Literal["field_missing"] = "field_missing"
    field: str


class FieldPresent(_ConditionBase):
    type: Literal["field_present"] = "field_present"
    field: str


class NumericLt(_ConditionBase):
    type: Literal["numeric_lt"] = "numeric_lt"
    field: str
    value: float


class NumericGt(_ConditionBase):
    type: Literal["numeric_gt"] = "numeric_gt"
    field: str
    value: float


class DateBefore(_ConditionBase):
    type: Literal["date_before"] = "date_before"
    field: str
    value: date


class DateAfter(_ConditionBase):
    type: Literal["date_after"] = "date_after"
    field: str
    value: date


class AllOf(_ConditionBase):
    type: Literal["all_of"] = "all_of"
    conditions: list[Condition] = Field(min_length=1)


class AnyOf(_ConditionBase):
    type: Literal["any_of"] = "any_of"
    conditions: list[Condition] = Field(min_length=1)


class NoneOf(_ConditionBase):
    type: Literal["none_of"] = "none_of"
    conditions: list[Condition] = Field(min_length=1)


Condition = Annotated[
    ContainsAny
    | ContainsAll
    | RegexMatch
    | FieldEquals
    | FieldIn
    | FieldMissing
    | FieldPresent
    | NumericLt
    | NumericGt
    | DateBefore
    | DateAfter
    | AllOf
    | AnyOf
    | NoneOf,
    Field(discriminator="type"),
]

AllOf.model_rebuild()
AnyOf.model_rebuild()
NoneOf.model_rebuild()


@dataclass(frozen=True)
class MatchSpan:
    """在 canonical_text 中的命中区间 [start, end)。"""

    start: int
    end: int


@dataclass(frozen=True)
class ConditionResult:
    triggered: bool
    spans: tuple[MatchSpan, ...] = ()


_MAX_REGEX_MATCHES = 50  # 防止极端文本产生海量证据


def _text_matches(text: str, keyword: str) -> list[MatchSpan]:
    return [
        MatchSpan(m.start(), m.end()) for m in re.finditer(re.escape(keyword), text, re.IGNORECASE)
    ]


def _dedupe(spans: list[MatchSpan]) -> tuple[MatchSpan, ...]:
    unique = {(s.start, s.end) for s in spans}
    return tuple(MatchSpan(start, end) for start, end in sorted(unique))


def _fact(facts: dict[str, Any], field: str) -> Any:
    return facts.get(field)


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def evaluate_condition(
    condition: Condition, text: str, facts: dict[str, Any] | None = None
) -> ConditionResult:
    """对单个条件求值。类型错误/数值错误直接抛出，由引擎转成系统 finding。"""
    facts = facts or {}

    if isinstance(condition, ContainsAny):
        spans: list[MatchSpan] = []
        for keyword in condition.keywords:
            spans.extend(_text_matches(text, keyword))
        deduped = _dedupe(spans)
        return ConditionResult(triggered=bool(deduped), spans=deduped)

    if isinstance(condition, ContainsAll):
        spans = []
        for keyword in condition.keywords:
            matches = _text_matches(text, keyword)
            if not matches:
                return ConditionResult(triggered=False)
            spans.extend(matches)
        return ConditionResult(triggered=True, spans=_dedupe(spans))

    if isinstance(condition, RegexMatch):
        spans = [
            MatchSpan(m.start(), m.end())
            for m in re.finditer(condition.pattern, text, re.IGNORECASE)
        ][:_MAX_REGEX_MATCHES]
        deduped = _dedupe(spans)
        return ConditionResult(triggered=bool(deduped), spans=deduped)

    if isinstance(condition, FieldEquals):
        value = _fact(facts, condition.field)
        if isinstance(value, str) and isinstance(condition.value, str):
            triggered = value.strip().casefold() == condition.value.strip().casefold()
        else:
            triggered = value == condition.value
        return ConditionResult(triggered=triggered)

    if isinstance(condition, FieldIn):
        value = _fact(facts, condition.field)
        if isinstance(value, str):
            allowed = {v.strip().casefold() for v in condition.values}
            triggered = value.strip().casefold() in allowed
        else:
            triggered = value in condition.values
        return ConditionResult(triggered=triggered)

    if isinstance(condition, FieldMissing):
        return ConditionResult(triggered=_is_missing(_fact(facts, condition.field)))

    if isinstance(condition, FieldPresent):
        return ConditionResult(triggered=not _is_missing(_fact(facts, condition.field)))

    if isinstance(condition, NumericLt):
        triggered = float(_fact(facts, condition.field)) < condition.value
        return ConditionResult(triggered=triggered)

    if isinstance(condition, NumericGt):
        triggered = float(_fact(facts, condition.field)) > condition.value
        return ConditionResult(triggered=triggered)

    if isinstance(condition, DateBefore):
        triggered = date.fromisoformat(str(_fact(facts, condition.field))) < condition.value
        return ConditionResult(triggered=triggered)

    if isinstance(condition, DateAfter):
        triggered = date.fromisoformat(str(_fact(facts, condition.field))) > condition.value
        return ConditionResult(triggered=triggered)

    if isinstance(condition, AllOf):
        spans: list[MatchSpan] = []
        for child in condition.conditions:
            result = evaluate_condition(child, text, facts)
            if not result.triggered:
                return ConditionResult(triggered=False)
            spans.extend(result.spans)
        return ConditionResult(triggered=True, spans=_dedupe(spans))

    if isinstance(condition, AnyOf):
        spans = []
        triggered = False
        for child in condition.conditions:
            result = evaluate_condition(child, text, facts)
            if result.triggered:
                triggered = True
                spans.extend(result.spans)
        return ConditionResult(triggered=triggered, spans=_dedupe(spans))

    if isinstance(condition, NoneOf):
        # 所有子条件都不成立时才触发（用于“缺失某条款”的规则）
        for child in condition.conditions:
            if evaluate_condition(child, text, facts).triggered:
                return ConditionResult(triggered=False)
        return ConditionResult(triggered=True)

    raise TypeError(f"未知条件类型：{type(condition).__name__}")
