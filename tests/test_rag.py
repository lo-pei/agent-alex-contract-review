"""RAG MVP 测试：manifest 校验、BM25 检索、引用可追溯、默认关闭、DOCX 条文切分。"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.rag import (
    MAX_SECTION_CHARS,
    RELATIVE_SCORE_RATIO,
    KnowledgeConfigError,
    load_knowledge_base,
    tokenize,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
#: 测试固定使用项目自拟示例语料，避免受用户真实语料变动影响
KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "knowledge" / "examples"
REAL_KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "knowledge"

MANIFEST_TEMPLATE = """version: 1
documents:
  - source_id: T1
    title: 测试文档
    publisher: 项目
    version: "1"
    jurisdiction: 中国
    effective_date: "2026-01-01"
    language: zh
    file: doc.md
    license: internal
"""


def _write_corpus(tmp_path: Path, manifest: str, files: tuple[str, ...] = ("doc.md",)) -> Path:
    for name in files:
        (tmp_path / name).write_text("## 付款条款\n买方应按期付款。\n", encoding="utf-8")
    (tmp_path / "manifest.yaml").write_text(manifest, encoding="utf-8")
    return tmp_path


# ---------- 默认关闭 ----------


def test_rag_disabled_by_default() -> None:
    # ADR-007：默认 RAG_ENABLED=false；关闭时不加载、不报错
    assert load_knowledge_base(KNOWLEDGE_DIR, enabled=False) is None


# ---------- 示例语料 ----------


def test_example_corpus_loads_with_metadata() -> None:
    knowledge = load_knowledge_base(KNOWLEDGE_DIR, enabled=True)
    assert knowledge is not None
    assert [document.source_id for document in knowledge.documents] == [
        "EX-INCOTERMS",
        "EX-CISG",
        "EX-CN-CONTRACT",
    ]
    assert len(knowledge) >= 9
    assert "EX-INCOTERMS#s1" in knowledge.citations()
    # 元数据必须可追溯（授权/版本/生效日期）
    for document in knowledge.documents:
        assert document.license
        assert document.version
        assert document.effective_date


def test_search_hits_expected_section() -> None:
    knowledge = load_knowledge_base(KNOWLEDGE_DIR, enabled=True)
    assert knowledge is not None

    hits = knowledge.search("贸易术语未注明 Incoterms 版本", min_score=0.0)
    assert hits
    assert hits[0].citation == "EX-INCOTERMS#s2"
    assert hits[0].heading == "贸易术语与版本"

    hits = knowledge.search("仲裁与管辖 未约定仲裁机构", min_score=0.0)
    assert hits
    assert hits[0].citation == "EX-CN-CONTRACT#s3"


def test_search_respects_top_k_and_relative_cutoff() -> None:
    knowledge = load_knowledge_base(KNOWLEDGE_DIR, enabled=True)
    assert knowledge is not None

    hits = knowledge.search("合同 付款 风险 交付 仲裁", top_k=2, min_score=0.0)
    assert len(hits) == 2
    assert hits[0].score >= hits[1].score
    # 相对阈值：不把与最佳命中差距过大的长尾片段塞进提示词
    assert all(hit.score >= hits[0].score * RELATIVE_SCORE_RATIO for hit in hits)


def test_search_no_hit_returns_empty() -> None:
    knowledge = load_knowledge_base(KNOWLEDGE_DIR, enabled=True)
    assert knowledge is not None
    assert knowledge.search("zzzz qqqq", min_score=1.0) == []


def test_tokenize_keeps_chinese_bigrams() -> None:
    tokens = tokenize("付款 Payment Terms")
    assert "付" in tokens and "付款" in tokens
    assert "payment" in tokens and "terms" in tokens


# ---------- manifest 校验 ----------


def test_missing_manifest_raises(tmp_path: Path) -> None:
    with pytest.raises(KnowledgeConfigError, match="manifest"):
        load_knowledge_base(tmp_path, enabled=True)


def test_missing_required_field_raises(tmp_path: Path) -> None:
    manifest = MANIFEST_TEMPLATE.replace("    license: internal\n", "")
    _write_corpus(tmp_path, manifest)
    with pytest.raises(KnowledgeConfigError, match="license"):
        load_knowledge_base(tmp_path, enabled=True)


def test_unknown_field_raises(tmp_path: Path) -> None:
    manifest = MANIFEST_TEMPLATE + "    foo: bar\n"
    _write_corpus(tmp_path, manifest)
    with pytest.raises(KnowledgeConfigError, match="未定义字段"):
        load_knowledge_base(tmp_path, enabled=True)


def test_duplicate_source_id_raises(tmp_path: Path) -> None:
    manifest = """version: 1
documents:
  - source_id: T1
    title: 测试文档
    publisher: 项目
    version: "1"
    jurisdiction: 中国
    effective_date: "2026-01-01"
    language: zh
    file: doc.md
    license: internal
  - source_id: T1
    title: 测试文档二
    publisher: 项目
    version: "1"
    jurisdiction: 中国
    effective_date: "2026-01-01"
    language: zh
    file: doc2.md
    license: internal
"""
    _write_corpus(tmp_path, manifest, files=("doc.md", "doc2.md"))
    with pytest.raises(KnowledgeConfigError, match="重复"):
        load_knowledge_base(tmp_path, enabled=True)


def test_path_traversal_raises(tmp_path: Path) -> None:
    manifest = MANIFEST_TEMPLATE.replace("file: doc.md", "file: ../outside.md")
    _write_corpus(tmp_path, manifest)
    with pytest.raises(KnowledgeConfigError, match="越出语料目录"):
        load_knowledge_base(tmp_path, enabled=True)


def test_bad_effective_date_raises(tmp_path: Path) -> None:
    manifest = MANIFEST_TEMPLATE.replace('"2026-01-01"', '"2026/01/01"')
    _write_corpus(tmp_path, manifest)
    with pytest.raises(KnowledgeConfigError, match="effective_date"):
        load_knowledge_base(tmp_path, enabled=True)


def test_bad_source_id_raises(tmp_path: Path) -> None:
    manifest = MANIFEST_TEMPLATE.replace("source_id: T1", "source_id: 1-BAD")
    _write_corpus(tmp_path, manifest)
    with pytest.raises(KnowledgeConfigError, match="source_id"):
        load_knowledge_base(tmp_path, enabled=True)


def test_empty_documents_raises(tmp_path: Path) -> None:
    _write_corpus(tmp_path, "version: 1\ndocuments: []\n")
    with pytest.raises(KnowledgeConfigError, match="非空列表"):
        load_knowledge_base(tmp_path, enabled=True)


def test_non_utf8_file_raises(tmp_path: Path) -> None:
    _write_corpus(tmp_path, MANIFEST_TEMPLATE)
    (tmp_path / "doc.md").write_bytes(b"\xff\xfe\x00bad")
    with pytest.raises(KnowledgeConfigError, match="UTF-8"):
        load_knowledge_base(tmp_path, enabled=True)


# ---------- 文件类型 ----------


def _manifest_for(file: str) -> str:
    return f"""version: 1
documents:
  - source_id: T1
    title: 测试文档
    publisher: 项目
    version: "1"
    jurisdiction: 中国
    effective_date: "2026-01-01"
    language: zh
    file: {file}
    license: internal
"""


def test_legacy_doc_is_rejected_with_conversion_hint(tmp_path: Path) -> None:
    (tmp_path / "old.doc").write_bytes(b"not really a doc")
    (tmp_path / "manifest.yaml").write_text(_manifest_for("old.doc"), encoding="utf-8")
    with pytest.raises(KnowledgeConfigError, match="转换为"):
        load_knowledge_base(tmp_path, enabled=True)


def test_unsupported_suffix_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "doc.pdf").write_bytes(b"%PDF-1.4")
    (tmp_path / "manifest.yaml").write_text(_manifest_for("doc.pdf"), encoding="utf-8")
    with pytest.raises(KnowledgeConfigError, match="文件类型不支持"):
        load_knowledge_base(tmp_path, enabled=True)


def test_docx_corpus_splits_by_article(tmp_path: Path) -> None:
    from docx import Document

    document = Document()
    for line in (
        "测试法",
        "（2026年1月1日通过）",
        "目　　录",
        "第一编　总　　则",
        "第一章　基本规定",
        "第一条　为了保护当事人合法权益，制定本法。",
        "第二条　民事主体的人身权利受法律保护。",
        "第三条　本编没有规定的，适用其他规定。",
    ):
        document.add_paragraph(line)
    document.save(str(tmp_path / "law.docx"))
    (tmp_path / "manifest.yaml").write_text(_manifest_for("law.docx"), encoding="utf-8")

    knowledge = load_knowledge_base(tmp_path, enabled=True)
    assert knowledge is not None
    citations = knowledge.citations()
    assert "T1#第一条" in citations
    assert "T1#第三条" in citations
    # 目录/编章节不单独成段
    assert all("目　　录" not in chunk.text for chunk in knowledge.chunks)
    third = next(chunk for chunk in knowledge.chunks if chunk.section == "第三条")
    assert third.heading == "第三条"
    assert "本编没有规定的" in third.text
    # 条文所属章节作为上下文保留，便于检索
    assert "第一章" in third.text


# ---------- 超长片段 ----------


def test_long_section_is_split_and_numbered(tmp_path: Path) -> None:
    body = "\n".join(f"这是第{i}段说明，用于测试超长片段切分。" * 8 for i in range(40))
    (tmp_path / "doc.md").write_text(f"## 长条款\n{body}\n", encoding="utf-8")
    (tmp_path / "manifest.yaml").write_text(MANIFEST_TEMPLATE, encoding="utf-8")

    knowledge = load_knowledge_base(tmp_path, enabled=True)
    assert knowledge is not None
    assert len(knowledge.chunks) > 1
    assert all(len(chunk.text) <= MAX_SECTION_CHARS for chunk in knowledge.chunks)
    assert knowledge.chunks[0].section == "s1"
    assert knowledge.chunks[1].section == "s1-2"
    assert len(knowledge.citations()) == len(knowledge.chunks)


def test_english_article_headers_are_recognised(tmp_path: Path) -> None:
    text = (
        "# Convention\n"
        "**Preamble**\n"
        "The States Parties to this Convention,\n"
        "***Article 1***\n"
        "This Convention applies to contracts of sale of goods.\n"
        "***Article 2***\n"
        "This Convention does not apply to sales of consumer goods.\n"
    )
    (tmp_path / "doc.md").write_text(text, encoding="utf-8")
    (tmp_path / "manifest.yaml").write_text(MANIFEST_TEMPLATE, encoding="utf-8")

    knowledge = load_knowledge_base(tmp_path, enabled=True)
    assert knowledge is not None
    headings = [chunk.heading for chunk in knowledge.chunks]
    assert "Article 1" in headings and "Article 2" in headings
    assert "Preamble" in headings


# ---------- 缓存 ----------


def test_cache_reuses_result_until_corpus_changes(tmp_path: Path) -> None:
    _write_corpus(tmp_path, MANIFEST_TEMPLATE)
    first = load_knowledge_base(tmp_path, enabled=True)
    second = load_knowledge_base(tmp_path, enabled=True)
    assert first is second

    (tmp_path / "doc.md").write_text("## 新条款\n内容已更新。\n", encoding="utf-8")
    third = load_knowledge_base(tmp_path, enabled=True)
    assert third is not first
    assert third is not None and third.chunks[0].heading == "新条款"


# ---------- 真实语料冒烟（缺失时跳过） ----------


@pytest.mark.skipif(
    not (REAL_KNOWLEDGE_DIR / "manifest.yaml").is_file(),
    reason="真实语料未提供",
)
def test_real_corpus_loads_and_covers_key_topics() -> None:
    knowledge = load_knowledge_base(REAL_KNOWLEDGE_DIR, enabled=True)
    assert knowledge is not None
    source_ids = {document.source_id for document in knowledge.documents}
    assert {"CISG-ZH", "CISG-EN", "INCOTERMS-2020", "CN-CIVIL-CODE", "RISK-REDLINE"} <= source_ids
    # DOCX 按条文切分，引用稳定可追溯
    assert "CN-CIVIL-CODE#第五百七十七条" in knowledge.citations()
    # 所有片段长度受控，引用不重复
    assert all(len(chunk.text) <= MAX_SECTION_CHARS for chunk in knowledge.chunks)
    assert len(knowledge.citations()) == len(knowledge.chunks)

    hits = knowledge.search("根本违约 实质剥夺", min_score=0.0)
    assert hits
    assert all(hit.citation in knowledge.citations() for hit in hits)

