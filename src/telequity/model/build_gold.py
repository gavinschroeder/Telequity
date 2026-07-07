"""Assemble the gold star schema from the transformed county tables.

Gold tables written to data/processed/ (these are what Power BI connects to):

  fact_county.csv            One row per county: broadband tiers, complaint
                             totals + friction, ACS features, infrastructure
                             load/water, equity_index, mismatch_score, flags.
                             (This is the central fact/measure table.)
  dim_county.csv             County key -> name, state (join to a map shape).
  dim_category.csv           Complaint category lookup.
  fact_complaint_category.csv  Long: county x category counts (for drill-downs).
  fact_data_center.csv       Facility-level points (lat/long) for the overlay map.

Star schema:  fact_county  --county_fips-->  dim_county
              fact_complaint_category --county_fips--> dim_county
              fact_complaint_category --category--> dim_category
              fact_data_center --county_fips--> dim_county
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import Config, load_config
from ..utils import get_logger, write_table

log = get_logger("model.gold")


def _equity_tier(idx: pd.Series, cfg: Config) -> pd.Series:
    """Bucket the equity index into 4 named severity tiers so Power BI maps can
    color by a categorical column (4 choices) instead of thousands of values."""
    b0, b1, b2 = cfg["index"].get("tier_breaks", [12.7, 16.8, 23])
    labels = [
        f"1 · Lower (< {b0})",
        f"2 · Moderate ({b0}–{b1})",
        f"3 · High ({b1}–{b2})",
        f"4 · Very high (> {b2})",
    ]
    v = pd.to_numeric(idx, errors="coerce")
    return pd.Series(np.select([v < b0, v < b1, v < b2], labels[:3], default=labels[3]), index=v.index)


# County attributes copied onto secondary tables so each is self-sufficient in
# Power BI (no relationships / no web-modeling needed to slice by these).
_COUNTY_ATTRS = [
    "county_fips", "county_name", "equity_index", "equity_tier", "mismatch_score",
    "mismatch_quadrant", "pct_below_benchmark", "is_digital_desert", "pct_rural",
]


def _enrich_with_county(df: pd.DataFrame | None, fact_county: pd.DataFrame) -> pd.DataFrame | None:
    """Left-join county attributes onto any table keyed by county_fips.

    Makes fact_complaint_category and fact_data_center standalone-usable so the
    report needs no relationships (works even when web modeling is disabled).
    """
    if df is None or df.empty or "county_fips" not in df.columns:
        return df
    attrs = [c for c in _COUNTY_ATTRS if c in fact_county.columns]
    lut = fact_county[attrs].drop_duplicates("county_fips").copy()
    out = df.copy()
    out["county_fips"] = out["county_fips"].astype("string")
    lut["county_fips"] = lut["county_fips"].astype("string")
    overlap = [c for c in attrs if c in out.columns and c != "county_fips"]
    out = out.drop(columns=overlap)
    return out.merge(lut, on="county_fips", how="left")


def _write_workbook(sheets: dict[str, pd.DataFrame], path: Path) -> Path:
    """Write all gold tables into ONE .xlsx (a sheet per table).

    A single file means a single upload/connection in Power BI, and — when the
    file lives in OneDrive/SharePoint — automatic refresh.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as xl:
        for name, df in sheets.items():
            df.to_excel(xl, sheet_name=name[:31], index=False)
    return path


def assemble_fact_county(
    *,
    county_dim: pd.DataFrame,
    broadband: pd.DataFrame,
    complaints_wide: pd.DataFrame,
    acs_features: pd.DataFrame,
    infrastructure: pd.DataFrame,
) -> pd.DataFrame:
    """Left-join every county-level table onto the full county dimension.

    Using the dimension as the spine guarantees every county appears even if a
    source has no rows for it (e.g. a county with zero data centers).
    """
    fact = county_dim.copy()
    fact["county_fips"] = fact["county_fips"].astype("string")
    for name, df in (
        ("broadband", broadband),
        ("complaints", complaints_wide),
        ("acs", acs_features),
        ("infrastructure", infrastructure),
    ):
        if df is None or df.empty:
            log.warning("Source '%s' empty; columns will be null in fact_county.", name)
            continue
        d = df.copy()
        d["county_fips"] = d["county_fips"].astype("string")
        # avoid duplicate non-key columns (e.g. county_name) on re-merge
        dup = [c for c in d.columns if c in fact.columns and c != "county_fips"]
        d = d.drop(columns=dup)
        fact = fact.merge(d, on="county_fips", how="left")

    # Fill structural zeros where a county simply had no records.
    zero_cols = [c for c in fact.columns if c.startswith(("complaints_", "data_center", "planned", "operational"))]
    fact[zero_cols] = fact[zero_cols].fillna(0)
    return fact


def write_gold(
    fact_county: pd.DataFrame,
    complaint_long: pd.DataFrame,
    data_centers: pd.DataFrame,
    cfg: Config | None = None,
    *,
    demo: bool = False,
) -> dict[str, str]:
    """Write all gold tables; returns {table_name: path}. `demo` adds a suffix."""
    cfg = cfg or load_config()
    suffix = "_DEMO" if demo else ""
    written: dict[str, str] = {}

    # Bake the equity severity tier onto fact_county; enrichment then copies it
    # onto the other tables so every map can color by it with no DAX.
    if "equity_index" in fact_county.columns:
        fact_county = fact_county.copy()
        fact_county["equity_tier"] = _equity_tier(fact_county["equity_index"], cfg)

    # Make secondary tables self-sufficient (no relationships required in BI).
    complaint_long = _enrich_with_county(complaint_long, fact_county)
    data_centers = _enrich_with_county(data_centers, fact_county)

    def _out(name: str) -> str:
        return str(cfg.data_path("processed", f"{name}{suffix}.csv"))

    # dim_county
    dim_cols = [c for c in ("county_fips", "county_name", "state_fips", "state_abbr") if c in fact_county.columns]
    dim_county_df = fact_county[dim_cols].drop_duplicates()
    write_table(dim_county_df, _out("dim_county"))
    written["dim_county"] = _out("dim_county")

    # dim_category
    cats = sorted(set(cfg["complaints"]["category_map"].values()) | {"other"})
    dim_cat = pd.DataFrame({"category": cats})
    dim_cat["category_label"] = dim_cat["category"].str.replace("_", " ").str.title()
    write_table(dim_cat, _out("dim_category"))
    written["dim_category"] = _out("dim_category")

    # fact_county
    write_table(fact_county, _out("fact_county"))
    written["fact_county"] = _out("fact_county")

    # fact_complaint_category (long)
    if complaint_long is not None and not complaint_long.empty:
        write_table(complaint_long, _out("fact_complaint_category"))
        written["fact_complaint_category"] = _out("fact_complaint_category")

    # fact_data_center (facility points)
    if data_centers is not None and not data_centers.empty:
        write_table(data_centers, _out("fact_data_center"))
        written["fact_data_center"] = _out("fact_data_center")

    # --- single workbook: one upload/connection; OneDrive-friendly refresh ---
    sheets: dict[str, pd.DataFrame] = {
        "fact_county": fact_county,
        "dim_county": dim_county_df,
        "dim_category": dim_cat,
    }
    if complaint_long is not None and not complaint_long.empty:
        sheets["fact_complaint_category"] = complaint_long
    if data_centers is not None and not data_centers.empty:
        sheets["fact_data_center"] = data_centers

    wb_path = cfg.data_path("processed", f"telequity_gold{suffix}.xlsx")
    _write_workbook(sheets, wb_path)
    written["workbook"] = str(wb_path)

    # Optional: also drop the workbook into a synced folder (e.g. OneDrive) so
    # Power BI auto-refreshes without any manual re-upload.
    # Prefer an env override (keeps personal paths out of the committed config).
    publish_to = os.environ.get("TELEQUITY_PUBLISH_DIR") or cfg["paths"].get("publish_workbook_to")
    if publish_to:
        pub = Path(publish_to).expanduser() / f"telequity_gold{suffix}.xlsx"
        try:
            _write_workbook(sheets, pub)
            written["workbook_published"] = str(pub)
            log.info("Published workbook -> %s", pub)
        except OSError as e:
            log.warning("Could not write workbook to publish path %s: %s", pub, e)

    log.info("Wrote %s gold outputs -> %s", len(written), cfg.data_path("processed"))
    return written
