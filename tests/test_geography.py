"""Test ZIP -> county assignment against a small temp crosswalk."""
import pandas as pd

from telequity.config import Config
from telequity.transform.geography import assign_county_by_zip


def _cfg_with_crosswalk(tmp_path):
    xwalk = pd.DataFrame({
        "zcta": ["75001", "73301", "88888"],
        "county_fips": ["48113", "48453", "48001"],
        "weight": [1.0, 1.0, 1.0],
    })
    path = tmp_path / "xwalk.csv"
    xwalk.to_csv(path, index=False)
    raw = {
        "scope": {"state_fips": "48", "state_abbr": "TX"},
        "reference": {"zcta_county_crosswalk": "xwalk.csv"},
    }
    return Config(raw=raw, root=tmp_path)


def test_zip_assignment_maps_known_zips(tmp_path):
    cfg = _cfg_with_crosswalk(tmp_path)
    df = pd.DataFrame({"zip5": ["75001", "73301"]})
    out = assign_county_by_zip(df, cfg)
    assert out.loc[0, "county_fips"] == "48113"
    assert out.loc[1, "county_fips"] == "48453"


def test_zip_assignment_unknown_zip_is_na(tmp_path):
    cfg = _cfg_with_crosswalk(tmp_path)
    df = pd.DataFrame({"zip5": ["00000"]})
    out = assign_county_by_zip(df, cfg)
    assert pd.isna(out.loc[0, "county_fips"])
