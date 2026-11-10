"""Exploratory analyses on SYNTHETIC data: internal consistency, rates, reproducible outputs."""

from decimal import Decimal

from synthetic_data import SIH_RECORDS

from hospital_analytics.analysis import pct, ratio, run_analysis, write_report


def test_rate_helpers_round_half_up_and_guard_zero():
    assert pct(1, 3) == Decimal("33.33")
    assert pct(2, 3) == Decimal("66.67")
    assert pct(1, 0) is None
    assert ratio(7, 2) == Decimal("3.50")


def test_dimensions_add_up_to_the_base(sih_layers):
    _, processed, _, _ = sih_layers
    report = run_analysis(processed)
    n = len(SIH_RECORDS)
    assert report["totals"]["records"] == n
    for dim, rows in report["dimensions"].items():
        assert sum(r["records"] for r in rows) == n, dim
        assert sum(r["deaths"] for r in rows) == sum(r.morte for r in SIH_RECORDS), dim
    assert sum(r["records"] for r in report["age"]) == n
    assert sum(r["records"] for r in report["pyramid"]) == n


def test_mortality_rate_matches_oracle(sih_layers):
    _, processed, _, _ = sih_layers
    report = run_analysis(processed)
    ident = {r["code"]: r for r in report["dimensions"]["IDENT"]}
    ident1 = [r for r in SIH_RECORDS if r.ident == "1"]
    assert ident["1"]["mortality_per_100_records"] == pct(sum(r.morte for r in ident1), len(ident1))


def test_lorenz_curve_is_monotonic_from_0_to_100(sih_layers):
    _, processed, _, _ = sih_layers
    points = [p["value_pct"] for p in run_analysis(processed)["lorenz"]]
    assert points[0] == 0 and points[-1] == 100
    assert points == sorted(points)


def test_outputs_are_reproducible(tmp_path, sih_layers):
    _, processed, _, _ = sih_layers
    first = write_report(run_analysis(processed), tmp_path / "a", "analysis")
    second = write_report(run_analysis(processed), tmp_path / "b", "analysis")
    assert [p.name for p in first] == [p.name for p in second]
    assert [p.read_bytes() for p in first] == [p.read_bytes() for p in second]
