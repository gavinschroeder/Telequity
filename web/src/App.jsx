import { useEffect, useState } from "react";
import { PROJECT, REPORT_PAGES, EMBED_MODE, PUBLIC_EMBED_URL } from "./config";
import { fetchEmbedConfig } from "./api";
import Header from "./components/Header.jsx";
import ReportRail from "./components/ReportRail.jsx";
import ReportCanvas from "./components/ReportCanvas.jsx";
import PublicReportCanvas from "./components/PublicReportCanvas.jsx";

export default function App() {
  const [activeKey, setActiveKey] = useState(REPORT_PAGES[0].key);
  const [embed, setEmbed] = useState({ status: "loading", data: null, error: null });

  const isPublic = EMBED_MODE === "public";

  useEffect(() => {
    // Public (Publish to web) mode needs no token call — it's a plain iframe.
    if (isPublic) {
      setEmbed({
        status: PUBLIC_EMBED_URL ? "ready" : "not_configured",
        data: null,
        error: null,
      });
      return;
    }
    // Secure mode: fetch an embed token from the backend.
    let alive = true;
    fetchEmbedConfig()
      .then((data) => alive && setEmbed({ status: "ready", data, error: null }))
      .catch((error) => alive && setEmbed({ status: error.code || "error", data: null, error }));
    return () => {
      alive = false;
    };
  }, [isPublic]);

  const activePage = REPORT_PAGES.find((p) => p.key === activeKey) ?? REPORT_PAGES[0];

  return (
    <div className="app">
      <Header project={PROJECT} embedStatus={embed.status} />
      <div className="layout">
        <ReportRail pages={REPORT_PAGES} activeKey={activeKey} onSelect={setActiveKey} />
        <main className="canvas-wrap">
          {isPublic ? (
            <PublicReportCanvas url={PUBLIC_EMBED_URL} page={activePage} />
          ) : (
            <ReportCanvas embed={embed} page={activePage} />
          )}
        </main>
      </div>
    </div>
  );
}
