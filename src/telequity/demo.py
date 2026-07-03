"""Labeled SYNTHETIC demo data generator.

Purpose: let the full pipeline, gold tables, and Power BI dashboards be built
and demonstrated WITHOUT credentials or multi-GB downloads. Everything here is
modeled/synthetic — NOT real measurements — and every output table is written
with a ``_DEMO`` suffix so it can never be confused with a real run.

What is real vs. synthetic:
  * REAL   : Texas county FIPS codes (the 254 odd codes 48001..48507). These
             key correctly to county map shapes in Power BI.
  * REAL-ish: complaint category proportions seeded from the actual statewide
             distribution observed via the FCC API (Phone ~71%, Internet ~17%,
             TV ~9%, Emergency/Radio/Accessibility the remainder).
  * SYNTHETIC: all county metric *values* (broadband shares, counts, income,
             data-center MW, coordinates), generated with correlations that
             mimic reality (rural -> worse access + more friction).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import Config, load_config
from .transform.broadband import flag_deserts
from .utils import get_logger

log = get_logger("demo")

# Real statewide complaint mix (from the live FCC API), used to split totals.
_CATEGORY_MIX = {
    "wireless_wireline": 0.715,  # "Phone"
    "internet": 0.169,
    "tv_video": 0.086,
    "emergency": 0.013,
    "radio": 0.013,
    "accessibility": 0.003,
    "billing_dispute": 0.001,
    "other": 0.0,
}

# Bounding boxes for placing synthetic facility points.
_TX_LAT, _TX_LON = (25.9, 36.4), (-106.5, -93.6)
_US_LAT, _US_LON = (25.0, 49.0), (-124.0, -67.0)  # continental US

# Public list of every US county FIPS (used only to give the DEMO real county
# identities so the choropleth geocodes). The real pipeline gets counties from
# the Census ACS instead.
_US_FIPS_URL = "https://raw.githubusercontent.com/plotly/datasets/master/fips-unemp-16.csv"


def _texas_county_fips() -> list[str]:
    """The 254 Texas county FIPS: state 48 + odd county codes 001..507."""
    return [f"48{n:03d}" for n in range(1, 508, 2)]


def _texas_fallback() -> pd.DataFrame:
    fips = _texas_county_fips()
    return pd.DataFrame({"county_fips": fips, "county_name": [f"County {f}" for f in fips]})


def _read_counties_csv(path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)
    fcol = "county_fips" if "county_fips" in df.columns else ("fips" if "fips" in df.columns else df.columns[0])
    df["county_fips"] = df[fcol].astype("string").str.zfill(5)
    df["county_name"] = (
        df["county_name"].astype("string") if "county_name" in df.columns
        else "County " + df["county_fips"]
    )
    # 50 states + DC (state FIPS <= 56); drop territories like PR (72).
    df = df[df["county_fips"].str[:2].str.isdigit()]
    df = df[df["county_fips"].str[:2].astype(int) <= 56]
    return df[["county_fips", "county_name"]].drop_duplicates("county_fips").sort_values("county_fips")


def _load_us_counties(cfg) -> pd.DataFrame:
    """All US counties (fips + name). Cached reference file → download → Texas."""
    path = cfg.data_path("reference", "us_county_fips.csv")
    if path.exists():
        return _read_counties_csv(path)
    try:
        import urllib.request
        path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(_US_FIPS_URL, path)
        log.info("Downloaded US county list -> %s", path)
        return _read_counties_csv(path)
    except Exception as e:  # offline / URL down
        log.warning("Could not fetch US county list (%s); using Texas only.", e)
        return _texas_fallback()


def _county_table(cfg) -> pd.DataFrame:
    """County fips+name for the run's scope: all US, or one state."""
    tbl = _load_us_counties(cfg)
    if not cfg.is_national:
        sub = tbl[tbl["county_fips"].str[:2] == cfg.state_fips]
        tbl = sub if len(sub) else _texas_fallback()
    return tbl.reset_index(drop=True)


def _bbox(cfg):
    """(lat_range, lon_range) for synthetic facility placement."""
    if cfg.is_national:
        return _US_LAT, _US_LON
    if cfg.state_fips == "48":
        return _TX_LAT, _TX_LON
    return _US_LAT, _US_LON


def generate_demo_inputs(
    cfg: Config | None = None, *, seed: int = 42
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return (county_pre_score, complaint_long, facilities) for the pipeline."""
    cfg = cfg or load_config()
    rng = np.random.default_rng(seed)
    ctbl = _county_table(cfg)
    fips = ctbl["county_fips"].tolist()
    names = ctbl["county_name"].tolist()
    n = len(fips)

    # --- population: heavy-tailed (few big metros, many small rural) ---------
    population = (10 ** rng.normal(4.4, 0.55, n)).round().astype(int).clip(500, 4_700_000)
    households = (population / rng.normal(2.7, 0.15, n)).round().astype(int).clip(200)

    # rurality: inverse-ish to population (small counties more rural) ---------
    pop_rank = pd.Series(population).rank(pct=True).to_numpy()
    pct_rural = np.clip(1 - pop_rank + rng.normal(0, 0.12, n), 0, 1)

    # income: higher in urban, lower in rural + noise -----------------------
    median_income = (38_000 + 42_000 * pop_rank + rng.normal(0, 6_000, n)).clip(22_000, 130_000)
    median_age = (32 + 12 * pct_rural + rng.normal(0, 2.5, n)).clip(22, 55)
    pct_65_plus = np.clip(0.10 + 0.18 * pct_rural + rng.normal(0, 0.03, n), 0.03, 0.45)

    # --- broadband: underserved share grows with rurality -------------------
    pct_underserved = np.clip(0.05 + 0.45 * pct_rural + rng.normal(0, 0.07, n), 0, 0.95)
    pct_unserved = np.clip(0.01 + 0.20 * pct_rural + rng.normal(0, 0.04, n), 0, 0.8)
    pct_unserved = np.minimum(pct_unserved, 1 - pct_underserved)
    pct_served = np.clip(1 - pct_underserved - pct_unserved, 0, 1)
    pct_below_benchmark = pct_underserved + pct_unserved

    # --- complaints: scale with population, friction noise ------------------
    base_rate = rng.normal(11, 3, n).clip(2)  # complaints per 1k households
    friction_boost = 1 + 0.6 * pct_below_benchmark  # worse access -> more friction
    complaints_total = (households / 1000 * base_rate * friction_boost).round().astype(int)

    df = pd.DataFrame({
        "county_fips": fips,
        "county_name": names,
        "state_fips": cfg.state_fips,
        "state_abbr": cfg.state_abbr,
        "total_population": population,
        "total_households": households,
        "median_household_income": median_income.round().astype(int),
        "median_age": median_age.round(1),
        "pct_65_plus": pct_65_plus.round(4),
        "pct_rural": pct_rural.round(4),
        "pct_served": pct_served.round(4),
        "pct_underserved": pct_underserved.round(4),
        "pct_unserved": pct_unserved.round(4),
        "pct_below_benchmark": pct_below_benchmark.round(4),
        "complaints_total": complaints_total,
    })
    df["complaints_per_1k_hh"] = (df["complaints_total"] / df["total_households"] * 1000).round(2)

    # --- split totals into category columns + long form ---------------------
    long_rows = []
    for cat, share in _CATEGORY_MIX.items():
        col = f"complaints_{cat}"
        df[col] = (df["complaints_total"] * share).round().astype(int)
        for fp, cnt in zip(df["county_fips"], df[col]):
            if cnt > 0:
                long_rows.append({"county_fips": fp, "category": cat, "complaint_count": int(cnt)})
    complaint_long = pd.DataFrame(long_rows)

    # --- digital desert flag (uses real config method) ----------------------
    df = flag_deserts(df, cfg)

    # --- data centers: cluster planned MW into ~18 counties -----------------
    facilities, infra = _demo_data_centers(df, cfg, rng)
    df = df.merge(infra, on="county_fips", how="left")
    fill = ["data_center_count", "planned_count", "planned_mw", "operational_mw", "modeled_water_l_per_year"]
    df[fill] = df[fill].fillna(0)

    scope = "US" if cfg.is_national else (cfg.state_abbr or cfg.state_fips)
    log.info("Generated demo inputs for %s counties (%s, seed=%s).", n, scope, seed)
    return df, complaint_long, facilities


def _demo_data_centers(county: pd.DataFrame, cfg: Config, rng) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Place synthetic data centers. Deliberately seed some in well-served
    metros AND some in underserved rural counties so the mismatch metric has
    a real signal to surface."""
    # Pick counties: a mix of high-population and high-underserved. Scale the
    # count with the number of counties so a national run looks national.
    lat_range, lon_range = _bbox(cfg)
    k = max(12, len(county) // 70)
    pop_top = county.nlargest(k, "total_population")["county_fips"].tolist()
    under_top = county.nlargest(k + 2, "pct_underserved")["county_fips"].tolist()
    chosen = list(dict.fromkeys(pop_top + under_top))

    rows = []
    statuses = ["operational", "under construction", "proposed", "planned"]
    for fp in chosen:
        for _ in range(int(rng.integers(1, 4))):
            status = rng.choice(statuses, p=[0.4, 0.25, 0.2, 0.15])
            mw = round(float(rng.uniform(15, 600)), 1)
            rows.append({
                "name": f"DC-{fp}-{int(rng.integers(100, 999))}",
                "status": status,
                "latitude": round(float(rng.uniform(*lat_range)), 5),
                "longitude": round(float(rng.uniform(*lon_range)), 5),
                "planned_mw": mw,
                "source": "DEMO",
                "county_fips": fp,
            })
    facilities = pd.DataFrame(rows)

    planned_set = cfg["infrastructure"]["planned_statuses"]
    facilities["is_planned"] = facilities["status"].apply(
        lambda s: any(p in str(s).lower() for p in planned_set)
    )
    grp = facilities.groupby("county_fips")
    infra = pd.DataFrame({
        "data_center_count": grp.size(),
        "planned_count": grp["is_planned"].sum(),
        "planned_mw": grp.apply(lambda g: g.loc[g["is_planned"], "planned_mw"].sum(), include_groups=False),
        "operational_mw": grp.apply(lambda g: g.loc[~g["is_planned"], "planned_mw"].sum(), include_groups=False),
    }).reset_index()
    l_per_kwh = cfg["water"]["modeled_l_per_kwh"]
    infra["modeled_water_l_per_year"] = infra["planned_mw"] * 1000 * 8760 * l_per_kwh
    return facilities.drop(columns="is_planned"), infra
