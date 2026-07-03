# Reference geographies & crosswalks

These files are downloaded **once** and reused across runs. They are git-ignored
(too large to commit); download them locally before a real (non-demo) run.

| File | What it is | Where to get it |
|---|---|---|
| `tl_2023_us_county/` | TIGER/Line county shapefile (geometry for choropleths + point-in-polygon) | https://www2.census.gov/geo/tiger/TIGER2023/COUNTY/ |
| `zcta_county_crosswalk.csv` | ZCTA → county FIPS relationship (maps complaint ZIPs to counties) | https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/ |
| `county_urban_rural.csv` | County % rural population (rurality component of the index) | Census 2020 urban/rural; or ACS-derived. See `transform/acs.py`. |

Notes
- The pipeline assigns each complaint to a county two ways and prefers whichever
  is present: (1) lat/long point-in-polygon against the county shapefile, then
  (2) ZIP → county via the crosswalk as a fallback.
- If you only need a quick demo, you don't need any of these — run the pipeline
  with `--demo` and it generates a labeled synthetic Texas dataset instead.
