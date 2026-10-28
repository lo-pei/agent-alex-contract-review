"""大模型厂商目录：前端“API 配置”下拉框的唯一事实来源（ADR-013）。

角色：把常见的 OpenAI 兼容厂商整理成可选配置，减少用户手填 base_url/model 的成本。
依赖：无项目内依赖；被 `app/services/accounts.py` 与 `app/api.py` 引用。
约束：
- 只收录 **OpenAI 兼容** Chat Completions 接口；不集成本项目未验证的私有 SDK；
- 这里只给默认值，用户仍可改 base_url/model（`provider="custom"`）；
- 判级与 HITL 不受影响：换模型只影响抽取质量与解释措辞。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Provider:
    id: str
    label: str
    base_url: str
    models: tuple[str, ...]
    note: str = ""
    #: 本地推理服务（Ollama 等）允许不填 Key
    key_optional: bool = False


PROVIDERS: tuple[Provider, ...] = (
    Provider(
        id="openai",
        label="OpenAI",
        base_url="https://api.openai.com/v1",
        models=("gpt-4.1-mini", "gpt-4o-mini", "gpt-4.1"),
        note="需要 OpenAI 平台 API Key。",
    ),
    Provider(
        id="deepseek",
        label="DeepSeek",
        base_url="https://api.deepseek.com/v1",
        models=("deepseek-chat", "deepseek-reasoner"),
        note="OpenAI 兼容接口；中文合同解释表现稳定。",
    ),
    Provider(
        id="moonshot",
        label="Moonshot / Kimi",
        base_url="https://api.moonshot.cn/v1",
        models=("moonshot-v1-8k", "moonshot-v1-32k", "kimi-k2-0905-preview"),
        note="长上下文模型，适合长合同。",
    ),
    Provider(
        id="zhipu",
        label="智谱 GLM",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        models=("glm-4-flash", "glm-4-plus", "glm-4-air"),
        note="智谱开放平台的 OpenAI 兼容入口。",
    ),
    Provider(
        id="dashscope",
        label="阿里云百炼 / 通义千问",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        models=("qwen-plus", "qwen-max", "qwen-turbo"),
        note="使用百炼的兼容模式地址与 API Key。",
    ),
    Provider(
        id="siliconflow",
        label="硅基流动 SiliconFlow",
        base_url="https://api.siliconflow.cn/v1",
        models=(
            "Qwen/Qwen2.5-72B-Instruct",
            "deepseek-ai/DeepSeek-V3",
            "Qwen/Qwen2.5-7B-Instruct",
        ),
        note="聚合多家开源模型。",
    ),
    Provider(
        id="openrouter",
        label="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        models=("openai/gpt-4o-mini", "anthropic/claude-3.5-sonnet", "deepseek/deepseek-chat"),
        note="一个 Key 调用多家模型，按量计费。",
    ),
    Provider(
        id="gemini",
        label="Google Gemini（兼容模式）",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        models=("gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"),
        note="使用 Gemini API 的 OpenAI 兼容入口，Key 来自 AI Studio。",
    ),
    Provider(
        id="xai",
        label="xAI Grok",
        base_url="https://api.x.ai/v1",
        models=("grok-3-mini", "grok-4"),
        note="xAI 控制台的 OpenAI 兼容接口。",
    ),
    Provider(
        id="groq",
        label="Groq",
        base_url="https://api.groq.com/openai/v1",
        models=("llama-3.3-70b-versatile", "llama-3.1-8b-instant"),
        note="推理速度快，适合反复抽取；英文模型对中文合同仍可用。",
    ),
    Provider(
        id="mistral",
        label="Mistral AI",
        base_url="https://api.mistral.ai/v1",
        models=("mistral-large-latest", "mistral-small-latest"),
        note="欧洲厂商，OpenAI 兼容接口。",
    ),
    Provider(
        id="together",
        label="Together AI",
        base_url="https://api.together.xyz/v1",
        models=("meta-llama/Llama-3.3-70B-Instruct-Turbo", "Qwen/Qwen2.5-72B-Instruct-Turbo"),
        note="聚合开源模型。",
    ),
    Provider(
        id="volcano",
        label="火山方舟（豆包）",
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        models=("doubao-1-5-pro-32k-250115", "doubao-1-5-lite-32k-250115"),
        note="模型处可填方舟的接入点 ID（ep-…）或上面列出的模型名。",
    ),
    Provider(
        id="qianfan",
        label="百度千帆（文心）",
        base_url="https://qianfan.baidubce.com/v2",
        models=("ernie-4.5-turbo-128k", "ernie-4.5-8k-preview", "ernie-speed-128k"),
        note="千帆 v2 的 OpenAI 兼容入口。",
    ),
    Provider(
        id="hunyuan",
        label="腾讯混元",
        base_url="https://api.hunyuan.cloud.tencent.com/v1",
        models=("hunyuan-turbos-latest", "hunyuan-large", "hunyuan-lite"),
        note="腾讯云混元的 OpenAI 兼容接口。",
    ),
    Provider(
        id="minimax",
        label="MiniMax",
        base_url="https://api.minimax.chat/v1",
        models=("MiniMax-Text-01", "abab6.5s-chat"),
        note="MiniMax 开放平台的兼容接口。",
    ),
    Provider(
        id="stepfun",
        label="阶跃星辰 StepFun",
        base_url="https://api.stepfun.com/v1",
        models=("step-2-16k", "step-1-8k"),
        note="阶跃星辰的 OpenAI 兼容接口。",
    ),
    Provider(
        id="lmstudio",
        label="LM Studio（本地）",
        base_url="http://localhost:1234/v1",
        models=(),
        note="本地加载模型后开放 1234 端口；Key 可留空。",
        key_optional=True,
    ),
    Provider(
        id="ollama",
        label="Ollama（本地）",
        base_url="http://localhost:11434/v1",
        models=("llama3.1", "qwen2.5", "deepseek-r1"),
        note="本地推理，不需要联网；Key 可留空。",
        key_optional=True,
    ),
    Provider(
        id="custom",
        label="自定义（OpenAI 兼容）",
        base_url="",
        models=(),
        note="自行填写服务地址与模型名；必须是 /v1 形式的兼容接口。",
        key_optional=True,
    ),
)

PROVIDER_BY_ID = {provider.id: provider for provider in PROVIDERS}


def provider_payload() -> list[dict]:
    """给前端的只读目录（不含任何用户 Key）。"""
    return [
        {
            "id": provider.id,
            "label": provider.label,
            "base_url": provider.base_url,
            "models": list(provider.models),
            "note": provider.note,
            "key_optional": provider.key_optional,
        }
        for provider in PROVIDERS
    ]


def resolve_provider(provider_id: str | None) -> Provider | None:
    if not provider_id:
        return None
    return PROVIDER_BY_ID.get(provider_id)
