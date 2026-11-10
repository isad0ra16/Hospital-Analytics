"""Internal consistency of the historical reference values recovered from the old project.

These tests do not touch any data. They check that the recovered numbers agree with
each other, and they pin down known inconsistencies so they cannot be silently dropped.
"""

from decimal import ROUND_HALF_UP, Decimal

import pytest

from hospital_analytics.config import load_params, to_money

CENT = Decimal("0.01")


@pytest.fixture(scope="module")
def ref():
    return load_params()["historical_reference"]


def _round2(x: Decimal) -> Decimal:
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


def test_discharge_years_add_up_to_total(ref):
    years = sum(v["value"] for v in ref["discharge_year"].values())
    assert years == ref["full_base"]["records"]["value"]


@pytest.mark.parametrize("field", ["records", "deaths"])
def test_ident_counts_add_up_to_total(ref, field):
    by_ident = sum(group[field]["value"] for group in ref["by_ident"].values())
    assert by_ident == ref["full_base"][field]["value"]


def test_ident_money_adds_up_to_total_exactly(ref):
    by_ident = sum(to_money(g["val_tot_sum"]["value"]) for g in ref["by_ident"].values())
    assert by_ident == to_money(ref["full_base"]["val_tot_sum"]["value"])


def test_full_base_mean_value_matches_sum_over_records(ref):
    base = ref["full_base"]
    mean = to_money(base["val_tot_sum"]["value"]) / base["records"]["value"]
    assert _round2(mean) == to_money(base["mean_val_tot"]["value"])


@pytest.mark.parametrize("ident", ["1", "5"])
def test_ident_mean_value_matches_sum_over_records(ref, ident):
    group = ref["by_ident"][ident]
    mean = to_money(group["val_tot_sum"]["value"]) / group["records"]["value"]
    assert _round2(mean) == to_money(group["mean_val_tot"]["value"])


def test_overall_length_of_stay_is_compatible_with_weighted_ident_means(ref):
    """Each recorded mean is rounded to 2 decimals, so it stands for an interval
    [v - 0.005, v + 0.005). The weighted combination of the IDENT intervals must
    overlap the interval of the recorded overall mean."""
    half = 0.005
    groups = ref["by_ident"].values()
    n_total = sum(g["records"]["value"] for g in groups)

    def weighted(offset):
        return (
            sum(
                g["records"]["value"] * (g["mean_length_of_stay_days"]["value"] + offset)
                for g in groups
            )
            / n_total
        )

    low, high = weighted(-half), weighted(+half)
    overall = ref["full_base"]["mean_length_of_stay_days"]["value"]
    assert low < overall + half and high > overall - half


def test_crude_mortality_discrepancy_is_flagged(ref):
    """4664 / 73046 = 6.3850...% rounds (half-up) to 6.39%, while 6.38% was recorded.
    Until explained, the reference must stay flagged as needs_verification."""
    base = ref["full_base"]
    computed = _round2(Decimal(base["deaths"]["value"]) / base["records"]["value"] * 100)
    recorded = Decimal(str(base["crude_mortality_pct"]["value"]))
    assert computed == Decimal("6.39")
    assert computed != recorded
    assert base["crude_mortality_pct"]["status"] == "needs_verification"


def test_repeated_aih_counts_are_only_consistent_as_excess_rows(ref):
    """50 distinct repeated numbers need at least 100 rows in total, so the
    56 'occurrences' cannot be total rows; excess rows is the consistent reading."""
    rep = ref["repeated_aih_numbers"]
    occurrences, distinct = rep["occurrences"]["value"], rep["distinct_numbers"]["value"]
    assert occurrences < 2 * distinct  # cannot be total rows involved
    assert occurrences >= distinct  # consistent with excess rows
    assert rep["occurrences"]["status"] == "criterion_unknown"


def test_every_reference_has_a_known_status(ref):
    allowed = {"recorded", "needs_verification", "criterion_unknown"}

    def walk(node):
        if isinstance(node, dict):
            if "value" in node:
                assert node.get("status") in allowed, node
            for child in node.values():
                walk(child)

    walk(ref)
