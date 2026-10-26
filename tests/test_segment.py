"""segment_clauses 节点测试：偏移一致性、条款编号、类型分类、空输入。"""

from __future__ import annotations

from app.nodes.segment import segment_clauses, split_blocks
from app.schemas import ContractReviewState


def test_block_offsets_match_text(sample_state: ContractReviewState) -> None:
    raw = sample_state.raw_text
    assert len(sample_state.clauses) >= 5
    for clause in sample_state.clauses:
        assert raw[clause.start : clause.end] == clause.text
        assert clause.end <= len(raw)


def test_clause_ids_are_stable_and_unique(sample_state: ContractReviewState) -> None:
    clause_ids = [c.clause_id for c in sample_state.clauses]
    assert clause_ids == [f"C{i:03d}" for i in range(1, len(clause_ids) + 1)]


def test_offsets_are_monotonic(sample_state: ContractReviewState) -> None:
    starts = [c.start for c in sample_state.clauses]
    assert starts == sorted(starts)
    assert len(set(starts)) == len(starts)


def test_clause_type_classification(sample_state: ContractReviewState) -> None:
    types = {c.clause_type for c in sample_state.clauses}
    assert "payment" in types
    assert "delivery" in types


def test_title_is_first_line(sample_state: ContractReviewState) -> None:
    payment_clause = next(c for c in sample_state.clauses if c.clause_type == "payment")
    assert payment_clause.title.startswith("2.")


def test_single_paragraph_fallback() -> None:
    state = ContractReviewState(
        review_id="t", source_filename="x.txt", raw_text="Seller: A. Buyer: B. Delivery: C."
    )
    update = segment_clauses(state)
    assert len(update["clauses"]) == 1
    assert update["clauses"][0].start == 0


def test_empty_text_returns_no_clauses() -> None:
    state = ContractReviewState(review_id="t", source_filename="x.txt")
    assert segment_clauses(state)["clauses"] == []


def test_split_blocks_keeps_offsets() -> None:
    text = "A\n\nB\nC\n\n\nD"
    blocks = split_blocks(text)
    assert [text[start:end] for _, start, end in blocks] == ["A", "B\nC", "D"]
