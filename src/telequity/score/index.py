"""Digital Equity Exposure Index.

A transparent 0-100 composite per county:

    index = 100 * ( w_avail * availability_gap_norm
                  + w_friction * complaint_friction_norm
                  + w_socio   * socioeconomic_norm )

Each component is min-max normalized to 0-1 across the counties in scope, so a
higher index = greater digital-equity exposure (worse paper access, more lived
friction, more socioeconomic vulnerability). Weights live in config.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..config import Config, load_config
from ..utils import get_logger

log = get_logger("score.index")


def minmax(s: pd.Series) -> pd.Series:
    """Min-max scale to [0,1]; constant/all-NaN series -> 0.0."""
    s = pd.to_numeric(s, errors="coerce")
    lo, hi = s.min(), s.max()
    if pd.isna(lo) or pd.isna(hi) or hi == lo:
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - lo) / (hi - lo)


def zscore(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    mu, sd = s.mean(), s.std(ddof=0)
    if pd.isna(sd) or sd == 0:
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - mu) / sd


def _norm(s: pd.Series, method: str) -> pd.Series:
    return zscore(s) if method == "zscore" else minmax(s)


def socioeconomic_score(df: pd.DataFrame, cfg: Config) -> pd.Series:
    """Vulnerability composite: low income + rurality + age, each normalized.

    Income is *inverted* (lower income -> higher vulnerability).
    """
    sw = cfg["index"]["socioeconomic_weights"]
    method = cfg["index"]["normalization"]

    low_income = 1 - _norm(df.get("median_household_income", pd.Series(dtype=float)), method)
    rurality = _norm(df.get("pct_rural", pd.Series(dtype=float)), method)
    age_vuln = _norm(df.get("pct_65_plus", pd.Series(dtype=float)), method)

    parts, weights = [], []
    for series, key in ((low_income, "low_income"), (rurality, "rurality"), (age_vuln, "age_vulnerability")):
        if series.notna().any():
            parts.append(series.fillna(0) * sw[key])
            weights.append(sw[key])
    if not parts:
        return pd.Series(np.zeros(len(df)), index=df.index)
    total_w = sum(weights)
    return sum(parts) / total_w  # renormalize over available components


def compute_index(county: pd.DataFrame, cfg: Config | None = None) -> pd.DataFrame:
    """Add component columns and the final `equity_index` (0-100).

    Expects a county-level frame already joined across broadband, complaints
    and ACS features (i.e. the gold county fact rows pre-score).
    """
    cfg = cfg or load_config()
    w = cfg["index"]["weights"]
    method = cfg["index"]["normalization"]
    out = county.copy()

    # Component 1: availability gap (share below the 100/20 benchmark).
    avail = out.get("pct_below_benchmark")
    if avail is None:
        avail = out.get("pct_underserved", pd.Series(np.zeros(len(out)), index=out.index))
    out["c_availability_gap"] = _norm(avail, method).fillna(0)

    # Component 2: complaint friction (per 1k households).
    out["c_complaint_friction"] = _norm(
        out.get("complaints_per_1k_hh", pd.Series(np.zeros(len(out)), index=out.index)), method
    ).fillna(0)

    # Component 3: socioeconomic vulnerability.
    out["c_socioeconomic"] = socioeconomic_score(out, cfg).fillna(0)

    out["equity_index"] = 100 * (
        w["availability_gap"] * out["c_availability_gap"]
        + w["complaint_friction"] * out["c_complaint_friction"]
        + w["socioeconomic"] * out["c_socioeconomic"]
    )
    out["equity_index"] = out["equity_index"].round(2)
    log.info(
        "Computed equity index for %s counties (range %.1f–%.1f).",
        len(out), out["equity_index"].min(), out["equity_index"].max(),
    )
    return out
