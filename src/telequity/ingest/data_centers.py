"""Data-center infrastructure ingestion — PNNL Atlas + LBNL interconnection queue.

Both are FILE-based sources (download once; no live API):

* PNNL Data Center Atlas — operational/planned facilities w/ locations.
  https://www.pnnl.gov/publications/mapping-future-data-centers-new-public-tool
* LBNL interconnection queue — large planned loads (MW) seeking grid connection.
  https://emp.lbl.gov/queues

We normalize both to a common per-facility schema:
    name, status, latitude, longitude, planned_mw, source
Facilities are assigned to counties later (transform/infrastructure.py) by
point-in-polygon on lat/long.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..config import Config, load_config
from ..utils import get_logger, write_table

log = get_logger("ingest.datacenters")

_LAT_ALIASES = ["latitude", "lat", "y"]
_LON_ALIASES = ["longitude", "lon", "lng", "x"]
_MW_ALIASES = ["planned_mw", "mw", "capacity_mw", "load_mw", "requested_mw", "size_mw"]
_STATUS_ALIASES = ["status", "project_status", "phase", "queue_status"]
_NAME_ALIASES = ["name", "facility", "project_name", "site_name", "project"]


def _first(df: pd.DataFrame, aliases: list[str]) -> pd.Series | None:
    lower = {c.lower(): c for c in df.columns}
    for a in aliases:
        if a in lower:
            return df[lower[a]]
    return None


def _normalize(df: pd.DataFrame, source: str) -> pd.DataFrame:
    out = pd.DataFrame()
    out["name"] = _first(df, _NAME_ALIASES)
    status = _first(df, _STATUS_ALIASES)
    out["status"] = status.astype("string").str.lower() if status is not None else pd.NA
    out["latitude"] = pd.to_numeric(_first(df, _LAT_ALIASES), errors="coerce")
    out["longitude"] = pd.to_numeric(_first(df, _LON_ALIASES), errors="coerce")
    mw = _first(df, _MW_ALIASES)
    out["planned_mw"] = pd.to_numeric(mw, errors="coerce") if mw is not None else pd.NA

    # If the source already carries state + county codes (e.g. PNNL Atlas:
    # state_id + county_id), build county_fips directly — no geocoding needed.
    state_id = _first(df, ["state_id", "statefp", "state_fips"])
    county_id = _first(df, ["county_id", "countyfp"])
    if state_id is not None and county_id is not None:
        sf = state_id.astype("string").str.extract(r"(\d+)")[0].str.zfill(2)
        cf = county_id.astype("string").str.extract(r"(\d+)")[0].str.zfill(3)
        out["county_fips"] = (sf + cf).where(sf.notna() & cf.notna())

    out["source"] = source
    return out


def load_data_centers(cfg: Config | None = None, *, save: bool = True) -> pd.DataFrame:
    """Load + merge PNNL and LBNL files into a single facility table.

    Missing files are skipped with a warning (so a partial run still works);
    if BOTH are missing the function raises with download instructions.
    """
    cfg = cfg or load_config()
    infra = cfg["infrastructure"]
    frames: list[pd.DataFrame] = []

    pnnl = cfg.path(infra["pnnl_atlas_path"])
    if Path(pnnl).exists():
        frames.append(_normalize(pd.read_csv(pnnl, dtype=str), "PNNL"))
        log.info("Loaded PNNL atlas: %s", pnnl)
    else:
        log.warning("PNNL atlas not found at %s", pnnl)

    lbnl = cfg.path(infra["lbnl_queue_path"])
    if Path(lbnl).exists():
        frames.append(_normalize(pd.read_csv(lbnl, dtype=str), "LBNL"))
        log.info("Loaded LBNL queue: %s", lbnl)
    else:
        log.warning("LBNL queue not found at %s", lbnl)

    if not frames:
        raise RuntimeError(
            "No data-center source files found. Download:\n"
            "  PNNL Atlas -> "
            f"'{infra['pnnl_atlas_path']}'  (https://www.pnnl.gov/publications/"
            "mapping-future-data-centers-new-public-tool-illuminates-whats-next)\n"
            "  LBNL queue -> "
            f"'{infra['lbnl_queue_path']}'  (https://emp.lbl.gov/queues)"
        )

    df = pd.concat(frames, ignore_index=True)
    df = df.dropna(subset=["latitude", "longitude"]).reset_index(drop=True)
    if save:
        out = cfg.data_path("raw", "data_centers.parquet")
        write_table(df, out)
        log.info("Saved %s data-center facilities -> %s", len(df), out)
    return df


def is_planned(status: str, cfg: Config) -> bool:
    planned = cfg["infrastructure"]["planned_statuses"]
    return any(p in str(status).lower() for p in planned)


if __name__ == "__main__":  # pragma: no cover
    print(load_data_centers().head())
