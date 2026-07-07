"""FCC 'Fixed Broadband Summary by Geography' parsing -> county tiers."""
import pandas as pd

from telequity.config import load_config
from telequity.ingest.broadband import _is_summary, _parse_summary
from telequity.transform.broadband import county_broadband

_TECH = "All Wired and Licensed Fixed Wireless"


def _row(fips, units, br, tech, s253, s10020, geo="County"):
    return {
        "area_data_type": "Total", "geography_type": geo, "geography_id": fips,
        "geography_desc": fips, "geography_desc_full": fips, "total_units": units,
        "biz_res": br, "technology": tech, "speed_02_02": "1", "speed_10_1": "1",
        "speed_25_3": s253, "speed_100_20": s10020, "speed_250_25": "0.5",
        "speed_1000_100": "0.3",
    }


def _summary_df():
    return pd.DataFrame([
        _row("01001", "1000", "R", _TECH, "0.95", "0.90"),           # target row
        _row("01001", "1000", "B", _TECH, "0.99", "0.99"),           # business -> ignored
        _row("01001", "1000", "R", "All Satellite", "1", "1"),        # satellite -> ignored
        _row("99", "1", "R", "Any Technology", "1", "1", geo="National"),  # national -> ignored
        _row("01003", "500", "R", _TECH, "0.80", "0.50"),            # target row
    ])


def test_is_summary_detects_format():
    assert _is_summary(_summary_df())


def test_parse_summary_computes_tiers():
    out = _parse_summary(_summary_df()).set_index("county_fips")
    assert set(out.index) == {"01001", "01003"}
    assert abs(out.loc["01001", "pct_served"] - 0.90) < 1e-9
    assert abs(out.loc["01001", "pct_below_benchmark"] - 0.10) < 1e-9
    assert abs(out.loc["01001", "pct_underserved"] - 0.05) < 1e-9   # 0.95 - 0.90
    assert abs(out.loc["01001", "pct_unserved"] - 0.05) < 1e-9      # 1 - 0.95
    assert abs(out.loc["01003", "pct_below_benchmark"] - 0.50) < 1e-9


def test_county_broadband_passthrough():
    out = county_broadband(_parse_summary(_summary_df()), load_config())
    assert "pct_below_benchmark" in out.columns
    assert len(out) == 2
