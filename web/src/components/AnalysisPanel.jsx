import { useEffect, useState } from "react";

// Fetch analysis.json once and share across all panels.
let _cache = null;
function loadAnalysis() {
  if (!_cache) {
    _cache = fetch(import.meta.env.BASE_URL + "analysis.json")
      .then((r) => (r.ok ? r.json() : null))
      .catch(() => null);
  }
  return _cache;
}

function SparkIcon() {
  return (
    <svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor" aria-hidden="true">
      <path d="M12 2l1.8 5.2L19 9l-5.2 1.8L12 16l-1.8-5.2L5 9l5.2-1.8L12 2z" />
      <path d="M19 14l.9 2.6L22.5 17.5l-2.6.9L19 21l-.9-2.6L15.5 17.5l2.6-.9L19 14z" opacity="0.6" />
    </svg>
  );
}

export default function AnalysisPanel({ pageKey }) {
  const [data, setData] = useState(undefined); // undefined = loading, null = none

  useEffect(() => {
    let alive = true;
    loadAnalysis().then((d) => alive && setData(d));
    return () => {
      alive = false;
    };
  }, []);

  if (data === undefined) {
    return (
      <section className="ai-panel">
        <div className="ai-head"><span className="ai-badge"><SparkIcon /> AI Analysis</span></div>
        <p className="ai-summary ai-muted">Loading analysis…</p>
      </section>
    );
  }
  const sec = data?.sections?.[pageKey];
  if (!sec) return null; // no analysis for this page (e.g., analysis.json not generated yet)

  return (
    <section className="ai-panel">
      <div className="ai-head">
        <span className="ai-badge"><SparkIcon /> AI Analysis</span>
        {data.demo && <span className="ai-demo">demo data</span>}
      </div>
      <p className="ai-summary">{sec.summary}</p>
      {Array.isArray(sec.callouts) && sec.callouts.length > 0 && (
        <ul className="ai-callouts">
          {sec.callouts.map((c, i) => (
            <li key={i}>{c}</li>
          ))}
        </ul>
      )}
      <div className="ai-foot">Automated analysis generated from the underlying county data.</div>
    </section>
  );
}
