"""segment_clauses 节点测试：标题切分、偏移一致性、合并、超长拆分、上限、fallback。"""

from __future__ import annotations

from pathlib import Path

from app.nodes.ingest import ingest_document
from app.nodes.segment import (
    MAX_CLAUSE_CHARS,
    is_heading,
    segment_clauses,
    split_blocks,
)
from app.schemas import ContractReviewState
from tests.fixtures.pdf_builder import make_pdf


def _state(text: str) -> ContractReviewState:
    return ContractReviewState(review_id="t", source_filename="x.txt", raw_text=text)


def test_block_offsets_match_text(sample_state: ContractReviewState) -> None:
    raw = sample_state.raw_text
    assert len(sample_state.clauses) >= 5
    for clause in sample_state.clauses:
        assert raw[clause.start : clause.end] == clause.text
        assert clause.end <= len(raw)


def test_clause_ids_are_stable_and_unique(sample_state: ContractReviewState) -> None:
    clause_ids = [c.clause_id for c in sample_state.clauses]
    assert clause_ids == [f"C{i:03d}" for i in range(len(clause_ids))]
    assert len(set(clause_ids)) == len(clause_ids)


def test_preamble_is_c000(sample_state: ContractReviewState) -> None:
    first = sample_state.clauses[0]
    assert first.clause_id == "C000"
    assert first.clause_type == "preamble"
    assert "INTERNATIONAL SALES CONTRACT" in first.text


def test_offsets_are_monotonic(sample_state: ContractReviewState) -> None:
    starts = [c.start for c in sample_state.clauses]
    assert starts == sorted(starts)
    assert len(set(starts)) == len(starts)
    assert all(
        a.end <= b.start
        for a, b in zip(sample_state.clauses, sample_state.clauses[1:], strict=False)
    )


def test_clause_type_classification(sample_state: ContractReviewState) -> None:
    types = {c.clause_type for c in sample_state.clauses}
    assert "payment" in types
    assert "delivery" in types


def test_title_is_heading_line(sample_state: ContractReviewState) -> None:
    payment_clause = next(c for c in sample_state.clauses if c.clause_type == "payment")
    assert payment_clause.title.startswith("2.")


def test_english_article_headings() -> None:
    text = (
        "PREAMBLE TEXT\n\n"
        f"ARTICLE 1 GOODS\n{'Steel coils, grade Q235B. ' * 5}\n\n"
        f"ARTICLE 2 PAYMENT\n{'Payment by T/T in advance. ' * 5}\n"
    )
    clauses = segment_clauses(_state(text))["clauses"]
    assert [c.clause_id for c in clauses] == ["C000", "C001", "C002"]
    assert clauses[1].title.startswith("ARTICLE 1")
    assert clauses[2].title.startswith("ARTICLE 2")
    assert text[clauses[2].start : clauses[2].end] == clauses[2].text


def test_chinese_headings() -> None:
    text = (
        "前言\n\n"
        f"第一条 货物\n{'钢卷 5000 吨，规格 Q235B。' * 6}\n\n"
        f"第二条 付款\n{'买方应于签约后五个银行工作日内电汇预付。' * 5}"
    )
    clauses = segment_clauses(_state(text))["clauses"]
    assert [c.clause_id for c in clauses] == ["C000", "C001", "C002"]
    assert clauses[1].title.startswith("第一条")


def test_body_line_starting_with_number_is_not_heading() -> None:
    text = (
        "ARTICLE 1 DELIVERY\n"
        "30 days after receipt of the payment. Shipment shall be effected by sea.\n\n"
        f"ARTICLE 2 PAYMENT\n{'Payment by T/T in advance. ' * 5}"
    )
    clauses = segment_clauses(_state(text))["clauses"]
    assert len(clauses) == 2
    assert "30 days after receipt" in clauses[0].text


def test_heading_detection_rules() -> None:
    assert is_heading("ARTICLE 1 GOODS")
    assert is_heading("第一条 货物")
    assert is_heading("一、货物")
    assert is_heading("（一）货物")
    assert is_heading("2. Price and Payment")
    assert not is_heading("30 days after receipt of the payment.")
    assert not is_heading("x" * 200)


def test_small_clause_merged_into_previous() -> None:
    """界面轮 12：带标题的小条款保留边界，只有“无标题的小段”才并回上一条。"""
    body = "x" * 200
    text = (
        f"ARTICLE 1 A\n{body}\n\n"
        "ARTICLE 2 B\nshort\n\n"
        f"ARTICLE 3 C\n{body}\n"
    )
    clauses = segment_clauses(_state(text))["clauses"]
    assert len(clauses) == 3
    assert clauses[1].title.startswith("ARTICLE 2")

    with_orphan = f"ARTICLE 1 A\n{body}\n\n{body}\nshort tail\n\nARTICLE 2 B\n{body}\n"
    merged = segment_clauses(_state(with_orphan))["clauses"]
    assert len(merged) == 2
    assert "short tail" in merged[0].text


def test_heading_in_same_line_as_body_is_recognised() -> None:
    """`13. 争议解决：凡因……` / `违约责任：……` 这种“标题 + 正文同一行”也要切出来。"""
    assert is_heading("13. 争议解决：凡因本合同引起的或与本合同有关的任何争议，双方同意提交仲裁。")
    assert is_heading("12. 通知：所有通知用中文写成并按首部地址送达，地址变更应提前通知另一方。")
    assert is_heading("违约责任：如果卖方未能按合同约定按时交货，应向买方支付违约金。")
    assert is_heading("Force Majeure: Force majeure refers to unforeseeable events beyond control.")
    assert not is_heading("装运港：                     Port of Shipment:")
    assert not is_heading("30 days after receipt of the goods before the claim is filed.")
    assert not is_heading("| 1. 货物名称 Commodity | 2. 包装 Packing |")


def test_bilingual_blocks_do_not_split_into_two_clauses() -> None:
    """中英对照合同：中文条款紧跟英文译本时，不能拆成两条。"""
    text = (
        "特别提示：\n\n1. 请核对签约主体；\n\n2. 请保留证据。\n\n"
        "销售合同书\n\nSALES CONTRACT\n\n"
        "1. 质量标准及检验：本合同项下产品质量适用国家标准。\n\n"
        "Quality Standard and Inspection: national standard shall be applied.\n\n"
        "2. 不可抗力：不可抗力是指无法预见的客观情况。\n\n"
        "Force Majeure: force majeure refers to unforeseeable objective conditions.\n"
    )
    clauses = segment_clauses(_state(text))["clauses"]

    preamble = clauses[0]
    assert preamble.clause_type == "preamble"
    assert "特别提示" in preamble.text and "请保留证据" in preamble.text
    assert len(clauses) == 3
    assert "Quality Standard" in clauses[1].text
    assert "Force Majeure" in clauses[2].text


def test_clause_titles_are_short_labels_for_toc() -> None:
    """界面轮 12：目录只显示“编号 + 主题词”，不把整行正文当标题。"""
    text = (
        "PREAMBLE\n\n"
        "5. 付款条件：                      Payment:\n买方应于装运前电汇全部货款。\n\n"
        "违约责任：如果卖方未能按合同约定按时交货，应向买方支付违约金。\n"
    )
    clauses = segment_clauses(_state(text))["clauses"]
    titles = [clause.title for clause in clauses]
    assert "5. 付款条件" in titles
    assert "违约责任" in titles
    assert all(len(title) <= 120 for title in titles)


def test_duplicate_bilingual_heading_does_not_create_two_clauses() -> None:
    """同一个“付款条件”标题在中英对照里出现两次时，只留一条（避免目录出现两个付款条件）。"""
    text = (
        "SALES CONTRACT\n\n"
        "5. 付款条件： Payment:\n\n100% T/T in advance.\n\n"
        "5. 付款条件： Payment:\n\nBuyer shall pay by T/T before shipment.\n\n"
        "6. 保险： Insurance:\n\nInsurance shall cover 110% of invoice value.\n"
    )
    clauses = segment_clauses(_state(text))["clauses"]
    payment = [clause for clause in clauses if "付款条件" in clause.title]

    assert len(payment) == 1
    assert "100% T/T" in payment[0].text
    assert "before shipment" in payment[0].text
    # 合并后偏移仍可回溯到原文
    assert text[payment[0].start : payment[0].end] == payment[0].text


def test_long_clause_is_split_with_suffix() -> None:
    body = "\n\n".join(["A" * 1500] * 4)
    text = f"ARTICLE 1 TERMS\n{body}"
    clauses = segment_clauses(_state(text))["clauses"]

    assert len(clauses) >= 2
    assert clauses[0].clause_id == "C001-1"
    assert clauses[1].clause_id == "C001-2"
    assert all(len(clause.text) <= MAX_CLAUSE_CHARS for clause in clauses)
    for clause in clauses:
        assert text[clause.start : clause.end] == clause.text


def test_clause_count_limit() -> None:
    text = "".join(f"ARTICLE {index} T\n{'x' * 120}\n\n" for index in range(1, 202))
    update = segment_clauses(_state(text))
    assert update["status"] == "failed"
    assert update["clauses"] == []
    assert "条款数过多" in update["errors"][0]


def test_paragraph_fallback_aggregation() -> None:
    text = "\n\n".join("a" * 50 for _ in range(10))
    update = segment_clauses(_state(text))
    clauses = update["clauses"]

    assert 1 <= len(clauses) <= 10
    assert all(text[clause.start : clause.end] == clause.text for clause in clauses)
    assert any("按段落聚合" in warning for warning in update["warnings"])


def test_single_paragraph_fallback() -> None:
    state = _state("Seller: A. Buyer: B. Delivery: C.")
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


def test_pdf_pages_are_mapped_to_clauses(tmp_path: Path) -> None:
    path = tmp_path / "contract.pdf"
    path.write_bytes(
        make_pdf(
            [
                ["ARTICLE 1 GOODS", "Steel coils, 5000 tons"],
                [
                    "ARTICLE 2 PAYMENT",
                    "Payment by T/T in advance within ten banking days after signing.",
                ],
            ]
        )
    )
    initial = ContractReviewState(
        review_id="t", source_filename=path.name, source_path=str(path)
    )
    ingested = ContractReviewState.model_validate(
        {**initial.model_dump(), **ingest_document(initial)}
    )
    clauses = segment_clauses(ingested)["clauses"]

    assert len(clauses) == 2
    assert clauses[0].page == 1
    assert clauses[1].page == 2
    assert clauses[1].start >= ingested.pages[1].start_offset
