import { describe, it, expect } from "vitest";
import { REPORT_PAGES, EQUITY_LEGEND, PROJECT } from "./config.js";

describe("report pages", () => {
  it("defines 5 pages with unique keys and valid Power BI page IDs", () => {
    expect(REPORT_PAGES).toHaveLength(5);
    const keys = REPORT_PAGES.map((p) => p.key);
    expect(new Set(keys).size).toBe(5);
    for (const p of REPORT_PAGES) {
      expect(p.pageName).toMatch(/^[a-f0-9]{20}$/); // 20-char report-section id
      expect(p.label.length).toBeGreaterThan(0);
      expect(p.blurb.length).toBeGreaterThan(0);
    }
  });

  it("flags exactly the two map pages for the equity legend", () => {
    const legendPages = REPORT_PAGES.filter((p) => p.legend === "equity").map((p) => p.key);
    expect(legendPages.sort()).toEqual(["datacenter-map", "equity-map"]);
  });
});

describe("equity legend", () => {
  it("has a caption and four color tiers with hex + range + label", () => {
    expect(EQUITY_LEGEND.caption).toBeTruthy();
    expect(EQUITY_LEGEND.tiers).toHaveLength(4);
    for (const t of EQUITY_LEGEND.tiers) {
      expect(t.color).toMatch(/^#[0-9a-f]{6}$/i);
      expect(t.range).toBeTruthy();
      expect(t.label).toBeTruthy();
    }
  });
});

describe("project meta", () => {
  it("has a name", () => {
    expect(PROJECT.name).toBe("Telequity");
  });
});
