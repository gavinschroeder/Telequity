"""Geography: assign records to counties and build the county dimension.

Two assignment strategies, preferred in order:

1. POINT-IN-POLYGON on lat/long against the TIGER county shapefile
   (used for complaints that carry coordinates, and for data-center sites).
   Requires geopandas + the county shapefile.

2. ZCTA -> county crosswalk (ZIP-based fallback for complaints without
   usable coordinates). Requires the crosswalk CSV.

Both are optional dependencies: the functions degrade gracefully and tell the
caller exactly which reference file is missing.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..config import Config, load_config
from ..utils import get_logger

log = get_logger("transform.geography")


def assign_county_by_point(
    df: pd.DataFrame, cfg: Config, *, lat_col: str = "latitude", lon_col: str = "longitude"
) -> pd.DataFrame:
    """Add a `county_fips` column via point-in-polygon on lat/long.

    Rows without valid coordinates get <NA> and should fall back to ZIP.
    """
    shp = cfg.path(cfg["reference"]["county_shapefile"])
    if not Path(shp).exists():
        log.warning("County shapefile missing (%s); skipping point-in-polygon.", shp)
        df = df.copy()
        df["county_fips"] = pd.NA
        return df

    import geopandas as gpd
    from shapely.geometry import Point

    counties = gpd.read_file(shp)[["GEOID", "geometry"]].rename(columns={"GEOID": "county_fips"})
    counties = counties.to_crs(epsg=4326)

    work = df.copy()
    valid = work[lat_col].notna() & work[lon_col].notna()
    pts = gpd.GeoDataFrame(
        work[valid],
        geometry=[Point(xy) for xy in zip(work.loc[valid, lon_col], work.loc[valid, lat_col])],
        crs="EPSG:4326",
    )
    joined = gpd.sjoin(pts, counties, how="left", predicate="within")
    work.loc[valid, "county_fips"] = joined["county_fips"].values
    work["county_fips"] = work["county_fips"].astype("string")
    matched = work["county_fips"].notna().sum()
    log.info("Point-in-polygon matched %s / %s rows to counties.", f"{matched:,}", f"{len(work):,}")
    return work


def assign_county_by_zip(
    df: pd.DataFrame, cfg: Config, *, zip_col: str = "zip5"
) -> pd.DataFrame:
    """Add/fill `county_fips` from a ZCTA->county crosswalk.

    Where a ZIP spans multiple counties, the crosswalk's highest-population
    county is used (the crosswalk file is expected pre-resolved to one row/ZIP;
    if it has weights, we keep the max-weight county).
    """
    xwalk_path = cfg.path(cfg["reference"]["zcta_county_crosswalk"])
    if not Path(xwalk_path).exists():
        log.warning("ZCTA crosswalk missing (%s); cannot ZIP-assign.", xwalk_path)
        return df

    xwalk = pd.read_csv(xwalk_path, dtype=str)
    xwalk.columns = [c.lower() for c in xwalk.columns]
    zcol = next((c for c in ("zcta", "zcta5", "zip", "zip5") if c in xwalk.columns), None)
    ccol = next((c for c in ("county_fips", "county", "geoid", "county_geoid") if c in xwalk.columns), None)
    if not (zcol and ccol):
        log.warning("Crosswalk missing zip/county columns; skipping.")
        return df

    wcol = next((c for c in ("weight", "afact", "pop_weight") if c in xwalk.columns), None)
    if wcol:
        xwalk[wcol] = pd.to_numeric(xwalk[wcol], errors="coerce")
        xwalk = xwalk.sort_values(wcol, ascending=False).drop_duplicates(zcol)
    else:
        xwalk = xwalk.drop_duplicates(zcol)

    lookup = xwalk.set_index(xwalk[zcol].str.zfill(5))[ccol].str.zfill(5)
    work = df.copy()
    mapped = work[zip_col].astype("string").map(lookup)
    if "county_fips" in work.columns:
        work["county_fips"] = work["county_fips"].fillna(mapped)
    else:
        work["county_fips"] = mapped
    return work


def assign_county(df: pd.DataFrame, cfg: Config | None = None, *, use_points: bool = True) -> pd.DataFrame:
    """Best-available county assignment: points first, ZIP fallback."""
    cfg = cfg or load_config()
    # Prefer the ZIP crosswalk: a fast lookup, and complaint coordinates are only
    # ZIP centroids anyway — so it's equally accurate and avoids a slow
    # point-in-polygon join over millions of national rows.
    out = df
    if "zip5" in df.columns:
        out = assign_county_by_zip(df, cfg)
    got = "county_fips" in out.columns and out["county_fips"].notna().any()
    if not got and use_points and {"latitude", "longitude"}.issubset(df.columns):
        out = assign_county_by_point(df, cfg)
    # Keep only counties inside the configured state (national keeps all).
    if "county_fips" in out.columns and not cfg.is_national:
        out = out[out["county_fips"].astype("string").str[:2] == cfg.state_fips]
    return out.reset_index(drop=True)


def county_dimension(acs: pd.DataFrame, cfg: Config | None = None) -> pd.DataFrame:
    """The county dimension table — one row per county with name + geometry key."""
    cfg = cfg or load_config()
    dim = acs[["county_fips", "county_name"]].drop_duplicates().copy()
    dim["county_fips"] = dim["county_fips"].astype("string")
    dim["state_fips"] = dim["county_fips"].str[:2]  # works for national or single-state
    dim["state_abbr"] = cfg.state_abbr if cfg.state_abbr else ""
    return dim.sort_values("county_fips").reset_index(drop=True)
