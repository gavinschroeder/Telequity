"""Infrastructure transform: aggregate data-center facilities to county and
compute the planned compute load + modeled water draw per county.

Outputs per-county:
  data_center_count, planned_count, planned_mw, operational_mw,
  modeled_water_l_per_year (from planned MW, if water enabled)
"""
from __future__ import annotations

import pandas as pd

from ..config import Config, load_config
from ..utils import get_logger
from .geography import assign_county_by_point

log = get_logger("transform.infrastructure")

_HOURS_PER_YEAR = 8760


def county_infrastructure(
    facilities: pd.DataFrame, cfg: Config | None = None
) -> pd.DataFrame:
    """Assign facilities to counties and aggregate load + modeled water."""
    cfg = cfg or load_config()
    df = facilities.copy()
    if "county_fips" not in df.columns:
        df = assign_county_by_point(df, cfg)
    df = df[df["county_fips"].notna()]
    df["county_fips"] = df["county_fips"].astype("string")

    planned_set = cfg["infrastructure"]["planned_statuses"]
    df["is_planned"] = df["status"].fillna("").apply(
        lambda s: any(p in str(s).lower() for p in planned_set)
    )
    df["planned_mw"] = pd.to_numeric(df.get("planned_mw"), errors="coerce")

    grp = df.groupby("county_fips")
    out = pd.DataFrame({
        "data_center_count": grp.size(),
        "planned_count": grp["is_planned"].sum(),
        "planned_mw": grp.apply(
            lambda g: g.loc[g["is_planned"], "planned_mw"].sum(min_count=1),
            include_groups=False,
        ),
        "operational_mw": grp.apply(
            lambda g: g.loc[~g["is_planned"], "planned_mw"].sum(min_count=1),
            include_groups=False,
        ),
    }).reset_index()

    out = _add_modeled_water(out, cfg)
    log.info("Aggregated %s facilities into %s counties.", len(df), len(out))
    return out


def _add_modeled_water(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Estimate annual water draw from planned MW (best-effort proxy).

    litres/year = MW * 1000 (kW) * hours/year * L_per_kWh
    Flagged explicitly as MODELED, not measured.
    """
    w = cfg["water"]
    if not w.get("enabled", False):
        df["modeled_water_l_per_year"] = pd.NA
        return df
    l_per_kwh = w["modeled_l_per_kwh"]
    df["modeled_water_l_per_year"] = (
        df["planned_mw"].fillna(0) * 1000 * _HOURS_PER_YEAR * l_per_kwh
    )
    return df
