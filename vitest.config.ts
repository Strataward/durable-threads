import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: [
      "packages/**/*.test.ts",
      "apps/api/tests/**/*.test.ts",
      "apps/worker/tests/**/*.test.ts",
      "apps/web/src/**/*.test.ts",
    ],
    exclude: ["**/node_modules/**", "**/dist/**"],
    environment: "node",
    testTimeout: 60_000,
    hookTimeout: 60_000,
  },
});
