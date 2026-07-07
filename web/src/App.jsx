import { useEffect, useState } from "react";
import { PROJECT, REPORT_PAGES, EMBED_MODE, PUBLIC_EMBED_URL } from "./config";
import { fetchEmbedConfig } from "./api";
import Header from "./components/Header.jsx";
import ReportRail from "./components/ReportRail.jsx";
import ReportCanvas from "./components/ReportCanvas.jsx";
import PublicReportCanvas from "./components/PublicReportCanvas.jsx";
import IntroView from "./components/IntroView.jsx";
import AboutView from "./components/AboutView.jsx";

export default function App() {
  // active is "overview" (default landing), "about", or a report page key.
  const [active, setActive] = useState("overview");
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
    let alive = true;
    fetchEmbedConfig()
      .then((data) => alive && setEmbed({ status: "ready", data, error: null }))
      .catch((error) => alive && setEmbed({ status: error.code || "error", data: null, error }));
    return () => {
      alive = false;
    };
  }, [isPublic]);

  let main;
  if (active === "overview") {
    main = <IntroView pages={REPORT_PAGES} onOpen={setActive} />;
  } else if (active === "about") {
    main = <AboutView />;
  } else {
    const page = REPORT_PAGES.find((p) => p.key === active) ?? REPORT_PAGES[0];
    main = isPublic ? (
      <PublicReportCanvas url={PUBLIC_EMBED_URL} page={page} />
    ) : (
      <ReportCanvas embed={embed} page={page} />
    );
  }

  return (
    <div className="app">
      <Header project={PROJECT} embedStatus={embed.status} />
      <div className="layout">
        <ReportRail pages={REPORT_PAGES} active={active} onSelect={setActive} />
        <main className="canvas-wrap">{main}</main>
      </div>
    </div>
  );
}
