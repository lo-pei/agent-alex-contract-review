"""LLM 服务：OpenAI 兼容接口 + 结构化输出 + 1 次修复重试 + 超时（ADR-003 §3.7 / ADR-013）。

角色：全项目唯一的 LLM 调用封装；节点只依赖 `StructuredLLM` 协议，测试用 Fake LLM。
依赖：`app/config.py`（默认模型/Key/超时/重试）、`langchain-openai`（仅真实实现）。
约束：
- LLM 只输出 Pydantic schema 定义的内容；schema 中没有 risk_level；
- 供应商不支持 `json_schema` 时回退 `function_calling`，校验不变；
- 失败最多 1 次修复重试（把错误回传模型），仍失败由调用方降级，不重试到底；
- 账号自带的模型配置（BYOK）只通过 `review_llm_scope()` 在**本次审查调用期间**生效，
  API Key 不写入图状态/checkpoint，也不出现在任何响应里。
"""

from __future__ import annotations

import hashlib
import threading
from collections import OrderedDict
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from app.config import settings

#: 修复提示的固定后缀；测试可据此断言“确实做了第二次调用”
REPAIR_SUFFIX = (
    "\n\n上一次输出未通过 schema 校验：{error}\n"
    "请只输出符合 schema 的 JSON，不要输出任何解释。"
)


class LLMError(RuntimeError):
    """LLM 调用失败的基类；节点捕获后降级，不让审查崩溃。"""


class LLMNotConfigured(LLMError):
    """没有配置 `LLM_API_KEY`，或供应商不可用。"""


class StructuredOutputError(LLMError):
    """重试后仍未得到符合 schema 的输出。"""


class StructuredLLM(Protocol):
    """节点依赖的最小接口；Fake LLM 只需实现 `model_id` 与 `invoke`。"""

    model_id: str

    def invoke[SchemaT: BaseModel](
        self, schema: type[SchemaT], system: str, user: str
    ) -> SchemaT: ...


@dataclass(frozen=True)
class LLMRuntime:
    """一次审查使用的模型配置（BYOK）；只在进程内传递，不进入图状态。"""

    provider: str
    base_url: str
    model: str
    api_key: str
    timeout_seconds: int = 60


class LLMProbe(BaseModel):
    """连通性探测的最小 schema：模型只需回一个布尔值。"""

    model_config = ConfigDict(extra="forbid")

    ok: bool


#: 按 `review_id` 登记的运行时配置（HITL 暂停期间保留，终态后清理）
_RUNTIME: dict[str, LLMRuntime] = {}
_RUNTIME_LOCK = threading.Lock()
#: 当前正在执行的审查；节点里的 `get_llm()` 靠它找到本次审查的模型配置
_ACTIVE_REVIEW: ContextVar[str | None] = ContextVar("alex_active_review", default=None)
#: 已构造的客户端缓存（键含 Key 摘要，避免把明文 Key 当字典键）
_CLIENTS: OrderedDict[tuple[str, str, str], StructuredLLM] = OrderedDict()
_CLIENT_LOCK = threading.Lock()
MAX_CACHED_CLIENTS = 8

PROBE_SYSTEM = "你是连通性检查程序。只回答 ok=true，不要输出其他内容。"
PROBE_USER = "请返回 ok=true，表示接口可用。"


def register_llm_runtime(review_id: str, runtime: LLMRuntime) -> None:
    with _RUNTIME_LOCK:
        _RUNTIME[review_id] = runtime


def get_llm_runtime(review_id: str) -> LLMRuntime | None:
    """读取已登记的运行时配置（HITL 恢复时用），没有则返回 None。"""
    with _RUNTIME_LOCK:
        return _RUNTIME.get(review_id)


def clear_llm_runtime(review_id: str) -> None:
    with _RUNTIME_LOCK:
        _RUNTIME.pop(review_id, None)


@contextmanager
def review_llm_scope(
    review_id: str, runtime: LLMRuntime | None = None
) -> Iterator[None]:
    """在本次图调用期间启用（可选的）用户模型配置。

    必须包住 `graph.invoke()`：LangGraph 同步执行节点时仍在当前线程/上下文，
    因此节点里的 `get_llm()` 能读到 `review_id`；调用结束后上下文自动还原。
    """
    if runtime is not None:
        register_llm_runtime(review_id, runtime)
    token = _ACTIVE_REVIEW.set(review_id)
    try:
        yield
    finally:
        _ACTIVE_REVIEW.reset(token)


def _looks_like_unsupported(exc: Exception) -> bool:
    """供应商不支持 json_schema / response_format 时的兜底判断。"""
    message = str(exc).casefold()
    keywords = ("json_schema", "response_format", "not supported", "unsupported")
    return any(keyword in message for keyword in keywords)


class OpenAICompatibleLLM:
    """OpenAI 兼容 Chat Completions 结构化输出（不绑定厂商）。"""

    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        api_key: str,
        timeout_seconds: int,
    ) -> None:
        from langchain_openai import ChatOpenAI

        self.model_id = model
        self._chat = ChatOpenAI(
            model=model,
            base_url=base_url,
            api_key=api_key,
            temperature=0,
            timeout=timeout_seconds,
            max_retries=0,
        )
        self._runnables: dict[tuple[str, type[BaseModel]], object] = {}

    def _runnable[SchemaT: BaseModel](self, schema: type[SchemaT], method: str):
        key = (method, schema)
        if key not in self._runnables:
            self._runnables[key] = self._chat.with_structured_output(schema, method=method)
        return self._runnables[key]

    def invoke[SchemaT: BaseModel](
        self, schema: type[SchemaT], system: str, user: str
    ) -> SchemaT:
        messages = [("system", system), ("human", user)]
        last_error: Exception | None = None

        for method in ("json_schema", "function_calling"):
            try:
                result = self._runnable(schema, method).invoke(messages)
            except Exception as exc:  # noqa: BLE001 - 供应商异常类型不统一
                last_error = exc
                if method == "json_schema" and _looks_like_unsupported(exc):
                    continue
                raise StructuredOutputError(
                    f"LLM 结构化输出失败（{method}）：{type(exc).__name__}: {exc}"
                ) from exc

            if not isinstance(result, schema):
                last_error = StructuredOutputError(
                    f"LLM 返回类型不是 {schema.__name__}：{type(result).__name__}"
                )
                raise last_error
            return result

        raise StructuredOutputError(f"LLM 不支持结构化输出：{last_error}")


def clear_llm_cache() -> None:
    """清空客户端缓存（测试与环境变量变更后调用）。"""
    with _CLIENT_LOCK:
        _CLIENTS.clear()


def _client_for(runtime: LLMRuntime) -> StructuredLLM:
    key = (
        runtime.base_url,
        runtime.model,
        hashlib.sha256(runtime.api_key.encode("utf-8")).hexdigest()[:12],
    )
    with _CLIENT_LOCK:
        cached = _CLIENTS.get(key)
        if cached is not None:
            _CLIENTS.move_to_end(key)
            return cached

    client = OpenAICompatibleLLM(
        model=runtime.model,
        base_url=runtime.base_url,
        api_key=runtime.api_key,
        timeout_seconds=runtime.timeout_seconds,
    )
    with _CLIENT_LOCK:
        _CLIENTS[key] = client
        _CLIENTS.move_to_end(key)
        while len(_CLIENTS) > MAX_CACHED_CLIENTS:
            _CLIENTS.popitem(last=False)
    return client


def get_llm() -> StructuredLLM:
    """取本次审查的模型客户端。

    优先级：当前审查登记的用户配置（BYOK）> 环境变量默认配置。
    都没有时显式抛 `LLMNotConfigured`，由节点降级（抽取降级 / 解释回退规则理由）。
    """
    review_id = _ACTIVE_REVIEW.get()
    if review_id is not None:
        with _RUNTIME_LOCK:
            runtime = _RUNTIME.get(review_id)
        if runtime is not None:
            return _client_for(runtime)

    if not settings.llm_api_key.strip():
        raise LLMNotConfigured(
            "未配置大模型：要素抽取已降级、解释回退规则理由。"
            "可在页面左下角“API 配置”里填写自己的模型 Key，或在 .env 设置 LLM_API_KEY。"
        )
    return _client_for(
        LLMRuntime(
            provider=settings.llm_provider,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            timeout_seconds=settings.llm_timeout_seconds,
        )
    )


get_llm.cache_clear = clear_llm_cache  # type: ignore[attr-defined]


def probe_llm(runtime: LLMRuntime) -> LLMProbe:
    """连通性探测：真实发一次最小请求；异常向上抛，由 API 转成可读错误。"""
    client = _client_for(runtime)
    result, _attempts = call_structured(
        client, LLMProbe, system=PROBE_SYSTEM, user=PROBE_USER
    )
    return result


def call_structured[SchemaT: BaseModel](
    llm: StructuredLLM,
    schema: type[SchemaT],
    *,
    system: str,
    user: str,
    max_repairs: int | None = None,
) -> tuple[SchemaT, int]:
    """调用并校验；失败时把错误回传做 1 次修复。返回 `(结果, 实际尝试次数)`。

    调用方负责捕获 `LLMError` 并降级（字段置 null / 记录 `degraded_steps`）。
    """
    repairs = settings.llm_max_repair_retries if max_repairs is None else max_repairs
    attempts = 1 + max(0, repairs)
    last_error: Exception | None = None
    prompt = user

    for attempt in range(1, attempts + 1):
        try:
            result = llm.invoke(schema, system, prompt)
        except LLMError:
            raise
        except Exception as exc:  # noqa: BLE001 - 网络/超时/解析异常都要转成可降级错误
            last_error = exc
            prompt = user + REPAIR_SUFFIX.format(error=f"{type(exc).__name__}: {exc}")
            continue

        if not isinstance(result, schema):
            last_error = StructuredOutputError(
                f"LLM 返回类型不是 {schema.__name__}：{type(result).__name__}"
            )
            prompt = user + REPAIR_SUFFIX.format(error=str(last_error))
            continue
        return result, attempt

    raise StructuredOutputError(
        f"LLM 结构化输出失败（已尝试 {attempts} 次）：{type(last_error).__name__}: {last_error}"
    ) from last_error
