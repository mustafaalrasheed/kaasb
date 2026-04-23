import { expect, test } from "@playwright/test";

/**
 * Smoke: auth pages render with form fields and social-login buttons.
 * Does NOT submit credentials — that's a backend integration test.
 */
test.describe("Auth pages smoke", () => {
    test("/auth/login returns 200 and has email + password fields", async ({ page }) => {
        const response = await page.goto("/auth/login");
        expect(response?.status()).toBe(200);

        await expect(page.locator('input[type="email"]').first()).toBeVisible();
        await expect(page.locator('input[type="password"]').first()).toBeVisible();
    });

    test("/auth/login has link to registration", async ({ page }) => {
        await page.goto("/auth/login");
        await expect(page.locator('a[href="/auth/register"]').first()).toBeVisible();
    });

    test("/auth/register returns 200 and has the required fields", async ({ page }) => {
        const response = await page.goto("/auth/register");
        expect(response?.status()).toBe(200);

        // From register-client.tsx — stable id attributes.
        await expect(page.locator("#email")).toBeVisible();
        await expect(page.locator("#password")).toBeVisible();
    });

    test("/auth/forgot-password returns 200 and has email field", async ({ page }) => {
        const response = await page.goto("/auth/forgot-password");
        expect(response?.status()).toBe(200);

        await expect(page.locator('input[type="email"]').first()).toBeVisible();
    });

    test("/privacy returns 200 and is not a placeholder", async ({ page }) => {
        // The privacy page flags itself as "pending formal review" via a banner
        // during beta — until counsel signs off (launch plan Legal track A).
        // We're checking substance length, not banner presence, so the test
        // stays green after the banner is removed post-review.
        const response = await page.goto("/privacy");
        expect(response?.status()).toBe(200);

        const bodyText = await page.locator("main").innerText();
        // Real privacy page is 800+ lines; a placeholder would be <500 chars.
        expect(bodyText.length).toBeGreaterThan(2000);
    });

    test("/terms returns 200 and is not a placeholder", async ({ page }) => {
        const response = await page.goto("/terms");
        expect(response?.status()).toBe(200);

        const bodyText = await page.locator("main").innerText();
        expect(bodyText.length).toBeGreaterThan(2000);
    });
});
