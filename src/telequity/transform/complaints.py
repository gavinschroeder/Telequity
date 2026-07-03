"""Complaints transform: clean, categorize, and aggregate to county.

Outputs two county-level tables:
  * complaints_by_county          — totals + per-category counts + per-1k-households
  * complaints_by_county_category — long form (county x category) for Power BI

The "friction" signal used by the equity index is complaints per 1,000
households (households, not raw population, since the household is the unit
of broadband access).
"""
from __future__ import annotations

import pandas as pd

from ..config import Config, load_config
from ..utils import get_logger
from .geography import assign_county

log = get_logger("transform.complaints")


def categorize(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    cmap: dict[str, str] = cfg["complaints"]["category_map"]
    work = df.copy()
    work["category"] = work["issue_type"].map(cmap).fillna("other")
    return work


def aggregate_to_county(
    complaints: pd.DataFrame, households: pd.DataFrame, cfg: Config | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aggregate categorized, county-assigned complaints to the county grain.

    Args:
        complaints: cleaned complaint rows (must have county_fips + category).
        households: DataFrame with county_fips + total_households (from ACS).
    Returns:
        (wide_by_county, long_by_county_category)
    """
    cfg = cfg or load_config()
    if "county_fips" not in complaints.columns:
        complaints = assign_county(complaints, cfg)
    complaints = categorize(complaints, cfg)

    # Long form: county x category counts.
    long_df = (
        complaints.groupby(["county_fips", "category"], dropna=True)
        .size()
        .reset_index(name="complaint_count")
    )

    # Wide form: total + one column per category.
    wide = long_df.pivot_table(
        index="county_fips", columns="category", values="complaint_count",
        fill_value=0, aggfunc="sum",
    )
    wide.columns = [f"complaints_{c}" for c in wide.columns]
    wide["complaints_total"] = wide.sum(axis=1)
    wide = wide.reset_index()

    # Friction per 1,000 households.
    hh = households[["county_fips", "total_households"]].copy()
    hh["county_fips"] = hh["county_fips"].astype("string")
    wide["county_fips"] = wide["county_fips"].astype("string")
    wide = wide.merge(hh, on="county_fips", how="left")
    wide["complaints_per_1k_hh"] = (
        wide["complaints_total"] / wide["total_households"].replace(0, pd.NA) * 1000
    )
    log.info("Aggregated complaints to %s counties.", len(wide))
    return wide, long_df
