"""End-to-end orchestrator for a single state (default: Texas).

Real run (needs CENSUS_API_KEY, broadband file/token, data-center files):
    python -m telequity.pipeline

Demo run (no credentials; labeled synthetic data so Power BI dev isn't blocked):
    python -m telequity.pipeline --demo

Stages: ingest (bronze) -> transform (silver) -> score -> assemble gold.
"""
from __future__ import annotations

import argparse

import pandas as pd

from .config import load_config
from .model.build_gold import assemble_fact_county, write_gold
from .score.index import compute_index
from .score.mismatch import compute_mismatch
from .utils import get_logger

log = get_logger("pipeline")


def run_real(cfg, *, max_records: int | None = None) -> dict[str, str]:
    """Full pipeline against live sources + downloaded reference files."""
    from .ingest.census_acs import fetch_acs
    from .ingest.broadband import load_broadband
    from .ingest.data_centers import load_data_centers
    from .ingest.fcc_complaints import fetch_complaints
    from .transform.acs import build_features
    from .transform.broadband import county_broadband, flag_deserts
    from .transform.complaints import aggregate_to_county
    from .transform.geography import assign_county_by_point, county_dimension
    from .transform.infrastructure import county_infrastructure

    log.info("=== Telequity pipeline (REAL) — %s ===", cfg["scope"]["state_name"])

    # --- auto-download stable reference files if missing (crosswalk, shapefile) ---
    from .ingest.fetch_reference import fetch_all as fetch_reference
    fetch_reference(cfg)

    # --- ingest + ACS features (also our household + county-dim source) ---
    acs = fetch_acs(cfg)
    acs_features = build_features(acs, cfg)
    county_dim = county_dimension(acs, cfg)

    # --- complaints -> county ---
    complaints_raw = fetch_complaints(cfg, max_records=max_records)
    complaints_wide, complaint_long = aggregate_to_county(complaints_raw, acs, cfg)

    # --- broadband -> county tiers + desert flag ---
    bb_raw = load_broadband(cfg)
    county_bb = flag_deserts(county_broadband(bb_raw, cfg), cfg)

    # --- data centers -> county load + modeled water ---
    facilities = load_data_centers(cfg)
    # Prefer county codes carried by the source (e.g. PNNL); geocode only if absent.
    if "county_fips" not in facilities.columns or facilities["county_fips"].isna().all():
        facilities = assign_county_by_point(facilities, cfg)
    infra = county_infrastructure(facilities, cfg)

    fact = assemble_fact_county(
        county_dim=county_dim,
        broadband=county_bb,
        complaints_wide=complaints_wide,
        acs_features=acs_features,
        infrastructure=infra,
    )
    fact = compute_index(fact, cfg)
    fact = compute_mismatch(fact, cfg)
    return write_gold(fact, complaint_long, facilities, cfg, demo=False)


def run_demo(cfg) -> dict[str, str]:
    """Pipeline over labeled synthetic data (real TX county identities, modeled
    metrics). Exercises the SAME scoring + gold code as a real run."""
    from .demo import generate_demo_inputs

    log.info("=== Telequity pipeline (DEMO — synthetic metrics) ===")
    county_pre, complaint_long, facilities = generate_demo_inputs(cfg)
    fact = compute_index(county_pre, cfg)
    fact = compute_mismatch(fact, cfg)
    paths = write_gold(fact, complaint_long, facilities, cfg, demo=True)
    log.info("Demo gold tables written (suffix _DEMO). NOT real measurements.")
    return paths


def run(*, demo: bool = False, config_path: str | None = None, max_records: int | None = None):
    cfg = load_config(config_path)
    return run_demo(cfg) if demo else run_real(cfg, max_records=max_records)


def main() -> None:
    p = argparse.ArgumentParser(description="Telequity pipeline")
    p.add_argument("--demo", action="store_true", help="run with labeled synthetic data")
    p.add_argument("--config", default=None, help="path to a config.yaml override")
    p.add_argument("--max-records", type=int, default=None, help="cap complaint rows")
    args = p.parse_args()
    paths = run(demo=args.demo, config_path=args.config, max_records=args.max_records)
    print("\nGold tables written:")
    for name, path in paths.items():
        print(f"  {name:28s} {path}")


if __name__ == "__main__":  # pragma: no cover
    main()
