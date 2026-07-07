"""Gold assembly: equity tier bucketing + county-attribute enrichment."""
import pandas as pd

from telequity.config import load_config
from telequity.model.build_gold import _enrich_with_county, _equity_tier, assemble_fact_county


def test_equity_tier_buckets():
    cfg = load_config()  # tier_breaks [12.7, 16.8, 23]
    tiers = _equity_tier(pd.Series([5.0, 14.0, 20.0, 30.0]), cfg).tolist()
    assert tiers[0].startswith("1")   # < 12.7
    assert tiers[1].startswith("2")   # 12.7–16.8
    assert tiers[2].startswith("3")   # 16.8–23
    assert tiers[3].startswith("4")   # > 23


def test_enrich_propagates_county_attributes():
    fc = pd.DataFrame({
        "county_fips": ["01001"], "county_name": ["Autauga County, Alabama"],
        "equity_index": [30.0], "equity_tier": ["4 · Very high (> 23)"],
    })
    other = pd.DataFrame({"county_fips": ["01001"], "category": ["internet"], "complaint_count": [5]})
    out = _enrich_with_county(other, fc)
    assert out["county_name"].iloc[0] == "Autauga County, Alabama"
    assert out["equity_tier"].iloc[0].startswith("4")


def test_assemble_fact_county_left_joins_on_dimension():
    dim = pd.DataFrame({"county_fips": ["01001", "01003"], "county_name": ["A", "B"],
                        "state_fips": ["01", "01"], "state_abbr": ["", ""]})
    bb = pd.DataFrame({"county_fips": ["01001"], "pct_below_benchmark": [0.2]})
    fact = assemble_fact_county(
        county_dim=dim, broadband=bb,
        complaints_wide=pd.DataFrame(), acs_features=pd.DataFrame(),
        infrastructure=pd.DataFrame(),
    )
    assert len(fact) == 2                                   # every county kept
    assert fact.set_index("county_fips").loc["01003"].isna().any()  # missing source -> null
