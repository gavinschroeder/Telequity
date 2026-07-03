export default function ReportRail({ pages, activeKey, onSelect }) {
  return (
    <nav className="rail" aria-label="Report pages">
      <div className="rail-head">Dashboards</div>
      <ul className="rail-list">
        {pages.map((p, i) => {
          const active = p.key === activeKey;
          return (
            <li key={p.key}>
              <button
                className={`rail-item ${active ? "is-active" : ""}`}
                onClick={() => onSelect(p.key)}
                aria-current={active ? "page" : undefined}
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
      <div className="rail-foot">
        Data: FCC · Census ACS · FCC Broadband Map · PNNL / LBNL
      </div>
    </nav>
  );
}
