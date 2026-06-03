"""Tests for the paiq-d CLI (offline mock provider; no keys needed)."""

from __future__ import annotations

import json

from src.cli import main


def test_cli_flag(capsys):
    rc = main(["flag", "--provider", "mock"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["provider"] == "mock"
    assert out["d_extraction_enabled"] is False  # default OFF


def test_cli_extract_d_mode(tmp_path, capsys):
    doc_file = tmp_path / "doc.txt"
    doc_file.write_text("FIELD drug_name=Adalimumab\nEDGE requires DRUG_A DRUG_B\n", encoding="utf-8")
    rc = main(["extract", str(doc_file), "--provider", "mock", "--d-mode", "--journal-dir", str(tmp_path / "j")])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["extraction_complete"] is True
    assert any(e["kind"] == "requires" for e in out["edges"])


def test_cli_version(capsys):
    rc = main(["version"])
    assert rc == 0
    assert capsys.readouterr().out.strip()
