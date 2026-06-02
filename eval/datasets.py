"""Eval dataset loader.

The sample dataset under `eval/labels/sample/` is SYNTHETIC and non-PHI, for dev /
CI / demo only. Production eval runs point `--eval-set` at the access-controlled
production label store (the F6 relationship-type + contradiction-validity labels
per `eval/README.md`), NEVER this sample. The Kill Criteria gates are only
meaningful on the real labels.

Dataset format (one JSON object per line):
  {
    "document_id": "sample-001",
    "chunks": ["FIELD drug_name=Adalimumab\\nEDGE requires DRUG_A DRUG_B age_min=18"],
    "gold_edges": [ {Edge JSON} ... ],
    "gold_fields": {"drug_name": "Adalimumab"}
  }
"""

from __future__ import annotations

import json
from pathlib import Path

from src.d_extraction.schema import Edge

SAMPLE_DATASET = Path(__file__).resolve().parent / "labels" / "sample" / "dataset.jsonl"


def resolve_dataset_path(eval_set) -> Path:
    """Resolve a dataset file from a dir or a direct .jsonl path.

    Accepts: a `dataset.jsonl` file, a dir containing one, or a dir whose
    `sample/dataset.jsonl` exists. Falls back to the bundled sample.
    """
    path = Path(eval_set)
    if path.is_file():
        return path
    if path.is_dir():
        for candidate in (path / "dataset.jsonl", path / "sample" / "dataset.jsonl"):
            if candidate.exists():
                return candidate
    return SAMPLE_DATASET


def load_dataset(eval_set) -> list[dict]:
    """Load dataset records (one per document)."""
    path = resolve_dataset_path(eval_set)
    records: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def gold_edges(record: dict) -> list[Edge]:
    """Build Edge objects from a record's gold_edges."""
    return [Edge.model_validate(e) for e in record.get("gold_edges", [])]


def gold_fields(record: dict) -> dict:
    return dict(record.get("gold_fields", {}))
