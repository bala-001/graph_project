# CLAUDE.md — graph_project (PAIQ Idea 11.3 Phase 1)

This file gives Claude Code context for working on this project.

## Project context

PAIQ Idea 11.3 Phase 1 — relationship-aware extraction (Approach D) +
extraction-time guardrails. Modifies the PAIQ extraction pipeline to emit
structured edge-triples natively and adds a consistency check that catches
logical inconsistencies before they're committed.

Sibling docs to read for full context:
- `docs/design.md` — design doc
- `docs/ceo-plan.md` — CEO plan iter-5 (contains 20 closed decisions D1-D8 from CEO review + D1-D12 from eng review)
- `docs/test-plan.md` — what to test where
- `docs/architecture/` — integration spec, Kill Criteria, data model

## Locked architecture decisions (from eng-review iter-5)

- **D1 schema-guided decoding**: provider built-in structured outputs (OpenAI `response_format: json_schema` strict OR Anthropic tool-use). NOT a custom decoder.
- **D2 partial-edge state**: persist-as-you-go with `extraction_complete: bool` flag.
- **D3 cascade coupling**: re-calibrate cascade-OCR judge on D-mode output BEFORE D ships.
- **D4 FP definition**: 3-counter telemetry, FP = rejected-then-same-edge with canonicalization.
- **D5 shadow data**: D-output vs analyst-corrected ground truth on cascade-OCR eval set.
- **D6 test coverage**: complete coverage in Phase 1 — ~33-35 tests total.
- **D7 I/O batching**: batched-write journal (10 edges OR 5 sec, whichever first).
- **D9 timeline**: 2 engineers, 2-2.5 quarters honestly.
- **D10 multi-turn protocol**: multi-call extraction with guardrails firing AFTER each LLM call, BEFORE next chunk commits.
- **D11 regression suite**: iso-precision regression across ALL existing field types (drug name, age limit, dates, step therapy entries, quantity limit).
- **D12 small spec additions**: FP canonicalization, rollback feature flag (`paiq.d_extraction.enabled`), downstream consumer policy (treat `extraction_complete=false` as invisible + 24-hour GC), cascade re-cal uses existing OCR labels, statistical significance lower-bound on Kill Criteria.

## Phase-2 candidates (DEFERRED with revisit triggers)

Do NOT pull these into Phase 1 scope:

- **Approach B** (in-house PageIndex-equivalent + extracted-fact graph as query layer) — revisit when D shadow data shows precision/recall ≥85% AND analysts want a graph query layer
- **Approach F** (embedding similarity) — revisit when ≥20% of remaining false-negative complaints are paraphrase / semantic-equivalence class
- **OSS release** — revisit when B Phase-2 ships AND a differentiation story emerges AND Cognizant legal clears the license
- **Research publication** — revisit when D shadow data N≥50 AND external collaborator identified

## Kill Criteria (do NOT skip these gates)

Full reference at `docs/architecture/kill-criteria.md`. Critical gates:

- **Week-1 sponsor commitment** — written conditional Phase-2 funding terms
- **Week-2 complaint root cause** — <50% relationship-shaped → downgrade
- **Week-3 structure prototype** — Phase-2-only, NOT a Phase 1 gate
- **Week-4 D extraction precision regression** — >5% on existing field types → revert
- **Week-6 guardrails FP rate** — outside 1-15% (counter 1 / total) → tune or disable
- **Quarter-1 D shadow result** — relationship precision <85% OR recall <80% → no Phase 2

## Testing

- Framework: **pytest** (Python).
- Run: `pytest tests/` from project root.
- Coverage target: 100% for Phase 1 — all 33-35 tests in `tests/` must pass before ship.
- Mandatory: `tests/test_extraction_regression.py` proves no regression on existing field types (Week-4 Kill Criteria gate depends on this).
- For prompt changes: run the eval suite at `eval/runners/edge_precision.py` AND `eval/runners/regression.py` and compare against baseline. CI gate posts results.

## Prompt/LLM changes — files that trigger eval suite

If a PR touches any of these patterns, the full eval suite must run:

- `src/d_extraction/prompts.py` — extraction prompt templates
- `src/d_extraction/schema.py` — Pydantic edge schema
- `src/guardrails/detector.py` — guardrails detection logic
- `src/cascade_integration/recal.py` — cascade judge interaction

## Skill routing

When the user's request matches an available gstack skill, invoke it via the Skill tool.

Key routing rules for this project:
- Product strategy / scope expansion → `/plan-ceo-review` (already cleared iter-4)
- Architecture / tests / shipping gate → `/plan-eng-review` (already cleared iter-5)
- Run QA on a feature → `/qa` (uses `docs/test-plan.md` as primary input)
- Just bug-report without fixes → `/qa-only`
- Pre-landing diff review → `/review`
- Visual polish (N/A for this project — no UI) → skip
- Ship / land / deploy → `/ship` then `/land-and-deploy`
- Save progress mid-work → `/context-save`
- Resume from saved context → `/context-restore`

## Project conventions

- **No em dashes in code comments or docs.** Voice rule from gstack.
- **ASCII diagrams** in code comments for non-obvious flows (state machines, request flow, pipeline stages).
- **Pydantic models** for all schemas; provider built-in structured outputs derive from these schemas.
- **Feature flags** for any production-touching change: `paiq.<feature>.enabled` namespace.
- **`extraction_complete: bool`** flag on every persisted edge record; downstream consumers MUST check this.
- **Canonicalize edges** before comparing for the same-edge FP counter (sort tuple elements, canonical drug IDs, normalized predicate names).

## Common commands

```bash
# Install dev dependencies
pip install -e .[dev]

# Run full test suite
pytest tests/

# Run a specific test file
pytest tests/test_guardrails_detection.py -v

# Run eval (edge precision per edge type)
python eval/runners/edge_precision.py

# Run regression suite (iso-precision on existing field types)
python eval/runners/regression.py

# Run cascade-OCR judge re-calibration check
python eval/runners/judge_pass_rate.py
```
