"""ACS transform: derive the socioeconomic features used by the equity index.

Produces per-county:
  median_household_income, median_age, total_households, total_population,
  pct_65_plus, pct_rural
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..config import Config, load_config
from ..utils import get_logger

log = get_logger("transform.acs")


def build_features(acs: pd.DataFrame, cfg: Config | None = None) -> pd.DataFrame:
    cfg = cfg or load_config()
    df = acs.copy()
    df["county_fips"] = df["county_fips"].astype("string")

    if {"pop_65_plus", "total_population"}.issubset(df.columns):
        df["pct_65_plus"] = (df["pop_65_plus"] / df["total_population"]).clip(0, 1)
    else:
        df["pct_65_plus"] = pd.NA

    df = _attach_rurality(df, cfg)
    keep = [
        "county_fips", "county_name", "total_population", "total_households",
        "median_household_income", "median_age", "pct_65_plus", "pct_rural",
    ]
    return df[[c for c in keep if c in df.columns]]


def _attach_rurality(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Join county % rural from the reference file if present; else NA."""
    path = cfg.path(cfg["reference"]["urban_rural_file"])
    if not Path(path).exists():
        log.warning("Urban/rural file missing (%s); pct_rural set to NA.", path)
        df["pct_rural"] = pd.NA
        return df
    ur = pd.read_csv(path, dtype=str)
    ur.columns = [c.lower() for c in ur.columns]
    fips_col = next((c for c in ("county_fips", "fips", "geoid") if c in ur.columns), None)
    rural_col = next((c for c in ("pct_rural", "rural_pct", "percent_rural") if c in ur.columns), None)
    if not (fips_col and rural_col):
        df["pct_rural"] = pd.NA
        return df
    ur["county_fips"] = ur[fips_col].astype("string").str.zfill(5)
    ur["pct_rural"] = pd.to_numeric(ur[rural_col], errors="coerce")
    if ur["pct_rural"].max() is not None and ur["pct_rural"].max() > 1.5:
        ur["pct_rural"] = ur["pct_rural"] / 100.0  # normalize percentages to 0-1
    return df.merge(ur[["county_fips", "pct_rural"]], on="county_fips", how="left")
