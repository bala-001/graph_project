"""Command-line entrypoint for the PAIQ D extraction service.

Installed as `paiq-d` (see pyproject [project.scripts]).

  paiq-d extract <document-file>   run extraction; chunks split on a delimiter
  paiq-d flag                      show the resolved config (provider, flag, ...)
  paiq-d version                   print the package version

The default provider is the offline MockProvider and the D feature flag defaults
OFF, so `paiq-d extract` is safe to run with no API keys; it will do baseline
field extraction only until PAIQ_D_EXTRACTION_ENABLED=true and a real provider
are configured.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import Config
from .d_extraction import extract_document


def _build_config(args) -> Config:
    cfg = Config.from_env()
    if getattr(args, "provider", None):
        cfg.provider = args.provider
    if getattr(args, "d_mode", None) is not None:
        cfg.d_enabled = args.d_mode
    if getattr(args, "journal_dir", None):
        cfg.journal_dir = args.journal_dir
    return cfg


def cmd_extract(args) -> int:
    cfg = _build_config(args)
    text = Path(args.document).read_text(encoding="utf-8")
    chunks = [c for c in text.split(args.delim) if c.strip()]
    if not chunks:
        chunks = [text]
    document_id = args.document_id or Path(args.document).stem
    doc = extract_document(document_id, chunks, cfg)
    print(doc.model_dump_json(indent=2))
    return 0


def cmd_flag(args) -> int:
    import json

    cfg = _build_config(args)
    print(json.dumps({
        "provider": cfg.provider,
        "d_extraction_enabled": cfg.d_enabled,
        "openai_model": cfg.openai_model,
        "anthropic_model": cfg.anthropic_model,
        "journal_dir": cfg.journal_dir,
        "batch_size": cfg.batch_size,
        "batch_timeout_seconds": cfg.batch_timeout_seconds,
        "max_retries": cfg.max_retries,
    }, indent=2))
    return 0


def cmd_version(args) -> int:
    try:
        from importlib.metadata import version

        print(version("paiq-graph"))
    except Exception:
        print("0.1.0 (uninstalled)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="paiq-d", description="PAIQ 11.3 relationship-aware extraction (D + guardrails)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_extract = sub.add_parser("extract", help="run extraction on a document file")
    p_extract.add_argument("document", type=str, help="path to a document file")
    p_extract.add_argument("--document-id", type=str, default=None)
    p_extract.add_argument("--delim", type=str, default="\n\n", help="chunk delimiter (default: blank line)")
    p_extract.add_argument("--provider", choices=["mock", "openai", "anthropic"], default=None)
    p_extract.add_argument("--d-mode", dest="d_mode", action="store_true", default=None, help="force D mode on")
    p_extract.add_argument("--journal-dir", type=str, default=None)
    p_extract.set_defaults(func=cmd_extract)

    p_flag = sub.add_parser("flag", help="show resolved configuration")
    p_flag.add_argument("--provider", choices=["mock", "openai", "anthropic"], default=None)
    p_flag.add_argument("--d-mode", dest="d_mode", action="store_true", default=None)
    p_flag.add_argument("--journal-dir", type=str, default=None)
    p_flag.set_defaults(func=cmd_flag)

    p_version = sub.add_parser("version", help="print version")
    p_version.set_defaults(func=cmd_version)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
