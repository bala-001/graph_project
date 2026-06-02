"""Tests for the provider abstraction + end-to-end extraction pipeline (T1 wiring).

Uses the offline MockProvider, so these run with no network and no API key and
exercise the full multi-call + between-call-guardrail loop (D10) end to end.
"""

from __future__ import annotations

import json

from src.config import Config
from src.d_extraction import extract_document
from src.d_extraction.provider import MockProvider, get_provider
from src.d_extraction.schema import EdgeKind


def _cfg(tmp_path, d_enabled=True):
    return Config(provider="mock", d_enabled=d_enabled, journal_dir=str(tmp_path))


def test_mock_provider_parses_dsl():
    edges, fields = MockProvider().extract_chunk("p", "FIELD drug_name=Adalimumab\nEDGE requires DRUG_A DRUG_B age_min=18")
    assert fields == {"drug_name": "Adalimumab"}
    assert len(edges) == 1
    assert edges[0].kind == EdgeKind.REQUIRES
    assert edges[0].qualifiers["age_min"] == 18


def test_get_provider_selects_by_config():
    assert isinstance(get_provider(Config(provider="mock")), MockProvider)


def test_extract_document_d_mode_emits_edges_and_fields(tmp_path):
    doc = extract_document(
        "doc-1",
        ["FIELD drug_name=Adalimumab\nEDGE requires DRUG_A DRUG_B age_min=18"],
        _cfg(tmp_path),
    )
    assert doc.extraction_complete is True
    assert doc.existing_fields == {"drug_name": "Adalimumab"}
    assert len(doc.edges) == 1 and doc.edges[0].kind == EdgeKind.REQUIRES
    # Canonical metadata is materialized on completion.
    written = json.loads((tmp_path / "doc-1.json").read_text(encoding="utf-8"))
    assert written["extraction_complete"] is True


def test_extract_document_baseline_mode_emits_no_edges(tmp_path):
    doc = extract_document(
        "doc-2",
        ["FIELD age_limit=>=21\nEDGE requires DRUG_A DRUG_B"],
        _cfg(tmp_path, d_enabled=False),
    )
    assert doc.edges == []  # flag off -> no edges, no guardrails (D12 rollback path)
    assert doc.existing_fields == {"age_limit": ">=21"}


def test_extract_document_guardrail_loop_replaces_conflicting_edge(tmp_path):
    # requires A->B then excludes A->B: the second is a prereq mismatch, retried,
    # and the mock returns a benign applies_to edge that passes (counter 2 = TP).
    doc = extract_document(
        "doc-3",
        ["EDGE requires DRUG_A DRUG_B\nEDGE excludes DRUG_A DRUG_B"],
        _cfg(tmp_path),
    )
    kinds = sorted(e.kind.value for e in doc.edges)
    assert kinds == ["applies_to", "requires"]  # excludes was caught + replaced
    assert doc.guardrails_counter_2_different_edge == 1
    assert doc.guardrails_counter_1_same_edge == 0


def test_extract_document_multi_chunk_accumulates(tmp_path):
    doc = extract_document(
        "doc-4",
        ["EDGE requires DRUG_A DRUG_B", "EDGE applies_to DRUG_A IND_X"],
        _cfg(tmp_path),
    )
    assert len(doc.edges) == 2
