"""Tests for the 4 guardrails detection scenarios.

Covers ~4 of the 23 edge-focused tests from the coverage diagram:
- Circular dependency detection
- Contradictory age limits detection
- Prerequisite chain mismatch detection
- Age conflict detection

T4 + T9 deliverables. All stubs.
"""

from __future__ import annotations

import pytest

from src.guardrails.detector import (
    Verdict,
    detect_circular_dependency,
    detect_contradictory_limits,
    detect_prerequisite_chain_mismatch,
    detect_age_conflict,
)
from src.guardrails.state import PartialEdgeState


def test_detect_circular_dependency_fires_on_simple_cycle():
    """A requires B; B requires A → REJECT_RETRY."""
    pytest.skip("T4 deliverable")


def test_detect_contradictory_limits_age_range_overlap():
    """age >= 5 AND age <= 65 emitted for same drug-indication → REJECT_RETRY."""
    pytest.skip("T4 deliverable")


def test_detect_prerequisite_chain_mismatch_against_existing_edges():
    """New 'A excludes B' edge contradicts already-extracted 'A requires B' → REJECT_RETRY."""
    pytest.skip("T4 deliverable")


def test_detect_age_conflict_against_existing_qualifier():
    """New age qualifier contradicts already-extracted age qualifier for same drug-indication → REJECT_RETRY."""
    pytest.skip("T4 deliverable")
