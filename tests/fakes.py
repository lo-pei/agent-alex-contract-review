"""测试用 Fake LLM：不联网、不需要 Key，可按剧本返回结构化对象或抛异常。

角色：`extract` / `llm` / 图端到端测试的共享替身，实现 `app.services.llm.StructuredLLM` 协议。
约束：只替身“模型调用”这一层，Pydantic 校验、修复重试、降级逻辑仍走真实代码。
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from app.schemas import EXTRACTED_FIELDS, ExtractedFieldSet, FieldValue

Handler = Callable[[type[BaseModel], str, str], Any]

_CLAUSE_ID_PATTERN = re.compile(r"条款编号：(\S+)")


class FakeLLM:
    """`invoke(schema, system, user)` 交给 `handler`；返回值是 Exception 时抛出。"""

    model_id = "fake-llm"

    def __init__(self, handler: Handler) -> None:
        self._handler = handler
        self.calls: list[dict[str, str]] = []

    def invoke(self, schema: type[BaseModel], system: str, user: str) -> BaseModel:
        self.calls.append({"system": system, "user": user})
        result = self._handler(schema, system, user)
        if isinstance(result, Exception):
            raise result
        return result


def clause_id_of(user_prompt: str) -> str | None:
    match = _CLAUSE_ID_PATTERN.search(user_prompt)
    return match.group(1) if match else None


def field(value: str | int | float | None = None, quote: str | None = None) -> FieldValue:
    return FieldValue(value=value, quote=quote)


def field_set(**values: FieldValue) -> ExtractedFieldSet:
    """只填指定字段，其余字段保持默认（value/quote 均为 null）。"""
    unknown = set(values) - set(EXTRACTED_FIELDS)
    if unknown:
        raise ValueError(f"未知字段：{sorted(unknown)}")
    return ExtractedFieldSet(**values)


def by_clause(mapping: dict[str, ExtractedFieldSet]) -> FakeLLM:
    """按 `条款编号` 返回固定抽取结果；未列出的条款返回全 null。"""

    def handler(schema: type[BaseModel], system: str, user: str) -> ExtractedFieldSet:
        return mapping.get(clause_id_of(user) or "", ExtractedFieldSet())

    return FakeLLM(handler)
