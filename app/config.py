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


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"环境变量 {name} 必须是数字，当前值：{raw!r}") from exc


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    value = raw.strip().casefold()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"环境变量 {name} 必须是布尔值（true/false），当前值：{raw!r}")


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
    #: HITL 待审批时间戳（跨进程超时判定）与上传暂存目录
    pending_dir: str
    upload_dir: str

    # 账号 / Skill / 模型配置（ADR-013；本地 SQLite，零额外依赖）
    user_db_path: str
    #: 本地密文主密钥（第三方 API Key 静态保护）；首次启动自动生成
    user_secret_path: str
    session_ttl_days: int

    # RAG（ADR-007 / ADR-008；默认关闭）
    rag_enabled: bool
    rag_knowledge_dir: str
    rag_top_k: int
    rag_min_score: float

    # 文档上限（ADR-005）
    max_upload_mb: int
    max_contract_chars: int
    max_pages: int

    # OCR（扫描件 / 图片 PDF；RapidOCR 本地推理，不联网）
    ocr_enabled: bool
    ocr_max_pages: int
    ocr_render_scale: float


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
        pending_dir=os.getenv(
            "PENDING_DIR", str(PROJECT_ROOT / ".data" / "pending")
        ),
        upload_dir=os.getenv(
            "UPLOAD_DIR", str(PROJECT_ROOT / ".data" / "uploads")
        ),
        user_db_path=os.getenv(
            "USER_DB_PATH", str(PROJECT_ROOT / ".data" / "app.sqlite")
        ),
        user_secret_path=os.getenv(
            "USER_SECRET_PATH", str(PROJECT_ROOT / ".data" / "secret.key")
        ),
        session_ttl_days=_int_env("SESSION_TTL_DAYS", 7),
        rag_enabled=_bool_env("RAG_ENABLED", False),
        rag_knowledge_dir=os.getenv(
            "RAG_KNOWLEDGE_DIR", str(PROJECT_ROOT / "data" / "knowledge")
        ),
        rag_top_k=_int_env("RAG_TOP_K", 3),
        rag_min_score=_float_env("RAG_MIN_SCORE", 1.0),
        max_upload_mb=_int_env("MAX_UPLOAD_MB", 30),
        max_contract_chars=_int_env("MAX_CONTRACT_CHARS", 200_000),
        max_pages=_int_env("MAX_PAGES", 200),
        ocr_enabled=_bool_env("OCR_ENABLED", True),
        ocr_max_pages=_int_env("OCR_MAX_PAGES", 20),
        ocr_render_scale=_float_env("OCR_RENDER_SCALE", 2.2),
    )


settings = load_settings()
