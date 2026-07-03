# Data dictionary — gold tables (`data/processed/`)

All tables key on **`county_fips`** (5-digit string, e.g. `48201`). Demo runs
append `_DEMO` to every filename.

## `fact_county` — central fact/measure table (one row per county)

| Column | Type | Meaning |
|---|---|---|
| `county_fips` | string | 5-digit county FIPS (join key) |
| `county_name` | string | County name |
| `state_fips`, `state_abbr` | string | `48` / `TX` |
| `total_population` | int | ACS population |
| `total_households` | int | ACS households (denominator for friction) |
| `median_household_income` | int | ACS median household income (USD) |
| `median_age` | float | ACS median age |
| `pct_65_plus` | float 0–1 | Share of population 65+ |
| `pct_rural` | float 0–1 | Share rural (rurality component) |
| `pct_served` | float 0–1 | Locations ≥ 100/20 Mbps |
| `pct_underserved` | float 0–1 | Locations 25/3–100/20 Mbps |
| `pct_unserved` | float 0–1 | Locations < 25/3 Mbps |
| `pct_below_benchmark` | float 0–1 | underserved + unserved (the availability gap) |
| `complaints_total` | int | All complaints in window |
| `complaints_per_1k_hh` | float | Complaints per 1,000 households (friction) |
| `complaints_<category>` | int | Per-category counts (internet, wireless_wireline, tv_video, emergency, radio, accessibility, billing_dispute, other) |
| `desert_cutoff` | float | The underserved-share cutoff used this run |
| `is_digital_desert` | bool | County in the low-access tier |
| `data_center_count` | int | Facilities assigned to county |
| `planned_count` | int | Facilities with a "planned" status |
| `planned_mw` | float | Planned compute load (MW) — infra metric |
| `operational_mw` | float | Operational load (MW) |
| `modeled_water_l_per_year` | float | **Modeled** annual water draw from planned MW |
| `c_availability_gap` | float 0–1 | Normalized availability component |
| `c_complaint_friction` | float 0–1 | Normalized friction component |
| `c_socioeconomic` | float 0–1 | Normalized socioeconomic component |
| `equity_index` | float 0–100 | **Digital Equity Exposure Index** |
| `infra_norm` | float 0–1 | Normalized planned MW |
| `access_norm` | float 0–1 | Normalized equity index |
| `mismatch_score` | float 0–100 | **Access–Infrastructure Mismatch** |
| `mismatch_quadrant` | string | compute_in_underserved / compute_in_served / low_compute_underserved / low_compute_served |

## `dim_county`
`county_fips`, `county_name`, `state_fips`, `state_abbr` — the map/lookup dimension.

## `dim_category`
`category`, `category_label` — complaint category lookup.

## `fact_complaint_category` (long)
`county_fips`, `category`, `complaint_count` — for category drill-downs.

## `fact_data_center` (facility points)
`name`, `status`, `latitude`, `longitude`, `planned_mw`, `source`, `county_fips`
— individual sites for the overlay map.

---

### Notes on interpretation
- `modeled_water_l_per_year` is an **estimate** (planned MW × hours × L/kWh),
  not a measured value — label it as modeled in any visual.
- Normalization is min-max across the counties in scope, so component and
  `*_norm` columns are relative within the run, not absolute national values.
