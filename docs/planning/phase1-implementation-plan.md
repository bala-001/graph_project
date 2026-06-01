# PAIQ Idea 11.3 Phase 1 — Implementation Plan (D + Guardrails)

Lead engineer build plan. Synthesizes the buildability analysis, the gstack gap
analysis, and the Phase-0 prerequisite analysis into one decisive sequence.
Corrected after a two-reviewer adversarial pass (see Section 8).

## 1. Current state

The scaffold is complete and the plan is cleared to build. Every `src/` package,
test file, and eval runner exists. Some modules are real and validate today:
`src/d_extraction/schema.py` (EdgeKind, DrugNode, IndicationNode, Edge,
DocumentExtraction Pydantic models; `canonicalize_edge()` is still a stub),
`src/guardrails/state.py` (PartialEdgeState), `src/feature_flags/flags.py`
(is_d_enabled / set_d_enabled env-var shim only; the central-flag-service routing
is still deferred per its own docstring), and `src/telemetry/counters.py`
(PerDocumentCounters, fp_rate, 3-counter increments). Others are stubs raising
NotImplementedError or returning placeholders: `src/guardrails/detector.py`,
`src/guardrails/retry.py`, the `flush` / `materialize_complete` / `replay_journal`
paths in `src/journal/`, `canonicalize_edge()`, `src/shadow/harness.py`
(compare_d_to_ground_truth, wilson_lower_bound), and
`src/cascade_integration/recal.py`. All `tests/` are `pytest.skip(...)`
placeholders and pytest is not yet installed (`pip install -e .[dev]` not run).
The two required gstack plan reviews are CLEAR: `/plan-ceo-review` (iter-4, scope
locked to D + guardrails) and `/plan-eng-review` (iter-5, 12 decisions integrated,
~33-35 tests, 2-2.5 quarters). Design and DX reviews are correctly n/a (no UI, OSS
deferred to Phase 2).

## 2. Is gstack blocking the build?

No. Both required plan reviews are CLEAR with zero unresolved items
(`/plan-ceo-review` CLEAR, `/plan-eng-review` CLEAR-PLAN). `/plan-design-review`
and `/plan-devex-review` are n/a for Phase 1 and stay deferred. The only pre-build
blockers are non-gstack items: human decisions (Q3 prompt scope, Q1 staffing, Q8
retry policy), the F1 integration-spec artifact, and Phase-0 data (eval labels,
complaint audit, cascade eval set). Re-run `/plan-eng-review` ONLY if closing Q3
materially changes which prompts/schemas are touched versus the iter-5 assumption,
since that would move the locked eng-week estimate and test scope.

## 3. The dependency split (the crux)

### Buildable now (no Phase-0 dependency)

All of these run against synthetic Edge / DocumentExtraction / PartialEdgeState
fixtures already supplied by `tests/conftest.py`. No live LLM provider, no real
eval set. "Buildable now" means the logic is implementable and unit-testable now;
it does NOT mean the task is fully ship-complete (see the residual-work notes and
Section 4's milestone framing).

- **T6** (slice) — feature flag + prompt-routing slice. flags.py env-var shim is
  done; only verbatim baseline-prompt content is Q3-gated, so build the flag
  mechanics and `get_prompt(d_mode=...)` routing with monkeypatched synthetic
  prompt entries. Residual non-now work: central-flag-service routing.
- **T2** — persist-as-you-go partial-edge state. PartialEdgeState and
  `extraction_complete` already exist; finish the in-memory state wiring.
- **T5** — batched-write journal. Implement `flush()`, `materialize_complete()`,
  `replay_journal()` over the existing append/_should_flush skeleton
  (BATCH_SIZE=10, BATCH_TIMEOUT=5s) using tmp_path + monkeypatched time.
- **T12** — Wilson lower-bound. Self-contained statistics function in
  `src/shadow/harness.py`; no data dependency. Note: TODOS.md lists T12 as
  depending on T11, but `wilson_lower_bound()` is pure binomial math with no data
  dependency, so it is deliberately pulled forward as a zero-dependency entry
  point. T11 only CONSUMES it.
- **T4** (+ `canonicalize_edge`) — guardrails: 4 detect_* scenarios +
  reject/retry/exhaust + 3-counter FP telemetry. Also implement
  `canonicalize_edge()` in schema.py. MAX_RETRIES=3 placeholder is sufficient to
  build and test; Q8 only tunes the constant later. CAUTION: `detector.py` is a
  CLAUDE.md eval-trigger file — see the Section 4 merge-gate note before landing.
- **T13** — D observability aggregation. counters.py core is done; add per-day
  rolling aggregation and guardrails firing-rate emission over synthetic snapshots.
  No skip-test exists to un-skip; T13 requires authoring a new test file
  (`tests/test_observability.py`) + synthetic counter-snapshot fixtures from scratch.
- **T7** (in-process slice only) — downstream consumer policy. Buildable now: the
  in-process "treat `extraction_complete=false` as invisible" filter plus an
  age-based GC PREDICATE (a pure function over synthetic timestamped records).
  NOT buildable now and out of in-process Phase-1 scope: the actual 24h GC
  scheduler / re-queue, which `src/journal/replay.py` states is an infra-layer
  background job. T7 has no existing test; add `tests/test_downstream_visibility.py`.
- **T3 / T11 logic cores** — the pure comparison/statistics math is buildable now
  with synthetic fixtures, even though the live end-to-end runs are blocked (see
  next list). Specifically: `compare_d_to_ground_truth` set-intersection
  precision/recall + iso-precision delta (T11) against synthetic D and GT edge
  lists via tmp_path, and `recalibrate_judge` pass-rate + Wilson-threshold logic
  (T3) against an injected fake `d_extraction_module` callable. The drafted tests
  `test_shadow_compare_computes_precision_recall` and
  `test_judge_pass_rate_threshold_uses_wilson_lower_bound` already use this shape.
- **T9** (unit subset only) — the buildable-now portion of the edge-focused tests:
  flag-routing, journal flush/timeout/replay, guardrails detection/retry,
  canonicalize on synthetic surface forms, Wilson, visibility filter. This is a
  SUBSET of the eng-review "~23 edge tests" total. The remainder of T9 is blocked
  (see next list).

### Blocked until Phase-0 lands

- **T14** — F1 D integration spec is a tech-lead decision artifact; completing it
  requires Q3 (prompt/schema scope) and Q8 (retry threshold) closed in writing.
- **T1** — Pydantic schema half is done, but the load-bearing work (which prompts
  change + real OpenAI json_schema-strict / Anthropic tool-use wiring in
  extractor.py and prompts.py) is gated on Q3 and live provider access.
- **T3 (live run)** — cascade-OCR judge re-cal on REAL D-mode output needs the real
  50-doc cascade eval set with OCR labels (blocked by T1/Q3). Logic core is in the
  buildable-now list above.
- **T8** — relationship-type + contradiction-validity labels are an analyst data
  deliverable sourced from PHI-adjacent corrected extractions; not synthesizable.
- **T10** — iso-precision regression gate (Week-4 Kill Criteria) compares D-mode
  vs baseline on real eval-set documents with analyst ground truth. The 10
  `@pytest.mark.regression` tests cannot go green now.
- **T11 (live run)** — shadow harness comparison ON the eval set needs
  analyst-corrected ground truth and real D-mode output (blocked by T1/T8). Logic
  core is in the buildable-now list above.
- **T9 (blocked subset)** — the d_extraction provider/multi-call tests
  (`test_d_extraction.py`, tagged T1), the surface-form-to-canonical-ID test that
  needs the real drug dictionary, the 10 regression tests, and the live shadow
  compare test.

## 4. Recommended build sequence

Tests already exist as skips. Follow the project pytest + 100% Phase-1 coverage
rule: for each task with a drafted test, un-skip the target tests FIRST (TDD red),
implement to green, then refactor. T7 and T13 are the exceptions — they need new
test files authored from scratch (no skip to flip). Run `pytest tests/` per task
and keep the suite green as the buildable-now subset grows.

**Milestone framing (important):** the buildable-now subset reaches a
**unit-green** milestone, NOT a ship-ready one. `/ship` is gated behind the
Phase-0 wave (T1/T10/T11 live + T3 re-cal) per Section 6.

**Merge-gate on eval-trigger files (important):** per CLAUDE.md, any PR touching
`src/d_extraction/prompts.py`, `src/d_extraction/schema.py`,
`src/guardrails/detector.py`, or `src/cascade_integration/recal.py` MUST run the
full eval suite. The eval runners require the F6 labels, which are Phase-0-blocked.
So the buildable-now work on `detector.py` (T4 + canonicalize) and `schema.py`
(canonicalize) can be WRITTEN now, but it cannot LAND to the protected branch until
F6 labels exist and the eval suite can run. Build it on an isolated branch with a
documented merge-block, or hold the merge until the Phase-0 eval set lands.

Two engineers run two parallel lanes after a shared step 0. Dependency-ordered
within each lane.

### Step 0 — both engineers (env setup, must precede all code)

1. `pip install -e .[dev]` so pytest and tooling exist.
2. Local version control: the project is not a git repo. `git init` + an initial
   commit + a feature branch is recommended before feature work, but it is a
   repo-state action that needs your explicit go-ahead — it is not done
   automatically. It does not gate the technical work; it is workflow hygiene.

### Lane A — extraction-core (Engineer 1)

`tests/test_feature_flag.py`, `tests/test_journal.py`, new
`tests/test_downstream_visibility.py`.

1. **T6** (slice) — feature flag + `get_prompt(d_mode=...)` routing
   (`src/feature_flags/flags.py`, `src/d_extraction/prompts.py`). No deps.
2. **T2** — persist-as-you-go partial-edge state (`src/guardrails/state.py`,
   `src/d_extraction/`). Builds on existing schema types.
3. **T5** — batched-write journal flush/materialize/replay
   (`src/journal/writer.py`, `src/journal/replay.py`). Depends on T2.
4. **T7** (in-process slice) — downstream visibility filter + 24h GC predicate
   (new module + new test). GC scheduler stays out of scope. Depends on T2.

### Lane B — guardrails-core + eval-stats (Engineer 2)

`tests/test_guardrails_detection.py`, `tests/test_guardrails_retry.py`,
`tests/test_canonicalization.py`, `tests/test_shadow_harness.py`, new
`tests/test_observability.py`.

1. **T12** — `wilson_lower_bound()` in `src/shadow/harness.py`. No real deps; un-skip
   the drafted Wilson test.
2. **canonicalize_edge()** in `src/d_extraction/schema.py` (sort tuple elements,
   canonical drug IDs, normalized predicate names). Prerequisite for the T4 FP
   counter; land it with `tests/test_canonicalization.py` (the synthetic-surface-form
   case; the real-drug-dictionary case stays blocked under T1). Eval-trigger file:
   honor the Section 4 merge-gate.
3. **T4** — guardrails: 4 detect_* scenarios in `src/guardrails/detector.py`,
   reject/retry/exhaust `handle_verdict` in `src/guardrails/retry.py`
   (MAX_RETRIES=3 placeholder), wired to the 3-counter FP telemetry. Depends on the
   canonicalize step and consumes the synthetic PartialEdgeState + fake
   retry_llm_call callable. Eval-trigger file (`detector.py`): honor the merge-gate.
4. **T11 / T3 logic cores** — `compare_d_to_ground_truth` set-math (T11) and
   `recalibrate_judge` pass-rate/threshold math with an injected callable (T3),
   both against synthetic fixtures. Live runs stay blocked until Phase-0.
5. **T13** — observability aggregation / firing-rate emission over
   `src/telemetry/counters.py` snapshots, with a new test file. Depends on T4.

### Convergence — T9 unit subset (either engineer, lockstep)

Implement the buildable-now edge-focused unit tests across detection, retry
counters, journal crash-recovery, canonicalization (synthetic surface forms),
visibility filter, and flag routing. These land in lockstep with T2/T4/T5/T6/T7.
The provider/multi-call tests, the real-drug-dictionary canonicalization test, the
10 regression tests, and the live shadow compare test stay skipped until Phase-0.
Target: the full buildable-now subset green (unit-green milestone) before Phase-0
unblocks T1/T3-live/T8/T10/T11-live.

## 5. Phase-0 prerequisites to unblock the rest

| Prerequisite | Owner | What it unblocks |
| --- | --- | --- |
| Q3 prompt/schema scope: enumerate every existing PAIQ prompt (drug-name, age-limit, dates, step-therapy, quantity-limit) and define each D-mode variant that also emits edges | Tech lead | T1 (BASELINE/D_PROMPTS content + provider wiring), T14 (F1 spec), D eng-week estimate |
| Q8 retry/exhaust threshold (recommend N=3) + 1-15% FP operating band, with review cadence | Tech lead | Finalizes T4 retry constant; completes T14 |
| F1 D integration spec (`docs/architecture/d-integration-spec.md`); lands before code that crosses the extraction/guardrails/journal/shadow contract | Tech lead | T14, the cross-module contract for T1/T3/T11 (depends on Q3 + Q8) |
| Real PAIQ pipeline access: chunking + LLM-call path, provider structured-output credentials, drug dictionary for canonical IDs, live cascade-OCR judge harness | Tech lead / PAIQ platform owners | T1, T3-live, T11-live end-to-end extraction + drug-ID resolution |
| Base 50-doc cascade-OCR eval set with OCR-quality labels (shared cascade-OCR artifact) | Cascade-OCR plan owner | T3 judge re-cal, substrate for T8 labels |
| F6 eval labels: `eval/labels/relationship_types.jsonl` + `eval/labels/contradiction_validity.jsonl` from analyst-corrected extractions | Tech lead (analyst-sourced) | T8, T10, T11-live; real edge_precision.py / regression.py runs; unblocks the eval-trigger merge-gate |
| Phase-0 complaint root-cause audit (Week-2: >=50% relationship/contradiction-shaped, kappa >= 0.7) + V1 baseline measurement | Project lead + sponsor | Architectural go/no-go; regression baseline for regression.py |
| Week-1 sponsor commitment: written conditional Phase-2 funding terms | Project lead | Week-1 Kill Criteria; absence auto-downgrades to Approach A |
| Q1 staffing: written confirmation of 2 engineers for 2-2.5 quarters | Engineering manager | Whether the two parallel lanes can actually run |
| Q2 framing-gate decision tree (scope redirect if non-relationship pain dominates), signed | Project lead + sponsor | Phase-0 exit decision |
| Week-1 SLA budget X seconds (graph budget = 0.2X) | Project lead + sponsor | Quarter-1 latency Kill Criteria gate |

Note: every prerequisite has `code_can_proceed_without=true` for the
buildable-now subset. They gate the second wave (T1/T3-live/T8/T10/T11-live) and
the merge-gate, not the writing of Step 0 through the T9 unit subset.

**Build-at-risk caveat:** the buildable-now coding can start before the Week-1
sponsor-commitment gate and the Week-2 complaint-root-cause gate clear, but it is
spent at risk. A Week-1 "no sponsor commitment" or a Week-2 "<50%
relationship-shaped" result downgrades the whole effort to Approach A
(contradiction-only) and discards most of the D + guardrails build. Decide
consciously whether to spend engineering before those two gates clear.

## 6. gstack workflow from here

### Pre-build (do now)

1. Environment: `pip install -e .[dev]`. Local git setup (init + branch) is
   recommended but needs your go-ahead (Section 4 Step 0).
2. No plan-level gstack re-run. CEO + Eng are CLEAR. Re-run `/plan-eng-review`
   only if Q3 materially changes the prompt/schema touch surface.
3. `/context-save` at the start so the two engineers share a checkpoint; CLAUDE.md
   routes mid-work saves to `/context-save` and resumes to `/context-restore`.

### During build (per feature, in order)

1. `/context-save` at handoffs and before context fills.
2. `/qa` on each feature as it lands (D extraction, guardrails detection/retry,
   journal, feature flag, downstream policy), using `docs/test-plan.md` as the
   primary input; pair with `pytest tests/`. Use `/qa-only` for bug reports
   without fixes.
3. `/review` on every diff immediately before landing. PRs touching
   `src/d_extraction/prompts.py`, `src/d_extraction/schema.py`,
   `src/guardrails/detector.py`, or `src/cascade_integration/recal.py` MUST run the
   full eval suite (`eval/runners/edge_precision.py`, `eval/runners/regression.py`,
   `eval/runners/judge_pass_rate.py`) per CLAUDE.md. This is the merge-gate that
   blocks landing the buildable-now detector/schema work until F6 labels exist.

### Ship and deploy (only after the Phase-0 wave completes)

`/ship` is NOT reachable from the buildable-now subset alone. It requires the
Phase-0 wave: T1 (live D-mode prompts), T10 (regression suite green on real data),
T11 (shadow precision/recall), and T3 (cascade re-cal on FINAL D-mode output).

1. Pre-ship checkpoint: T3 cascade re-cal runs on FINAL D-mode prompt output
   (post-T1/Q3) and passes Wilson-lower >= 95% before `/ship`. recal.py is an
   eval-trigger file, so its implementation PR also runs the eval suite.
2. `/ship` — verify 100% pass on all ~33-35 tests, mandatory
   `tests/test_extraction_regression.py` green for the Week-4 Kill Criteria, eval
   baselines compared, cascade re-cal judge-pass-rate >= 95% (Wilson lower-bound).
3. `/land-and-deploy` — land behind `paiq.d_extraction.enabled` with the baseline
   prompt path preserved (one-config rollback per D12).
4. `/canary` (recommended) — gradual rollout of the prompt-mode swap; monitor
   Week-4 precision-regression and Week-6 guardrails FP-rate (1-15% band) windows.
5. `/document-release` (recommended) — record what shipped, the feature flag, the
   `extraction_complete=false` consumer policy, and rollback steps.

## 7. Immediate next action

Run `pip install -e .[dev]` from the project root so pytest exists. (If you want
local version control, tell me and I will `git init` + branch first.) Then start
**Lane A T6** and **Lane B T12** in parallel: un-skip `tests/test_feature_flag.py`
and the Wilson test in `tests/test_shadow_harness.py`, watch them fail, and
implement the flag-routing slice and `wilson_lower_bound()` to green. These are the
two zero-dependency entry points and need no Phase-0 input and no eval-trigger
merge-gate.

## 8. Adversarial review corrections (what changed from the first draft)

Two reviewers verified the first synthesis against the code, the locked decisions
D1-D12, and the Kill Criteria. Corrections folded in:

- **T4/canonicalize/schema eval-trigger merge-gate** (major): `detector.py` and
  `schema.py` are CLAUDE.md eval-trigger files; the FIRST PR touching them must run
  the eval suite, which is Phase-0-blocked. Buildable-now work on them can be
  written but not landed to the protected branch until F6 labels exist.
- **`/ship` not reachable from buildable-now** (major): the regression suite (T10)
  and shadow (T11) that the ship gate asserts are Phase-0-blocked. The buildable-now
  target is relabeled "unit-green, not ship-ready" and `/ship` is gated behind the
  Phase-0 wave.
- **T7 over-claimed** (major): only the in-process visibility filter + GC predicate
  are buildable now; the 24h GC scheduler is infra-layer and out of in-process
  scope. A new `tests/test_downstream_visibility.py` is required.
- **T3/T11 over-blocked** (major): their pure comparison/statistics cores are
  unit-testable now with synthetic fixtures; only the live runs are blocked.
- **T12-vs-TODOS dependency override** (minor): flagged explicitly.
- **T13 has no skip to flip** (minor): noted that it needs a new test file authored
  from scratch.
- **"23 tests" conflation** (minor): split into buildable-now unit subset vs
  Phase-0-blocked subset.
- **git init as mandatory Step 0** (minor): downgraded to "needs your go-ahead."
- **Week-1/Week-2 Kill Criteria gates** (minor): added the build-at-risk caveat.
