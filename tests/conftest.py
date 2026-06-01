"""Pytest configuration + shared fixtures for the PAIQ 11.3 Phase 1 test suite.

The full suite covers ~33-35 tests across 10 test files. Each test file maps to a
specific eng-review T-number deliverable from the JSONL at
~/.gstack/projects/projects_poc_innovations/tasks-eng-review-20260526-173441.jsonl

Test framework: pytest. Markers defined in pyproject.toml:
- @pytest.mark.regression — iso-precision regression on existing fields (Week-4 Kill Criteria gate)
- @pytest.mark.eval — full LLM eval runs (skipped by default; opt-in via -m eval)
- @pytest.mark.slow — takes >30 seconds
"""

from __future__ import annotations

import pytest

from src.d_extraction.schema import (
    DocumentExtraction,
    Edge,
    EdgeKind,
    DrugNode,
    IndicationNode,
)


@pytest.fixture
def sample_drug_node() -> DrugNode:
    return DrugNode(canonical_id="DRUG_A_CANONICAL", surface_form="Drug A")


@pytest.fixture
def sample_indication_node() -> IndicationNode:
    return IndicationNode(canonical_id="IND_X", surface_form="Condition X")


@pytest.fixture
def sample_requires_edge(sample_drug_node) -> Edge:
    return Edge(
        kind=EdgeKind.REQUIRES,
        subject=sample_drug_node,
        object=DrugNode(canonical_id="DRUG_B_CANONICAL", surface_form="Drug B"),
        qualifiers={},
        source_page=1,
        source_chunk_id="chunk-1",
        model_confidence=0.9,
    )


@pytest.fixture
def empty_document_extraction() -> DocumentExtraction:
    return DocumentExtraction(
        document_id="doc-test-001",
        extraction_complete=False,
        edges=[],
        existing_fields={},
        extraction_started_at="2026-05-26T17:00:00Z",
    )
