"""Environment configuration for the outage assistant."""

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class AgentConfig:
    api_key: str | None
    base_url: str | None
    model: str
    model_timeout_seconds: float
    tool_timeout_seconds: float


def _positive_float(name: str, default: str) -> float:
    raw_value = os.getenv(name, default)
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


def load_config(require_key: bool = False) -> AgentConfig:
    """Load local settings without requiring a key for offline checks."""
    load_dotenv(ROOT_DIR / ".env")
    api_key = os.getenv("OPENAI_API_KEY") or None
    if require_key and not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for a real model call")

    model = os.getenv("AGENT_MODEL", "gpt-4o-mini").strip()
    if not model:
        raise ValueError("AGENT_MODEL must not be empty")

    return AgentConfig(
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL") or None,
        model=model,
        model_timeout_seconds=_positive_float("MODEL_TIMEOUT_SECONDS", "30"),
        tool_timeout_seconds=_positive_float(
            "OUTAGE_TOOL_TIMEOUT_SECONDS", "0.35"
        ),
    )
