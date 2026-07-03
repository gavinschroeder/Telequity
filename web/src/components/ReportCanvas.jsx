import { useEffect, useRef } from "react";
import { PowerBIEmbed } from "powerbi-client-react";
import { models } from "powerbi-client";
import StateCard from "./StateCard.jsx";

export default function ReportCanvas({ embed, page }) {
  const reportRef = useRef(null);

  // When the selected dashboard changes, navigate the embedded report to the
  // matching Power BI page (only possible once a pageName is configured).
  useEffect(() => {
    const report = reportRef.current;
    if (report && page?.pageName) {
      report.setPage(page.pageName).catch(() => {
        /* page name not found yet — harmless until the .pbix is published */
      });
    }
  }, [page]);

  if (embed.status === "loading") {
    return <StateCard tone="neutral" title="Connecting to Power BI…" spinner />;
  }

  if (embed.status === "unreachable") {
    return (
      <StateCard
        tone="bad"
        title="Token backend is offline"
        body="The embed-token service isn't responding. Start it locally with:"
        code="cd web && npm run server"
      />
    );
  }

  if (embed.status === "not_configured") {
    return (
      <StateCard
        tone="warn"
        title="Power BI embed not configured yet"
        body={
          embed.error?.detail
            ? `Backend is running, but these values are missing: ${embed.error.detail.join(", ")}. Fill them in web/server/.env, then publish the report.`
            : "Add your Azure service-principal credentials and report IDs to web/server/.env, then refresh. See web/README.md."
        }
      />
    );
  }

  if (embed.status !== "ready" || !embed.data) {
    return (
      <StateCard
        tone="bad"
        title="Couldn't load the report"
        body={embed.error?.message || "Unknown embed error."}
      />
    );
  }

  const { embedUrl, embedToken, reportId } = embed.data;

  return (
    <div className="report-shell">
      <div className="report-titlebar">
        <h2>{page.label}</h2>
        <p>{page.blurb}</p>
      </div>
      <div className="report-frame">
        <PowerBIEmbed
          embedConfig={{
            type: "report",
            id: reportId,
            embedUrl,
            accessToken: embedToken,
            tokenType: models.TokenType.Embed,
            settings: {
              panes: {
                filters: { visible: false },
                pageNavigation: { visible: true },
              },
              background: models.BackgroundType.Transparent,
            },
          }}
          eventHandlers={
            new Map([
              ["loaded", () => {}],
              ["error", (event) => console.error("Power BI error:", event?.detail)],
            ])
          }
          cssClassName="pbi-embed"
          getEmbeddedComponent={(embedded) => {
            reportRef.current = embedded;
          }}
        />
      </div>
    </div>
  );
}
