# Eval — PAIQ 11.3 Phase 1 evaluation infrastructure

This directory holds the labeled eval set + the runners that exercise it. All
quality / correctness gates in the Kill Criteria depend on these runs.

## What's here

```
eval/
├── README.md                          (this file)
├── labels/                            (per-document labels for the eval set)
│   ├── .gitkeep
│   ├── relationship_types.jsonl       (per-page relationship-type labels; F6)
│   └── contradiction_validity.jsonl   (per-pair contradiction-validity labels; F6)
└── runners/
    ├── edge_precision.py              (D edge precision/recall per edge type)
    ├── regression.py                  (iso-precision regression on existing fields; T10)
    └── judge_pass_rate.py             (cascade-OCR judge re-cal pass-rate; T3)
```

## Eval set provenance

The base 50-document labeled set originates from the cascade-OCR plan
(`~/.gstack/projects/projects_poc_innovations/2125509-idea1.1-cascade-ocr-eng-review-20260526-130000.md`).
That set has OCR-quality labels (page-level "cheap was fine" vs "needed GPT-4o").

Phase 1 F6 deliverable EXTENDS that set with two additional label types:

1. **Relationship-type labels** (`labels/relationship_types.jsonl`): per-page
   ground-truth edges (subject, predicate, object, qualifiers). Sourced from
   analyst-corrected production extractions where corrections imply the edges
   were missed by baseline.
2. **Contradiction-validity labels** (`labels/contradiction_validity.jsonl`):
   per-pair ground-truth "this pair of extracted facts contradicts each other"
   labels. Used by `test_guardrails_detection.py` and by
   `runners/edge_precision.py` for guardrails firing-rate ground truth.

Per D5 (shadow data definition): D-output is compared against these labels
(analyst-corrected ground truth) on the same documents the cascade-OCR set covers.

## How to run

```bash
# Edge precision per edge type (drives the Quarter-1 D shadow result gate)
python eval/runners/edge_precision.py \
    --eval-set eval/labels/ \
    --d-mode-only \
    --output reports/edge_precision_2026-05-26.json

# Iso-precision regression on existing field types (Week-4 Kill Criteria)
python eval/runners/regression.py \
    --eval-set eval/labels/ \
    --baseline-vs-d-mode \
    --regression-threshold 0.05 \
    --output reports/regression_2026-05-26.json

# Cascade-OCR judge re-cal pass-rate (D3 deliverable; T3)
python eval/runners/judge_pass_rate.py \
    --eval-set eval/labels/ \
    --d-mode-only \
    --threshold 0.95 \
    --use-wilson-lower-bound \
    --output reports/judge_pass_rate_2026-05-26.json
```

## PHI handling (per CEO plan Compliance section)

Labels in this directory may be PHI-adjacent. Treat per the existing PAIQ data
classification policy:

- `.gitignore` excludes `labels/*.jsonl` from version control
- Local development uses synthetic / de-identified labels only
- Production eval runs use the access-controlled production label store, not
  this directory

## Acceptance gates (Kill Criteria triggers)

- **edge_precision.py**: Wilson lower-bound on edge precision must be ≥85% AND
  recall ≥80% to pass the Quarter-1 D shadow result gate.
- **regression.py**: every existing field type's iso-precision delta must be
  ≤5% to pass the Week-4 extraction-precision regression gate.
- **judge_pass_rate.py**: Wilson lower-bound on judge-pass-rate must be ≥95% to
  pass D3's cascade re-cal gate before D ships to production-shadow.

Failing ANY of these blocks the corresponding Kill Criteria. Failing
regression.py specifically triggers an automatic feature-flag flip
(`paiq.d_extraction.enabled=false`) per the D12 rollback path.
