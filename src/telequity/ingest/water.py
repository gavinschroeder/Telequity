"""Water-use ingestion (best-effort) — USGS county water-use data.

Per the project plan this is the acknowledged weak link: there is no clean,
per-site data-center water dataset. Strategy:

* If a USGS county water-use file is present, load county industrial/
  thermoelectric withdrawals as community context.
* The MODELED data-center water draw (litres/kWh * MWh) is computed later in
  transform/infrastructure.py from planned MW; this module only supplies the
  community-level USGS baseline.

If the file is absent and water.enabled is true, the pipeline continues with
modeled water only and logs a clear notice (no hard failure).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..config import Config, load_config
from ..utils import get_logger, write_table

log = get_logger("ingest.water")

_FIPS_ALIASES = ["county_fips", "fips", "geoid", "statecounty_fips"]
_WITHDRAWAL_ALIASES = [
    "total_withdrawal_mgd", "to_wtotl", "total_mgd", "withdrawal_mgd",
]


def load_water(cfg: Config | None = None, *, save: bool = True) -> pd.DataFrame:
    """Load USGS county water-use baseline if available; else empty frame."""
    cfg = cfg or load_config()
    wcfg = cfg["water"]
    if not wcfg.get("enabled", False):
        log.info("Water module disabled in config.")
        return pd.DataFrame()

    path = cfg.path(wcfg["usgs_county_water_path"])
    if not Path(path).exists():
        log.warning(
            "USGS water file not found at %s — continuing with MODELED water only.",
            path,
        )
        return pd.DataFrame()

    raw = pd.read_csv(path, dtype=str)
    lower = {c.lower(): c for c in raw.columns}
    out = pd.DataFrame()
    for canon, aliases in (("county_fips", _FIPS_ALIASES),
                           ("total_withdrawal_mgd", _WITHDRAWAL_ALIASES)):
        for a in aliases:
            if a in lower:
                out[canon] = raw[lower[a]]
                break
    if "county_fips" in out:
        out["county_fips"] = out["county_fips"].astype("string").str.zfill(5)
        if not cfg.is_national:
            out = out[out["county_fips"].str[:2] == cfg.state_fips]
    if "total_withdrawal_mgd" in out:
        out["total_withdrawal_mgd"] = pd.to_numeric(
            out["total_withdrawal_mgd"], errors="coerce"
        )
    if save and not out.empty:
        write_table(out, cfg.data_path("raw", "water_usgs.parquet"))
    return out.reset_index(drop=True)
