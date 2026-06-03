"""Tests for paiq.d_extraction.enabled feature flag per D6 + D12.

Covers the flag + prompt-routing slice (T6):
- Flag off -> baseline prompts used (rollback path)
- Flag on -> D-modified prompts used
- Flag flip is instant (no code rollback needed)

T6 + T9 deliverables.
"""

from __future__ import annotations

from src.feature_flags import is_d_enabled, set_d_enabled
from src.d_extraction import prompts


def _seed_prompts(monkeypatch):
    # Register the env var with monkeypatch so it is restored after the test,
    # then seed synthetic prompt entries (real content is Q3-gated).
    monkeypatch.setenv("PAIQ_D_EXTRACTION_ENABLED", "false")
    monkeypatch.setitem(prompts.BASELINE_PROMPTS, "extract_drug_fields", "BASELINE: extract drug fields")
    monkeypatch.setitem(prompts.D_PROMPTS, "extract_drug_fields", "D-MODE: extract drug fields + edges")


def test_flag_off_returns_baseline_prompt(monkeypatch):
    """When PAIQ_D_EXTRACTION_ENABLED=false, resolve_prompt returns baseline."""
    _seed_prompts(monkeypatch)
    set_d_enabled(False)
    assert is_d_enabled() is False
    assert prompts.resolve_prompt("extract_drug_fields") == "BASELINE: extract drug fields"


def test_flag_on_returns_d_modified_prompt(monkeypatch):
    """When PAIQ_D_EXTRACTION_ENABLED=true, resolve_prompt returns D-modified."""
    _seed_prompts(monkeypatch)
    set_d_enabled(True)
    assert is_d_enabled() is True
    assert prompts.resolve_prompt("extract_drug_fields") == "D-MODE: extract drug fields + edges"


def test_flag_flip_takes_effect_immediately(monkeypatch):
    """Toggling the flag mid-extraction is observed on the next resolve_prompt call."""
    _seed_prompts(monkeypatch)
    set_d_enabled(False)
    assert prompts.resolve_prompt("extract_drug_fields").startswith("BASELINE")
    set_d_enabled(True)
    assert prompts.resolve_prompt("extract_drug_fields").startswith("D-MODE")
