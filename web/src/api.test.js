import { describe, it, expect, vi, afterEach } from "vitest";
import { fetchEmbedConfig } from "./api.js";

afterEach(() => vi.restoreAllMocks());

describe("fetchEmbedConfig (secure-mode embed API)", () => {
  it("maps HTTP 501 to a 'not_configured' error with the missing list", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      status: 501,
      ok: false,
      json: async () => ({ message: "not set", missing: ["AZURE_TENANT_ID"] }),
    });
    await expect(fetchEmbedConfig()).rejects.toMatchObject({
      code: "not_configured",
      detail: ["AZURE_TENANT_ID"],
    });
  });

  it("maps a network failure to 'unreachable'", async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error("boom"));
    await expect(fetchEmbedConfig()).rejects.toMatchObject({ code: "unreachable" });
  });

  it("returns the embed config on success", async () => {
    const cfg = { embedUrl: "u", embedToken: "t", reportId: "r", expiry: "z" };
    global.fetch = vi.fn().mockResolvedValue({ status: 200, ok: true, json: async () => cfg });
    await expect(fetchEmbedConfig()).resolves.toEqual(cfg);
  });
});
