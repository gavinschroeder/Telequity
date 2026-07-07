"""Analysis engine: every dashboard gets a grounded summary + callouts."""
import pandas as pd

from telequity.analysis import build_sections

_PAGE_KEYS = {"mismatch", "avail-vs-friction", "categories", "equity-map", "datacenter-map"}


def _frames():
    fc = pd.DataFrame({
        "county_fips": ["01001", "06075", "48201"],
        "county_name": ["Autauga County, Alabama", "San Francisco County, California",
                        "Harris County, Texas"],
        "equity_index": [8.0, 20.0, 50.0],
        "mismatch_score": [10.0, 40.0, 5.0],
        "mismatch_quadrant": ["low_compute_served", "compute_in_underserved", "low_compute_underserved"],
        "pct_below_benchmark": [0.05, 0.30, 0.60],
        "complaints_per_1k_hh": [5.0, 20.0, 30.0],
        "is_digital_desert": [False, True, True],
        "data_center_count": [2, 1, 0],
    })
    cl = pd.DataFrame({
        "county_fips": ["01001", "01001", "06075"],
        "category": ["internet", "wireless_wireline", "internet"],
        "complaint_count": [100, 300, 50],
    })
    dc = pd.DataFrame({
        "name": ["x", "y"], "county_fips": ["01001", "06075"],
        "equity_index": [8.0, 20.0], "latitude": [1.0, 2.0], "longitude": [3.0, 4.0],
    })
    return fc, cl, dc


def test_all_dashboards_present():
    sections = build_sections(*_frames())
    assert set(sections.keys()) == _PAGE_KEYS


def test_each_section_has_grounded_content():
    sections = build_sections(*_frames())
    for key, sec in sections.items():
        assert isinstance(sec["summary"], str) and len(sec["summary"]) > 20, key
        assert isinstance(sec["callouts"], list)


def test_categories_summary_mentions_a_total():
    sections = build_sections(*_frames())
    # 100+300+50 = 450 complaints should be referenced.
    assert "450" in sections["categories"]["summary"]
