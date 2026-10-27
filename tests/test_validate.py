"""`validate_extraction` 节点测试：引文定位、丢弃、数值归一、冲突与一致性检查。"""

from __future__ import annotations

from app.nodes.validate import validate_extraction
from app.schemas import Clause, ClauseExtraction, ContractReviewState
from tests.fakes import field, field_set


def _state(
    raw: str,
    clause_texts: list[str],
    extractions: list[ClauseExtraction],
) -> ContractReviewState:
    clauses: list[Clause] = []
    cursor = 0
    for index, text in enumerate(clause_texts, start=1):
        start = raw.index(text, cursor)
        clauses.append(
            Clause(
                clause_id=f"C{index:03d}",
                text=text,
                start=start,
                end=start + len(text),
                page=1,
            )
        )
        cursor = start + len(text)
    return ContractReviewState(
        review_id="test-validate",
        source_filename="contract.txt",
        raw_text=raw,
        clauses=clauses,
        extractions=extractions,
        extraction_status="ok",
    )


def _fields(clause_id: str, **values) -> ClauseExtraction:
    return ClauseExtraction(clause_id=clause_id, fields=field_set(**values))


# ---------- 正常定位 ----------


def test_grounded_fields_become_facts() -> None:
    raw = "Currency: USD\n\nThe total contract price is 3,100,000."
    state = _state(
        raw,
        ["Currency: USD", "The total contract price is 3,100,000."],
        [
            _fields("C001", currency=field("USD", "Currency: USD")),
            _fields(
                "C002",
                total_amount=field("3,100,000", "The total contract price is 3,100,000."),
            ),
        ],
    )

    updates = validate_extraction(state)

    assert updates["facts"]["currency"] == "USD"
    assert updates["facts"]["total_amount"] == 3_100_000.0
    evidence = updates["fact_evidence"]["total_amount"]
    assert evidence.grounded
    assert evidence.clause_id == "C002"
    assert evidence.page == 1
    assert raw[evidence.start : evidence.end] == "The total contract price is 3,100,000."
    # 币种与总价齐全 → 不产生一致性待核对
    assert updates["to_verify"] == []


def test_quote_with_different_whitespace_is_accepted() -> None:
    raw = "Payment shall be made\nby T/T."
    state = _state(
        raw,
        [raw],
        [_fields("C001", payment_method=field("T/T", "Payment shall be made by T/T."))],
    )

    updates = validate_extraction(state)

    assert updates["facts"]["payment_method"] == "T/T"
    evidence = updates["fact_evidence"]["payment_method"]
    assert raw[evidence.start : evidence.end] == "Payment shall be made\nby T/T."


# ---------- 引文缺失/无法定位 ----------


def test_missing_quote_drops_field() -> None:
    raw = "Currency: USD"
    state = _state(raw, [raw], [_fields("C001", currency=field("USD", None))])

    updates = validate_extraction(state)

    assert updates["facts"] == {}
    assert updates["fact_evidence"] == {}
    assert any("缺少原文引文" in item.reason for item in updates["to_verify"])
    assert any("被丢弃" in warning for warning in updates["warnings"])


def test_ungrounded_quote_drops_field() -> None:
    raw = "Currency: USD"
    state = _state(raw, [raw], [_fields("C001", currency=field("JPY", "JPY"))])

    updates = validate_extraction(state)

    assert updates["facts"] == {}
    assert any("无法在原文定位" in item.reason for item in updates["to_verify"])


def test_blank_value_is_ignored() -> None:
    raw = "Currency: USD"
    state = _state(raw, [raw], [_fields("C001", currency=field("   ", "Currency: USD"))])

    updates = validate_extraction(state)

    assert updates["facts"] == {}
    assert updates["to_verify"] == []


def test_unknown_clause_id_is_ignored() -> None:
    raw = "Currency: USD"
    state = _state(raw, [raw], [_fields("C999", currency=field("USD", "Currency: USD"))])

    updates = validate_extraction(state)

    assert updates["facts"] == {}
    assert any("不存在的条款" in item.reason for item in updates["to_verify"])


# ---------- 数值归一化 ----------


def test_numeric_string_is_normalized() -> None:
    raw = "Total: 3,100,000"
    state = _state(
        raw,
        [raw],
        [_fields("C001", total_amount=field("3,100,000", "Total: 3,100,000"))],
    )

    updates = validate_extraction(state)

    assert updates["facts"]["total_amount"] == 3_100_000.0
    assert not any(item.field == "total_amount" for item in updates["to_verify"])


def test_numeric_with_currency_residue_needs_verification() -> None:
    raw = "Total: USD 3,100,000"
    state = _state(
        raw,
        [raw],
        [_fields("C001", total_amount=field("USD 3,100,000", "Total: USD 3,100,000"))],
    )

    updates = validate_extraction(state)

    assert updates["facts"]["total_amount"] == 3_100_000.0
    assert any("含单位或币种残留" in item.reason for item in updates["to_verify"])


def test_unparsable_number_keeps_original_value() -> None:
    raw = "Total: to be agreed"
    state = _state(
        raw,
        [raw],
        [_fields("C001", total_amount=field("to be agreed", "Total: to be agreed"))],
    )

    updates = validate_extraction(state)

    assert updates["facts"]["total_amount"] == "to be agreed"
    assert any("无法解析为数值" in item.reason for item in updates["to_verify"])


# ---------- 冲突与一致性 ----------


def test_conflicting_values_keep_first_and_verify() -> None:
    raw = "Currency: USD\n\nCurrency: EUR"
    state = _state(
        raw,
        ["Currency: USD", "Currency: EUR"],
        [
            _fields("C001", currency=field("USD", "Currency: USD")),
            _fields("C002", currency=field("EUR", "Currency: EUR")),
        ],
    )

    updates = validate_extraction(state)

    assert updates["facts"]["currency"] == "USD"
    assert any("取值不一致" in item.reason for item in updates["to_verify"])


def test_missing_currency_with_amount_needs_verification() -> None:
    raw = "Total: 3,100,000"
    state = _state(
        raw,
        [raw],
        [_fields("C001", total_amount=field("3,100,000", "Total: 3,100,000"))],
    )

    updates = validate_extraction(state)

    reasons = [item.reason for item in updates["to_verify"] if item.field == "currency"]
    assert reasons and "币种" in reasons[0]


def test_unit_price_without_total_needs_verification() -> None:
    raw = "Unit price: USD 620 per ton"
    state = _state(
        raw,
        [raw],
        [_fields("C001", unit_price=field(620, "Unit price: USD 620 per ton"))],
    )

    updates = validate_extraction(state)

    assert updates["facts"]["unit_price"] == 620.0
    assert any(item.field == "total_amount" for item in updates["to_verify"])


def test_incoterms_without_version_needs_verification() -> None:
    raw = "FOB Shanghai"
    state = _state(raw, [raw], [_fields("C001", incoterms=field("FOB", "FOB Shanghai"))])

    updates = validate_extraction(state)

    assert updates["facts"]["incoterms"] == "FOB"
    assert any(item.field == "incoterms_version" for item in updates["to_verify"])


def test_non_iso_delivery_date_needs_verification() -> None:
    raw = "Shipment within 45 days after receipt of the advance payment."
    state = _state(
        raw,
        [raw],
        [_fields("C001", delivery_date=field("within 45 days", raw))],
    )

    updates = validate_extraction(state)

    assert updates["facts"]["delivery_date"] == "within 45 days"
    assert any(item.field == "delivery_date" for item in updates["to_verify"])


# ---------- 空输入 ----------


def test_no_extractions_returns_empty_facts() -> None:
    raw = "Currency: USD"
    state = _state(raw, [raw], [])

    updates = validate_extraction(state)

    assert updates["facts"] == {}
    assert updates["fact_evidence"] == {}
    assert "validate_extraction_ms" in updates["timings"]
