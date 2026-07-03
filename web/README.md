# Telequity — Project Console (web)

A React + Vite app that hosts the Telequity Power BI dashboards. The page is a
clean shell: a header status strip, a left rail for the seven report pages, and
an embed canvas. Until a report is linked it shows a clear "not configured yet"
state instead of breaking.

It supports **two embedding modes** (set `VITE_EMBED_MODE` in `web/.env`):

- **`public`** *(default)* — **Publish to web**. A plain public iframe. No
  backend, no Azure. Free forever. Best for this project since the data is
  public FCC/Census. The report is publicly viewable (no sign-in / no
  row-level security).
- **`secure`** — **Power BI Embedded** via the service-principal token backend
  in `web/server/`. Auth + row-level security, but needs paid Fabric capacity
  (or a trial). Use this only if you need private, gated dashboards.

```
web/
├── index.html            # Vite entry
├── src/
│   ├── App.jsx           # shell + embed-config fetch
│   ├── config.js         # project meta + the 7 report pages
│   ├── api.js            # calls the token backend
│   ├── components/       # Header, ReportRail, ReportCanvas, StateCard
│   └── styles.css        # the design system
└── server/               # Express token backend (mints embed tokens)
    ├── index.js
    └── powerbi.js
```

## Why a backend?

A browser can't safely hold the Azure client secret, and Power BI embed tokens
must be minted server-side. The Express server authenticates a service principal
and returns a short-lived embed token to the React app.

```
React app  ──GET /api/embed-token──►  Express server  ──MSAL──►  Azure AD
   ▲                                        │                       │
   └────────  { embedUrl, embedToken } ◄─────┴──Power BI REST◄──────┘
```

## Run it locally

### Public mode (default — no backend needed)

```bash
cd web && npm install
npm run dev          # React dev server on :5173
```

Open http://localhost:5173. Until you set `VITE_PUBLISH_TO_WEB_URL`, you'll see
the "Report not linked yet" card — that's expected. Once you paste your
Publish-to-web link into `web/.env` and restart, the dashboards load.

### Secure mode (optional — service principal)

```bash
cd web && npm install
cd server && npm install && cd ..
# set VITE_EMBED_MODE=secure in web/.env, then:
npm run server       # terminal 1 — token backend (:3001)
npm run dev          # terminal 2 — React app (:5173)
```

Build for production: `npm run build` (output in `web/dist/`).

## Publish to web (default, free)

1. **Get a Power BI–capable account.** Power BI needs a *work/school* Microsoft
   account — a personal Gmail won't sign in. If you don't have one, the cheapest
   path is a Microsoft 365 Business Basic trial (creates a `you@…onmicrosoft.com`
   account). See the chat steps / `../SETUP.md` notes.
2. **Build & publish the report** to the Power BI Service (Mac-friendly path:
   upload the gold CSVs at app.powerbi.com → build the report in the browser).
3. In the report: **File → Embed report → Publish to web (public)**. Confirm,
   then copy the **link** (`https://app.powerbi.com/view?r=…`).
   - If the option is greyed out, enable it in the Admin portal → Tenant settings
     → "Publish to web". (Microsoft disables it by default in 2026.)
4. Put it in `web/.env`:
   ```
   VITE_EMBED_MODE=public
   VITE_PUBLISH_TO_WEB_URL=https://app.powerbi.com/view?r=...
   ```
5. Restart `npm run dev`. The dashboards now load in the page.

> Optional: to drive the left rail's per-page navigation, fill each
> `REPORT_PAGES[].pageName` in `src/config.js` with the report's internal page
> names. Otherwise the embedded report's own page tabs handle navigation.

## Configure Power BI Embedded (secure mode — optional)

You need an Azure AD **service principal**, a Power BI **workspace** containing
the published report, and that workspace on **Embedded/Premium/Fabric capacity**
for production embedding.

1. **Build & publish the report.** Create the `.pbix` per `../powerbi/POWERBI_GUIDE.md`,
   publish it to a Power BI workspace. Note the **workspace (group) ID** and
   **report ID** from the report URL.
2. **Register an Azure AD app** (Entra ID → App registrations). Note the
   **Application (client) ID** and **Directory (tenant) ID**; create a **client
   secret**.
3. **Enable service principals in Power BI** (Admin portal → Tenant settings →
   "Allow service principals to use Power BI APIs"), and add the SP to a security
   group if your tenant scopes it that way.
4. **Add the SP to the workspace** as Member or Admin.
5. **Assign capacity** to the workspace (Power BI Embedded A-SKU, Premium, or
   Fabric) for non-trial embedding.
6. **Fill `web/server/.env`** (copy from `.env.example`):
   `AZURE_TENANT_ID`, `POWERBI_CLIENT_ID`, `POWERBI_CLIENT_SECRET`,
   `POWERBI_WORKSPACE_ID`, `POWERBI_REPORT_ID`.
7. Restart `npm run server` and refresh — the report embeds.

### Wiring the rail to report pages
Once published, each Power BI page has an internal name (e.g.
`ReportSection0a1b…`). Put those in `src/config.js` → `REPORT_PAGES[].pageName`
so the left rail drives in-report navigation. Until then the rail is cosmetic and
Power BI's own page tabs handle navigation.

## Notes
- Embed tokens are short-lived. For long sessions, refresh by re-calling
  `/api/embed-token` before `expiry` (hook point is in `src/api.js`).
- `.env` files are git-ignored. Never commit secrets.
- Mac users: building the `.pbix` needs Power BI Desktop (Windows) or the Power
  BI Service — only the *publish* step touches Windows; this web app is platform
  agnostic.
