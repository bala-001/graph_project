"""Tests for the eval runners against the SYNTHETIC sample dataset.

These prove the runners execute end-to-end and emit structured reports. The
statistical GATE pass/fail is only meaningful on production-scale labels; on the
tiny synthetic sample the small-N lower bounds intentionally can't certify the
85% / 95% gates, so we assert on the point estimates and report shape, not the
gate verdict (except regression, which legitimately passes: D does not regress
fields vs baseline).
"""

from __future__ import annotations

import json

from eval.runners import edge_precision, regression, judge_pass_rate

SAMPLE = "eval/labels/sample"


def test_regression_runner_passes_on_sample(tmp_path):
    out = tmp_path / "reg.json"
    rc = regression.main(["--eval-set", SAMPLE, "--output", str(out)])
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["passed"] is True  # D field extraction is iso-precise vs baseline
    assert report["regressed_fields"] == []
    assert rc == 0


def test_edge_precision_runner_reports_perfect_point_estimate(tmp_path):
    out = tmp_path / "edge.json"
    edge_precision.main(["--eval-set", SAMPLE, "--output", str(out)])
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["aggregate"]["precision"] == 1.0  # mock emits exactly the gold edges
    assert report["aggregate"]["recall"] == 1.0
    assert set(report["per_edge_type"]) == {"requires", "excludes", "applies_to", "overrides", "effective_from"}


def test_judge_runner_reports_pass_rate(tmp_path):
    out = tmp_path / "judge.json"
    judge_pass_rate.main(["--eval-set", SAMPLE, "--use-wilson-lower-bound", "--output", str(out)])
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["judge_pass_rate"] == 1.0
    assert report["n_pages"] >= 1
