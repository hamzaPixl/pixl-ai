import { defineConfig } from "vitest/config";

// @cloudflare/vitest-pool-workers requires a compatible wrangler version
// and does not yet support vitest 4.x. Using Node environment for unit
// testing pure TypeScript helpers and validation functions instead.
export default defineConfig({
  test: {
    environment: "node",
    include: ["tests/**/*.test.ts"],
  },
});
