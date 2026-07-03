"""FCC National Broadband Map (BDC) ingestion — fixed broadband availability.

Two supported access paths:

1. BULK CSV (recommended, simplest, what most analysts use)
   Download the state's fixed-broadband availability file from
   https://broadbandmap.fcc.gov/data-download (filter to Texas, fixed
   broadband, current vintage). Point `broadband.bulk_download_path` at it.

2. BDC PUBLIC DATA API (programmatic, needs an FCC account + API token)
   Requires FCC_BDC_USERNAME + FCC_BDC_TOKEN in .env. Spec:
   https://www.fcc.gov/sites/default/files/bdc-public-data-api-spec.pdf

Both paths normalize to the same row schema (one row per location-technology):
    block_geoid, county_fips, tech_code, max_down, max_up
which the transform layer rolls up to county served/underserved shares.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..config import Config, load_config
from ..utils import get_logger, write_table

log = get_logger("ingest.broadband")

# Common column aliases seen across BDC file vintages -> canonical names.
_COLUMN_ALIASES = {
    "block_geoid": ["block_geoid", "block_fips", "geoid", "census_block"],
    "tech_code": ["technology", "tech_code", "technology_code"],
    "max_down": ["max_advertised_download_speed", "maxaddown", "max_down"],
    "max_up": ["max_advertised_upload_speed", "maxadup", "max_up"],
}


def _canonicalize(df: pd.DataFrame) -> pd.DataFrame:
    lower = {c.lower(): c for c in df.columns}
    out = {}
    for canon, aliases in _COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lower:
                out[canon] = df[lower[alias]]
                break
    res = pd.DataFrame(out)
    if "block_geoid" in res:
        res["block_geoid"] = res["block_geoid"].astype("string").str.zfill(15)
        # county FIPS = state(2)+county(3) = first 5 digits of the 15-digit block
        res["county_fips"] = res["block_geoid"].str[:5]
    for col in ("tech_code", "max_down", "max_up"):
        if col in res:
            res[col] = pd.to_numeric(res[col], errors="coerce")
    return res


# --- "Fixed Broadband Summary by Geography Type" (already county-aggregated) ---
# This national file gives, per geography, the SHARE of residential units with
# access at each speed tier. We select the county rows, residential units, and
# the BEAD-aligned "reliable" technology bundle (wired + licensed fixed wireless,
# i.e. excluding satellite / unlicensed).
_SUMMARY_TECH = "All Wired and Licensed Fixed Wireless"


def _is_summary(df: pd.DataFrame) -> bool:
    return {"geography_type", "speed_100_20"}.issubset(df.columns)


def _parse_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Turn the geography-summary file directly into per-county tiers."""
    d = df[
        (df["geography_type"] == "County")
        & (df["area_data_type"] == "Total")
        & (df["biz_res"] == "R")
        & (df["technology"] == _SUMMARY_TECH)
    ].copy()
    d["county_fips"] = d["geography_id"].astype("string").str.zfill(5)
    for c in ("speed_25_3", "speed_100_20", "total_units"):
        d[c] = pd.to_numeric(d[c], errors="coerce")

    out = pd.DataFrame({"county_fips": d["county_fips"]})
    out["locations"] = d["total_units"]
    out["pct_served"] = d["speed_100_20"].clip(0, 1)
    out["pct_unserved"] = (1 - d["speed_25_3"]).clip(0, 1)
    out["pct_underserved"] = (d["speed_25_3"] - d["speed_100_20"]).clip(0, 1)
    out["pct_below_benchmark"] = (1 - d["speed_100_20"]).clip(0, 1)
    for tier in ("served", "underserved", "unserved"):
        out[tier] = (out[f"pct_{tier}"] * out["locations"]).round()
    return out.dropna(subset=["county_fips"]).reset_index(drop=True)


def load_broadband(cfg: Config | None = None, *, save: bool = True) -> pd.DataFrame:
    """Load broadband availability. Supports two file shapes automatically:
    the FCC 'Summary by Geography' file (already county-level) or raw
    location-level availability files. Returns either county tiers or
    location rows; the transform layer handles both."""
    cfg = cfg or load_config()
    bulk = Path(cfg.path(cfg["broadband"]["bulk_download_path"]))
    if bulk.is_dir():
        files = sorted(bulk.glob("*.csv"))
        if not files:
            log.warning("No broadband CSVs in %s — skipping the broadband layer.", bulk)
            return pd.DataFrame()
        raw = [pd.read_csv(f, dtype=str) for f in files]
        log.info("Loading %d broadband CSV(s) from %s", len(files), bulk)
    elif bulk.exists():
        log.info("Loading broadband bulk file: %s", bulk)
        raw = [pd.read_csv(bulk, dtype=str)]
    else:
        log.info("No bulk file at %s — attempting BDC API.", bulk)
        return _fetch_via_api(cfg)

    if any(_is_summary(r) for r in raw):
        # County-level summary path (preferred, laptop-friendly).
        df = pd.concat([_parse_summary(r) for r in raw if _is_summary(r)], ignore_index=True)
        log.info("Parsed broadband summary -> %s counties.", f"{len(df):,}")
    else:
        # Location-level path.
        df = pd.concat([_canonicalize(r) for r in raw], ignore_index=True)
        if "county_fips" not in df.columns or "block_geoid" not in df.columns:
            log.warning(
                "Broadband file(s) have no usable columns (need either the "
                "'Summary by Geography' file, or location-level block_geoid + "
                "speeds). Skipping the broadband layer."
            )
            return pd.DataFrame()

    # Restrict to the configured state (national keeps every county).
    if not cfg.is_national:
        df = df[df["county_fips"].str[:2] == cfg.state_fips].reset_index(drop=True)
    if save and not df.empty:
        out = cfg.data_path("raw", f"broadband_{cfg.scope_slug}.parquet")
        write_table(df, out)
        log.info("Saved %s broadband rows -> %s", f"{len(df):,}", out)
    return df


def _fetch_via_api(cfg: Config) -> pd.DataFrame:
    """BDC Public Data API path. Requires FCC account + token.

    The BDC API issues *file* downloads behind an authenticated listing call
    rather than returning rows inline, so this helper documents and performs
    the token-authenticated listing, then guides the user. Implemented
    defensively: if credentials are missing it raises a clear, actionable error.
    """
    username = Config.secret("FCC_BDC_USERNAME")
    token = Config.secret("FCC_BDC_TOKEN")
    if not (username and token):
        raise RuntimeError(
            "No broadband data available. Either:\n"
            f"  (a) download the Texas fixed-broadband CSV from "
            "https://broadbandmap.fcc.gov/data-download and place it at "
            f"'{cfg['broadband']['bulk_download_path']}', or\n"
            "  (b) set FCC_BDC_USERNAME and FCC_BDC_TOKEN in .env for API access."
        )
    # API listing endpoint (auth via username + token headers).
    import requests

    base = "https://broadbandmap.fcc.gov/api/public/map/downloads/listAvailabilityData"
    headers = {"username": username, "hash_value": token}
    log.info("Querying BDC API availability listing ...")
    resp = requests.get(base, headers=headers, timeout=60)
    resp.raise_for_status()
    listings = resp.json().get("data", [])
    raise RuntimeError(
        "BDC API returned a file listing of "
        f"{len(listings)} downloadable datasets. Automated bulk retrieval of "
        "multi-GB national files is intentionally left to a manual download step "
        "for reliability — pick the Texas fixed-broadband file from the listing "
        f"and save it to '{cfg['broadband']['bulk_download_path']}'."
    )


if __name__ == "__main__":  # pragma: no cover
    print(load_broadband().head())
