# Install

PAIQ 11.3 D-extraction is a Python package (`paiq-graph`, importable as `src`)
with a `paiq-d` CLI. It runs offline by default (MockProvider, feature flag OFF),
so it installs and runs with no API keys.

## Requirements
- Python 3.10+
- pip

## Install

```bash
# Core (offline mock provider only):
pip install -e .

# With real LLM providers (needed when PAIQ_PROVIDER=openai|anthropic):
pip install -e ".[providers]"

# With the eval runners (scipy for Clopper-Pearson / Wilson):
pip install -e ".[eval]"

# Everything for development (tests, coverage, providers, scipy):
pip install -e ".[dev]"
```

## Quick start (offline, no keys)

```bash
paiq-d flag                       # show resolved config
echo "FIELD drug_name=Adalimumab
EDGE requires DRUG_A DRUG_B age_min=18" > /tmp/doc.txt
paiq-d extract /tmp/doc.txt --provider mock --d-mode
```

The mock provider parses a small DSL (`FIELD key=value`, `EDGE kind subj obj qual=val`)
so you can exercise the full extraction + guardrail loop with no network.

## Run tests and eval

```bash
pytest tests/                                            # 68 tests
pytest tests/ --cov=src --cov-report=term-missing        # coverage (>=90%)

# Eval runners against the synthetic sample (non-PHI, dev/CI only):
python eval/runners/regression.py     --eval-set eval/labels/sample   # PASS
python eval/runners/edge_precision.py --eval-set eval/labels/sample   # report
python eval/runners/judge_pass_rate.py --eval-set eval/labels/sample --use-wilson-lower-bound
```

## Configuration (environment variables)

| Variable | Default | Meaning |
| --- | --- | --- |
| `PAIQ_PROVIDER` | `mock` | `mock` \| `openai` \| `anthropic` |
| `PAIQ_OPENAI_MODEL` | `gpt-4o` | OpenAI model when provider=openai |
| `PAIQ_ANTHROPIC_MODEL` | `claude-opus-4-7` | Anthropic model when provider=anthropic |
| `PAIQ_D_EXTRACTION_ENABLED` | `false` | D feature flag (D12 rollback path) |
| `PAIQ_JOURNAL_DIR` | `.paiq-journals` | batched-write journal dir |
| `PAIQ_JOURNAL_BATCH_SIZE` | `10` | D7 flush size |
| `PAIQ_JOURNAL_BATCH_TIMEOUT` | `5.0` | D7 flush seconds |
| `PAIQ_GUARDRAILS_MAX_RETRIES` | `3` | Q8 retry/exhaust threshold |
| `PAIQ_ALLOW_TEMPLATE_PROMPTS` | (unset) | override the fail-closed guard that blocks a real provider on the bundled template prompts (testing only) |

Real provider keys are read by the provider SDKs from the environment
(`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`); this package never stores them.

## Before real-document use (production prerequisites)

The bundled prompts are TEMPLATES and the eval data is SYNTHETIC. The extractor
FAILS CLOSED: a real provider (`openai`/`anthropic`) refuses to run while those
templates are unedited (override only for testing with
`PAIQ_ALLOW_TEMPLATE_PROMPTS=true`). Before extracting real PBM documents you must
supply, from the org:
1. The real PAIQ extraction prompts (the Q3 decision) into `src/d_extraction/prompts.py`
   (replacing the template text automatically releases the fail-closed guard).
2. Provider credentials and set `PAIQ_PROVIDER` + `PAIQ_D_EXTRACTION_ENABLED=true`.
3. The F6 relationship/contradiction labels + the cascade-OCR eval set into the
   access-controlled label store, then certify the Kill Criteria gates on them.

See `docs/DEPLOYMENT.md` and `docs/planning/phase1-implementation-plan.md`.
