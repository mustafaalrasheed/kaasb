import { expect, test } from "@playwright/test";

/**
 * Smoke: the three help/content pages shipped in Phase 7 load cleanly
 * with their required SEO artifacts. These live against production, so
 * failures indicate a user-visible regression, not a dev-environment
 * hiccup.
 *
 * Selectors intentionally go through document-level text / raw HTML
 * rather than `<main>` — layout.tsx already wraps children in its own
 * `<main>`, so inner page `<main>` elements resolve ambiguously under
 * Playwright strict mode.
 */
test.describe("Help / FAQ / How-it-works pages smoke", () => {
    test("/help returns 200 and publishes the SLA commitment", async ({ page }) => {
        const response = await page.goto("/help");
        expect(response?.status()).toBe(200);

        // SLA numbers are load-bearing promises to users — catch it if
        // they ever silently disappear. body-level text search avoids
        // the nested-<main> strict-mode conflict.
        await expect(page.locator("body")).toContainText("8h");
        await expect(page.locator("body")).toContainText("48h");
    });

    test("/faq returns 200 and emits FAQPage JSON-LD", async ({ page }) => {
        const response = await page.goto("/faq");
        expect(response?.status()).toBe(200);

        // FAQPage schema is what enables Google rich-result snippets.
        // Read all JSON-LD blocks and check any of them is an FAQPage —
        // tolerant to other schemas on the page (Organization, Website).
        const scripts = await page
            .locator('script[type="application/ld+json"]')
            .allTextContents();
        expect(scripts.length).toBeGreaterThan(0);
        const hasFaqPage = scripts.some((s) => s.includes('"@type":"FAQPage"') || s.includes('"@type": "FAQPage"'));
        expect(hasFaqPage).toBe(true);
    });

    test("/how-it-works returns 200 and has both client + freelancer sections", async ({ page }) => {
        const response = await page.goto("/how-it-works");
        expect(response?.status()).toBe(200);

        // Anchor IDs are referenced from /help and external links — they
        // are API surface, not internal implementation.
        await expect(page.locator("#clients")).toBeVisible();
        await expect(page.locator("#freelancers")).toBeVisible();
    });

    test("homepage footer links to all three content pages", async ({ page }) => {
        await page.goto("/");

        // These are the links wired in db14e1f's layout.tsx footer update.
        // Using `.first()` because the header nav may also link to /help
        // on mobile screens, and we only need to assert the footer link
        // exists somewhere visible.
        await expect(page.locator('a[href="/help"]').first()).toBeVisible();
        await expect(page.locator('a[href="/faq"]').first()).toBeVisible();
        await expect(page.locator('a[href="/how-it-works"]').first()).toBeVisible();
    });
});
