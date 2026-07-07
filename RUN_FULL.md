# Running the full project on REAL national data (no demo)

End state: every US county, real complaints + broadband + ACS + data centers,
flowing into the Power BI dashboards and the webpage.

## What's automated vs. what you do once

| Step | Automated? |
|---|---|
| Pull FCC complaints (all states) | ✅ API, no key |
| Pull Census ACS (all counties) | ✅ API (needs free key) |
| Download county geometry + ZIP↔county crosswalk | ✅ auto-downloads on first run |
| Aggregate to county, score, build gold tables + workbook | ✅ |
| Publish workbook to OneDrive | ✅ (path in config) |
| Get a Census key / FCC token | ⛔ one-time signup |
| Download broadband CSVs | ⛔ one-time (huge national dataset) |
| Download PNNL + LBNL data-center files | ⛔ one-time (no stable public URL) |
| Build the Power BI report | ⛔ once (see powerbi/POWERBI_GUIDE.md) |

## Step 1 — keys (one-time)

- **Census API key** (free): https://api.census.gov/data/key_signup.html →
  put in `.env` as `CENSUS_API_KEY=...` (already done).
- *(Optional)* **FCC BDC API token** for broadband via API instead of manual
  download: create an FCC user account, generate a token, put in `.env`
  (`FCC_BDC_USERNAME`, `FCC_BDC_TOKEN`). Skip if using the download below.

## Step 2 — source files (one-time downloads)

1. **Broadband** — https://broadbandmap.fcc.gov/data-download, current vintage.
   From the left **Summary** column download **"Fixed Broadband Summary by
   Geography Type → State, County, ..."** — a single national CSV, already
   aggregated to county. Drop it into `data/raw/bdc/`. (The loader also accepts
   location-level availability files, but the summary is the laptop-friendly one.)
2. **Data centers**
   - PNNL Data Center Atlas CSV → `data/raw/pnnl_data_center_atlas.csv`
     (download from https://im3.pnnl.gov/datacenter-atlas)
   - *(Optional)* LBNL interconnection queue → `data/raw/lbnl_interconnection_queue.csv`
3. *(Optional)* **USGS** county water use → `data/raw/usgs_county_water_use.csv`
4. **County geometry + ZIP↔county crosswalk** — *nothing to do*; auto-downloaded
   on first run.

## Step 3 — confirm config

`config/config.yaml` is already set for the full run:
- `scope.mode: national`
- `broadband.bulk_download_path: "data/raw/bdc"` (the folder from Step 2)

To also auto-publish the workbook to a synced folder (OneDrive/SharePoint) so
Power BI refreshes on its own, set `TELEQUITY_PUBLISH_DIR` in your local `.env`
to that folder, e.g. `/Users/you/Library/CloudStorage/OneDrive-<org>/Telequity`.

## Step 4 — run it (no demo)

```bash
cd ~/PycharmProjects/Telequity
source .venv/bin/activate
pip install -r requirements.txt          # first time / after updates
python scripts/run_texas_pilot.py        # NOTE: no --demo  = real national run
```

This pulls complaints + ACS, auto-fetches the crosswalk/shapefile, loads your
broadband + data-center files, scores every US county, regenerates the
per-dashboard `analysis.json`, and writes `data/processed/telequity_gold.xlsx`
(and, if `TELEQUITY_PUBLISH_DIR` is set, a copy there for Power BI auto-refresh).

*(geopandas is optional — if it isn't installed, county assignment uses the ZIP
crosswalk automatically.)*

## Step 5 — Power BI (once)

1. If you connected Power BI to the OneDrive workbook already: **⋯ → Refresh
   now**. Otherwise **Get data → Files → OneDrive → `telequity_gold.xlsx`**.
   (Real run drops the `_DEMO` suffix — connect to `telequity_gold.xlsx`.)
2. Your 4 pages now show real national data. Build the county **choropleth**
   per `powerbi/POWERBI_GUIDE.md` (§ "US county choropleth").
3. The Publish-to-web link and the webpage tabs keep working unchanged.

## Step 6 — webpage

```bash
cd web && npm run dev      # tabs already wired to your 4 pages
```

## Re-running later

Just repeat Step 4 (`python scripts/run_texas_pilot.py`). Cached reference files
and downloaded sources are reused; the workbook overwrites in OneDrive and Power
BI auto-refreshes. Refresh broadband/data-center files only when new vintages
publish (broadband: twice a year, Jun 30 / Dec 31).
