"""Audit on SYNTHETIC data: content, privacy of sensitive columns, determinism."""

import json

from hospital_analytics.audit import SENSITIVE_COLUMNS, run_audit, to_markdown, write_report


def test_checks(sih_layers):
    raw, processed, _, _ = sih_layers
    report = run_audit(raw, processed)
    assert report.records == 11
    rep = report.checks["repeated_aih"][0]
    assert (rep["excess_records"], rep["distinct_numbers"], rep["numbers_ident_1_and_5"]) == (
        1,
        1,
        1,
    )
    assert report.checks["full_row_duplicates"][0]["identical_duplicate_records"] == 0
    dates = report.checks["date_consistency"][0]
    assert dates["discharge_before_admission"] == 0
    assert dates["los_differs_ident_5"] == 1  # 2023-01-01 -> 2024-01-31 but DIAS_PERM = 31
    assert {"DT_SAIDA", "SEQUENCIA", "IDENT"} <= set(report.repeated_aih_varying_columns)


def test_sensitive_values_never_reported(sih_layers):
    raw, processed, _, _ = sih_layers
    report = run_audit(raw, processed)
    for profile in report.profiles:
        if profile.name in SENSITIVE_COLUMNS:
            assert profile.top_values is None
    text = to_markdown(report) + json.dumps(report.to_dict(), default=str)
    assert "3324100000007" not in text  # an N_AIH value
    assert "19800101" not in text  # a NASC value


def test_reports_are_deterministic(tmp_path, sih_layers):
    raw, processed, _, _ = sih_layers
    first = write_report(run_audit(raw, processed), tmp_path / "a", "r")
    second = write_report(run_audit(raw, processed), tmp_path / "b", "r")
    assert [p.read_bytes() for p in first] == [p.read_bytes() for p in second]
