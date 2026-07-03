# Power BI build guide

This guide turns the gold tables in `data/processed/` into the report described
in the project brief. You build the `.pbix` once; thereafter **Refresh** re-reads
the CSVs the Python pipeline regenerates.

> Tip for first build: run `python scripts/run_texas_pilot.py --demo` and point
> Power BI at the `*_DEMO.csv` files. The layout is identical to a real run —
> just swap the source folder later.

---

## 1. Connect

**Recommended (Mac / Power BI Service, auto-refresh):** the pipeline writes a
single workbook `data/processed/telequity_gold.xlsx` with one sheet per table.
Put it in OneDrive/SharePoint and connect once:

1. Set `paths.publish_workbook_to` in `config/config.yaml` to a OneDrive-synced
   folder, then run the pipeline — the workbook lands in OneDrive automatically.
   (Or just copy `telequity_gold.xlsx` into OneDrive.)
2. In the Power BI **Service**: **Get data → Files → OneDrive – Business** →
   pick `telequity_gold.xlsx` → **Import**. All five tables load at once.
3. **Dataset → Settings → Scheduled refresh** (OneDrive files also refresh
   ~hourly automatically). Re-running the pipeline now updates the dashboards
   with no manual re-upload.

**Alternative (Desktop):** **Get Data → Folder** → `data/processed/` → load each
CSV, or **Get Data → Excel** → `telequity_gold.xlsx`.

Set column types in Power Query:
- `county_fips` → **Text** (never let it become a number — leading zeros matter).
- All `pct_*`, `*_norm`, `equity_index`, `mismatch_score` → **Decimal**.
- `is_digital_desert` → **True/False**.

## 2. Model (relationships are OPTIONAL)

**You do not need relationships.** Each table is denormalized to be
self-sufficient: `fact_county` has every county metric (incl. per-category
complaint counts as columns), and `fact_complaint_category` /
`fact_data_center` each carry the county fields they need (`county_name`,
`equity_index`, `mismatch_score`, `is_digital_desert`, `pct_below_benchmark`,
`pct_rural`). So build any visual from a **single table** — no model editing,
which matters because "Open semantic model" (formerly "model view") is often
disabled by a tenant admin and needs no fallback here.

**Which table per page:**
- Pages 2–5, 7 (metrics, index map, mismatch) → **`fact_county`** alone.
- Complaint-category drill (page 1) → **`fact_complaint_category`** alone.
- Data-center points (page 6 overlay) → **`fact_data_center`** alone.

**Optional (only if "Open semantic model" IS available):** for nicer
cross-filtering you can still add single-direction (1→*) relationships
`dim_county[county_fips]` → each fact, and `dim_category[category]` →
`fact_complaint_category`. Not required.

## 3. Core DAX measures

Most numbers are precomputed, but these measures drive titles, KPIs and the
what-if threshold. Create a `_Measures` table to hold them.

```DAX
Avg Equity Index   = AVERAGE ( fact_county[equity_index] )
Desert County Count = CALCULATE ( COUNTROWS ( fact_county ), fact_county[is_digital_desert] = TRUE )
Total Planned MW   = SUM ( fact_county[planned_mw] )
Complaints / 1k HH = AVERAGE ( fact_county[complaints_per_1k_hh] )

-- Counties where incoming compute meets the worst access:
Compute-in-Underserved Counties =
CALCULATE (
    COUNTROWS ( fact_county ),
    fact_county[mismatch_quadrant] = "compute_in_underserved"
)

-- Highest-mismatch county name (for a dynamic card/title):
Top Mismatch County =
VAR t = TOPN ( 1, fact_county, fact_county[mismatch_score], DESC )
RETURN MAXX ( t, fact_county[county_name] )
```

### Optional what-if: live desert threshold
Add a **numeric range parameter** `Desert Threshold` (0.10–0.90, step 0.05),
then a dynamic flag so reviewers can move the line themselves:

```DAX
Dynamic Desert =
VAR cut = SELECTEDVALUE ( 'Desert Threshold'[Desert Threshold Value] )
RETURN
CALCULATE (
    COUNTROWS ( fact_county ),
    FILTER ( fact_county, fact_county[pct_below_benchmark] >= cut )
)
```

## 4. Report pages (maps to the brief)

| # | Page | Primary visual | Key fields |
|---|---|---|---|
| 1 | **Complaint categories** by state/county/time | stacked bar + line | `fact_complaint_category` by `category`; trend by date |
| 2 | **Availability vs complaint intensity** | scatter | x=`pct_below_benchmark`, y=`complaints_per_1k_hh`, size=`total_households` |
| 3 | **Rural vs urban service friction** | clustered bar / box | `pct_rural` buckets vs `complaints_per_1k_hh` |
| 4 | **Equity index map** | filled map (county) | color = `equity_index`; tooltip = components |
| 5 | **Reported vs experienced access** | filled map | color = `pct_below_benchmark` vs `complaints_per_1k_hh` toggle (bookmark) |
| 6 | **Data-center overlay** *(the finale)* | filled map + bubble layer | base = `equity_index`; bubbles from `fact_data_center` (lat/long), size = `planned_mw` |
| 7 | **Mismatch leaderboard** | table + bar | sort `fact_county` by `mismatch_score`; color by `mismatch_quadrant` |

### Building the US county choropleth (the signature map)

This shades every county by an access metric — the end-goal national map. Build
it from **fact_county** alone (no relationships needed):

1. Add a **Filled map** visual (Visualizations → the filled-map / choropleth icon).
   - If you don't see it: **⋯ (more visuals) → Get more visuals**, or use the
     built-in "Azure Map" and switch its layer to a filled/choropleth style.
2. **Location** well → drag **`county_name`**. Then set its geography so Power BI
   geocodes correctly: select the `county_name` field → **Column tools → Data
   category → County** (do this in the model; you have model access). Also add
   **`state_abbr`** to Location *below* county_name so duplicate county names
   (e.g., every "Washington County") resolve to the right state.
   - More robust alternative: use **`county_fips`** in Location with Data
     category = **County** — FIPS is unambiguous nationwide.
3. **Color / Legend (fill)** → drag **`equity_index`** (set aggregation to
   **Average** or **Don't summarize**, since it's one value per county). Red-high
   diverging scale reads as "worst access = darkest."
4. **Tooltips** → add `pct_below_benchmark`, `complaints_per_1k_hh`,
   `planned_count`, `planned_mw` so hovering a county shows access, friction, and
   whether data centers are planned there.
5. To flag data-center counties: **Format → Fill colors → conditional**, or add a
   border/second layer driven by `planned_count > 0`.

That single visual = accessibility + complaints + data-center presence per county,
nationwide. Swap `equity_index` for `pct_below_benchmark` or `complaints_per_1k_hh`
to retell the story from each angle.

### Building the data-center points overlay (page 6)
1. Filled map shaded by `equity_index` (or `pct_below_benchmark`).
2. Add a second map layer / ArcGIS visual using `fact_data_center` latitude &
   longitude, bubble size = `planned_mw`, color by `status`.
3. Add a slicer on `mismatch_quadrant` defaulting to `compute_in_underserved`
   so the page opens on the ethical signal: compute planned where access is worst.

## 5. The honesty note (put it on the report)

Add a text box to pages 6–7:

> *Data-center locations are shown alongside access metrics to illustrate where
> infrastructure investment is concentrating relative to digital-access gaps.
> This is a spatial juxtaposition, not a causal claim — data centers do not
> provide residential broadband. Water figures are modeled estimates.*

## 6. Refresh workflow

1. Re-run the pipeline (`python scripts/run_texas_pilot.py`) to regenerate CSVs.
2. In Power BI: **Home → Refresh**. The model and visuals update in place.
3. For scheduled refresh in the Power BI Service, place `data/processed/` on a
   gateway-accessible path or OneDrive/SharePoint and configure a data gateway.

## 7. Suggested theme
Diverging color scale for the index/mismatch maps (e.g. low = teal, high = deep
red) so "worst" reads instantly. Keep data-center bubbles a neutral high-contrast
outline so they sit on top of the choropleth without implying causation.
