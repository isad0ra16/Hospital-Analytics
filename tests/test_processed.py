"""Processed layer, built from SYNTHETIC SIH-like data."""

from datetime import date

import pandas as pd
import pyarrow.parquet as pq
import pytest
from synthetic_data import SIH_FIELDS, SIH_RECORDS

from hospital_analytics.processed import (
    DERIVED_COLUMNS,
    TransformError,
    build_processed,
    check_no_name_clash,
    reduced_precision,
    scaled_int_to_text,
    text_to_date,
    text_to_scaled_int,
)


@pytest.mark.parametrize(
    ("text", "decimals", "expected"),
    [("123.45", 2, 12345), ("0.00", 2, 0), ("-2.50", 2, -250), ("42", 0, 42), ("-7", 0, -7)],
)
def test_scaled_int_roundtrip(text, decimals, expected):
    (value,) = text_to_scaled_int(pd.Series([text]), decimals)
    assert value == expected
    assert scaled_int_to_text(value, decimals) == text


def test_blank_numeric_is_null_not_zero():
    assert text_to_scaled_int(pd.Series(["", "1.00"]), 2).tolist() == [pd.NA, 100]


@pytest.mark.parametrize("bad", ["1.2.3", "abc", "1e3", "12,50", " 1.00"])
def test_malformed_numbers_stop_the_build(bad):
    with pytest.raises(TransformError):
        text_to_scaled_int(pd.Series([bad]), 2)


def test_reduced_precision_only_when_too_wide():
    original = pd.Series(["166200.0", "16620.0"])
    back = pd.Series(["166200.00", "16620.00"])
    # N8.2: '166200.00' (9 chars) does not fit -> accepted; '16620.00' (8 chars) fits -> not
    assert reduced_precision(original, back, width=8).tolist() == [True, False]


def test_invalid_dates_become_null_and_are_counted():
    parsed, invalid = text_to_date(pd.Series(["20240131", "20240231", "", "2024013"]))
    assert parsed.tolist() == [date(2024, 1, 31), None, None, None]
    assert invalid == 3


def test_original_columns_are_untouched(sih_layers):
    raw, processed, raw_report, processed_report = sih_layers
    assert processed_report.original_columns_fingerprint == raw_report.content_fingerprint
    table = pq.read_table(processed)
    assert table.column_names[: len(SIH_FIELDS)] == [f.name for f in SIH_FIELDS]
    assert table.num_rows == len(SIH_RECORDS)


def test_derived_values(sih_layers):
    _, processed, _, report = sih_layers
    df = pd.read_parquet(processed)
    assert df["val_tot_cents"].tolist() == [int(r.val_tot.replace(".", "")) for r in SIH_RECORDS]
    ages = dict(zip(df["COD_IDADE"] + ":" + df["IDADE"], df["age_years"], strict=True))
    assert ages["2:15"] == pytest.approx(15 / 365.25)
    assert ages["3:6"] == pytest.approx(0.5)
    assert ages["5:2"] == 102
    assert df["died"].sum() == sum(r.morte for r in SIH_RECORDS)
    assert df.loc[df["N_AIH"] == "3324100000007", "aih_occurrences"].tolist() == [2, 2]
    assert df["aih_repeated"].sum() == 2
    assert df["discharge_year"].tolist() == [int(r.dt_saida[:4]) for r in SIH_RECORDS]
    assert report.reduced_precision_values == {"VAL_UTI": 1}
    assert report.invalid_dates == {"admission_date": 0, "discharge_date": 0, "birth_date": 0}


def test_numeric_conversions_are_reversible(sih_layers):
    _, processed, _, _ = sih_layers
    df = pd.read_parquet(processed)
    back = [scaled_int_to_text(v, 2) for v in df["val_tot_cents"]]
    assert back == df["VAL_TOT"].tolist()


def test_refuses_to_overwrite(sih_layers):
    raw, processed, _, _ = sih_layers
    with pytest.raises(FileExistsError):
        build_processed(raw, processed)


def test_derived_names_never_clash_with_originals_ignoring_case():
    with pytest.raises(TransformError, match="clashes"):
        check_no_name_clash(["DT_INTER"], ["dt_inter"])
    check_no_name_clash([f.name for f in SIH_FIELDS], [c.name for c in DERIVED_COLUMNS])


def test_every_derived_column_is_documented():
    from hospital_analytics.config import project_root

    doc = (project_root() / "docs" / "03_tratamento.md").read_text(encoding="utf-8")
    missing = [c.name for c in DERIVED_COLUMNS if f"`{c.name}`" not in doc]
    assert not missing, f"undocumented derived columns: {missing}"
