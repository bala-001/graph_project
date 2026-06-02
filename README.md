# PAIQ Idea 11.3 — Document Graph (Phase 1: D + Guardrails)

Relationship-aware extraction for the PAIQ pipeline. Modifies extraction to emit
structured edge-triples natively (Approach D) and adds extraction-time guardrails
that detect logical inconsistencies before they're committed to client-facing
output.

This is **Phase 1** scope per the iter-5 standalone CEO plan. Approach B (in-house
PageIndex-equivalent + extracted-fact graph as a query surface), Approach F
(embedding similarity), OSS release, and research publication are deferred as
**Phase-2 candidates** with concrete revisit triggers tied to Phase-1 shadow data.

## What this project does

PAIQ extracts pharmaceutical PA / ST / QL / age-limit criteria from PBM policy
documents. Today the extracted facts come out as isolated values. Clients have
complained about contradictory or incomplete outputs where individual facts are
correct but the **relationships** between them are lost (e.g., "Drug A requires
step therapy with Drug B" + "Drug B has age restrictions" extracted as 3
disconnected facts).

Phase 1 fixes this by:

1. **Approach D** — extraction emits structured edge-triples natively
   (`requires`, `excludes`, `applies_to`, `overrides`, `effective_from`) via the
   LLM provider's built-in structured output mode (OpenAI `response_format:
   json_schema` strict OR Anthropic tool-use).
2. **Guardrails** — extraction-time consistency check that consults the partial
   edge state and rejects/retries edges that would create logical inconsistencies
   (circular dependencies, contradictory limits, prerequisite mismatches, age
   conflicts).

## Phase 1 scope (locked through iter-5)

- ~2 engineers, **2-2.5 quarters** honestly (per eng-review D9)
- ~33-35 tests including mandatory iso-precision regression suite on existing
  field types (per D11)
- Cascade-OCR judge re-calibration on D-mode output before D ships
  (per D3) — coordinates with the sibling cascade-OCR plan
- Multi-call extraction protocol with guardrails firing BETWEEN calls (per D10)
- Persist-as-you-go partial-edge state with `extraction_complete` flag and
  batched-write journal (per D2 + D7)
- Provider built-in structured outputs for schema enforcement (per D1) — known
  limit: schema enforcement covers SHAPE, not semantic correctness; semantic
  defense lives in eval suite + guardrails
- Feature-flag rollback (`paiq.d_extraction.enabled`) preserving baseline prompt
  (per D12)
- Statistical-significance gates (Wilson / Clopper-Pearson lower-bound) on
  Phase-2 trigger thresholds (per D12)

## Key references

- **Design doc**: `docs/design.md` (the office-hours-approved 9/10 design)
- **CEO plan iter-5**: `docs/ceo-plan.md` (scope + 20 closed decisions)
- **Test plan**: `docs/test-plan.md` (primary input for `/qa`)
- **D integration spec**: `docs/architecture/d-integration-spec.md` (F1 deliverable; lands before any code)
- **Kill Criteria reference**: `docs/architecture/kill-criteria.md` (all gates with triggers, decisions, owners)
- **Data model**: `docs/architecture/data-model.md` (Pydantic edge schema + provider config)

## Project structure

```
graph_project/
├── README.md                  (this file)
├── CLAUDE.md                  (Claude Code project config)
├── TODOS.md                   (eng-review + Phase-2 candidate tracking)
├── pyproject.toml             (Python deps + tool config)
├── .gitignore
├── docs/
│   ├── design.md              (idea_11.3 design doc, copy)
│   ├── ceo-plan.md            (standalone CEO plan iter-5, copy)
│   ├── test-plan.md           (eng-review test plan, copy)
│   └── architecture/
│       ├── d-integration-spec.md   (F1 deliverable stub)
│       ├── kill-criteria.md        (Kill Criteria reference card)
│       └── data-model.md           (Pydantic edge schema spec)
├── src/
│   ├── d_extraction/          (D's structured-edge emission)
│   ├── guardrails/            (4 detection scenarios + retry policy)
│   ├── journal/               (batched-write journal + replay)
│   ├── feature_flags/         (paiq.d_extraction.enabled)
│   ├── shadow/                (D-vs-GT shadow harness)
│   ├── telemetry/             (3-counter FP rate metrics)
│   └── cascade_integration/   (cascade-OCR judge re-calibration)
├── tests/
│   ├── conftest.py
│   ├── test_d_extraction.py
│   ├── test_guardrails_detection.py
│   ├── test_guardrails_retry.py
│   ├── test_journal.py
│   ├── test_feature_flag.py
│   ├── test_extraction_regression.py    (iso-precision across existing fields)
│   ├── test_shadow_harness.py
│   ├── test_cascade_recal.py
│   └── test_canonicalization.py
└── eval/
    ├── README.md
    ├── labels/                (relationship-type + contradiction-validity labels)
    └── runners/               (edge_precision, regression, judge_pass_rate)
```

## Quick start

```bash
# Install dependencies
pip install -e .[dev]

# Run tests
pytest tests/

# Run extraction offline (mock provider, D mode) via the CLI
printf 'FIELD drug_name=Adalimumab\nEDGE requires DRUG_A DRUG_B age_min=18\n' > /tmp/doc.txt
paiq-d extract /tmp/doc.txt --provider mock --d-mode

# Eval runners against the synthetic sample (non-PHI; dev/CI only)
python eval/runners/edge_precision.py --eval-set eval/labels/sample
python eval/runners/regression.py     --eval-set eval/labels/sample
python eval/runners/judge_pass_rate.py --eval-set eval/labels/sample --use-wilson-lower-bound
```

Full install/config/deploy: `docs/INSTALL.md`, `docs/DEPLOYMENT.md`.

## Status

**Engineering: complete and deployable (offline).** Every module is implemented
(no stubs), wired into an end-to-end pipeline (`extract_document`), packaged with
a `paiq-d` CLI, a Dockerfile, and GitHub Actions CI. It installs and runs with no
API keys: the provider defaults to an offline `MockProvider` and the D feature
flag defaults OFF. 68 tests pass (10 production-gate regression tests skipped),
coverage 91.9%. See `docs/INSTALL.md` and `docs/DEPLOYMENT.md`.

**NOT yet production-validated for real PBM documents.** Before real-document use,
the org must supply: (1) the real extraction prompts (the Q3 decision; the
bundled prompts in `src/d_extraction/prompts.py` are clearly-marked TEMPLATES),
(2) provider credentials + `PAIQ_PROVIDER` + `PAIQ_D_EXTRACTION_ENABLED=true`,
(3) the F6 relationship/contradiction labels + cascade-OCR eval set in the
access-controlled store, with the Kill Criteria gates certified on them (the
bundled `eval/labels/sample/` is synthetic, non-PHI, for dev/CI only), and
(4) Week-1 sponsor commitment + Week-2 complaint root-cause audit cleared.

**Phase 0 (org, in progress)** — complaint root-cause audit, sponsor KPI
conversation, SLA budget confirmation. Owners/dates in the CEO plan Open Questions.
