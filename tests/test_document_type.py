"""文档类型闸门：论文 / 法规不得被当成合同进入判级。

分两层：
- 纯规则：`classify_document` 对合成样本与仓库内 50 份合同语料的判定；
- 集成：图在 `precheck_document` 处停下，不产出任何风险结论。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.graph_demo import run_review
from app.services.document_type import classify_document

ROOT = Path(__file__).resolve().parents[1]

#: 典型论文开头/结构（不是任何真实文件，只复用真实论文的排版特征）
PAPER = """全球比较下的我国人工智能立法

丁晓东

摘要：本文认为，人工智能立法应当兼顾创新与安全，并在比较法视野下审视我国立法路径。
关键词：人工智能；立法；比较法；风险治理

一、问题的提出
本研究采用比较法的方法，梳理欧盟、美国与我国的立法经验。本文提出三层治理框架，
并试图回答监管强度与产业发展的关系问题。

二、文献综述
既有研究多集中于算法透明与数据治理（See, e.g., Müller et al., 2021）。
参考文献
[1] 丁晓东. 人工智能与法学研究[J]. 法学研究, 2022.
[2] Müller, P. et al. Regulating AI. Oxford, 2021.
"""

#: 法规条文：有“第 X 条”但没有买卖双方、合同编号与签署语
LAW = """中华人民共和国民法典

第一编 总则

第一章 基本规定

第一条 为了保护民事主体的合法权益，维护社会和经济秩序，根据宪法，制定本法。

第二条 民法调整平等主体的自然人、法人和非法人组织之间的人身关系和财产关系。

第二章 自然人

第十三条 自然人从出生时起到死亡时止，具有民事权利能力，依法享有民事权利，承担民事义务。

第十四条 自然人的民事权利能力一律平等。

依照本法相关规定，本章所称民事权利能力不因性别、民族、职业而有所不同。
"""


def test_paper_is_rejected() -> None:
    check = classify_document(PAPER)
    assert check.is_contract is False
    assert check.confidence >= 0.8
    assert any("学术" in reason for reason in check.reasons)
    assert any("不是" in hint or "其他流程" in hint for hint in check.hints)


def test_law_text_is_rejected() -> None:
    check = classify_document(LAW)
    assert check.is_contract is False
    assert any("法规" in reason or "法律" in reason for reason in check.reasons)


def test_too_short_text_is_rejected() -> None:
    check = classify_document("合同")
    assert check.is_contract is False
    assert any("过短" in reason for reason in check.reasons)


@pytest.mark.parametrize(
    "directory",
    [
        "data/contracts",
        "data/contracts_holdout",
        "data/contracts_holdout2",
        "data/contracts_holdout3",
        "data/contracts_holdout4",
    ],
)
def test_contract_corpus_passes_gate(directory: str) -> None:
    """宁可放过也不要误杀：仓库内每一份合同都必须通过类型闸门。"""
    folder = ROOT / directory
    if not folder.is_dir():
        pytest.skip(f"{directory} 不存在")
    rejected = []
    for path in sorted(folder.glob("*")):
        if path.suffix.lower() not in {".txt", ".md"}:
            continue
        check = classify_document(path.read_text(encoding="utf-8", errors="replace"))
        if not check.is_contract:
            rejected.append((path.name, check.reasons))
    assert rejected == []


def test_samples_pass_gate() -> None:
    for name in ("sample_sales_contract.txt", "sample_clean_contract.txt"):
        path = ROOT / "data" / "samples" / name
        check = classify_document(path.read_text(encoding="utf-8"))
        assert check.is_contract is True, (name, check.reasons)


def test_graph_stops_on_paper(tmp_path: Path) -> None:
    """论文上传后：不切条款、不抽取、不判级、不产出风险结论。"""
    path = tmp_path / "paper.md"
    path.write_text(PAPER, encoding="utf-8")

    state = run_review(path)

    assert state.status == "not_contract"
    assert state.overall_level == "unknown"
    assert state.clauses == []
    assert state.rule_evaluations == []
    assert state.extraction_status == "skipped"
    assert state.document_check is not None and state.document_check.is_contract is False

    assert state.report is not None
    assert state.report.status == "not_contract"
    assert state.report.findings == []
    assert "未执行合同审查" in state.report.summary
    assert any("没有被识别为合同" in item for item in state.report.limitations)


def test_graph_continues_on_real_contract(sample_path: Path) -> None:
    state = run_review(sample_path)
    assert state.document_check is not None
    assert state.document_check.is_contract is True
    # 有红色风险 → 停在 interrupt 等人工确认（未传 decision 时 status 仍是 running）
    assert state.status in {"running", "approved", "completed"}
    assert len(state.rule_evaluations) == 13
    assert state.report is None or state.report.status != "not_contract"
