"""证据定位测试：精确匹配、空白折叠、NFC、失败不伪造偏移（ADR-005 §3.4）。"""

from __future__ import annotations

import unicodedata

from app.services.evidence import locate_quote, normalize


def test_exact_match() -> None:
    text = "Payment shall be made by T/T."
    assert locate_quote(text, "made by T/T") == (17, 28)


def test_empty_quote_returns_none() -> None:
    assert locate_quote("any text", "") is None
    assert locate_quote("any text", "   ") is None


def test_quote_not_found_returns_none() -> None:
    assert locate_quote("Payment by L/C.", "Payment in advance") is None


def test_newlines_and_repeated_spaces_are_folded() -> None:
    text = "Payment shall be\nmade     by T/T within 5 days."
    span = locate_quote(text, "Payment shall be made by T/T")
    assert span is not None
    start, end = span
    assert text[start:end] == "Payment shall be\nmade     by T/T"
    assert normalize(text[start:end]) == "Payment shall be made by T/T"


def test_cross_paragraph_quote() -> None:
    text = "Clause 1 text.\n\nClause 2 begins here."
    span = locate_quote(text, "text. Clause 2")
    assert span is not None
    assert text[span[0] : span[1]] == "text.\n\nClause 2"


def test_nfc_composed_vs_decomposed() -> None:
    raw = "Cafe\u0301 contract"  # e + 组合重音符
    span = locate_quote(raw, "Caf\u00e9")
    assert span is not None
    start, end = span
    assert unicodedata.normalize("NFC", raw[start:end]) == "Caf\u00e9"


def test_leading_whitespace_is_dropped_in_normalization() -> None:
    assert normalize("   \n  hello  world  ") == "hello world"


def test_exact_match_wins_even_if_normalized_form_also_matches() -> None:
    text = "A  B A B"
    assert locate_quote(text, "A B") == (5, 8)


def test_offsets_are_usable_on_original_text() -> None:
    text = "Seller: ABC Trading Co., Ltd.\nBuyer: Global Import LLC"
    span = locate_quote(text, "Buyer: Global Import LLC")
    assert span is not None
    assert text[span[0] : span[1]] == "Buyer: Global Import LLC"
