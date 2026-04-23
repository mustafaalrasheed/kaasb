import { defineConfig, devices } from "@playwright/test";

/**
 * Kaasb Playwright smoke test configuration.
 *
 * These run against the live production site (https://kaasb.com) by default.
 * They're read-only page-load + critical-selector checks — do NOT place tests
 * here that create data, submit forms, or modify state. For flows that need
 * full isolation (register → order → dispute), use backend integration tests
 * in `backend/tests/integration/` or a future staging environment.
 *
 * Local override:
 *   BASE_URL=http://localhost:3000 npm run test:smoke
 *
 * CI: set BASE_URL in the workflow; default is production.
 */
export default defineConfig({
    testDir: "./tests/e2e",

    // Fail the CI if you accidentally left test.only in the source code.
    forbidOnly: !!process.env.CI,

    // Retries only in CI — locally, a failing test should surface immediately.
    retries: process.env.CI ? 2 : 0,

    // Limit parallelism on hosted runners; local can go wider.
    workers: process.env.CI ? 2 : undefined,

    // Reporters: stdout for humans, JUnit XML for CI result parsing.
    reporter: process.env.CI
        ? [["github"], ["junit", { outputFile: "playwright-results.xml" }]]
        : [["list"]],

    use: {
        baseURL: process.env.BASE_URL || "https://kaasb.com",
        trace: "on-first-retry",
        screenshot: "only-on-failure",

        // Iraqi primary audience — AR RTL default. Tests override per-case.
        locale: "ar-IQ",
        timezoneId: "Asia/Baghdad",

        // Be polite to production — don't hammer.
        actionTimeout: 10_000,
        navigationTimeout: 30_000,
    },

    // Chromium-only for smoke. Cross-browser costs more than it's worth until
    // we have a real browser-compat regression.
    projects: [
        {
            name: "chromium",
            use: { ...devices["Desktop Chrome"] },
        },
    ],
});
