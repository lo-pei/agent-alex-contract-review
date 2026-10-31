"""审查过程进度：给前端“处理过程”面板用的轻量事件流（ADR-017）。

角色：每个图节点开始时写一条 `running` 事件，结束时把同一条改成 `done`（带耗时与摘要）；
前端在等待上传结果时轮询 `GET /api/reviews/{id}/progress`，把这一串事件渲染成
“正在启动 → 读取文件 → 切分条款 → …”的过程列表（像对话产品里的“思考过程”）。

约束：
- **只描述过程，不参与判级**：事件里不写 `risk_level`，等级仍只来自规则结果；
- 摘要只复述节点自己产出的数量/状态（条款数、命中数等），不改写、不推断；
- 只保留最近若干次审查的事件在内存里（进程重启即丢）；过程可以丢，结论不能丢；
- 不写 checkpoint、不进报告，因此不影响任何既有结果与幂等语义。
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from datetime import UTC, datetime
from time import perf_counter

#: 节点 id → 展示名（与 `app/graph.py` 注册的节点一一对应）
NODE_LABELS: dict[str, str] = {
    "ingest_document": "读取文件",
    "precheck_document": "判断是不是合同",
    "segment_clauses": "切分条款",
    "extract_fields": "抽取关键要素",
    "validate_extraction": "校验抽取结果",
    "expert_payment": "付款专家",
    "expert_delivery": "交付专家",
    "expert_dispute": "争议专家",
    "collect_expert_findings": "汇总专家意见",
    "evaluate_rules": "规则判定",
    "research_tools": "检索补充材料",
    "human_review": "人工确认",
    "explain_risks": "生成解释",
    "build_report": "生成报告",
}

#: 节点运行前的一句说明（前端每条步骤的第二行）
NODE_HINTS: dict[str, str] = {
    "ingest_document": "解析 PDF / Word / 文本，建立页码与原文位置。",
    "precheck_document": "先确认这份文件是合同；不是合同就不判级。",
    "segment_clauses": "按标题把合同切成条款，作为逐条审查的最小单位。",
    "extract_fields": "抽取金额、期限、单据等要素；没有模型时显式降级。",
    "validate_extraction": "核对抽取值能否在原文定位，定位不到就降级。",
    "expert_payment": "付款专家并行给出参考意见（不判级）。",
    "expert_delivery": "交付专家并行给出参考意见（不判级）。",
    "expert_dispute": "争议专家并行给出参考意见（不判级）。",
    "collect_expert_findings": "汇总三个专家的参考意见。",
    "evaluate_rules": "用 Python 规则逐条判定等级——等级的唯一来源。",
    "research_tools": "按规则命中的问题检索补充材料。",
    "human_review": "红色风险必须人工确认，确认后才继续。",
    "explain_risks": "依据规则结果与原文生成解释，并过质量门。",
    "build_report": "汇总为可追溯报告。",
}

#: 最多保留多少次审查的过程（超出丢最旧的）
MAX_REVIEWS = 40
#: 单次审查最多保留多少条事件（防止异常循环把内存撑爆）
MAX_EVENTS = 80


class ProgressStore:
    """进程内过程事件表；线程安全（图节点可能并行）。"""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._items: OrderedDict[str, list[dict]] = OrderedDict()

    def begin(self, review_id: str, node: str) -> None:
        """记录节点开始；同名节点（并行专家）各自一条，按开始顺序排列。"""
        if not review_id or node not in NODE_LABELS:
            return
        event = {
            "node": node,
            "label": NODE_LABELS[node],
            "hint": NODE_HINTS.get(node, ""),
            "status": "running",
            "detail": "",
            "duration_ms": 0.0,
            "started_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "_started": perf_counter(),
        }
        with self._lock:
            items = self._items.setdefault(review_id, [])
            items.append(event)
            del items[:-MAX_EVENTS]
            self._items.move_to_end(review_id)
            while len(self._items) > MAX_REVIEWS:
                self._items.popitem(last=False)

    def finish(
        self,
        review_id: str,
        node: str,
        *,
        status: str = "done",
        detail: str = "",
    ) -> None:
        """把该节点最近一条 `running` 事件收尾；没有就补一条（容错）。"""
        if not review_id or node not in NODE_LABELS:
            return
        with self._lock:
            items = self._items.get(review_id) or []
            target = None
            for event in reversed(items):
                if event["node"] == node and event["status"] == "running":
                    target = event
                    break
            if target is None:
                self.begin(review_id, node)
                items = self._items.get(review_id) or []
                if not items:
                    return
                target = items[-1]
            started = target.pop("_started", None)
            if started is not None:
                target["duration_ms"] = round((perf_counter() - started) * 1000, 2)
            target["status"] = status
            target["detail"] = detail

    def events(self, review_id: str) -> list[dict]:
        """返回可 JSON 序列化的事件副本（去掉内部计时句柄）。"""
        with self._lock:
            items = self._items.get(review_id) or []
            return [{key: value for key, value in event.items() if not key.startswith("_")}
                    for event in items]

    def any_running(self, review_id: str) -> bool:
        return any(event["status"] == "running" for event in self.events(review_id))

    def clear(self, review_id: str) -> None:
        with self._lock:
            self._items.pop(review_id, None)


_STORE = ProgressStore()


def progress_store() -> ProgressStore:
    return _STORE
