"""CLI end to end in a temporary project root, with SYNTHETIC data."""

import json
import stat

import pytest
from synthetic_data import SYNTHETIC_FIELDS, money_sum

from hospital_analytics.cli import main
from hospital_analytics.integrity import sha256_file


@pytest.fixture
def project(tmp_path, dbc_file):
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    source = raw / "SYNTH.dbc"
    source.write_bytes(dbc_file.read_bytes())
    common = ["--root", str(tmp_path), "--manifest", str(tmp_path / "data" / "MANIFEST.json")]
    return tmp_path, source, raw / "SYNTH.parquet", common


def register(source, common, **extra):
    args = [
        *common,
        "register-source",
        "--source",
        str(source),
        "--official-url",
        "ftp://example.invalid/SYNTH.dbc",
        "--obtained-at",
        "2026-01-01",
        "--obtained-by",
        "test",
    ]
    for key, value in extra.items():
        args += [f"--{key.replace('_', '-')}", str(value)]
    return main(args)


def test_full_pipeline(project, rows, capsys):
    root, source, parquet, common = project
    assert register(source, common, expected_sha256=sha256_file(source)) == 0
    assert not source.stat().st_mode & stat.S_IWUSR  # source made read-only

    assert main([*common, "convert", "--source", str(source), "--destination", str(parquet)]) == 0
    assert not parquet.stat().st_mode & stat.S_IWUSR

    manifest = json.loads((root / "data" / "MANIFEST.json").read_text())
    assert set(manifest["sources"]) == {"data/raw/SYNTH.dbc"}
    assert manifest["derived"]["data/raw/SYNTH.parquet"]["derived_from"] == "data/raw/SYNTH.dbc"

    capsys.readouterr()
    code = main(
        [
            *common,
            "validate",
            "--parquet",
            str(parquet),
            "--expect-records",
            str(len(rows)),
            "--expect-columns",
            str(len(SYNTHETIC_FIELDS)),
            "--expect-val-tot",
            money_sum(rows),
        ]
    )
    assert code == 0, capsys.readouterr().out


def test_validate_with_historical_targets_reports_divergence(project, capsys):
    """Synthetic data must never pass as the real base: default targets are historical."""
    _, source, parquet, common = project
    register(source, common)
    main([*common, "convert", "--source", str(source), "--destination", str(parquet)])
    capsys.readouterr()
    assert main([*common, "validate", "--parquet", str(parquet)]) == 1
    assert "DIVERGENCE FOUND" in capsys.readouterr().out


def test_convert_requires_registered_source(project, capsys):
    _, source, parquet, common = project
    assert main([*common, "convert", "--source", str(source), "--destination", str(parquet)]) == 1
    assert "not registered" in capsys.readouterr().err
    assert not parquet.exists()


def test_convert_refuses_source_changed_after_registration(project, capsys):
    _, source, parquet, common = project
    register(source, common)
    source.chmod(0o644)
    source.write_bytes(source.read_bytes() + b"\x00")
    assert main([*common, "convert", "--source", str(source), "--destination", str(parquet)]) == 1
    assert "SHA-256" in capsys.readouterr().err
    assert not parquet.exists()


def test_register_rejects_wrong_expected_hash(project, capsys):
    root, source, _, common = project
    assert register(source, common, expected_sha256="0" * 64) == 1
    assert not (root / "data" / "MANIFEST.json").exists()


def test_verify_reports_ok_missing_and_mismatch(project, capsys):
    root, source, parquet, common = project
    register(source, common)
    main([*common, "convert", "--source", str(source), "--destination", str(parquet)])
    capsys.readouterr()
    assert main([*common, "verify"]) == 0
    assert capsys.readouterr().out.count(": OK") == 2

    parquet.unlink()  # derived files can be regenerated: reported, not fatal
    assert main([*common, "verify"]) == 0
    assert "MISSING (regenerate" in capsys.readouterr().out

    source.chmod(0o644)
    source.write_bytes(b"corrupted")
    assert main([*common, "verify"]) == 1
    assert "SHA-256 MISMATCH" in capsys.readouterr().out

    source.unlink()  # a missing original source is fatal
    assert main([*common, "verify"]) == 1
    assert "[source] data/raw/SYNTH.dbc: MISSING" in capsys.readouterr().out
