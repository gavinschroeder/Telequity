function HomeIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M3 11.5 12 4l9 7.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M5 10v9h14v-9" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function InfoIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5" strokeLinecap="round" />
      <circle cx="12" cy="7.6" r="0.9" fill="currentColor" stroke="none" />
    </svg>
  );
}

export default function ReportRail({ pages, active, onSelect }) {
  return (
    <nav className="rail" aria-label="Navigation">
      <button
        className={`rail-nav ${active === "overview" ? "is-active" : ""}`}
        onClick={() => onSelect("overview")}
        aria-current={active === "overview" ? "page" : undefined}
      >
        <HomeIcon />
        <span>Overview</span>
      </button>

      <div className="rail-head">Dashboards</div>
      <ul className="rail-list">
        {pages.map((p, i) => {
          const isActive = p.key === active;
          return (
            <li key={p.key}>
              <button
                className={`rail-item ${isActive ? "is-active" : ""}`}
                onClick={() => onSelect(p.key)}
                aria-current={isActive ? "page" : undefined}
              >
                <span className="rail-index">{String(i + 1).padStart(2, "0")}</span>
                <span className="rail-text">
                  <span className="rail-label">{p.label}</span>
                  <span className="rail-blurb">{p.blurb}</span>
                </span>
              </button>
            </li>
          );
        })}
      </ul>

      <button
        className={`rail-nav rail-nav-bottom ${active === "about" ? "is-active" : ""}`}
        onClick={() => onSelect("about")}
        aria-current={active === "about" ? "page" : undefined}
      >
        <InfoIcon />
        <span>About &amp; Methodology</span>
      </button>
      <div className="rail-foot">Data: FCC · Census ACS · FCC Broadband Map · PNNL</div>
    </nav>
  );
}
