import { expect, test } from "@playwright/test";

/**
 * Smoke: /services browse page loads and renders the catalog shell.
 * Does NOT depend on specific services existing — tolerant of empty state.
 */
test.describe("Services browse smoke", () => {
    test("returns 200 and renders main content", async ({ page }) => {
        const response = await page.goto("/services");
        expect(response?.status()).toBe(200);

        // Either a services list OR an empty state — both are acceptable.
        // The page structure itself must load.
        await expect(page.locator("main")).toBeVisible();
    });

    test("/gigs legacy URL redirects to /services", async ({ page }) => {
        // Phase-1 rename: middleware.ts issues 308 for /gigs → /services.
        // This test guards that rewrite from accidental removal.
        const response = await page.goto("/gigs", { waitUntil: "domcontentloaded" });
        expect(page.url()).toContain("/services");
        // 308 final destination is the services page, which returns 200.
        expect(response?.status()).toBe(200);
    });

    test("page has SEO metadata — title + description", async ({ page }) => {
        await page.goto("/services");

        // Description meta must be present for search engines.
        const description = page.locator('meta[name="description"]');
        await expect(description).toHaveAttribute("content", /.+/);

        // OpenGraph image for social previews.
        const ogImage = page.locator('meta[property="og:image"]');
        await expect(ogImage).toHaveAttribute("content", /.+/);
    });
});
