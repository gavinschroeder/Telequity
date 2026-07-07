const SOURCES = [
  {
    name: "FCC Consumer Complaints (CGB)",
    detail:
      "~1.6M informal, consumer-filed complaints (2021–present) across internet, phone/wireless, TV, billing, robocalls, and accessibility. Pulled from the FCC Open Data (Socrata) API. Self-reported and unverified by the FCC.",
  },
  {
    name: "FCC National Broadband Map",
    detail:
      "Fixed Broadband Summary by Geography (Dec 2025 vintage): the share of residential locations in each county served at each speed tier, limited to reliable technologies (wired + licensed fixed wireless).",
  },
  {
    name: "U.S. Census — ACS 5-year (2022)",
    detail:
      "County median household income, households, median age, and population — the socioeconomic context layer.",
  },
  {
    name: "PNNL Data Center Atlas",
    detail:
      "Locations of ~1,500 U.S. data-center facilities, derived from OpenStreetMap with county and state assignment.",
  },
];

const METHOD = [
  {
    h: "Geographic grain",
    p: "Every metric is aggregated to the U.S. county (50 states + DC), keyed by 5-digit FIPS — roughly 3,200 counties.",
  },
  {
    h: "Broadband tiers (BEAD definitions)",
    p: "Federal statutory thresholds: a location is unserved below 25/3 Mbps and underserved below 100/20 Mbps (the FCC's fixed-broadband benchmark).",
  },
  {
    h: "Digital Equity Exposure Index (0–100)",
    p: "A transparent weighted composite, min-max normalized across counties: availability gap (40%), complaint friction per 1,000 households (35%), and socioeconomic vulnerability from income, age, and rurality (25%). Higher = more exposure/risk.",
  },
  {
    h: "Digital deserts",
    p: "Counties in the top quartile of locations below the 100/20 benchmark are flagged as digital deserts.",
  },
  {
    h: "Access–Infrastructure Mismatch",
    p: "Data-center intensity × equity exposure, so a county scores high only when both are high. Intensity currently uses facility count as a proxy; planned-capacity (megawatt) data will replace it once integrated.",
  },
];

export default function AboutView() {
  return (
    <div className="doc">
      <div className="doc-inner">
        <p className="doc-eyebrow">About &amp; Methodology</p>
        <h1 className="doc-title">How the platform is built.</h1>

        <section className="doc-section">
          <h2>The platform</h2>
          <p>
            Telequity runs on a reproducible Python data pipeline that pulls from public federal
            datasets, aggregates everything to the county level, computes the equity metrics, and
            publishes analysis-ready tables to Microsoft Power BI. The dashboards on this site are
            live Power BI reports embedded in the page; the underlying data refreshes as new
            source vintages are released.
          </p>
        </section>

        <section className="doc-section">
          <h2>Data sources</h2>
          <div className="doc-list">
            {SOURCES.map((s) => (
              <div key={s.name} className="doc-row">
                <div className="doc-row-name">{s.name}</div>
                <div className="doc-row-detail">{s.detail}</div>
              </div>
            ))}
          </div>
        </section>

        <section className="doc-section">
          <h2>Methodology</h2>
          <div className="doc-list">
            {METHOD.map((m) => (
              <div key={m.h} className="doc-row">
                <div className="doc-row-name">{m.h}</div>
                <div className="doc-row-detail">{m.p}</div>
              </div>
            ))}
          </div>
        </section>

        <section className="doc-section">
          <h2>Accuracy &amp; disclaimer</h2>
          <div className="doc-disclaimer">
            <ul>
              <li>
                Consumer complaints are self-reported and are not verified by the FCC; they reflect
                who chooses to file, not a complete census of every problem.
              </li>
              <li>
                Index and normalized values are <strong>relative within this dataset</strong> —
                meaningful for comparing counties to one another, not as absolute national ratings.
              </li>
              <li>
                The data-center overlay is a <strong>spatial juxtaposition, not a causal claim</strong>:
                data centers do not provide residential broadband. It highlights where investment
                concentrates relative to access gaps.
              </li>
              <li>
                Figures reflect specific data vintages (broadband Dec 2025; ACS 2022) and may lag
                current conditions.
              </li>
              <li>
                Embedded dashboards are cached (~1 hour), so very recent edits or data refreshes may
                take time to appear.
              </li>
            </ul>
          </div>
        </section>
      </div>
    </div>
  );
}
