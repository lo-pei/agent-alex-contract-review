"""`validate_extraction` 节点：Python 校验 LLM 抽取结果，产出合同级事实（ADR-003 §3.7）。

角色：图的第四站，是规则引擎唯一可信的字段来源。
依赖：`app/services/evidence.py`（quote 定位）、`app/schemas.py`。
校验规则：
1. 非 null 字段必须有 quote；quote 必须能在所属条款原文定位（精确 → NFC/空白规范化）；
2. 定位失败 → 该字段丢弃为 null + `to_verify`（绝不伪造偏移）；
3. 数值字段清理千分位；无法解析 → 保留原文 + `to_verify`；
4. 多条款同名字段冲突 → 保留第一个命中的值 + `to_verify`；
5. 金额/币种/日期/Incoterms 版本等一致性检查 → `to_verify`，不自动换算。
"""

from __future__ import annotations

import re
from time import perf_counter

from app.schemas import (
    EXTRACTED_FIELDS,
    NUMERIC_FIELDS,
    Clause,
    ContractReviewState,
    Evidence,
    ToVerifyItem,
)
from app.services.evidence import locate_quote

_NUMBER_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")
_ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _coerce_number(value: str | int | float) -> tuple[float | None, bool]:
    """返回 `(数值, 是否需要人工核对)`；无法解析时数值为 None。"""
    if isinstance(value, (int, float)):
        return float(value), False
    cleaned = value.replace(",", "").replace("，", "").strip()
    match = _NUMBER_PATTERN.search(cleaned)
    if not match:
        return None, False
    number = float(match.group())
    # “3,100,000” 这类是正常写法；带单位/币种残留才需要人工核对
    leftover = cleaned.replace(match.group(), "").strip()
    return number, bool(leftover)


def _values_equal(left: str | int | float, right: str | int | float) -> bool:
    if isinstance(left, str) and isinstance(right, str):
        return left.strip().casefold() == right.strip().casefold()
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return abs(float(left) - float(right)) < 1e-9
    return False


def _clause_at(clauses: list[Clause], offset: int) -> Clause | None:
    return next((c for c in clauses if c.start <= offset < c.end), None)


def _ground(
    state: ContractReviewState,
    clause: Clause,
    quote: str,
) -> Evidence | None:
    """先在本条款定位；失败再全文中找（仍要求精确/空白规范化），找到后归属真实条款。"""
    local = locate_quote(clause.text, quote)
    if local is not None:
        start = clause.start + local[0]
        end = clause.start + local[1]
        return Evidence(
            quote=state.raw_text[start:end],
            start=start,
            end=end,
            page=clause.page,
            clause_id=clause.clause_id,
            grounded=True,
        )

    global_span = locate_quote(state.raw_text, quote)
    if global_span is None:
        return None
    start, end = global_span
    owner = _clause_at(state.clauses, start)
    return Evidence(
        quote=state.raw_text[start:end],
        start=start,
        end=end,
        page=owner.page if owner else clause.page,
        clause_id=owner.clause_id if owner else clause.clause_id,
        grounded=True,
    )


def _add_verify(
    items: list[ToVerifyItem],
    field: str,
    reason: str,
    clause_id: str | None = None,
) -> None:
    key = (field, reason, clause_id)
    if all((item.field, item.reason, item.clause_id) != key for item in items):
        items.append(ToVerifyItem(field=field, reason=reason, clause_id=clause_id))


def _consistency_checks(
    facts: dict[str, str | int | float | None],
    items: list[ToVerifyItem],
) -> None:
    if facts.get("total_amount") is not None and facts.get("currency") is None:
        _add_verify(items, "currency", "存在合同总价但未抽取到币种，需人工确认结算币种。")
    if facts.get("unit_price") is not None and facts.get("currency") is None:
        _add_verify(items, "currency", "存在单价但未抽取到币种，需人工确认结算币种。")
    if facts.get("unit_price") is not None and facts.get("total_amount") is None:
        _add_verify(items, "total_amount", "只抽取到单价，未抽取到合同总价，需人工核对。")
    if facts.get("incoterms") is not None and facts.get("incoterms_version") is None:
        _add_verify(
            items,
            "incoterms_version",
            "抽取到贸易术语但未抽取到 Incoterms 版本，风险转移节点可能歧义。",
        )

    delivery_date = facts.get("delivery_date")
    if isinstance(delivery_date, str) and not _ISO_DATE_PATTERN.match(delivery_date.strip()):
        _add_verify(
            items,
            "delivery_date",
            f"交付期限不是 ISO 日期（{delivery_date}），规则不按日期比较，请人工核对。",
        )


def validate_extraction(state: ContractReviewState) -> dict:
    started = perf_counter()

    def finish(**updates: object) -> dict:
        return {
            **updates,
            "timings": {
                **state.timings,
                "validate_extraction_ms": round((perf_counter() - started) * 1000, 2),
            },
        }

    if state.status == "failed" or not state.extractions:
        return finish(facts={}, fact_evidence={}, to_verify=list(state.to_verify))

    clause_map = {clause.clause_id: clause for clause in state.clauses}
    facts: dict[str, str | int | float | None] = {}
    fact_evidence: dict[str, Evidence] = {}
    to_verify: list[ToVerifyItem] = list(state.to_verify)
    dropped = 0

    for extraction in state.extractions:
        clause = clause_map.get(extraction.clause_id)
        if clause is None:
            _add_verify(
                to_verify,
                "*",
                f"抽取结果指向不存在的条款 {extraction.clause_id}，已忽略。",
                extraction.clause_id,
            )
            continue

        for field in EXTRACTED_FIELDS:
            field_value = getattr(extraction.fields, field)
            value = field_value.value
            if value is None or (isinstance(value, str) and not value.strip()):
                continue
            value = value.strip() if isinstance(value, str) else value

            quote = (field_value.quote or "").strip()
            if not quote:
                dropped += 1
                _add_verify(
                    to_verify,
                    field,
                    "抽取结果缺少原文引文，已丢弃该字段（不进入规则判定）。",
                    extraction.clause_id,
                )
                continue

            evidence = _ground(state, clause, quote)
            if evidence is None:
                dropped += 1
                _add_verify(
                    to_verify,
                    field,
                    "引文无法在原文定位，已丢弃该字段（不做模糊匹配）。",
                    extraction.clause_id,
                )
                continue

            if field in NUMERIC_FIELDS:
                number, needs_check = _coerce_number(value)
                if number is None:
                    _add_verify(
                        to_verify,
                        field,
                        f"无法解析为数值（{value}），保留原文供人工核对。",
                        evidence.clause_id,
                    )
                else:
                    if needs_check:
                        _add_verify(
                            to_verify,
                            field,
                            f"数值含单位或币种残留（{value}），已按数字 {number} 处理，请核对。",
                            evidence.clause_id,
                        )
                    value = number

            if field in facts:
                if not _values_equal(facts[field], value):
                    _add_verify(
                        to_verify,
                        field,
                        f"多个条款取值不一致（保留 {facts[field]!r}，忽略 {value!r}），"
                        "需人工确认。",
                        evidence.clause_id,
                    )
                continue

            facts[field] = value
            fact_evidence[field] = evidence

    _consistency_checks(facts, to_verify)

    warnings = list(state.warnings)
    if dropped:
        warnings.append(f"{dropped} 个抽取字段因引文缺失/无法定位被丢弃，见 to_verify。")

    return finish(
        facts=facts,
        fact_evidence=fact_evidence,
        to_verify=to_verify,
        warnings=warnings,
    )
