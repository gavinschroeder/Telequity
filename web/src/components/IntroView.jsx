// 1–2 sentence description of each dashboard, keyed by its page key.
const DASHBOARD_COPY = {
  mismatch:
    "Ranks counties by where data-center presence collides with the weakest consumer access. It surfaces the places absorbing new digital infrastructure while their residents report the most service friction.",
  "avail-vs-friction":
    "Plots each county's broadband availability gap against how often residents actually complain. Counties high on both axes are where service exists on paper but performs poorly in practice.",
  categories:
    "Breaks the national complaint record into categories — internet, wireless, billing, robocalls, accessibility. It shows what consumers are struggling with most.",
  "equity-map":
    "A choropleth of the Digital Equity Exposure Index for every U.S. county. Darker counties carry more combined risk: worse availability, more friction, and greater socioeconomic vulnerability.",
  "datacenter-map":
    "Maps individual U.S. data-center locations, colored by the access level of the county they sit in — revealing where compute is concentrating relative to digital-access gaps.",
};

export default function IntroView({ pages, onOpen }) {
  return (
    <div className="doc">
      <div className="doc-inner">
        <p className="doc-eyebrow">Digital Equity Intelligence · United States</p>
        <h1 className="doc-title">Where reported access and lived access diverge — and who's left behind.</h1>
        <p className="doc-lede">
          Telequity measures the gap between the broadband that providers report as
          <em> available</em> and the service Americans actually <em>experience</em>, county
          by county — then overlays it against where energy- and land-intensive data centers
          are being built.
        </p>

        <section className="doc-section">
          <h2>The problem</h2>
          <p>
            In much of the country broadband is treated as a solved problem, yet the distance
            between "available" and "usable" remains wide — and it falls hardest on rural and
            lower-income communities. At the same time, data centers are being sited across the
            nation, frequently in the very places whose residents report the worst connectivity.
            These two stories are rarely told on the same map.
          </p>
          <p className="doc-mission">
            <strong>Our mission:</strong> make the geography of digital equity visible and
            accountable — combining consumer complaints, broadband availability, socioeconomic
            context, and infrastructure siting into one county-level picture that anyone can read.
          </p>
        </section>

        <section className="doc-section">
          <h2>What's inside</h2>
          <div className="doc-grid">
            {pages.map((p, i) => (
              <button key={p.key} className="doc-card" onClick={() => onOpen(p.key)}>
                <span className="doc-card-index">{String(i + 1).padStart(2, "0")}</span>
                <span className="doc-card-title">{p.label}</span>
                <span className="doc-card-body">{DASHBOARD_COPY[p.key] ?? p.blurb}</span>
                <span className="doc-card-cta">Open →</span>
              </button>
            ))}
          </div>
        </section>

        <section className="doc-section">
          <h2>Getting around</h2>
          <p>
            Use the left rail to move between the five dashboards. Each is interactive — hover a
            county, bar, or point for details, and use a chart's built-in filters to focus on a
            state or category. Return here anytime via <strong>Overview</strong>, and open
            <strong> About &amp; Methodology</strong> for the data sources, how each metric is
            built, and important accuracy notes.
          </p>
          <div className="doc-actions">
            <button className="doc-btn" onClick={() => onOpen(pages[0].key)}>
              Open the first dashboard →
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}
