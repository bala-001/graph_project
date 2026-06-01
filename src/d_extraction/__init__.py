"""D — relationship-aware extraction (modifies the existing extraction pipeline).

Per eng-review D1: provider built-in structured outputs (OpenAI json_schema strict
OR Anthropic tool-use mode). NOT a custom decoder, NOT a constrained-decoding
library.

Public surface:
- `schema`: Pydantic edge schema + DocumentExtraction
- `prompts`: D-modified extraction prompts + provider-mode swap + BASELINE_PROMPTS preserved for rollback
- `extractor`: multi-call extraction protocol (D10)
"""

from .schema import (
    DocumentExtraction,
    Edge,
    EdgeKind,
    DrugNode,
    IndicationNode,
)
from .extractor import extract_document

__all__ = [
    "DocumentExtraction",
    "Edge",
    "EdgeKind",
    "DrugNode",
    "IndicationNode",
    "extract_document",
]
