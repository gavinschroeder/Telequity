// Project console configuration.
//
// `REPORT_PAGES` mirrors the 7 report pages described in
// powerbi/POWERBI_GUIDE.md. `pageName` is the *internal* Power BI page name
// (e.g. "ReportSection2b3c..."), which only exists once you build & publish the
// .pbix. Fill those in then; until then the rail still renders and the embedded
// report's own page tabs remain usable.

export const PROJECT = {
  name: "Telequity",
  tagline: "Reported vs. experienced digital access — overlaid on infrastructure.",
  pilot: "United States · county-level",
};

// The report pages that exist in Power BI. `pageName` is the page's internal
// id — the string after the report id in its URL (…/reports/<id>/<pageName>).
// Each rail item deep-links the embedded report to its page via &pageName=.
export const REPORT_PAGES = [
  {
    key: "mismatch",
    label: "Access Mismatch",
    blurb: "Counties where data-center presence meets the worst access.",
    pageName: "dcfb48bafb9eb4c1d776",
  },
  {
    key: "avail-vs-friction",
    label: "Availability vs. Friction",
    blurb: "Where broadband exists on paper but complaints run high.",
    pageName: "f196709460b38709f775",
  },
  {
    key: "categories",
    label: "Complaint Volume by Category",
    blurb: "Complaint mix — internet, wireless, billing, robocalls, accessibility.",
    pageName: "eaf9a3ca846e85c36f6b",
  },
  {
    key: "equity-map",
    label: "Equity Index Map",
    blurb: "Digital Equity Exposure Index by county — the national picture.",
    pageName: "952fed3444d3b0ea1416",
  },
  {
    key: "datacenter-map",
    label: "Data-Center Map",
    blurb: "U.S. data-center locations over the access surface.",
    pageName: "d036e92ea6347516d1ac",
  },
];

// Embedding mode:
//   "public" (default) — Publish to web. A plain public iframe; no backend,
//                        no Azure. Best for this public-data portfolio project.
//   "secure"          — service-principal token backend in web/server.
export const EMBED_MODE = import.meta.env.VITE_EMBED_MODE || "public";

// Publish-to-web embed URL. In Power BI: File → Embed report → Publish to web
// (public). Paste the link (looks like https://app.powerbi.com/view?r=...) into
// web/.env as VITE_PUBLISH_TO_WEB_URL, then restart `npm run dev`.
export const PUBLIC_EMBED_URL = import.meta.env.VITE_PUBLISH_TO_WEB_URL || "";

// Backend endpoint that mints the Power BI embed token (used only in "secure" mode).
export const EMBED_TOKEN_ENDPOINT =
  import.meta.env.VITE_EMBED_ENDPOINT || "/api/embed-token";
