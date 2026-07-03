"""Tests for the scoring math (index + mismatch). Pure-pandas, no I/O."""
import numpy as np
import pandas as pd

from telequity.config import load_config
from telequity.score.index import compute_index, minmax, zscore
from telequity.score.mismatch import compute_mismatch


def test_minmax_basic():
    out = minmax(pd.Series([0, 5, 10]))
    assert list(out) == [0.0, 0.5, 1.0]


def test_minmax_constant_series_is_zero():
    out = minmax(pd.Series([7, 7, 7]))
    assert (out == 0).all()


def test_zscore_mean_zero():
    out = zscore(pd.Series([1, 2, 3, 4]))
    assert abs(out.mean()) < 1e-9


def _toy_counties():
    # 3 counties: A worst access+poorest, C best.
    return pd.DataFrame({
        "county_fips": ["48001", "48003", "48005"],
        "pct_below_benchmark": [0.8, 0.4, 0.1],
        "complaints_per_1k_hh": [30.0, 15.0, 5.0],
        "median_household_income": [30_000, 55_000, 90_000],
        "pct_rural": [0.9, 0.5, 0.1],
        "pct_65_plus": [0.3, 0.2, 0.1],
        "planned_mw": [500.0, 0.0, 50.0],
    })


def test_index_monotonic_worst_county_highest():
    cfg = load_config()
    out = compute_index(_toy_counties(), cfg)
    # County A has the worst inputs across the board -> highest index.
    idx = out.set_index("county_fips")["equity_index"]
    assert idx["48001"] > idx["48003"] > idx["48005"]
    assert 0 <= idx.min() and idx.max() <= 100


def test_index_components_present():
    cfg = load_config()
    out = compute_index(_toy_counties(), cfg)
    for col in ("c_availability_gap", "c_complaint_friction", "c_socioeconomic"):
        assert col in out.columns
        assert out[col].between(0, 1).all()


def test_mismatch_is_product_high_only_when_both_high():
    cfg = load_config()
    scored = compute_index(_toy_counties(), cfg)
    out = compute_mismatch(scored, cfg)
    o = out.set_index("county_fips")
    # County A: high infra (500 MW) AND worst access -> top mismatch.
    assert o["mismatch_score"].idxmax() == "48001"
    # County B: zero planned MW -> mismatch must be 0 regardless of access.
    assert o.loc["48003", "mismatch_score"] == 0.0
    assert o.loc["48001", "mismatch_quadrant"] == "compute_in_underserved"
