"""LLM 服务测试：结构化输出、修复重试、异常不再重试、未配置降级（ADR-003 §3.7）。"""

from __future__ import annotations

from dataclasses import replace

import pytest
from pydantic import BaseModel

from app.config import settings
from app.services import llm as llm_module
from app.services.llm import (
    LLMError,
    LLMNotConfigured,
    StructuredOutputError,
    call_structured,
    get_llm,
)
from tests.fakes import FakeLLM


class _Payload(BaseModel):
    name: str
    score: int = 0


def test_returns_first_valid_result() -> None:
    fake = FakeLLM(lambda schema, system, user: _Payload(name="ok"))
    result, attempts = call_structured(fake, _Payload, system="s", user="u")

    assert isinstance(result, _Payload)
    assert result.name == "ok"
    assert attempts == 1
    assert len(fake.calls) == 1


def test_repairs_after_exception() -> None:
    calls = {"count": 0}

    def handler(schema, system, user):
        calls["count"] += 1
        if calls["count"] == 1:
            return ValueError("模型返回了非 JSON")
        return _Payload(name="fixed")

    fake = FakeLLM(handler)
    result, attempts = call_structured(fake, _Payload, system="s", user="u", max_repairs=1)

    assert result.name == "fixed"
    assert attempts == 2
    assert len(fake.calls) == 2
    assert "上一次输出未通过 schema 校验" in fake.calls[1]["user"]
    assert "模型返回了非 JSON" in fake.calls[1]["user"]


def test_repairs_after_wrong_type() -> None:
    calls = {"count": 0}

    def handler(schema, system, user):
        calls["count"] += 1
        if calls["count"] == 1:
            return {"name": "not-a-model"}
        return _Payload(name="fixed")

    fake = FakeLLM(handler)
    result, attempts = call_structured(fake, _Payload, system="s", user="u", max_repairs=1)

    assert result.name == "fixed"
    assert attempts == 2


def test_gives_up_after_repairs_exhausted() -> None:
    fake = FakeLLM(lambda schema, system, user: ValueError("总是失败"))

    with pytest.raises(StructuredOutputError, match="已尝试 2 次"):
        call_structured(fake, _Payload, system="s", user="u", max_repairs=1)
    assert len(fake.calls) == 2


def test_zero_repairs_means_single_attempt() -> None:
    fake = FakeLLM(lambda schema, system, user: ValueError("坏输出"))

    with pytest.raises(StructuredOutputError, match="已尝试 1 次"):
        call_structured(fake, _Payload, system="s", user="u", max_repairs=0)
    assert len(fake.calls) == 1


def test_llm_error_is_not_retried() -> None:
    fake = FakeLLM(lambda schema, system, user: LLMNotConfigured("无 Key"))

    with pytest.raises(LLMNotConfigured):
        call_structured(fake, _Payload, system="s", user="u", max_repairs=1)
    assert len(fake.calls) == 1


def test_get_llm_without_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm_module, "settings", replace(settings, llm_api_key=""))
    llm_module.get_llm.cache_clear()
    try:
        with pytest.raises(LLMNotConfigured, match="LLM_API_KEY"):
            get_llm()
    finally:
        llm_module.get_llm.cache_clear()


def test_llm_error_hierarchy() -> None:
    assert issubclass(LLMNotConfigured, LLMError)
    assert issubclass(StructuredOutputError, LLMError)
