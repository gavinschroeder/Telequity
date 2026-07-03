"""Auto-download the stable public reference files so they never need to be
fetched by hand. These live at permanent Census URLs and are cached after the
first download (re-running an analysis reuses them).

Automated here:
  * ZCTA -> county crosswalk (maps complaint ZIPs to counties; small text file)
  * TIGER county shapefile   (county geometry for point-in-polygon; optional —
                              Power BI draws its own county map, and the ZIP
                              crosswalk already covers county assignment)

Not automated (no stable public URL / require accounts): broadband BDC files and
the PNNL/LBNL data-center files. See config + data/reference/README.md.
"""
from __future__ import annotations

import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

from ..config import Config, load_config
from ..utils import get_logger

log = get_logger("ingest.reference")


def fetch_zcta_county_crosswalk(cfg: Config, *, force: bool = False) -> Path:
    """Download + normalize the Census ZCTA→county relationship file into a
    clean `zcta,county_fips,weight` crosswalk the geography step understands."""
    out = cfg.path(cfg["reference"]["zcta_county_crosswalk"])
    if out.exists() and not force:
        log.info("ZCTA→county crosswalk already present: %s", out)
        return out
    url = cfg["reference"]["zcta_county_url"]
    log.info("Downloading ZCTA→county crosswalk from Census …")
    # Census 2020 relationship files are pipe-delimited with a UTF-8 BOM.
    raw = pd.read_csv(url, dtype=str, sep="|", encoding="utf-8-sig")
    cols = {c.upper(): c for c in raw.columns}

    def _find(*needles: str) -> str | None:
        for up, orig in cols.items():
            if all(n in up for n in needles):
                return orig
        return None

    zcol = _find("ZCTA5", "GEOID") or _find("ZCTA")
    ccol = _find("COUNTY", "GEOID") or _find("COUNTY")
    acol = _find("AREALAND", "PART") or _find("AREALAND") or _find("AREA")
    if not (zcol and ccol):
        raise RuntimeError(f"Unexpected crosswalk columns: {list(raw.columns)}")

    df = pd.DataFrame({
        "zcta": raw[zcol].astype("string").str.zfill(5),
        "county_fips": raw[ccol].astype("string").str.zfill(5),
        "weight": pd.to_numeric(raw[acol], errors="coerce") if acol else 1.0,
    })
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    log.info("Saved crosswalk (%s rows) -> %s", f"{len(df):,}", out)
    return out


def fetch_county_shapefile(cfg: Config, *, force: bool = False) -> Path:
    """Download + unzip the national TIGER county shapefile (optional)."""
    shp = cfg.path(cfg["reference"]["county_shapefile"])
    if shp.exists() and not force:
        log.info("County shapefile already present: %s", shp)
        return shp
    url = cfg["reference"]["county_shapefile_url"]
    dest_dir = shp.parent
    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir.with_suffix(".zip")
    log.info("Downloading TIGER county shapefile …")
    urllib.request.urlretrieve(url, zip_path)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(dest_dir)
    zip_path.unlink(missing_ok=True)
    log.info("Extracted county shapefile -> %s", dest_dir)
    return shp


def fetch_all(cfg: Config | None = None) -> dict[str, str]:
    """Best-effort: fetch every auto-downloadable reference file that's missing.

    Failures are logged, not raised — the pipeline degrades gracefully (e.g. if
    the shapefile fails, county assignment falls back to the ZIP crosswalk).
    """
    cfg = cfg or load_config()
    results: dict[str, str] = {}
    for name, fn in (
        ("zcta_county_crosswalk", fetch_zcta_county_crosswalk),
        ("county_shapefile", fetch_county_shapefile),
    ):
        try:
            results[name] = str(fn(cfg))
        except Exception as e:  # noqa: BLE001 — never let a fetch abort the run
            log.warning("Auto-fetch of %s failed (%s). Provide it manually if needed.", name, e)
    return results


if __name__ == "__main__":  # pragma: no cover
    print(fetch_all())
