"""Access-Infrastructure Mismatch — the platform's signature metric.

Question it answers: *where is large-scale compute being planned on top of the
worst lived digital access?*

    infra_norm  = minmax(planned_mw)        # incoming data-center load
    access_norm = minmax(equity_index)      # how bad access/equity already is
    mismatch    = 100 * infra_norm * access_norm

The product (not the sum) is deliberate: a county scores high ONLY when both
are high — lots of incoming infrastructure AND severe existing access gaps.
A quadrant label is attached for the dashboard narrative.

Framing guardrail: this is juxtaposition / resource-allocation equity, NOT a
causal claim. Data centers do not serve residential broadband; the metric
highlights *where investment flows vs. where access lags*.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..config import Config, load_config
from ..utils import get_logger
from .index import minmax

log = get_logger("score.mismatch")


def compute_mismatch(county: pd.DataFrame, cfg: Config | None = None) -> pd.DataFrame:
    cfg = cfg or load_config()
    m = cfg["mismatch"]
    out = county.copy()

    infra = out.get(m["infra_metric"])
    # Fall back to facility COUNT when there's no planned-MW signal (e.g. the
    # PNNL Atlas has locations but no megawatts). Swaps in automatically once a
    # planned-capacity source provides real MW.
    if infra is None or float(pd.to_numeric(infra, errors="coerce").fillna(0).sum()) == 0:
        infra = out.get("data_center_count", pd.Series(np.zeros(len(out)), index=out.index))
        log.info("No planned-MW signal; using data_center_count as infrastructure intensity.")
    access = out.get(m["access_metric"], pd.Series(np.zeros(len(out)), index=out.index))

    out["infra_norm"] = minmax(pd.to_numeric(infra, errors="coerce").fillna(0))
    out["access_norm"] = minmax(access.fillna(0))
    out["mismatch_score"] = (100 * out["infra_norm"] * out["access_norm"]).round(2)
    out["mismatch_quadrant"] = _quadrant(out["infra_norm"], out["access_norm"])
    log.info(
        "Computed mismatch; %s counties in the high-infra/high-gap quadrant.",
        int((out["mismatch_quadrant"] == "compute_in_underserved").sum()),
    )
    return out


def _quadrant(infra_norm: pd.Series, access_norm: pd.Series, thresh: float = 0.5) -> pd.Series:
    hi_i = infra_norm >= thresh
    hi_a = access_norm >= thresh
    labels = np.select(
        [hi_i & hi_a, hi_i & ~hi_a, ~hi_i & hi_a],
        ["compute_in_underserved", "compute_in_served", "low_compute_underserved"],
        default="low_compute_served",
    )
    return pd.Series(labels, index=infra_norm.index)
