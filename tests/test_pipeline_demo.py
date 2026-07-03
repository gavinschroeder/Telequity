"""Smoke test: the demo pipeline runs and produces sane gold tables."""
import pandas as pd

from telequity.config import load_config
from telequity.demo import generate_demo_inputs
from telequity.score.index import compute_index
from telequity.score.mismatch import compute_mismatch


def test_demo_produces_national_counties_with_scores():
    cfg = load_config()
    county, long_df, facilities = generate_demo_inputs(cfg)
    # National scope: thousands of US counties (states + DC), all 5-digit FIPS.
    assert len(county) > 3000
    assert county["county_fips"].str.len().eq(5).all()
    assert county["county_fips"].str[:2].astype(int).le(56).all()

    fact = compute_mismatch(compute_index(county, cfg), cfg)
    assert fact["equity_index"].between(0, 100).all()
    assert fact["mismatch_score"].between(0, 100).all()
    assert not fact[["equity_index", "mismatch_score"]].isna().any().any()
    # The whole point of the platform: at least one underserved+compute county.
    assert (fact["mismatch_quadrant"] == "compute_in_underserved").any()


def test_demo_complaint_long_matches_categories():
    cfg = load_config()
    _, long_df, _ = generate_demo_inputs(cfg)
    valid = set(cfg["complaints"]["category_map"].values()) | {"other"}
    assert set(long_df["category"]).issubset(valid)
    assert (long_df["complaint_count"] > 0).all()
