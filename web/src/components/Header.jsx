const STATUS_META = {
  loading: { label: "Connecting", tone: "neutral" },
  ready: { label: "Report live", tone: "good" },
  not_configured: { label: "Awaiting Power BI setup", tone: "warn" },
  unreachable: { label: "Backend offline", tone: "bad" },
  error: { label: "Embed error", tone: "bad" },
};

export default function Header({ project, embedStatus }) {
  const meta = STATUS_META[embedStatus] ?? STATUS_META.error;
  return (
    <header className="header">
      <div className="brand">
        <span className="brand-mark" aria-hidden="true">
          {/* signal-tower glyph: the "tele" in Telequity */}
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.8">
            <path d="M12 13.5v7.5" strokeLinecap="round" />
            <circle cx="12" cy="11" r="2" fill="currentColor" stroke="none" />
            <path d="M7.5 6.5a6 6 0 0 0 0 9M16.5 6.5a6 6 0 0 1 0 9" strokeLinecap="round" />
            <path d="M4.7 3.8a10 10 0 0 0 0 14.4M19.3 3.8a10 10 0 0 1 0 14.4" strokeLinecap="round" opacity="0.55" />
          </svg>
        </span>
        <div className="brand-text">
          <h1>{project.name}</h1>
        </div>
      </div>
      <div className="header-right">
        <span className="pilot-pill">{project.pilot}</span>
        <span className={`status-chip status-${meta.tone}`}>
          <span className="status-dot" />
          {meta.label}
        </span>
      </div>
    </header>
  );
}
