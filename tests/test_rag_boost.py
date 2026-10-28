"""检索加权（提问点名条号 / 来源）与中文条号互转的单元测试。

背景：检索评测（ISSUE-018）显示条号题 strict R@1 只有 0.16，根因是“问第584条时
解读稿与相邻条文压过条文原文”。这里锁住三条行为：
1. 点名条号 → 该条文片段排第一；
2. 点名来源 → 该来源加权，但**不**过滤掉其他来源（跨法域题仍能召回）；
3. 没有线索 → 加权全为 1.0，与原 BM25 完全一致。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.chinese_numbers import (
    NumberFormatError,
    from_chinese_number,
    to_chinese_number,
)
from app.services.rag import (
    _article_numbers,
    _query_boosts,
    load_knowledge_base,
)

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge"


@pytest.fixture(scope="module")
def knowledge():
    return load_knowledge_base(KNOWLEDGE_DIR, enabled=True)


def test_chinese_number_roundtrip() -> None:
    for value in (1, 7, 10, 12, 25, 39, 49, 68, 101, 110, 584, 580, 1050, 1260):
        assert from_chinese_number(to_chinese_number(value)) == value
    assert to_chinese_number(110) == "一百一十"
    assert to_chinese_number(101) == "一百零一"
    assert to_chinese_number(1050) == "一千零五十"
    assert to_chinese_number(12) == "十二"

    with pytest.raises(NumberFormatError):
        to_chinese_number(0)
    with pytest.raises(NumberFormatError):
        to_chinese_number(10000)
    with pytest.raises(NumberFormatError):
        from_chinese_number("第584条")
    with pytest.raises(NumberFormatError):
        from_chinese_number("")


def test_article_numbers_ignore_clause_suffix() -> None:
    assert _article_numbers("《民法典》第584条可预见性") == (584,)
    assert _article_numbers("CISG第39(2)条的两年期限") == (39,)
    assert _article_numbers("买方依据第49(1)(b)条宣告无效") == (49,)
    assert _article_numbers("第2条第2款最密切联系") == (2,)
    assert _article_numbers("第五百八十四条与第580条") == (584, 580)
    # 没有“第…条”就不是条号线索（“第74题”不是条文）
    assert _article_numbers("第74题怎么做") == ()
    assert _article_numbers("根本违约的判断标准") == ()


def test_article_query_ranks_that_article_first(knowledge) -> None:
    top = knowledge.search("《民法典》第584条可预见性的时间点是订立合同时还是违约时", top_k=3)
    assert top, "条号题不应召回空"
    assert top[0].citation == "CN-CIVIL-CODE#第五百八十四条"

    top = knowledge.search("第3条是否允许默示选择准据法", top_k=3)
    assert top[0].citation == "CN-LAW-APPLICATION#第三条"


def test_source_hint_boosts_but_never_filters(knowledge) -> None:
    hits = knowledge.search("FOB 与 CISG 在风险转移上的分工", top_k=5)
    sources = {chunk.source_id for chunk in hits}
    assert len(sources) >= 2, f"点名多个来源时不应只留一个：{sources}"
    assert any(source.startswith("CISG") for source in sources)
    assert "INCOTERMS-2020" in sources


def test_no_hint_keeps_pure_bm25(knowledge) -> None:
    boosts = _query_boosts("预付款比例过高有什么风险", knowledge.chunks)
    assert set(boosts) == {1.0}

    hint_boosts = _query_boosts("《民法典》第584条", knowledge.chunks)
    assert max(hint_boosts) > 1.0


def test_boosted_search_is_deterministic(knowledge) -> None:
    first = [chunk.citation for chunk in knowledge.search("CISG第25条根本违约", top_k=5)]
    second = [chunk.citation for chunk in knowledge.search("CISG第25条根本违约", top_k=5)]
    assert first == second
    assert first[0].startswith("CISG-"), "点名 CISG 第 25 条时首条应来自 CISG"
