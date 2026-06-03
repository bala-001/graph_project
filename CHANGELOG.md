# Changelog

All notable changes are documented here. Format loosely follows Keep a Changelog;
versions are MAJOR.MINOR.PATCH.

## [0.1.0] - 2026-06-03

First internal release of PAIQ Idea 11.3 Phase 1 (relationship-aware extraction
"Approach D" + extraction-time guardrails). Offline-safe and deployable. NOT yet
validated for real PBM documents (see README "Status" and `docs/DEPLOYMENT.md`).

### Added
- End-to-end multi-call extraction pipeline (`extract_document`) wiring provider ->
  guardrails (accept/retry/exhaust) -> batched-write journal -> 3-counter FP
  telemetry -> `extraction_complete`, with flag-gated baseline rollback
  (D2/D4/D7/D10/D12).
- Provider abstraction: offline `MockProvider` (deterministic DSL), `OpenAIProvider`
  (json_schema), `AnthropicProvider` (tool-use); selected by config, SDKs imported
  lazily (D1).
- Guardrails: 4 detection scenarios (circular dependency, contradictory limits,
  prerequisite-chain mismatch, age conflict) + reject/retry/exhaust policy +
  3-counter FP telemetry with edge canonicalization (D4/D12).
- Batched-write journal (flush at 10 edges or 5s) + crash-recovery replay (D7), and
  downstream `extraction_complete=false` invisibility + 24h-GC predicate (D12).
- Shadow harness: edge precision/recall with Wilson and Clopper-Pearson lower
  bounds (D5/D12). Cascade-OCR judge re-calibration logic (D3).
- Functional eval runners (edge precision, iso-precision regression, judge
  pass-rate) over a synthetic, non-PHI sample dataset.
- `paiq-d` CLI (extract / flag / version), 12-factor config, Dockerfile, GitHub
  Actions CI (tests + >=90% coverage gate + eval smoke), INSTALL + DEPLOYMENT docs.
- Pydantic edge schema + `canonicalize_edge`; feature flag `paiq.d_extraction.enabled`.

### Safety
- Provider defaults to the offline mock; the D feature flag defaults OFF.
- Fail-closed guard: a real provider refuses to run on the bundled TEMPLATE prompts
  unless `PAIQ_ALLOW_TEMPLATE_PROMPTS=true` is set.

### Not included (gated on Phase-0 org inputs)
- Real extraction prompts (Q3), provider credentials, the F6/PHI eval labels, and
  the live Kill Criteria certification required before any real-document use.

### Tests
- 71 passing, 10 skipped (production-gate regression suite awaiting real labels);
  91% line coverage on `src`.
