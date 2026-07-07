"""PNNL-style data-center normalization: county_fips from state_id + county_id."""
import pandas as pd

from telequity.ingest.data_centers import _normalize


def test_builds_county_fips_and_fields():
    df = pd.DataFrame({
        "state_id": ["34", "6"],       # NJ, CA (note CA is single digit)
        "county_id": ["023", "075"],
        "name": ["Site A", "Site B"],
        "lat": ["40.54", "37.77"],
        "lon": ["-74.49", "-122.41"],
    })
    out = _normalize(df, "PNNL")
    assert list(out["county_fips"]) == ["34023", "06075"]   # padded correctly
    assert out["latitude"].tolist() == [40.54, 37.77]
    assert out["longitude"].tolist() == [-74.49, -122.41]
    assert out["name"].tolist() == ["Site A", "Site B"]
    assert out["source"].tolist() == ["PNNL", "PNNL"]


def test_missing_county_codes_no_fips_column():
    df = pd.DataFrame({"name": ["X"], "latitude": ["1.0"], "longitude": ["2.0"]})
    out = _normalize(df, "OTHER")
    assert "county_fips" not in out.columns   # falls back to geocoding downstream
    assert out["latitude"].tolist() == [1.0]
