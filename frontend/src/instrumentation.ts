/**
 * Kaasb Platform - Next.js Instrumentation (Sentry)
 *
 * This file is loaded automatically by Next.js for both server and edge runtimes.
 * It initialises Sentry before any application code runs.
 *
 * Required env vars (set in .env.local or Vercel/Docker):
 *   NEXT_PUBLIC_SENTRY_DSN      — Sentry project DSN
 *   NEXT_PUBLIC_APP_VERSION     — Current release version (e.g. "0.1.0")
 *   NEXT_PUBLIC_ENVIRONMENT     — "development" | "staging" | "production"
 *
 * To install: npm install @sentry/nextjs
 * Then add to next.config.ts:
 *   import { withSentryConfig } from '@sentry/nextjs';
 *   export default withSentryConfig(nextConfig, { silent: true, org: "...", project: "..." });
 */

export async function register() {
  const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
  if (!dsn) return; // Sentry disabled — no DSN configured

  if (process.env.NEXT_RUNTIME === "nodejs") {
    // Server-side (Node.js) Sentry — handles API route errors, SSR errors
    const Sentry = await import("@sentry/nextjs");

    Sentry.init({
      dsn,
      environment: process.env.NEXT_PUBLIC_ENVIRONMENT ?? "development",
      release:     `kaasb@${process.env.NEXT_PUBLIC_APP_VERSION ?? "unknown"}`,

      // Send 100% of errors, 5% of performance traces (production)
      tracesSampleRate: process.env.NEXT_PUBLIC_ENVIRONMENT === "production" ? 0.05 : 1.0,

      // Never send PII to Sentry
      sendDefaultPii: false,

      beforeSend(event) {
        return scrubEvent(event);
      },

      // Ignore common non-actionable errors
      ignoreErrors: [
        "ResizeObserver loop limit exceeded",
        "ResizeObserver loop completed with undelivered notifications",
        /ChunkLoadError/,
        /Loading chunk \d+ failed/,
        "Non-Error promise rejection captured",
      ],
    });
  }

  if (process.env.NEXT_RUNTIME === "edge") {
    // Edge runtime Sentry (middleware, Edge API routes)
    const Sentry = await import("@sentry/nextjs");

    Sentry.init({
      dsn,
      environment:     process.env.NEXT_PUBLIC_ENVIRONMENT ?? "development",
      tracesSampleRate: 0.02,
      sendDefaultPii:   false,
    });
  }
}

// ─── PII scrubbing ────────────────────────────────────────────────────────────
const SENSITIVE_KEYS = new Set([
  "password", "new_password", "old_password", "confirm_password",
  "token", "access_token", "refresh_token", "authorization",
  "cookie", "card_number", "cvv", "secret",
]);

function scrubEvent(event: Record<string, unknown>): Record<string, unknown> {
  return JSON.parse(
    JSON.stringify(event, (_key, value) => {
      if (typeof _key === "string" && SENSITIVE_KEYS.has(_key.toLowerCase())) {
        return "[Filtered]";
      }
      return value;
    })
  );
}
