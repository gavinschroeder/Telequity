"""Per-dashboard analysis generator.

Computes REAL, grounded insights (rankings, correlations, outliers, shares)
from the gold tables and renders a plain-language summary + a few "callout"
bullets for each dashboard. Output is a static ``analysis.json`` the web app
reads — no backend, no per-view cost, and (because the numbers are computed,
not written by a model) no risk of hallucinated figures.

Optional: if ANTHROPIC_API_KEY is set, ``_llm_polish`` rewrites the summary
prose in a warmer voice while keeping the computed numbers fixed. Absent a key
(the default), the deterministic narrative is used as-is.

Keys in the output match REPORT_PAGES keys in the web app:
    mismatch, avail-vs-friction, categories, equity-map, datacenter-map
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pandas as pd

from .config import Config, load_config
from .utils import get_logger, read_table

log = get_logger("analysis")


# ---------- small helpers -------------------------------------------------
def _state_of(county_name: str) -> str:
    return county_name.split(",")[-1].strip() if isinstance(county_name, str) and "," in county_name else ""


def _names(df: pd.DataFrame, by: str, n: int = 5, ascending: bool = False) -> list[str]:
    if by not in df.columns:
        return []
    top = df.sort_values(by, ascending=ascending).head(n)
    return [str(x) for x in top["county_name"].tolist()]


def _fmt_list(items: list[str]) -> str:
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _pct(x: float) -> str:
    return f"{x * 100:.0f}%"


# ---------- per-dashboard sections ---------------------------------------
def _section_mismatch(fc: pd.DataFrame) -> dict:
    top = _names(fc, "mismatch_score", 5)
    callouts = []
    if "mismatch_quadrant" in fc.columns:
        n_hi = int((fc["mismatch_quadrant"] == "compute_in_underserved").sum())
        callouts.append(
            f"{n_hi} counties fall in the highest-concern group — meaningful data-center "
            "presence sitting on above-median access gaps."
        )
    if "data_center_count" in fc.columns:
        dc_counties = int((fc["data_center_count"] > 0).sum())
        callouts.append(f"Data centers are spread across {dc_counties} counties nationwide.")
    callouts.append(
        "Intensity is currently measured by facility count (planned-megawatt data isn't "
        "integrated yet), so this reads as 'data-center footprint vs. access gap.'"
    )
    summary = (
        "This view ranks counties by where data-center presence overlaps with the weakest "
        f"consumer access. The highest-scoring counties are {_fmt_list(top)}. A high score means "
        "a county carries both notable data-center activity and a large gap between the broadband "
        "reported as available and what residents actually experience."
    )
    return {"summary": summary, "callouts": callouts}


def _section_avail_friction(fc: pd.DataFrame) -> dict:
    callouts = []
    summary_bits = []
    if {"pct_below_benchmark", "complaints_per_1k_hh"}.issubset(fc.columns):
        sub = fc[["pct_below_benchmark", "complaints_per_1k_hh"]].dropna()
        corr = sub.corr().iloc[0, 1] if len(sub) > 2 else float("nan")
        # "paper access, poor experience": low availability gap but high friction
        avail_med = fc["pct_below_benchmark"].median()
        fric_med = fc["complaints_per_1k_hh"].median()
        friction_zone = fc[(fc["pct_below_benchmark"] <= avail_med) & (fc["complaints_per_1k_hh"] >= fric_med)]
        n_friction = len(friction_zone)
        top_friction = _names(friction_zone, "complaints_per_1k_hh", 4)
        rel = (
            "a weak positive" if 0.1 <= corr < 0.4 else
            "a moderate" if 0.4 <= corr < 0.7 else
            "a strong" if corr >= 0.7 else
            "little to no"
        )
        summary_bits.append(
            f"Across counties there is {rel} relationship (r = {corr:.2f}) between the broadband "
            "availability gap and how often residents complain."
        )
        callouts.append(
            f"{n_friction} counties sit in the 'paper access, poor experience' zone — availability "
            "looks fine but complaint friction is above the national median."
        )
        if top_friction:
            callouts.append(f"Notable examples of that pattern: {_fmt_list(top_friction)}.")
    summary = (
        (summary_bits[0] if summary_bits else "")
        + " Each dot is a county: the x-axis is the share of locations below the 100/20 Mbps "
        "benchmark, and the y-axis is complaints per 1,000 households. Counties toward the "
        "upper-right have both poor availability and high lived friction."
    ).strip()
    return {"summary": summary, "callouts": callouts}


def _section_categories(long_df: pd.DataFrame) -> dict:
    callouts = []
    total = int(long_df["complaint_count"].sum()) if "complaint_count" in long_df.columns else 0
    by_cat = (
        long_df.groupby("category")["complaint_count"].sum().sort_values(ascending=False)
        if {"category", "complaint_count"}.issubset(long_df.columns) else pd.Series(dtype=int)
    )
    labels = {
        "wireless_wireline": "phone/wireless", "internet": "internet", "tv_video": "TV",
        "emergency": "emergency", "radio": "radio", "accessibility": "accessibility",
        "billing_dispute": "billing disputes", "other": "other",
    }
    top3 = []
    for cat, cnt in by_cat.head(3).items():
        share = cnt / total if total else 0
        top3.append(f"{labels.get(cat, cat)} ({_pct(share)})")
    if len(by_cat):
        callouts.append(f"Largest category: {labels.get(by_cat.index[0], by_cat.index[0])} "
                        f"with {int(by_cat.iloc[0]):,} complaints.")
    if "accessibility" in by_cat.index:
        acc_share = by_cat["accessibility"] / total if total else 0
        callouts.append(f"Accessibility complaints are a small but distinct slice ({_pct(acc_share)}).")
    summary = (
        f"Of roughly {total:,} consumer complaints in the record, the mix is led by "
        f"{_fmt_list(top3)}. This shows what people are actually struggling with — not just "
        "whether service exists, but how it fails them day to day."
    )
    return {"summary": summary, "callouts": callouts}


def _section_equity(fc: pd.DataFrame) -> dict:
    callouts = []
    ei = fc["equity_index"] if "equity_index" in fc.columns else pd.Series(dtype=float)
    summary_bits = []
    if len(ei):
        summary_bits.append(
            f"The Digital Equity Exposure Index ranges from {ei.min():.0f} to {ei.max():.0f} "
            f"(median {ei.median():.0f}); higher means more combined risk — worse availability, "
            "more complaint friction, and greater socioeconomic vulnerability."
        )
        top_counties = _names(fc, "equity_index", 5)
        callouts.append(f"Highest-exposure counties: {_fmt_list(top_counties)}.")
        # state-level rollup
        tmp = fc.copy()
        tmp["state"] = tmp["county_name"].map(_state_of)
        st = tmp[tmp["state"] != ""].groupby("state")["equity_index"].mean().sort_values(ascending=False)
        if len(st):
            callouts.append(f"Highest average exposure by state: {_fmt_list(list(st.head(4).index))}.")
    if "is_digital_desert" in fc.columns:
        callouts.append(f"{int(fc['is_digital_desert'].sum())} counties are flagged as digital "
                        "deserts (top quartile of locations below the 100/20 benchmark).")
    summary = (" ".join(summary_bits) + " Darker counties on the map carry the most exposure.").strip()
    return {"summary": summary, "callouts": callouts}


def _section_datacenter(fc: pd.DataFrame, dc: pd.DataFrame) -> dict:
    callouts = []
    n_fac = len(dc)
    n_counties = dc["county_fips"].nunique() if "county_fips" in dc.columns else 0
    summary_bits = [f"{n_fac:,} data-center facilities are mapped across {n_counties} counties."]
    if {"equity_index"}.issubset(dc.columns):
        med = fc["equity_index"].median() if "equity_index" in fc.columns else None
        if med is not None:
            above = (pd.to_numeric(dc["equity_index"], errors="coerce") >= med).mean()
            callouts.append(
                f"{_pct(above)} of mapped data centers sit in counties with above-median "
                "digital-equity exposure — i.e., where access is already relatively weak."
            )
    if "data_center_count" in fc.columns and "equity_index" in fc.columns:
        hi = fc[fc["equity_index"] >= fc["equity_index"].quantile(0.75)]
        hi_dc = int((hi["data_center_count"] > 0).sum())
        callouts.append(f"{hi_dc} of the highest-exposure quartile counties already host at least "
                        "one data center.")
    callouts.append("Placement is shown as a spatial juxtaposition against access — not a claim "
                    "that data centers affect residential broadband.")
    summary = (" ".join(summary_bits) + " Bubbles are colored by the access level of the county "
               "they sit in, so clusters over darker counties show compute concentrating where "
               "connectivity is weakest.")
    return {"summary": summary, "callouts": callouts}


# ---------- orchestration -------------------------------------------------
def build_sections(fact_county: pd.DataFrame, complaint_long: pd.DataFrame,
                   data_centers: pd.DataFrame) -> dict:
    return {
        "mismatch": _section_mismatch(fact_county),
        "avail-vs-friction": _section_avail_friction(fact_county),
        "categories": _section_categories(complaint_long),
        "equity-map": _section_equity(fact_county),
        "datacenter-map": _section_datacenter(fact_county, data_centers),
    }


def generate_analysis(fact_county, complaint_long, data_centers, cfg: Config | None = None,
                      *, demo: bool = False) -> dict:
    """Build the analysis payload and write it to the configured JSON path(s)."""
    cfg = cfg or load_config()
    sections = build_sections(fact_county, complaint_long, data_centers)
    sections = _maybe_llm_polish(sections)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": cfg["scope"].get("state_name", "United States"),
        "demo": demo,
        "note": "Automated analysis generated from the underlying county data.",
        "sections": sections,
    }

    out_paths = []
    web_path = cfg.path(cfg["paths"].get("analysis_out", "web/public/analysis.json"))
    web_path.parent.mkdir(parents=True, exist_ok=True)
    web_path.write_text(json.dumps(payload, indent=2))
    out_paths.append(str(web_path))
    # keep a copy alongside the gold tables too
    proc = cfg.data_path("processed", "analysis.json")
    proc.write_text(json.dumps(payload, indent=2))
    out_paths.append(str(proc))

    log.info("Wrote analysis -> %s", ", ".join(out_paths))
    return payload


def analysis_from_disk(cfg: Config | None = None, *, demo: bool = False) -> dict:
    """Regenerate analysis from gold CSVs already on disk (no pipeline run)."""
    cfg = cfg or load_config()
    suffix = "_DEMO" if demo else ""
    fc = read_table(cfg.data_path("processed", f"fact_county{suffix}.csv"))
    cl = read_table(cfg.data_path("processed", f"fact_complaint_category{suffix}.csv"))
    dc = read_table(cfg.data_path("processed", f"fact_data_center{suffix}.csv"))
    return generate_analysis(fc, cl, dc, cfg, demo=demo)


# ---------- optional LLM polish (off unless ANTHROPIC_API_KEY set) --------
def _maybe_llm_polish(sections: dict) -> dict:
    """If an Anthropic key is present, rewrite each summary in a warmer voice
    while keeping callouts (the hard numbers) untouched. Fails safe."""
    key = Config.secret("ANTHROPIC_API_KEY")
    if not key:
        return sections
    try:  # pragma: no cover - network + key dependent
        import requests

        for name, sec in sections.items():
            prompt = (
                "Rewrite this dashboard summary in 2-3 clear, engaging sentences for a general "
                "audience. Do NOT invent or change any numbers; keep every figure exactly. "
                f"Summary: {sec['summary']}"
            )
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
                json={"model": "claude-haiku-4-5-20251001", "max_tokens": 300,
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=30,
            )
            if r.ok:
                txt = "".join(b.get("text", "") for b in r.json().get("content", []))
                if txt.strip():
                    sec["summary"] = txt.strip()
        log.info("LLM-polished analysis summaries.")
    except Exception as e:  # noqa: BLE001
        log.warning("LLM polish skipped (%s); using computed narrative.", e)
    return sections
