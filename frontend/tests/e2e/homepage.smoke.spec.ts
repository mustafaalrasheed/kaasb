import { expect, test } from "@playwright/test";

/**
 * Smoke: homepage loads and renders the expected hero + nav.
 * These are read-only checks — they do not submit forms or create data.
 */
test.describe("Home page smoke", () => {
    test("returns 200 and renders hero (Arabic default)", async ({ page }) => {
        const response = await page.goto("/");
        expect(response?.status()).toBe(200);

        // Arabic-first locale means the page title is Arabic.
        await expect(page).toHaveTitle(/كاسب/);

        // There should be exactly one h1 — the hero heading. We don't match
        // on its text (bilingual + may be edited) but its presence is load-bearing
        // for SEO + accessibility.
        await expect(page.locator("h1")).toHaveCount(1);

        // Document must declare RTL at root (i18n regression catcher).
        await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    });

    test("has primary nav with services, freelancers, jobs links", async ({ page }) => {
        await page.goto("/");

        // Nav links use href attributes that are stable across layout changes.
        await expect(page.locator('a[href="/services"]').first()).toBeVisible();
        await expect(page.locator('a[href="/freelancers"]').first()).toBeVisible();
        await expect(page.locator('a[href="/jobs"]').first()).toBeVisible();
    });

    test("footer has legal links", async ({ page }) => {
        await page.goto("/");

        await expect(page.locator('a[href="/privacy"]').first()).toBeVisible();
        await expect(page.locator('a[href="/terms"]').first()).toBeVisible();
    });

    test("FAQ JSON-LD structured data present", async ({ page }) => {
        await page.goto("/");

        // SEO regression catcher: JSON-LD must be in the HTML even after
        // client hydration. application/ld+json script tags are server-rendered.
        const ldJson = page.locator('script[type="application/ld+json"]');
        await expect(ldJson.first()).toBeAttached();
    });
});
