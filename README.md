# Telequity — Telecom Complaint Intelligence Platform

Mapping the gap between **reported** digital access (what ISPs file with the FCC)
and **experienced** access (what consumers actually complain about) — then
overlaying that gap against where **data-center infrastructure** is being planned.

The thesis in one line: *digital deserts vs. digital extraction* — large-scale
compute is increasingly being planned in the same rural places that already
score worst on broadband access and highest on consumer friction.

> **Framing guardrail.** The data-center overlay is presented as juxtaposition
> and resource-allocation equity, **not** causation. Data centers do not serve
> residential broadband; the platform highlights *where investment flows vs.
> where access lags*. This honesty is intentional and load-bearing.

---

## What it produces

A reproducible Python pipeline that fuses four public data sources at the
**county** grain (national — every US county) and emits Power-BI-ready "gold" tables, including
two signature metrics:

1. **Digital Equity Exposure Index (0–100)** — a transparent weighted composite
   of availability gap + complaint friction + socioeconomic vulnerability.
2. **Access–Infrastructure Mismatch** — `planned_MW_norm × equity_index_norm`,
   which scores high *only* where lots of incoming compute sits on top of the
   worst lived access.

## Data sources & access model

| Layer | Source | Access | Auth |
|---|---|---|---|
| Complaints | FCC CGB Consumer Complaints (Socrata) | live API | none (app token optional) |
| Socioeconomic | Census ACS 5-year | live API | **free key required** |
| Broadband | FCC National Broadband Map (BDC) | bulk file or API | FCC account/token *or* one-time download |
| Infrastructure | PNNL Data Center Atlas + LBNL interconnection queue | file download | none |
| Water (best-effort) | USGS county water use + modeled draw | file download | none |

The FCC complaint data intentionally has **no provider field** — which is *why*
the platform analyses places, not companies.

## Thresholds (not invented)

Broadband tiers use the **BEAD statutory definitions** (IIJA 2021):

- **Unserved** — location lacks 25/3 Mbps
- **Underserved** — location lacks 100/20 Mbps (FCC fixed benchmark, Mar 2024)

The speed thresholds are statutory; the *county-level* "digital desert" cutoff
(what share of a county's locations below benchmark makes the whole county a
desert) is an explicit analytic choice set from the distribution (top quartile),
configurable in `config/config.yaml`.

---

## Quick start

```bash
# 1. Install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2a. Demo run — NO credentials needed (labeled synthetic metrics, real TX
#     county FIPS). Lets you build the Power BI report immediately.
python scripts/run_texas_pilot.py --demo

# 2b. Real run — set up .env first (see below), download reference files
#     (see data/reference/README.md), then:
python scripts/run_texas_pilot.py
```

Gold tables land in `data/processed/` (demo tables carry a `_DEMO` suffix).
Point Power BI at that folder — see `powerbi/POWERBI_GUIDE.md`.

### Credentials (`.env`)

Copy `.env.example` to `.env` and fill in:

- `CENSUS_API_KEY` — free, required ([sign up](https://api.census.gov/data/key_signup.html))
- `FCC_BDC_USERNAME` / `FCC_BDC_TOKEN` — only if pulling broadband via API
- `FCC_SOCRATA_APP_TOKEN` — optional, raises complaint API rate limit

---

## Architecture (medallion)

```
ingest (bronze)            transform (silver)          score            model (gold)
─────────────────          ──────────────────          ──────           ────────────
fcc_complaints.py   ─┐     complaints.py  ─┐            index.py   ─┐    build_gold.py
census_acs.py        ├──►  broadband.py    ├──► county ─┤           ├──► fact_county
broadband.py         │     acs.py          │    (FIPS)  mismatch.py │    dim_county
data_centers.py      │     infrastructure.py│           ─┘          │    dim_category
water.py            ─┘     geography.py    ─┘                       ─┘    fact_complaint_category
                                                                         fact_data_center
```

Everything joins on one key: **`county_fips`** (5-digit string).

```
src/telequity/
├── config.py            # loads config/config.yaml + .env
├── ingest/              # bronze: pull raw sources
├── transform/           # silver: clean + roll up to county
├── score/               # equity index + mismatch
├── model/build_gold.py  # assemble the star schema
├── demo.py              # labeled synthetic generator (no creds)
└── pipeline.py          # orchestrator (real | --demo)
```

## Tests

```bash
pytest          # 13 unit + smoke tests (scoring math, BEAD tiers, ZIP join, demo)
```

## Scope: national

The pipeline defaults to **national** scope (`scope.mode: national` in
`config/config.yaml`) — every US county across the 50 states + DC. To restrict
to one state (e.g. the original Texas pilot), set `mode: state`, `state_fips: "48"`,
`state_abbr: "TX"`.

### Running the full US on real data

- **Complaints** (Socrata) and **ACS** (Census key) both pull nationally with no
  extra work — ACS returns all ~3,143 counties; complaints stream all states.
- **Broadband** is the heavy input: the national BDC location file is very large.
  Practical path — download the **fixed-broadband availability CSV per state**
  from broadbandmap.fcc.gov/data-download, drop them all into a folder, and point
  `broadband.bulk_download_path` at that **folder** (the loader concatenates every
  CSV in it). Or use FCC area/summary files. The pipeline aggregates to county
  regardless of how many files you provide.
- **Data centers** (PNNL + LBNL) are national files already.

Phasing: pilot ✔ → **national ✔ (code)** → automated refresh. Broadband refreshes
twice yearly (Jun 30 / Dec 31); water remains best-effort.

> The bundled `--demo` now generates a **national** synthetic dataset (real county
> FIPS + names for all states + DC) so the dashboards show the whole US before you
> run the real, credentialed pull.
