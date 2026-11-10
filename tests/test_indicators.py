"""Indicators on SYNTHETIC data, checked against an independent plain-Python oracle."""

from decimal import Decimal

import pandas as pd
import pytest
from synthetic_data import SIH_RECORDS

from hospital_analytics.indicators import (
    IndicatorSpec,
    aggregates_pandas,
    aggregates_sql,
    engines_agree,
    specs,
    status_for,
    values,
)


@pytest.fixture
def agg(sih_layers):
    _, processed, _, _ = sih_layers
    return aggregates_pandas(pd.read_parquet(processed)), aggregates_sql(processed)


def test_pandas_and_sql_agree(agg):
    pandas_agg, sql_agg = agg
    assert engines_agree(pandas_agg, sql_agg) == []


def test_engines_agree_detects_differences():
    assert engines_agree({"a": 1}, {"a": 2}) == ["aggregates.a: 1 != 2"]
    assert engines_agree({"a": 1.0}, {"a": 1.0 + 1e-15}) == []


def test_values_match_independent_oracle(agg):
    vals = values(agg[0])
    cents = [int(r.val_tot.replace(".", "")) for r in SIH_RECORDS]
    ident1 = [r for r in SIH_RECORDS if r.ident == "1"]
    assert vals["records_full"] == len(SIH_RECORDS)
    assert vals["val_tot_full"] == Decimal(sum(cents)) / 100
    assert vals["los_mean_ident_1"] == Decimal(sum(r.dias_perm for r in ident1)) / len(ident1)
    assert vals["deaths_full"] == sum(r.morte for r in SIH_RECORDS)
    assert vals["age_mean_hist_full"] == Decimal(sum(r.idade for r in SIH_RECORDS)) / len(
        SIH_RECORDS
    )
    assert vals["discharge_2023"] == sum(r.dt_saida.startswith("2023") for r in SIH_RECORDS)
    assert vals["aih_repeated_excess"] == 1
    # top 10%: k = floor(11 * 0.1) = 1 -> the single largest record
    assert vals["top10_share_full"] == Decimal(100 * max(cents)) / sum(cents)
    surgical = sum(int(r.val_tot.replace(".", "")) for r in ident1 if r.proc_rea.startswith("04"))
    total1 = sum(int(r.val_tot.replace(".", "")) for r in ident1)
    assert vals["surgical_value_share_ident_1"] == Decimal(100 * surgical) / total1


def _spec(historical, criterion, explanation=""):
    return IndicatorSpec("x", "x", "full", "d", "f", "f", "d", "f", "pct", historical, criterion,
                         divergence_explanation=explanation)  # fmt: skip


@pytest.mark.parametrize(
    ("historical", "criterion", "explanation", "reproduced", "expected"),
    [
        ("6.12", "documented", "", "6.1249", "✅ reproduzido"),
        ("6.12", "identified", "", "6.1249", "🟡 critério identificado"),
        ("6.38", "identified", "truncation", "6.385017", "🟠 divergente (explicado)"),
        ("58.20", "unknown", "", "57.7427", "🔴 divergente"),
        (None, "new", "", "43.85", "🆕 novo"),
    ],
)
def test_status_rules(historical, criterion, explanation, reproduced, expected):
    status, _, _ = status_for(_spec(historical, criterion, explanation), Decimal(reproduced))
    assert status == expected


def test_rounding_is_half_up_at_historical_precision():
    _, rounded, diff = status_for(_spec("6.38", "identified", "x"), Decimal("6.385017660"))
    assert (rounded, diff) == (Decimal("6.39"), Decimal("0.01"))


def test_specs_take_historical_values_from_params_and_are_complete():
    all_specs = specs()
    by_id = {s.id: s for s in all_specs}
    assert len(by_id) == len(all_specs)
    assert by_id["records_full"].historical == "73046"
    assert by_id["val_tot_ident_5"].historical == "1582165.98"
    assert by_id["mortality_full"].divergence_explanation
    for s in all_specs:
        assert all([s.name, s.definition, s.source_fields, s.formula, s.denominator, s.filters])
        assert (s.historical is None) == (s.criterion == "new")
