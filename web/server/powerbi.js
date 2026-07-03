/**
 * Power BI Embedded — "app owns data" (service principal) flow.
 *
 *   1. Acquire an Azure AD token for the Power BI service using the service
 *      principal's client credentials (MSAL client-credentials grant).
 *   2. GET the report to retrieve its embedUrl + datasetId.
 *   3. POST GenerateToken to mint a short-lived embed token scoped to the report.
 *
 * Requires (in web/server/.env):
 *   AZURE_TENANT_ID, POWERBI_CLIENT_ID, POWERBI_CLIENT_SECRET,
 *   POWERBI_WORKSPACE_ID (the Power BI "group" / workspace id),
 *   POWERBI_REPORT_ID
 *
 * Prereqs on the Azure/Power BI side (see web/README.md):
 *   - Service principal allowed in the Power BI tenant settings.
 *   - The SP is a Member/Admin of the workspace holding the report.
 *   - Workspace is on Embedded / Premium / Fabric capacity for production embed.
 */
import { ConfidentialClientApplication } from "@azure/msal-node";

const POWERBI_API = "https://api.powerbi.com/v1.0/myorg";
const SCOPE = "https://analysis.windows.net/powerbi/api/.default";

export const REQUIRED_ENV = [
  "AZURE_TENANT_ID",
  "POWERBI_CLIENT_ID",
  "POWERBI_CLIENT_SECRET",
  "POWERBI_WORKSPACE_ID",
  "POWERBI_REPORT_ID",
];

export function missingEnv() {
  return REQUIRED_ENV.filter((k) => !process.env[k]);
}

let msalApp = null;
function getMsalApp() {
  if (msalApp) return msalApp;
  msalApp = new ConfidentialClientApplication({
    auth: {
      clientId: process.env.POWERBI_CLIENT_ID,
      authority: `https://login.microsoftonline.com/${process.env.AZURE_TENANT_ID}`,
      clientSecret: process.env.POWERBI_CLIENT_SECRET,
    },
  });
  return msalApp;
}

async function getAadToken() {
  const result = await getMsalApp().acquireTokenByClientCredential({ scopes: [SCOPE] });
  if (!result?.accessToken) throw new Error("Failed to acquire Azure AD token for Power BI.");
  return result.accessToken;
}

async function pbiGet(path, aadToken) {
  const res = await fetch(`${POWERBI_API}${path}`, {
    headers: { Authorization: `Bearer ${aadToken}` },
  });
  if (!res.ok) throw new Error(`Power BI GET ${path} -> ${res.status}: ${await res.text()}`);
  return res.json();
}

async function pbiPost(path, aadToken, body) {
  const res = await fetch(`${POWERBI_API}${path}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${aadToken}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Power BI POST ${path} -> ${res.status}: ${await res.text()}`);
  return res.json();
}

/**
 * Build the embed configuration the React client needs.
 * @returns {{embedUrl: string, embedToken: string, reportId: string, expiry: string}}
 */
export async function getEmbedConfig() {
  const workspaceId = process.env.POWERBI_WORKSPACE_ID;
  const reportId = process.env.POWERBI_REPORT_ID;

  const aadToken = await getAadToken();
  const report = await pbiGet(`/groups/${workspaceId}/reports/${reportId}`, aadToken);

  const tokenRes = await pbiPost(
    `/groups/${workspaceId}/reports/${reportId}/GenerateToken`,
    aadToken,
    { accessLevel: "View", datasetId: report.datasetId }
  );

  return {
    embedUrl: report.embedUrl,
    embedToken: tokenRes.token,
    reportId,
    expiry: tokenRes.expiration,
  };
}
