"""LLM provider abstraction per eng-review D1 (provider built-in structured outputs).

Three implementations behind one interface:

- MockProvider  - deterministic, OFFLINE. Parses a tiny line DSL out of the chunk
  so dev / CI / tests exercise the full extraction + guardrail loop with no
  network and no API key. NOT for production extraction.
- OpenAIProvider     - response_format json_schema strict (D1 primary).
- AnthropicProvider  - forced tool-use (D1 fallback).

`get_provider(config)` selects by `config.provider`. The real providers import
their SDK lazily, so the package installs and runs in mock mode without those
SDKs or keys present.

Each provider returns, for one chunk, a (edges, fields) pair:
  - edges:  list[Edge] emitted for the chunk
  - fields: dict of existing field-level outputs (drug_name, age_limit, ...)

`retry_chunk(...)` is the retry path the guardrails use (D4): it re-asks the
model with the validator error attached and returns a single replacement Edge.
"""

from __future__ import annotations

import json
from typing import Protocol

from .schema import DocumentExtraction, Edge, EdgeKind, DrugNode, IndicationNode


class Provider(Protocol):
    """What the extractor needs from any provider."""

    def extract_chunk(self, prompt: str, chunk: str) -> tuple[list[Edge], dict]:
        ...

    def retry_chunk(self, prompt: str, chunk: str, rejected: Edge, validator_error: str) -> Edge:
        ...


# --------------------------------------------------------------------------- #
# Mock provider (offline, deterministic)                                      #
# --------------------------------------------------------------------------- #

class MockProvider:
    """Offline, deterministic provider for dev / CI / tests.

    Parses a line-oriented DSL from the chunk text:

        FIELD <key>=<value>
        EDGE <kind> <subject_id> <object_id> [qual=value ...]

    Example chunk:
        FIELD drug_name=Adalimumab
        EDGE requires DRUG_A DRUG_B age_min=18
        EDGE excludes DRUG_A DRUG_B

    Lines that don't match are ignored. This lets tests craft chunks that emit
    specific edges (including deliberately conflicting ones to drive guardrails).
    """

    def extract_chunk(self, prompt: str, chunk: str) -> tuple[list[Edge], dict]:
        edges: list[Edge] = []
        fields: dict = {}
        for raw in chunk.splitlines():
            line = raw.strip()
            if not line:
                continue
            if line.upper().startswith("FIELD "):
                body = line[6:].strip()
                if "=" in body:
                    key, _, value = body.partition("=")
                    fields[key.strip()] = value.strip()
            elif line.upper().startswith("EDGE "):
                edge = self._parse_edge(line[5:].strip())
                if edge is not None:
                    edges.append(edge)
        return edges, fields

    def retry_chunk(self, prompt: str, chunk: str, rejected: Edge, validator_error: str) -> Edge:
        """Deterministic correction: replace the rejected edge with a benign
        applies_to edge to a fresh indication, which passes every detector. This
        models the model 'fixing' a flagged relationship (-> guardrails counter 2).
        """
        return Edge(
            kind=EdgeKind.APPLIES_TO,
            subject=rejected.subject,
            object=IndicationNode(canonical_id=None, surface_form="unspecified-indication"),
            qualifiers={},
            source_page=rejected.source_page,
            source_chunk_id=rejected.source_chunk_id,
        )

    @staticmethod
    def _parse_edge(body: str) -> Edge | None:
        parts = body.split()
        if len(parts) < 3:
            return None
        kind_token, subject_id, object_id = parts[0], parts[1], parts[2]
        try:
            kind = EdgeKind(kind_token.lower())
        except ValueError:
            return None
        qualifiers: dict = {}
        for token in parts[3:]:
            if "=" in token:
                key, _, value = token.partition("=")
                qualifiers[key.strip()] = _coerce(value.strip())
        return Edge(
            kind=kind,
            subject=DrugNode(canonical_id=subject_id, surface_form=subject_id),
            object=DrugNode(canonical_id=object_id, surface_form=object_id),
            qualifiers=qualifiers,
        )


def _coerce(value: str):
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


# --------------------------------------------------------------------------- #
# OpenAI provider (json_schema strict)                                        #
# --------------------------------------------------------------------------- #

class OpenAIProvider:
    """OpenAI structured outputs (D1 primary). Imports the SDK lazily."""

    def __init__(self, model: str = "gpt-4o"):
        self.model = model

    def _client(self):
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - exercised only with the SDK absent
            raise RuntimeError("openai SDK not installed; `pip install openai` or use PAIQ_PROVIDER=mock") from exc
        return OpenAI()

    def extract_chunk(self, prompt: str, chunk: str) -> tuple[list[Edge], dict]:
        response = self._client().chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": chunk}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "document_extraction",
                    "schema": DocumentExtraction.model_json_schema(),
                    "strict": True,
                },
            },
        )
        doc = DocumentExtraction.model_validate_json(response.choices[0].message.content)
        return doc.edges, doc.existing_fields

    def retry_chunk(self, prompt: str, chunk: str, rejected: Edge, validator_error: str) -> Edge:
        retry_prompt = f"{prompt}\n\nThe previous extraction was rejected: {validator_error}\nRe-extract this relationship correctly."
        edges, _ = self.extract_chunk(retry_prompt, chunk)
        if not edges:
            raise RuntimeError("provider returned no edge on retry")
        return edges[0]


# --------------------------------------------------------------------------- #
# Anthropic provider (forced tool-use)                                        #
# --------------------------------------------------------------------------- #

class AnthropicProvider:
    """Anthropic tool-use structured outputs (D1 fallback). Imports the SDK lazily."""

    def __init__(self, model: str = "claude-opus-4-7"):
        self.model = model

    def _client(self):
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - exercised only with the SDK absent
            raise RuntimeError("anthropic SDK not installed; `pip install anthropic` or use PAIQ_PROVIDER=mock") from exc
        return anthropic.Anthropic()

    def extract_chunk(self, prompt: str, chunk: str) -> tuple[list[Edge], dict]:
        response = self._client().messages.create(
            model=self.model,
            max_tokens=4096,
            tools=[{
                "name": "emit_document_extraction",
                "description": "Emit the structured edges + existing fields extracted from this chunk",
                "input_schema": DocumentExtraction.model_json_schema(),
            }],
            tool_choice={"type": "tool", "name": "emit_document_extraction"},
            messages=[{"role": "user", "content": f"{prompt}\n\n---\n\n{chunk}"}],
        )
        tool_use = next(b for b in response.content if getattr(b, "type", None) == "tool_use")
        doc = DocumentExtraction.model_validate(tool_use.input)
        return doc.edges, doc.existing_fields

    def retry_chunk(self, prompt: str, chunk: str, rejected: Edge, validator_error: str) -> Edge:
        retry_prompt = f"{prompt}\n\nThe previous extraction was rejected: {validator_error}\nRe-extract this relationship correctly."
        edges, _ = self.extract_chunk(retry_prompt, chunk)
        if not edges:
            raise RuntimeError("provider returned no edge on retry")
        return edges[0]


def get_provider(config) -> Provider:
    """Select a provider by config.provider (mock | openai | anthropic)."""
    name = (config.provider or "mock").lower()
    if name == "mock":
        return MockProvider()
    if name == "openai":
        return OpenAIProvider(model=config.openai_model)
    if name == "anthropic":
        return AnthropicProvider(model=config.anthropic_model)
    raise ValueError(f"unknown provider: {config.provider!r} (expected mock|openai|anthropic)")
