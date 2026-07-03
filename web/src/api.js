import { EMBED_TOKEN_ENDPOINT } from "./config";

/**
 * Fetch a Power BI embed configuration from the token backend.
 *
 * Returns: { embedUrl, embedToken, reportId, expiry }
 * Throws an Error with a `.code` of:
 *   - "not_configured" : backend reachable but Azure creds/report not set (501)
 *   - "unreachable"    : backend not running / network error
 *   - "error"          : other backend failure
 */
export async function fetchEmbedConfig() {
  let res;
  try {
    res = await fetch(EMBED_TOKEN_ENDPOINT, { headers: { Accept: "application/json" } });
  } catch (e) {
    const err = new Error("Token backend is unreachable. Start it with `npm run server`.");
    err.code = "unreachable";
    throw err;
  }

  if (res.status === 501) {
    const body = await safeJson(res);
    const err = new Error(body?.message || "Power BI embed is not configured yet.");
    err.code = "not_configured";
    err.detail = body?.missing;
    throw err;
  }

  if (!res.ok) {
    const body = await safeJson(res);
    const err = new Error(body?.message || `Backend error (${res.status}).`);
    err.code = "error";
    throw err;
  }

  return res.json();
}

async function safeJson(res) {
  try {
    return await res.json();
  } catch {
    return null;
  }
}
