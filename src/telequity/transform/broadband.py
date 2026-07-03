"""Broadband transform: compute county served / underserved / unserved shares.

Applies the BEAD statutory speed tiers to each location-technology record,
then rolls up to the county share of *locations* in each tier.

A location is classified by the BEST reliable-technology offer available to it:
  served      : >= 100/20 Mbps
  underserved : >= 25/3  but < 100/20
  unserved    : < 25/3   (or no reliable offer at all)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..config import Config, load_config
from ..utils import get_logger

log = get_logger("transform.broadband")


def _classify_best_offer(g: pd.DataFrame, b: dict) -> str:
    down = g["max_down"].max()
    up = g["max_up"].max()
    if pd.isna(down) or pd.isna(up):
        return "unserved"
    if down >= b["underserved_down_mbps"] and up >= b["underserved_up_mbps"]:
        return "served"
    if down >= b["unserved_down_mbps"] and up >= b["unserved_up_mbps"]:
        return "underserved"
    return "unserved"


def county_broadband(broadband: pd.DataFrame, cfg: Config | None = None) -> pd.DataFrame:
    """Return per-county served/underserved/unserved shares.

    Input: location-technology rows (block_geoid, county_fips, tech_code,
    max_down, max_up). Filters to reliable technologies before classifying.
    """
    cfg = cfg or load_config()
    b = cfg["broadband"]
    df = broadband.copy()

    if df.empty:
        return pd.DataFrame(columns=["county_fips", "pct_served", "pct_underserved", "pct_unserved"])

    # Already county-level (from the FCC 'Summary by Geography' file)? Pass through.
    if "pct_below_benchmark" in df.columns:
        keep = ["county_fips", "locations", "served", "underserved", "unserved",
                "pct_served", "pct_underserved", "pct_unserved", "pct_below_benchmark"]
        log.info("Using pre-aggregated county broadband for %s counties.", f"{len(df):,}")
        return df[[c for c in keep if c in df.columns]]

    reliable = set(b["reliable_tech_codes"])
    if "tech_code" in df.columns:
        df = df[df["tech_code"].isin(reliable)]

    if df.empty:
        log.warning("No reliable-tech broadband rows; returning empty.")
        return pd.DataFrame(columns=["county_fips", "pct_served", "pct_underserved", "pct_unserved"])

    # Classify each location (block_geoid) by its best available offer.
    loc = (
        df.groupby(["county_fips", "block_geoid"])
        .apply(lambda g: _classify_best_offer(g, b), include_groups=False)
        .reset_index(name="tier")
    )

    counts = loc.pivot_table(
        index="county_fips", columns="tier", values="block_geoid",
        aggfunc="count", fill_value=0,
    )
    for tier in ("served", "underserved", "unserved"):
        if tier not in counts.columns:
            counts[tier] = 0
    counts["locations"] = counts[["served", "underserved", "unserved"]].sum(axis=1)
    out = counts.reset_index()
    out["pct_served"] = out["served"] / out["locations"]
    out["pct_underserved"] = out["underserved"] / out["locations"]
    out["pct_unserved"] = out["unserved"] / out["locations"]
    # "availability gap" = anything below the 100/20 benchmark.
    out["pct_below_benchmark"] = out["pct_underserved"] + out["pct_unserved"]
    log.info("Computed broadband tiers for %s counties.", len(out))
    return out[
        ["county_fips", "locations", "served", "underserved", "unserved",
         "pct_served", "pct_underserved", "pct_unserved", "pct_below_benchmark"]
    ]


def flag_deserts(county_bb: pd.DataFrame, cfg: Config | None = None) -> pd.DataFrame:
    """Add an `is_digital_desert` flag using the configured method.

    The speed thresholds are statutory; the county-share cutoff is an explicit
    analytic choice (percentile of underserved share, or an absolute cutoff).
    """
    cfg = cfg or load_config()
    d = cfg["desert"]
    out = county_bb.copy()
    if out.empty:
        out["is_digital_desert"] = pd.Series(dtype=bool)
        return out
    metric = d["metric"]
    if metric not in out.columns:
        log.warning("Desert metric '%s' not found; no flag set.", metric)
        out["is_digital_desert"] = False
        return out
    if d["method"] == "percentile":
        cutoff = np.nanpercentile(out[metric], d["percentile_cutoff"])
    else:
        cutoff = d["absolute_cutoff"]
    out["desert_cutoff"] = cutoff
    out["is_digital_desert"] = out[metric] >= cutoff
    log.info("Flagged %s digital-desert counties (cutoff %.3f).",
             int(out["is_digital_desert"].sum()), cutoff)
    return out
