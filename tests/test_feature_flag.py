"""Tests for paiq.d_extraction.enabled feature flag per D6 + D12.

Covers ~2 of the 23 edge-focused tests:
- Flag off → baseline prompts used
- Flag on → D-modified prompts used
- Flag flip is instant (no code rollback needed)

T6 + T9 deliverables. All stubs.
"""

from __future__ import annotations

import pytest

from src.feature_flags import is_d_enabled, set_d_enabled


def test_flag_off_returns_baseline_prompt(monkeypatch):
    """When PAIQ_D_EXTRACTION_ENABLED=false, get_prompt returns baseline."""
    pytest.skip("T6 deliverable")


def test_flag_on_returns_d_modified_prompt(monkeypatch):
    """When PAIQ_D_EXTRACTION_ENABLED=true, get_prompt returns D-modified."""
    pytest.skip("T6 deliverable")


def test_flag_flip_takes_effect_immediately(monkeypatch):
    """Toggling the env var mid-extraction is observed on the next get_prompt call."""
    pytest.skip("T6 deliverable")
