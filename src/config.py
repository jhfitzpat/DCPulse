"""Environment and runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Repository root (parent of src/)
REPO_ROOT = Path(__file__).resolve().parent.parent


def _env_bool(key: str, default: bool = False) -> bool:
    v = os.environ.get(key, "").strip().lower()
    if not v:
        return default
    return v in ("1", "true", "yes", "on")


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, "").strip() or default)
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, "").strip() or default)
    except ValueError:
        return default


def _env_str(key: str, default: str) -> str:
    v = (os.environ.get(key) or "").strip()
    return v if v else default


@dataclass(frozen=True)
class Config:
    """Pipeline configuration from environment variables."""

    dry_run: bool
    log_level: str
    lookback_days: int
    max_topics: int
    highlight_repost_count: int
    openai_api_key: Optional[str]
    openai_model: str
    llm_timeout_seconds: float
    skip_llm: bool
    # Email (optional; dry-run skips send)
    email_to: Optional[str]
    email_from: Optional[str]
    smtp_host: Optional[str]
    smtp_port: int
    smtp_user: Optional[str]
    smtp_password: Optional[str]
    smtp_use_tls: bool
    email_subject_prefix: str
    # Paths
    data_dir: Path
    sources_path: Path
    exclusions_path: Path
    prompts_dir: Path
    voice_path: Path

    @classmethod
    def from_env(cls) -> Config:
        root = REPO_ROOT
        data_dir = Path(os.environ.get("DC_PULSE_DATA_DIR", str(root / "data")))
        return cls(
            dry_run=_env_bool("DC_PULSE_DRY_RUN", False),
            log_level=os.environ.get("DC_PULSE_LOG_LEVEL", "INFO").upper(),
            lookback_days=_env_int("DC_PULSE_LOOKBACK_DAYS", 14),
            max_topics=_env_int("DC_PULSE_MAX_TOPICS", 7),
            highlight_repost_count=_env_int("DC_PULSE_HIGHLIGHT_REPOST", 3),
            openai_api_key=os.environ.get("OPENAI_API_KEY") or None,
            openai_model=_env_str("OPENAI_MODEL", "gpt-4o-mini"),
            llm_timeout_seconds=_env_float("DC_PULSE_LLM_TIMEOUT", 120.0),
            skip_llm=_env_bool("DC_PULSE_SKIP_LLM", False),
            email_to=os.environ.get("DC_PULSE_EMAIL_TO") or None,
            email_from=os.environ.get("DC_PULSE_EMAIL_FROM") or None,
            smtp_host=os.environ.get("DC_PULSE_SMTP_HOST") or None,
            smtp_port=_env_int("DC_PULSE_SMTP_PORT", 587),
            smtp_user=os.environ.get("DC_PULSE_SMTP_USER") or None,
            smtp_password=os.environ.get("DC_PULSE_SMTP_PASSWORD") or None,
            smtp_use_tls=_env_bool("DC_PULSE_SMTP_TLS", True),
            email_subject_prefix=os.environ.get("DC_PULSE_EMAIL_SUBJECT_PREFIX", "DC Pulse Weekly"),
            data_dir=data_dir,
            sources_path=data_dir / "sources.yml",
            exclusions_path=data_dir / "topic_exclusions.yml",
            prompts_dir=root / "src" / "prompts",
            voice_path=root / "src" / "voice" / "profile.md",
        )


def load_config() -> Config:
    return Config.from_env()
