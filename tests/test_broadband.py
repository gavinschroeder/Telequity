"""Tests for BEAD tier classification + digital-desert flagging."""
import pandas as pd

from telequity.config import load_config
from telequity.transform.broadband import county_broadband, flag_deserts


def _broadband_rows():
    # county 48001: one served loc (200/40) + one unserved loc (10/1)
    # county 48003: one underserved loc (50/10)
    return pd.DataFrame({
        "county_fips": ["48001", "48001", "48001", "48003"],
        "block_geoid": ["480010001001000", "480010001001000",
                        "480010002001000", "480030001001000"],
        "tech_code": [10, 10, 10, 40],   # all reliable
        "max_down": [200, 25, 10, 50],
        "max_up": [40, 3, 1, 10],
    })


def test_tiers_classify_by_best_offer():
    cfg = load_config()
    out = county_broadband(_broadband_rows(), cfg).set_index("county_fips")
    # 48001: block1 best offer 200/40 -> served; block2 10/1 -> unserved
    assert out.loc["48001", "served"] == 1
    assert out.loc["48001", "unserved"] == 1
    assert abs(out.loc["48001", "pct_below_benchmark"] - 0.5) < 1e-9
    # 48003: single block 50/10 -> underserved
    assert out.loc["48003", "underserved"] == 1


def test_unreliable_tech_excluded():
    cfg = load_config()
    rows = _broadband_rows()
    rows.loc[:, "tech_code"] = 60  # satellite-ish, not in reliable set
    out = county_broadband(rows, cfg)
    assert out.empty


def test_desert_flag_percentile():
    cfg = load_config()
    bb = county_broadband(_broadband_rows(), cfg)
    flagged = flag_deserts(bb, cfg)
    assert "is_digital_desert" in flagged.columns
    assert flagged["is_digital_desert"].dtype == bool
