"""测试共享 fixture：样例合同与“ingest + segment 后”的状态。"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.nodes.ingest import ingest_document
from app.nodes.segment import segment_clauses
from app.schemas import ContractReviewState

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLES = PROJECT_ROOT / "data" / "samples"


def make_state(path: Path) -> ContractReviewState:
    state = ContractReviewState(
        review_id="test-review",
        source_filename=path.name,
        source_path=str(path),
    )
    state = ContractReviewState.model_validate({**state.model_dump(), **ingest_document(state)})
    return ContractReviewState.model_validate({**state.model_dump(), **segment_clauses(state)})


@pytest.fixture
def sample_path() -> Path:
    return SAMPLES / "sample_sales_contract.txt"


@pytest.fixture
def clean_sample_path() -> Path:
    return SAMPLES / "sample_clean_contract.txt"


@pytest.fixture
def sample_state(sample_path: Path) -> ContractReviewState:
    return make_state(sample_path)


@pytest.fixture
def clean_state(clean_sample_path: Path) -> ContractReviewState:
    return make_state(clean_sample_path)
