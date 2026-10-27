"""LLM 服务：OpenAI 兼容接口 + 结构化输出 + 1 次修复重试 + 超时（ADR-003 §3.7）。

角色：全项目唯一的 LLM 调用封装；节点只依赖 `StructuredLLM` 协议，测试用 Fake LLM。
依赖：`app/config.py`（模型/Key/超时/重试）、`langchain-openai`（仅真实实现）。
约束：
- LLM 只输出 Pydantic schema 定义的内容；schema 中没有 risk_level；
- 供应商不支持 `json_schema` 时回退 `function_calling`，校验不变；
- 失败最多 1 次修复重试（把错误回传模型），仍失败由调用方降级，不重试到底。
"""

from __future__ import annotations

from functools import lru_cache
from typing import Protocol

from pydantic import BaseModel

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


@lru_cache(maxsize=1)
def get_llm() -> StructuredLLM:
    """按环境变量创建 LLM；没有 Key 时显式抛 `LLMNotConfigured`，由节点降级。"""
    if not settings.llm_api_key.strip():
        raise LLMNotConfigured(
            "未配置 LLM_API_KEY：要素抽取已降级。复制 .env.example 为 .env 并填写 Key 后重试。"
        )
    return OpenAICompatibleLLM(
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        timeout_seconds=settings.llm_timeout_seconds,
    )


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
