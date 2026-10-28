"""检索评测（ISSUE-018）的自检：映射正确、gold 不过期、指标算得对。

约束：
- 只用 Fake/真实本地语料，不联网、不调 LLM；
- `test_gold_matches_current_corpus` 是回归守卫：语料一改就会失败，提示重建 gold，
  避免拿旧 gold 报新召回率。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.chinese_numbers import NumberFormatError
from app.services.rag import load_knowledge_base
from eval.rag_eval import score
from eval.rag_gold import (
    GOLD_PATH,
    GoldConfigError,
    build_gold,
    cn_number,
    load_label_map,
    parse_questions,
)

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge"


@pytest.fixture(scope="module")
def knowledge():
    return load_knowledge_base(KNOWLEDGE_DIR, enabled=True)


def test_cn_number_matches_legal_numbering() -> None:
    assert cn_number(1) == "一"
    assert cn_number(9) == "九"
    assert cn_number(10) == "十"
    assert cn_number(12) == "十二"
    assert cn_number(20) == "二十"
    assert cn_number(25) == "二十五"
    assert cn_number(110) == "一百一十"
    assert cn_number(101) == "一百零一"
    assert cn_number(580) == "五百八十"
    assert cn_number(584) == "五百八十四"
    assert cn_number(1050) == "一千零五十"
    assert cn_number(1260) == "一千二百六十"

    with pytest.raises(NumberFormatError):
        cn_number(0)
    with pytest.raises(NumberFormatError):
        cn_number(10000)


def test_parse_questions_reads_all_rows() -> None:
    questions = parse_questions()
    assert len(questions) == 100
    assert [item.id for item in questions] == list(range(1, 101))
    first = questions[0]
    assert first.group.startswith("一、CISG")
    assert first.labels == ("CISG-25",)
    assert "根本违约" in first.section_hint


def test_label_map_rejects_unknown_shape(tmp_path: Path) -> None:
    broken = tmp_path / "map.yaml"
    broken.write_text("version: 2\nlabels: {}\ngaps: {}\n", encoding="utf-8")
    with pytest.raises(GoldConfigError):
        load_label_map(broken)

    bad_regex = tmp_path / "bad.yaml"
    bad_regex.write_text(
        "version: 1\nlabels:\n  X:\n    - source: A\n      heading: '([unclosed'\ngaps: {}\n",
        encoding="utf-8",
    )
    with pytest.raises(GoldConfigError):
        load_label_map(bad_regex)


def test_gold_resolves_generic_and_curated_labels(knowledge) -> None:
    gold = build_gold(knowledge, parse_questions(), load_label_map())
    by_id = {item["id"]: item for item in gold["questions"]}

    # 95 道可评测，5 道因语料未收录对应文本被排除（见 rag_label_map.yaml 的 gaps）
    assert gold["resolved_count"] == 95
    assert gold["unresolved_count"] == 5
    assert {item["id"] for item in gold["questions"] if not item["expected"]} == {
        42,
        69,
        86,
        87,
        88,
    }

    # 通用条号：CISG 中英 + 解读稿三路；《民法典》按中文条号
    assert {"CISG-ZH#s27", "CISG-EN#s26", "CISG-KEY#s25"} == set(by_id[1]["expected"])
    assert "CN-CIVIL-CODE#第五百八十四条" in by_id[76]["expected"]
    assert "CN-LAW-APPLICATION#第四十一条" in by_id[66]["expected"]
    assert "SPC-CONTRACT-2023#第一条" in by_id[80]["expected"]
    assert "SPC-CONTRACT-2023#前言" in by_id[85]["expected"]

    # Incoterms 整理稿按主题标题定位，不按 A/B 条号
    assert "INCOTERMS-2020#s12" in by_id[55]["expected"]
    assert "INCOTERMS-2020#s16" in by_id[53]["expected"]
    # 红线清单按标题定位
    assert "RISK-REDLINE#s11" in by_id[90]["expected"]

    # strict 剔除解读稿，lenient 保留
    assert by_id[1]["strict"] == ["CISG-ZH#s27", "CISG-EN#s26"]
    assert "CISG-KEY#s25" in by_id[1]["expected"]


def test_committed_gold_matches_current_corpus(knowledge) -> None:
    """语料或题目变更后必须 `python -m eval.rag_gold --write`，否则 gold 会静默过期。"""
    committed = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    rebuilt = build_gold(knowledge, parse_questions(), load_label_map())
    assert committed["question_count"] == rebuilt["question_count"]
    expected_committed = {item["id"]: sorted(item["expected"]) for item in committed["questions"]}
    expected_rebuilt = {item["id"]: sorted(item["expected"]) for item in rebuilt["questions"]}
    assert expected_committed == expected_rebuilt

    available = knowledge.citations()
    missing = {
        citation
        for item in committed["questions"]
        for citation in item["expected"]
        if citation not in available
    }
    assert not missing


def test_score_math_on_synthetic_gold() -> None:
    gold = {
        "questions": [
            {"id": 1, "group": "甲", "question": "q1", "expected": ["A#1"], "strict": ["A#1"]},
            {"id": 2, "group": "甲", "question": "q2", "expected": ["A#2"], "strict": ["A#2"]},
            {"id": 3, "group": "乙", "question": "q3", "expected": ["B#1"], "strict": ["B#1"]},
            {
                "id": 4,
                "group": "乙",
                "question": "q4",
                "expected": [],
                "strict": [],
                "unresolved": [],
            },
        ]
    }
    ranked = {
        1: ["A#1", "X"],
        2: ["X", "A#2"],
        3: ["X", "Y", "Z", "B#1"],
        4: ["X"],
    }
    result = score(gold, ranked, ks=(1, 3, 5))

    assert result["denominator"] == 3
    assert result["unresolved_count"] == 1
    assert result["overall"]["lenient"]["recall_at"] == {"1": 0.3333, "3": 0.6667, "5": 1.0}
    assert result["overall"]["lenient"]["mrr"] == round((1 + 0.5 + 0.25) / 3, 4)
    assert result["overall"]["lenient"]["not_found"] == 0
    assert result["by_group"]["甲"]["lenient"]["recall_at"]["1"] == 0.5
    assert [item["id"] for item in result["misses_beyond_k"]] == []
    assert [item["id"] for item in result["not_top1"]] == [2, 3]
