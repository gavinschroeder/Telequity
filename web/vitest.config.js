import { defineConfig } from "vitest/config";

// Lightweight unit tests for pure logic (config integrity, embed API).
// Component-render tests are intentionally omitted to keep the toolchain slim.
export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.test.{js,jsx}"],
  },
});
