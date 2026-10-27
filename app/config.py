"""配置：唯一读取环境变量与项目上限的地方。

依赖：`.env`（可选，参考项目根目录 `.env.example`）+ `python-dotenv`。
被以下模块引用：`app/nodes/ingest.py`、`app/services/*`（后续）、`app/api.py`（后续）。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 只读取项目根目录的 .env；不存在也不报错（测试/CI 不依赖）
load_dotenv(PROJECT_ROOT / ".env")


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:  # 配置写错要显式失败，不能静默用默认值
        raise ValueError(f"环境变量 {name} 必须是整数，当前值：{raw!r}") from exc


@dataclass(frozen=True)
class Settings:
    # LLM（阶段 3 后续步骤使用）
    llm_provider: str
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    llm_timeout_seconds: int
    llm_max_repair_retries: int
    max_extract_clauses: int

    # 持久化 / HITL
    checkpoint_backend: str
    checkpoint_sqlite_path: str
    hitl_timeout_minutes: int

    # 文档上限（ADR-005）
    max_upload_mb: int
    max_contract_chars: int
    max_pages: int


def load_settings() -> Settings:
    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "openai_compatible"),
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        llm_api_key=os.getenv("LLM_API_KEY", ""),
        llm_model=os.getenv("LLM_MODEL", "gpt-4.1-mini"),
        llm_timeout_seconds=_int_env("LLM_TIMEOUT_SECONDS", 60),
        llm_max_repair_retries=_int_env("LLM_MAX_REPAIR_RETRIES", 1),
        max_extract_clauses=_int_env("MAX_EXTRACT_CLAUSES", 40),
        checkpoint_backend=os.getenv("CHECKPOINT_BACKEND", "sqlite"),
        checkpoint_sqlite_path=os.getenv(
            "CHECKPOINT_SQLITE_PATH", str(PROJECT_ROOT / ".data" / "checkpoints.sqlite")
        ),
        hitl_timeout_minutes=_int_env("HITL_TIMEOUT_MINUTES", 30),
        max_upload_mb=_int_env("MAX_UPLOAD_MB", 15),
        max_contract_chars=_int_env("MAX_CONTRACT_CHARS", 200_000),
        max_pages=_int_env("MAX_PAGES", 200),
    )


settings = load_settings()
