import StateCard from "./StateCard.jsx";
import AnalysisPanel from "./AnalysisPanel.jsx";
import ColorLegend from "./ColorLegend.jsx";
import { EQUITY_LEGEND } from "../config";

/**
 * Public ("Publish to web") embed. Renders the report as a plain iframe — no
 * token, no backend. Page navigation appends &pageName=... when configured;
 * otherwise the report's own page tabs handle it.
 */
export default function PublicReportCanvas({ url, page }) {
  if (!url) {
    return (
      <StateCard
        tone="warn"
        title="Report not linked yet"
        body="Publish the report with 'Publish to web (public)', paste the embed link into web/.env as VITE_PUBLISH_TO_WEB_URL, then restart the dev server. Steps are in web/README.md."
      />
    );
  }

  const src = page?.pageName
    ? `${url}${url.includes("?") ? "&" : "?"}pageName=${encodeURIComponent(page.pageName)}`
    : url;

  return (
    <div className="report-shell">
      <div className="report-titlebar">
        <h2>{page.label}</h2>
        <p>{page.blurb}</p>
      </div>
      {page.legend === "equity" && <ColorLegend legend={EQUITY_LEGEND} />}
      <div className="report-frame">
        <iframe
          title={page.label}
          src={src}
          className="pbi-embed"
          allowFullScreen
        />
      </div>
      <AnalysisPanel pageKey={page.key} />
    </div>
  );
}
