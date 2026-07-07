# Telequity — Telecom Complaint Intelligence Platform

[![CI](https://github.com/gavinschroeder/Telequity/actions/workflows/ci.yml/badge.svg)](https://github.com/gavinschroeder/Telequity/actions/workflows/ci.yml)

Telequity maps the gap between **reported** digital access (what ISPs file with
the FCC) and **experienced** access (what consumers actually complain about) for
**every U.S. county**, then overlays that gap against where **data-center
infrastructure** is being built.

The thesis in one line: *digital deserts vs. digital extraction* — large-scale
compute is landing across the country, sometimes in the same rural places that
already report the worst connectivity. Telequity puts both on one map.

> **Framing guardrail.** The data-center overlay is a spatial juxtaposition, not
> a causal claim — data centers don't provide residential broadband. It shows
> *where investment concentrates relative to access gaps.*

---

## What it is

An end-to-end analytics platform:

1. A reproducible **Python pipeline** fuses four public federal datasets, rolls
   everything up to the **county** grain (~3,200 counties), and computes two
   signature metrics.
2. It publishes analysis-ready "gold" tables (CSV + a single Excel workbook) to
   **Microsoft Power BI**, which renders five dashboards.
3. A **React web console** embeds those dashboards with an intro/overview page,
   an about/methodology page, a color-severity legend, and an **auto-generated
   analysis panel** under each dashboard that summarizes the data in plain
   language (grounded in the actual numbers — no hallucinated figures).

### Signature metrics
- **Digital Equity Exposure Index (0–100)** — a transparent weighted composite
  of broadband availability gap, complaint friction, and socioeconomic
  vulnerability. Higher = more exposure / less equitable access.
- **Access–Infrastructure Mismatch** — data-center intensity × equity exposure,
  so a county scores high only when both are high.

## Data sources

| Layer | Source | Access |
|---|---|---|
| Consumer complaints | FCC CGB Consumer Complaints (FCC Open Data / Socrata) | live API, no key |
| Broadband availability | FCC National Broadband Map — *Fixed Broadband Summary by Geography* | one national CSV download |
| Socioeconomic context | U.S. Census ACS 5-year | live API (free key) |
| Data-center locations | PNNL Data Center Atlas | file download |

The public complaint data has **no provider field** — which is *why* Telequity
analyses places, not companies.

## Methodology (transparent)

- **Broadband tiers** use the federal **BEAD** definitions: unserved < 25/3 Mbps,
  underserved < 100/20 Mbps (reliable technologies only — wired + licensed fixed
  wireless).
- **Equity index** is min-max normalized across counties: availability gap
  (40%) + complaint friction per 1,000 households (35%) + socioeconomic
  vulnerability from income/age/rurality (25%).
- **Digital deserts** = counties in the top quartile of locations below the
  100/20 benchmark.
- Full detail lives in the app's **About & Methodology** page and in
  [`powerbi/POWERBI_GUIDE.md`](powerbi/POWERBI_GUIDE.md).

---

## Quick start (demo — no credentials)

```bash
# Python pipeline (bundled synthetic national data)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/run_texas_pilot.py --demo      # writes gold tables + analysis.json

# Web console
cd web && npm install && npm run dev           # http://localhost:5173
```

The demo generates a full **national** synthetic dataset (real county FIPS +
names) so the pipeline, dashboards, and web app all light up before you wire any
real data.

## Real national run

See **[`RUN_FULL.md`](RUN_FULL.md)** for the full checklist. In short: add a free
`CENSUS_API_KEY` to `.env`, drop the FCC broadband summary CSV into `data/raw/bdc/`
and the PNNL Atlas CSV into `data/raw/`, then:

```bash
python scripts/run_texas_pilot.py             # real, national (no --demo)
```

Reference geographies (county shapefile + ZIP↔county crosswalk) auto-download.
Scope is set in `config/config.yaml` (`scope.mode: national`, or `state` for a
single-state run).

## Tests & CI

```bash
pytest                 # Python pipeline tests
cd web && npm test     # web config/API tests
```

GitHub Actions ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs the
Python tests + a pipeline smoke test and the web build + tests on every push.

## Architecture

```
ingest (bronze)          transform (silver)        score          model (gold)          web
────────────────         ──────────────────        ──────         ────────────          ───
fcc_complaints  ─┐       complaints  ─┐             index    ─┐    build_gold      ─┐    React app
census_acs       │  ──►  broadband    │  ──► county friction ├──► fact_county       ├──► embeds
broadband        │       acs          │    (FIPS)  mismatch  ─┘    dim_* / fact_*    │    Power BI +
data_centers     │       infrastructure│                          analysis.json  ───┘    analysis
fetch_reference ─┘       geography    ─┘                           telequity_gold.xlsx
```

```
src/telequity/     Python pipeline (ingest / transform / score / model + analysis)
web/               React + Vite console (embeds Power BI, intro/about, AI panels)
powerbi/           Power BI build guide + data dictionary
config/            central config (scope, weights, thresholds, tier breaks)
tests/             pytest suite   ·   web/src/*.test.js   Vitest suite
RUN_FULL.md        real-data run checklist   ·   SETUP.md   cold-start setup
```

## Disclaimer

Consumer complaints are self-reported and unverified by the FCC. Index values are
relative within the dataset (comparisons between counties, not absolute ratings).
The data-center overlay is juxtaposition, not causation. Figures reflect specific
data vintages and may lag current conditions.
