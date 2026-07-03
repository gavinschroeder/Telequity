import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import { getEmbedConfig, missingEnv } from "./powerbi.js";

dotenv.config();

const app = express();
app.use(cors());

app.get("/api/health", (_req, res) => {
  res.json({ ok: true, configured: missingEnv().length === 0 });
});

/**
 * GET /api/embed-token
 *   200 -> { embedUrl, embedToken, reportId, expiry }
 *   501 -> { message, missing: [...] }   (Azure creds / report not set yet)
 *   500 -> { message }                    (Power BI / Azure call failed)
 */
app.get("/api/embed-token", async (_req, res) => {
  const missing = missingEnv();
  if (missing.length) {
    return res.status(501).json({
      message:
        "Power BI embed is not configured. Set the missing values in web/server/.env.",
      missing,
    });
  }
  try {
    const config = await getEmbedConfig();
    res.set("Cache-Control", "no-store");
    res.json(config);
  } catch (err) {
    console.error("embed-token error:", err);
    res.status(500).json({ message: err.message || "Failed to generate embed token." });
  }
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  const ready = missingEnv().length === 0;
  console.log(`Telequity embed-token server on :${PORT}`);
  console.log(
    ready
      ? "  Azure config detected — /api/embed-token will mint live tokens."
      : "  Not yet configured — fill web/server/.env (see web/README.md)."
  );
});
