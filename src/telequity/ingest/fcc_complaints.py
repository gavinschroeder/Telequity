"""FCC CGB Consumer Complaints — Socrata SODA API ingestion.

Endpoint (no auth required; app token optional for higher rate limits):
    https://opendata.fcc.gov/resource/3xyp-aqkj.json

Verified real schema (fields actually returned):
    id, ticket_created, date_created, issue_date, issue_time,
    issue_type, method, issue, caller_id_number, type_of_call_or_messge,
    advertiser_business_phone_number, city, state, zip,
    location_1 {latitude, longitude, human_address},
    type_of_property_goods_or_services

NOTE: there is intentionally NO provider/company field — this is why the
platform analyses *places*, not providers.
"""
from __future__ import annotations

import time
from typing import Iterator

import pandas as pd
import requests

from ..config import Config, load_config
from ..utils import get_logger, write_table

log = get_logger("ingest.complaints")

_BASE = "https://{domain}/resource/{dataset}.json"
_PAGE = 50_000  # Socrata max page size


def _session(app_token: str | None) -> requests.Session:
    s = requests.Session()
    if app_token:
        s.headers.update({"X-App-Token": app_token})
    s.headers.update({"User-Agent": "telequity/0.1 (digital-equity research)"})
    return s


def _iter_pages(
    session: requests.Session, url: str, params: dict, *, max_records: int | None
) -> Iterator[list[dict]]:
    offset = 0
    fetched = 0
    while True:
        page_params = {**params, "$limit": _PAGE, "$offset": offset}
        resp = session.get(url, params=page_params, timeout=60)
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            break
        if max_records is not None and fetched + len(rows) > max_records:
            rows = rows[: max_records - fetched]
        yield rows
        fetched += len(rows)
        offset += _PAGE
        if len(rows) < _PAGE or (max_records is not None and fetched >= max_records):
            break
        time.sleep(0.2)  # be polite to the API


def fetch_complaints(
    cfg: Config | None = None, *, max_records: int | None = None, save: bool = True
) -> pd.DataFrame:
    """Pull complaints for the configured state into a flat DataFrame.

    Args:
        cfg: loaded Config (loads default if None).
        max_records: cap rows (useful for smoke tests); None = all.
        save: write raw parquet to data/raw.
    """
    cfg = cfg or load_config()
    c = cfg["complaints"]
    url = _BASE.format(domain=c["socrata_domain"], dataset=c["dataset_id"])
    token = Config.secret("FCC_SOCRATA_APP_TOKEN")

    where = []
    if not cfg.is_national:
        where.append(f"state='{cfg.state_abbr}'")
    if c.get("date_from"):
        where.append(f"date_created >= '{c['date_from']}T00:00:00'")
    if c.get("date_to"):
        where.append(f"date_created <= '{c['date_to']}T00:00:00'")
    params = {"$order": "date_created"}
    if where:
        params["$where"] = " AND ".join(where)

    scope_label = "US (national)" if cfg.is_national else cfg.state_abbr
    log.info("Fetching complaints for %s (where: %s)", scope_label, params.get("$where", "<all>"))
    session = _session(token)
    frames: list[pd.DataFrame] = []
    total = 0
    for rows in _iter_pages(session, url, params, max_records=max_records):
        frames.append(pd.json_normalize(rows))
        total += len(rows)
        log.info("  ... %s rows", f"{total:,}")
    if not frames:
        log.warning("No complaint rows returned.")
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)
    df = _normalize(df)
    if save:
        out = cfg.data_path("raw", f"complaints_{cfg.scope_slug}.parquet")
        write_table(df, out)
        log.info("Saved %s complaints -> %s", f"{len(df):,}", out)
    return df


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Tidy column names/types and surface lat/long from nested location_1."""
    rename = {
        "location_1.latitude": "latitude",
        "location_1.longitude": "longitude",
    }
    df = df.rename(columns=rename)
    for col in ("latitude", "longitude"):
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "date_created" in df:
        df["date_created"] = pd.to_datetime(df["date_created"], errors="coerce")
    if "zip" in df:
        # keep first 5 digits as a clean string key
        df["zip5"] = df["zip"].astype("string").str.extract(r"(\d{5})", expand=False)
    keep = [
        "id", "date_created", "issue_type", "method", "issue",
        "city", "state", "zip5", "latitude", "longitude",
    ]
    return df[[col for col in keep if col in df.columns]]


if __name__ == "__main__":  # pragma: no cover
    fetch_complaints(max_records=2000)
