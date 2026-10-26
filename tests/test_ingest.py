"""ingest_document 节点测试：编码、空文件、类型、上限、偏移与 sha256。"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from app.nodes.ingest import ingest_document
from app.schemas import ContractReviewState


def _state(path: Path) -> ContractReviewState:
    return ContractReviewState(review_id="t", source_filename=path.name, source_path=str(path))


def test_ingest_sample_ok(sample_path: Path) -> None:
    state = _state(sample_path)
    update = ingest_document(state)

    assert update.get("status") != "failed"
    assert len(update["source_sha256"]) == 64
    assert update["source_filename"] == "sample_sales_contract.txt"
    assert update["media_type"] == "text"

    page = update["pages"][0]
    assert page.page_number == 1
    assert page.start_offset == 0
    assert page.end_offset == len(update["raw_text"])
    assert update["raw_text"][page.start_offset : page.end_offset] == update["raw_text"]


def test_ingest_missing_file(tmp_path: Path) -> None:
    update = ingest_document(_state(tmp_path / "not_exists.txt"))
    assert update["status"] == "failed"
    assert "不存在" in update["errors"][0]


def test_ingest_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "empty.txt"
    path.write_text("   \n\n", encoding="utf-8")
    update = ingest_document(_state(path))
    assert update["status"] == "failed"
    assert "为空" in update["errors"][0]


def test_ingest_unsupported_suffix(tmp_path: Path) -> None:
    path = tmp_path / "contract.pdf"
    path.write_bytes(b"%PDF-1.4 fake")
    update = ingest_document(_state(path))
    assert update["status"] == "failed"
    assert "暂不支持" in update["errors"][0]


def test_ingest_normalizes_newlines(tmp_path: Path) -> None:
    path = tmp_path / "crlf.txt"
    path.write_bytes(b"Seller: A\r\nBuyer: B\r\n\r\nClause one.\r\n")
    update = ingest_document(_state(path))
    assert update.get("status") != "failed"
    assert "\r" not in update["raw_text"]
    assert "Seller: A\nBuyer: B\n\nClause one." in update["raw_text"]


def test_ingest_gb18030_fallback(tmp_path: Path) -> None:
    path = tmp_path / "gbk.txt"
    path.write_bytes("甲方：上海公司\n乙方：汉堡公司\n".encode("gb18030"))
    update = ingest_document(_state(path))
    assert update.get("status") != "failed"
    assert "GB18030" in update["warnings"][0]
    assert "上海公司" in update["raw_text"]


def test_ingest_no_source_path() -> None:
    update = ingest_document(ContractReviewState(review_id="t", source_filename="x.txt"))
    assert update["status"] == "failed"
    assert "source_path" in update["errors"][0]


def test_ingest_rejects_oversize(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "big.txt"
    path.write_text("A" * 200, encoding="utf-8")

    import app.nodes.ingest as ingest_module

    monkeypatch.setattr(
        ingest_module,
        "settings",
        replace(ingest_module.settings, max_contract_chars=100),
    )
    update = ingest_document(_state(path))
    assert update["status"] == "failed"
    assert "过长" in update["errors"][0]
