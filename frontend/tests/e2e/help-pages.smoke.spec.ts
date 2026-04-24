import { expect, test } from "@playwright/test";

/**
 * Smoke: the three help/content pages shipped in Phase 7 load cleanly
 * with their required SEO artifacts. These live against production, so
 * failures indicate a user-visible regression, not a dev-environment
 * hiccup.
 */
test.describe("Help / FAQ / How-it-works pages smoke", () => {
    test("/help returns 200 and publishes the SLA commitment", async ({ page }) => {
        const response = await page.goto("/help");
        expect(response?.status()).toBe(200);

        // SLA numbers are load-bearing promises to users — catch it if
        // they ever silently disappear.
        await expect(page.locator("main")).toContainText("8h");
        await expect(page.locator("main")).toContainText("48h");
    });

    test("/faq returns 200 and emits FAQPage JSON-LD", async ({ page }) => {
        const response = await page.goto("/faq");
        expect(response?.status()).toBe(200);

        // FAQPage schema is what enables Google rich-result snippets.
        // Stripping it by accident would silently cost traffic.
        const ldJson = await page
            .locator('script[type="application/ld+json"]')
            .filter({ hasText: "FAQPage" })
            .first()
            .textContent();
        expect(ldJson).toBeTruthy();
        expect(ldJson!).toContain("FAQPage");
    });

    test("/how-it-works returns 200 and has both client + freelancer sections", async ({ page }) => {
        const response = await page.goto("/how-it-works");
        expect(response?.status()).toBe(200);

        // Anchor IDs are referenced from /help and external links — they
        // are API surface, not internal implementation.
        await expect(page.locator("#clients")).toBeVisible();
        await expect(page.locator("#freelancers")).toBeVisible();
    });

    // NOTE: The homepage-footer-link test lives in a follow-up commit that
    // lands AFTER the corresponding footer edit deploys to kaasb.com.
    // Playwright runs against live prod, so asserting on a footer edit
    // before its own deploy has shipped would fail the very push that
    // introduces it.
});
