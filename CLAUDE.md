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

## Current state & session continuity (READ THIS FIRST)

**v0.1.0 is shipped** (first internal release, 2026-06-03). The cleared scaffold is
now a fully-implemented, installable, deployable Python package. Do NOT re-plan or
re-scaffold; build forward from here.

### What exists and works (offline, no API keys)
- End-to-end pipeline `src/d_extraction/extractor.py::extract_document`: provider ->
  guardrails (accept/retry/exhaust) -> batched journal -> 3-counter FP telemetry ->
  `extraction_complete`. Multi-call (D10), flag-gated baseline rollback (D12).
- Provider abstraction `src/d_extraction/provider.py`: `MockProvider` (offline,
  deterministic DSL: `FIELD k=v`, `EDGE kind subj obj qual=val`), `OpenAIProvider`
  (json_schema), `AnthropicProvider` (tool-use). `get_provider(config)`, SDKs lazy.
- `src/config.py` `Config.from_env()` — all knobs are `PAIQ_*` env vars.
- Guardrails (`src/guardrails/`): 4 detectors + retry + 3-counter telemetry;
  `canonicalize_edge` in schema.py; subjects AND objects keyed via `node_canonical_id`.
- Journal (`src/journal/`): flush/materialize/replay + `downstream.py` visibility +
  24h-GC predicate. Shadow (`src/shadow/harness.py`): precision/recall + Wilson +
  Clopper-Pearson + `lower_bound(method="auto")`. Cascade recal (`src/cascade_integration/`).
- `src/cli.py` -> `paiq-d` console script (`extract` / `flag` / `version`).
- Tests: 71 pass + 10 skip (the per-field regression suite, awaiting real labels).
  Coverage ~91% on `src` (CI gate >=90%).
- Packaging: `src` IS the installed package (pyproject `where=["."] include=["src*"]`).
  Plus Dockerfile, `.github/workflows/ci.yml`, `docs/INSTALL.md`, `docs/DEPLOYMENT.md`,
  `CHANGELOG.md`.

### Safety model (healthcare — do NOT weaken)
- Default provider = offline `mock`; D flag (`PAIQ_D_EXTRACTION_ENABLED`) defaults OFF.
- FAIL-CLOSED: a real provider refuses to run on the bundled TEMPLATE prompts
  (`src/d_extraction/prompts.py`) unless `PAIQ_ALLOW_TEMPLATE_PROMPTS=true`. Bundled
  prompts are NOT production-validated; real prompts land at Q3.
- Eval sample (`eval/labels/sample/dataset.jsonl`) is SYNTHETIC, non-PHI (each record
  `"synthetic": true`). Real F6/PHI labels are gitignored, never committed.
- Never fabricate real prompts, PHI labels, or "passing" Kill Criteria gate results.

### Still gated on org inputs (cannot be coded here)
Q3 real prompts, provider API keys, F6 relationship/contradiction labels + the 50-doc
cascade-OCR eval set, sponsor commitment + complaint audit. Until these land, the
product stays offline-safe; real-document go-live is blocked.

### Git / release facts
- GitHub remote `origin` = github.com/bala-001/graph_project. Base branch: `master`.
- v0.1.0 shipped via PR #1 (merged to master, commit 6ccedd1) + tag `v0.1.0` pushed.
  Feature branch deleted. Wheel at `dist/paiq_graph-0.1.0-py3-none-any.whl`.
- `gh` CLI is NOT installed and there is no token env var; PRs and GitHub Releases
  are created via the web UI (or install + auth `gh` first). Do NOT extract the
  stored git credential to call the API — that is blocked and not authorized.
- Untracked on purpose: `docs/presentation/`, `docs/workflow.md` (user-authored).

### Process notes for the next session
- Eval-trigger merge gate (see "Prompt/LLM changes" below): any PR touching
  prompts.py / schema.py / detector.py / recal.py must run the full eval suite on
  REAL labels before merge to master. CI runs it on the synthetic sample only.
- OpenAI strict mode is off because the schema has open-ended maps (qualifiers,
  existing_fields); closing them is a Q3-era schema decision.
- Deferred (documented in DEPLOYMENT.md): rename generic `src` package -> `paiq_graph`
  before any multi-package deployment.
- History: `docs/planning/phase1-implementation-plan.md`, `TODOS.md`. CEO+Eng reviews
  CLEAR; Phase 2 still deferred.

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
- Coverage target: 100% for the full Phase 1. **Current (v0.1.0): 71 pass, 10 skip, ~91% on `src`** (CI gate >=90%). The 10 skips are `tests/test_extraction_regression.py` — the per-field iso-precision suite that needs the real F6 labels; it stays skipped until those land (do not delete or fake-pass it).
- Mandatory: `tests/test_extraction_regression.py` proves no regression on existing field types (Week-4 Kill Criteria gate depends on this). Runs for real only against the production label store.
- For prompt changes: run `eval/runners/edge_precision.py`, `eval/runners/regression.py`, `eval/runners/judge_pass_rate.py` (each takes `--eval-set`). CI runs them on `eval/labels/sample` (synthetic); the 85%/95% gates are only meaningful on real labels.

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
# Install (dev = tests + coverage + scipy + provider SDKs)
pip install -e .[dev]

# Tests + coverage gate
pytest tests/
pytest tests/ -o addopts="" -q --cov=src --cov-fail-under=90

# Run extraction offline (mock provider, D mode) via the CLI
printf 'FIELD drug_name=Adalimumab\nEDGE requires DRUG_A DRUG_B age_min=18\n' > /tmp/doc.txt
paiq-d extract /tmp/doc.txt --provider mock --d-mode
paiq-d flag          # show resolved config
paiq-d version

# Eval runners against the SYNTHETIC sample (non-PHI; dev/CI only)
python eval/runners/edge_precision.py  --eval-set eval/labels/sample
python eval/runners/regression.py      --eval-set eval/labels/sample
python eval/runners/judge_pass_rate.py --eval-set eval/labels/sample --use-wilson-lower-bound

# Build the wheel (python -m build is shadowed by a local build/ dir; use pip wheel)
python -m pip wheel . --no-deps -w dist
```

Provider/flag for real use (gated — see safety model above):
`PAIQ_PROVIDER=openai|anthropic`, `PAIQ_D_EXTRACTION_ENABLED=true`, plus
`OPENAI_API_KEY`/`ANTHROPIC_API_KEY`. A real provider needs real prompts (Q3) or
`PAIQ_ALLOW_TEMPLATE_PROMPTS=true` to bypass the fail-closed guard (testing only).
