"""Coverage-completeness tests for the buildable-now surface (gap-closing, found by /qa).

These exercise error paths, fallback branches, and helper functions that the
feature tests skipped, plus a regression for the GT-loader JSONL path. Excludes
the Phase-0-blocked stubs (extractor multi-call, provider wiring), which cannot
be exercised without a live provider.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from src.d_extraction import prompts
from src.d_extraction.schema import (
    DocumentExtraction,
    Edge,
    EdgeKind,
    DrugNode,
    IndicationNode,
    canonicalize_edge,
)
from src.guardrails.detector import (
    Verdict,
    check,
    detect_contradictory_limits,
    detect_prerequisite_chain_mismatch,
    detect_age_conflict,
)
from src.guardrails.retry import handle_verdict
from src.guardrails.state import PartialEdgeState
from src.journal.replay import replay_journal
from src.journal.downstream import is_orphaned
from src.shadow.harness import wilson_lower_bound, compare_d_to_ground_truth
from src.cascade_integration.recal import recalibrate_judge
from src.telemetry.counters import (
    PerDocumentCounters,
    increment_counter_1_same_edge,
    increment_counter_2_different_edge,
    increment_counter_3_retry_exhausted,
)


def _drug(cid, surface=None):
    return DrugNode(canonical_id=cid, surface_form=surface or cid)


# --- schema.canonicalize_edge: indication / string objects + value types ---

def test_canonicalize_indication_and_string_objects():
    ind = Edge(kind=EdgeKind.APPLIES_TO, subject=_drug("DRUG_A"),
               object=IndicationNode(canonical_id="IND_X", surface_form="Condition X"))
    lit = Edge(kind=EdgeKind.EFFECTIVE_FROM, subject=_drug("DRUG_A"), object="2026-01-01")
    assert canonicalize_edge(ind) != canonicalize_edge(lit)  # distinct, hashable tuples
    # Unresolved indication falls back to normalized surface form.
    ind1 = Edge(kind=EdgeKind.APPLIES_TO, subject=_drug("A"),
                object=IndicationNode(canonical_id=None, surface_form="Asthma"))
    ind2 = Edge(kind=EdgeKind.APPLIES_TO, subject=_drug("A"),
                object=IndicationNode(canonical_id=None, surface_form=" asthma "))
    assert canonicalize_edge(ind1) == canonicalize_edge(ind2)


def test_canonicalize_value_types_number_string_bool_text():
    base = dict(kind=EdgeKind.REQUIRES, subject=_drug("A"), object=_drug("B"))
    # numeric drift collapses: 18 == "18"
    assert canonicalize_edge(Edge(**base, qualifiers={"age_min": 18})) == \
        canonicalize_edge(Edge(**base, qualifiers={"age_min": "18"}))
    # bool tagged distinctly from int 1
    assert canonicalize_edge(Edge(**base, qualifiers={"flag": True})) != \
        canonicalize_edge(Edge(**base, qualifiers={"flag": 1}))
    # non-numeric text normalizes (case + whitespace)
    assert canonicalize_edge(Edge(**base, qualifiers={"note": " Brand "})) == \
        canonicalize_edge(Edge(**base, qualifiers={"note": "brand"}))


# --- prompts.get_prompt error paths ---

def test_get_prompt_unknown_templates_raise():
    with pytest.raises(KeyError):
        prompts.get_prompt("does-not-exist", d_mode=False)
    with pytest.raises(KeyError):
        prompts.get_prompt("does-not-exist", d_mode=True)


# --- retry ACCEPT passthrough ---

def test_handle_verdict_accept_passthrough():
    state = PartialEdgeState(document_id="d")
    edge = Edge(kind=EdgeKind.REQUIRES, subject=_drug("A"), object=_drug("B"))
    out = handle_verdict(edge, Verdict.ACCEPT, state, lambda err: edge)
    assert out.accepted_edge is edge
    assert (out.counter_1_delta, out.counter_2_delta, out.counter_3_delta) == (0, 0, 0)


# --- detector negative (no-trigger) branches ---

def test_detector_negative_branches():
    state = PartialEdgeState(document_id="d", edges=[
        Edge(kind=EdgeKind.REQUIRES, subject=_drug("A"), object=_drug("B"),
             qualifiers={"age_min": 5, "age_max": 65}),
    ])
    valid = Edge(kind=EdgeKind.REQUIRES, subject=_drug("A"), object=_drug("B"), qualifiers={"age_max": 60})
    assert detect_contradictory_limits(valid, state) is False  # 5..60 still satisfiable
    applies = Edge(kind=EdgeKind.APPLIES_TO, subject=_drug("A"), object=_drug("B"))
    assert detect_prerequisite_chain_mismatch(applies, state) is False  # not requires/excludes
    assert detect_age_conflict(valid, state) is False  # no age_exact qualifier
    assert check(valid, state) == Verdict.ACCEPT


# --- state.edges_about ---

def test_state_edges_about():
    a_b = Edge(kind=EdgeKind.REQUIRES, subject=_drug("A"), object=_drug("B"))
    c_d = Edge(kind=EdgeKind.REQUIRES, subject=_drug("C"), object=_drug("D"))
    state = PartialEdgeState(document_id="d", edges=[a_b, c_d])
    assert state.edges_about("A") == [a_b]


# --- replay: missing file + blank-line skipping ---

def test_replay_missing_file_and_blank_lines(tmp_path):
    assert replay_journal(tmp_path / "nope.journal") == []
    edge = Edge(kind=EdgeKind.REQUIRES, subject=_drug("A"), object=_drug("B"))
    jp = tmp_path / "j.journal"
    jp.write_text(edge.model_dump_json() + "\n\n   \n" + edge.model_dump_json() + "\n", encoding="utf-8")
    assert len(replay_journal(jp)) == 2


# --- downstream: naive started_at timestamp ---

def test_is_orphaned_handles_naive_started_at():
    doc = DocumentExtraction(document_id="x", extraction_complete=False,
                             extraction_started_at="2026-01-01T00:00:00")  # naive, no Z
    now = datetime(2026, 1, 3, tzinfo=timezone.utc)  # 2 days later
    assert is_orphaned(doc, now=now) is True


# --- shadow harness: non-default confidence, JSONL + dict GT, baseline regression ---

def test_wilson_non_default_confidence():
    assert 0.0 < wilson_lower_bound(50, 100, confidence=0.99) < 0.5


def test_compare_with_jsonl_ground_truth_and_baseline_regression(tmp_path):
    d = DocumentExtraction(
        document_id="doc", extraction_started_at="2026-01-01T00:00:00Z",
        edges=[
            Edge(kind=EdgeKind.REQUIRES, subject=_drug("A"), object=_drug("B")),
            Edge(kind=EdgeKind.REQUIRES, subject=_drug("A"), object=_drug("C")),
        ],
        existing_fields={"drug_name": "Aspirin", "age_limit": ">=18"},
    )
    baseline = DocumentExtraction(
        document_id="doc", extraction_started_at="2026-01-01T00:00:00Z",
        existing_fields={"drug_name": "Aspirin", "age_limit": ">=21"},  # changed -> regression
    )
    # Object-per-line JSONL (the format the first-char detector used to crash on).
    gt = tmp_path / "gt.jsonl"
    gt.write_text(
        "\n".join(json.dumps(json.loads(e.model_dump_json())) for e in d.edges),
        encoding="utf-8",
    )
    result = compare_d_to_ground_truth(d, gt, baseline_extraction=baseline)
    assert result.n_gt_edges == 2
    assert result.edge_precision_point == 1.0
    assert "age_limit" in result.regression_detected_fields
    assert result.field_iso_precision_per_field["drug_name"] == 0.0


def test_compare_with_dict_edges_wrapper(tmp_path):
    d = DocumentExtraction(
        document_id="doc", extraction_started_at="2026-01-01T00:00:00Z",
        edges=[Edge(kind=EdgeKind.REQUIRES, subject=_drug("A"), object=_drug("B"))],
    )
    gt = tmp_path / "gt.json"
    gt.write_text(json.dumps({"edges": [json.loads(d.edges[0].model_dump_json())]}), encoding="utf-8")
    result = compare_d_to_ground_truth(d, gt)
    assert result.n_gt_edges == 1 and result.edge_recall_point == 1.0


# --- cascade re-cal: failure-mode branch on incomplete extraction ---

def test_recalibrate_records_failure_modes(tmp_path):
    path = tmp_path / "eval.jsonl"
    path.write_text(
        "\n".join(json.dumps({"page_id": i, "text": f"p{i}", "ocr_label": "needs_gpt4o"}) for i in range(4)),
        encoding="utf-8",
    )
    result = recalibrate_judge(
        path,
        lambda text: DocumentExtraction(
            document_id="p", extraction_started_at="2026-01-01T00:00:00Z", extraction_complete=False
        ),
    )
    assert result.judge_pass_rate == 0.0
    assert result.failure_modes.get("needs_gpt4o") == 4
    assert result.threshold_met is False


# --- telemetry counters: increment functions + fp_rate + zero guard ---

def test_counter_increment_functions_and_fp_rate():
    c = PerDocumentCounters(document_id="d")
    assert c.fp_rate == 0.0  # zero-volume guard (no divide-by-zero)
    increment_counter_1_same_edge(c)
    increment_counter_2_different_edge(c)
    increment_counter_2_different_edge(c)
    increment_counter_3_retry_exhausted(c)
    assert c.total == 4
    assert c.fp_rate == 0.25
