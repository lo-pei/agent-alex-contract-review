"""`precheck_document` 节点：先判断上传对象是不是合同，再决定是否进入审查。

角色：`ingest_document` 之后的第一道闸门。
依赖：`app/services/document_type.py`（纯规则）、`app/schemas.py`。
约束：
- **不判风险、不碰规则等级**；只写 `document_check` 与状态；
- 解析已失败（`status == "failed"`）时原样放行，保留原有错误与提示，不覆盖成“非合同”；
- 判为“不是合同”时清空条款、置 `status="not_contract"`，并直接跳到 `build_report`
  （生成“未执行审查”的报告），绝不继续抽取/判级。
"""

from __future__ import annotations

from time import perf_counter
from typing import Literal

from app.schemas import ContractReviewState
from app.services.document_type import classify_document

NOT_CONTRACT_ERROR = "未执行审查：上传的文件不是合同，已停止规则判级与风险审查。"


def precheck_document(state: ContractReviewState) -> dict:
    started = perf_counter()

    def done(payload: dict) -> dict:
        return {
            **payload,
            "timings": {
                **state.timings,
                "precheck_document_ms": round((perf_counter() - started) * 1000, 2),
            },
        }

    if state.status == "failed" or not state.raw_text.strip():
        # 解析阶段已经报错：保持原样，交给后续节点（与旧行为一致）
        return done({})

    check = classify_document(state.raw_text)
    if check.is_contract:
        return done({"document_check": check})

    return done(
        {
            "document_check": check,
            "status": "not_contract",
            "clauses": [],
            "errors": [*state.errors, NOT_CONTRACT_ERROR],
        }
    )


def route_after_precheck(
    state: ContractReviewState,
) -> Literal["segment_clauses", "build_report"]:
    """不是合同 → 直接出“未执行”报告；其余情况照常走审查链路。"""
    if state.status == "not_contract":
        return "build_report"
    return "segment_clauses"
