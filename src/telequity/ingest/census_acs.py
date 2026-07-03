"""Census ACS 5-year ingestion (socioeconomic context).

Requires a free API key (CENSUS_API_KEY in .env):
    https://api.census.gov/data/key_signup.html

Pulls the configured variables for every county in the configured state.
"""
from __future__ import annotations

import pandas as pd
import requests

from ..config import Config, load_config
from ..utils import get_logger, write_table

log = get_logger("ingest.acs")

_BASE = "https://api.census.gov/data/{year}/{dataset}"


def fetch_acs(cfg: Config | None = None, *, save: bool = True) -> pd.DataFrame:
    """Fetch ACS variables for all counties in the configured state."""
    cfg = cfg or load_config()
    a = cfg["acs"]
    key = Config.secret("CENSUS_API_KEY")
    if not key:
        raise RuntimeError(
            "CENSUS_API_KEY is required. Get a free key at "
            "https://api.census.gov/data/key_signup.html and add it to .env"
        )

    var_map: dict[str, str] = a["variables"]
    get_vars = ["NAME", *var_map.keys()]
    url = _BASE.format(year=a["year"], dataset=a["dataset"])
    params = {"get": ",".join(get_vars), "for": "county:*", "key": key}
    if not cfg.is_national:
        params["in"] = f"state:{cfg.state_fips}"  # restrict to one state
    scope_label = "US (all counties)" if cfg.is_national else f"state {cfg.state_fips}"
    log.info("Fetching ACS %s %s for %s", a["year"], a["dataset"], scope_label)
    resp = requests.get(url, params=params, timeout=60)
    resp.raise_for_status()
    payload = resp.json()
    header, *rows = payload
    df = pd.DataFrame(rows, columns=header)

    # Build county FIPS key and rename measure columns.
    df["county_fips"] = (df["state"] + df["county"]).astype("string")
    df = df.rename(columns=var_map)
    measure_cols = list(var_map.values())
    for col in measure_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    # Census uses negative sentinels (e.g. -666666666) for "no data".
    df[measure_cols] = df[measure_cols].where(df[measure_cols] >= 0)

    out_cols = ["county_fips", "NAME", *measure_cols]
    df = df[out_cols].rename(columns={"NAME": "county_name"})
    if save:
        out = cfg.data_path("raw", f"acs_{cfg.scope_slug}.parquet")
        write_table(df, out)
        log.info("Saved ACS for %s counties -> %s", len(df), out)
    return df


if __name__ == "__main__":  # pragma: no cover
    print(fetch_acs().head())
