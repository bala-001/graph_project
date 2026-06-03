"""Central runtime configuration (12-factor) for the D extraction service.

Every deployment knob reads from an environment variable so the same artifact
runs unchanged across dev (offline mock, flag off), production-shadow, and
production. No secrets are hard-coded; provider API keys are read from the
environment by the provider SDKs at call time.

Env vars:
  PAIQ_PROVIDER                  mock | openai | anthropic   (default: mock)
  PAIQ_OPENAI_MODEL              default: gpt-4o
  PAIQ_ANTHROPIC_MODEL           default: claude-opus-4-7
  PAIQ_D_EXTRACTION_ENABLED      feature flag (D12 rollback)  (default: false)
  PAIQ_JOURNAL_DIR               batched-write journal dir    (default: .paiq-journals)
  PAIQ_JOURNAL_BATCH_SIZE        D7 flush size                (default: 10)
  PAIQ_JOURNAL_BATCH_TIMEOUT     D7 flush seconds             (default: 5.0)
  PAIQ_GUARDRAILS_MAX_RETRIES    Q8 retry/exhaust threshold   (default: 3)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ[name])
    except (KeyError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ[name])
    except (KeyError, ValueError):
        return default


@dataclass
class Config:
    """Resolved runtime configuration. Build with Config.from_env()."""
    provider: str = field(default_factory=lambda: os.environ.get("PAIQ_PROVIDER", "mock"))
    openai_model: str = field(default_factory=lambda: os.environ.get("PAIQ_OPENAI_MODEL", "gpt-4o"))
    anthropic_model: str = field(default_factory=lambda: os.environ.get("PAIQ_ANTHROPIC_MODEL", "claude-sonnet-4-6"))
    d_enabled: bool = field(default_factory=lambda: _env_bool("PAIQ_D_EXTRACTION_ENABLED", False))
    journal_dir: str = field(default_factory=lambda: os.environ.get("PAIQ_JOURNAL_DIR", ".paiq-journals"))
    batch_size: int = field(default_factory=lambda: _env_int("PAIQ_JOURNAL_BATCH_SIZE", 10))
    batch_timeout_seconds: float = field(default_factory=lambda: _env_float("PAIQ_JOURNAL_BATCH_TIMEOUT", 5.0))
    max_retries: int = field(default_factory=lambda: _env_int("PAIQ_GUARDRAILS_MAX_RETRIES", 3))

    @classmethod
    def from_env(cls) -> "Config":
        return cls()
