"""Validation checks, including divergence scenarios, on SYNTHETIC data."""

from decimal import Decimal

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from synthetic_data import SYNTHETIC_FIELDS, money_sum

from hospital_analytics.config import load_params
from hospital_analytics.convert import convert_dbc_to_parquet
from hospital_analytics.manifest import empty_manifest, record_derived, register_source
from hospital_analytics.validate import ReferenceTargets, summarize_money, validate_raw_parquet


@pytest.fixture
def setup(tmp_path, dbc_file, rows):
    out = tmp_path / "SYNTH.parquet"
    report = convert_dbc_to_parquet(dbc_file, out)
    manifest = empty_manifest()
    register_source(
        manifest,
        "src",
        dbc_file,
        official_url="x",
        obtained_at="x",
        obtained_by="x",
        data_version={},
    )
    derived = record_derived(manifest, "out", "src", report)
    targets = ReferenceTargets(len(rows), len(SYNTHETIC_FIELDS), Decimal(money_sum(rows)))
    return out, targets, derived


def failed(report):
    return {c.name for c in report.checks if not c.passed}


def test_all_checks_pass_on_matching_targets(setup):
    out, targets, derived = setup
    report = validate_raw_parquet(out, targets, derived_entry=derived)
    assert report.passed, report.format_table()
    assert len(report.checks) == 10  # 2 shape + 2 type + 3 money + 3 preservation


@pytest.mark.parametrize(
    ("change", "expected_failure"),
    [
        ({"records": 1}, "records == historical reference"),
        ({"columns": 1}, "columns == historical reference"),
        ({"val_tot_sum": Decimal("0.01")}, "VAL_TOT exact sum == historical reference"),
    ],
    ids=["one-more-record", "one-more-column", "one-cent"],
)
def test_divergence_from_reference_is_reported(setup, change, expected_failure):
    out, targets, derived = setup
    field, delta = next(iter(change.items()))
    shifted = ReferenceTargets(**{**targets.__dict__, field: getattr(targets, field) + delta})
    report = validate_raw_parquet(out, shifted, derived_entry=derived)
    assert not report.passed
    assert failed(report) == {expected_failure}
    assert "DIVERGENCE FOUND" in report.format_table()


def test_tampered_parquet_fails_preservation(tmp_path, setup):
    out, targets, derived = setup
    table = pq.read_table(out)
    values = table.column("N_AIH").to_pylist()
    values[0] = "9999999999999"
    tampered = tmp_path / "tampered.parquet"
    pq.write_table(table.set_column(0, table.schema.field(0), pa.array(values)), tampered)
    report = validate_raw_parquet(tampered, targets, derived_entry=derived)
    assert failed(report) == {
        "parquet SHA-256 == manifest",
        "content fingerprint == manifest (DBF values preserved)",
    }


def test_non_text_column_fails(tmp_path, setup):
    out, targets, _ = setup
    table = pq.read_table(out)
    retyped = tmp_path / "typed.parquet"
    pq.write_table(table.set_column(1, "IDENT", pa.array([1] * table.num_rows)), retyped)
    report = validate_raw_parquet(retyped, targets)
    assert "all columns are text (raw layer)" in failed(report)


def test_malformed_money_is_counted_not_ignored():
    table = pa.table({"VAL_TOT": ["10.50", "", "1e3", "abc", "-2.25", "NaN"]})
    summary = summarize_money(table, "VAL_TOT")
    assert summary.total == Decimal("8.25")
    assert (summary.blanks, summary.invalid) == (1, 3)


def test_targets_from_params_are_the_historical_references():
    targets = ReferenceTargets.from_params(load_params())
    assert targets == ReferenceTargets(73046, 113, Decimal("125440636.13"))
