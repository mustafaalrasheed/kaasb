"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuthStore } from "@/lib/auth-store";

/**
 * Hero CTA — renders "Get Started Free" for guests, "Open Dashboard" for
 * logged-in users. Lives in a client component so the button reflects the
 * auth-store state AFTER the silent /auth/refresh flow completes (the SSR
 * can only see the short-lived access_token cookie, not the long-lived
 * refresh_token, so a stale SSR render would flash "Get Started Free"
 * until the next full reload).
 */
export function HeroCta({
  ar,
  ssrLoggedIn,
  ssrDashboardHref,
  variant = "hero",
}: {
  ar: boolean;
  ssrLoggedIn: boolean;
  ssrDashboardHref: string;
  variant?: "hero" | "cta";
}) {
  const { isAuthenticated, isLoading, user } = useAuthStore();

  // Avoid hydration mismatch: first render MUST equal the SSR output, so we
  // seed with the SSR hint, then switch to the client auth-store state after
  // mount. This is what eliminates the "Get Started Free → Open Dashboard"
  // flash when the access_token cookie has expired but refresh_token is
  // still valid — the navbar's initialize() runs silent refresh in parallel,
  // and by the time isLoading flips to false the correct CTA renders.
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
  }, []);

  const resolvedLoggedIn = mounted && !isLoading ? isAuthenticated : ssrLoggedIn;
  const dashboardHref = mounted && !isLoading && user
    ? (user.is_superuser ? "/admin" : "/dashboard")
    : ssrDashboardHref;

  // While the client auth state is unresolved AND the SSR hint says "not
  // logged in" (likely stale because access_token has a 30-min TTL while
  // refresh_token has 7 days), render a neutral placeholder so the user
  // never sees the wrong CTA briefly.
  const unresolved = mounted && isLoading && !ssrLoggedIn;
  if (unresolved) {
    const placeholderClass = variant === "hero"
      ? "h-[52px] w-48 rounded-lg bg-white/30 animate-pulse"
      : "h-[52px] w-48 rounded-lg bg-gray-200 animate-pulse";
    return <div className={placeholderClass} aria-hidden="true" />;
  }

  const className = variant === "hero"
    ? "btn-primary bg-white text-brand-600 hover:bg-blue-50 text-center text-lg px-8 py-3"
    : "btn-primary text-lg px-8 py-3";

  if (resolvedLoggedIn) {
    const label = variant === "hero"
      ? (ar ? "الذهاب إلى لوحتي" : "Open Dashboard")
      : (ar ? "الذهاب إلى لوحتي" : "Go to Dashboard");
    return (
      <Link href={dashboardHref} className={className}>
        {label}
      </Link>
    );
  }

  if (variant === "cta") {
    return (
      <>
        <Link href="/auth/register" className={className}>
          {ar ? "سجّل كمستقل" : "Sign Up as Freelancer"}
        </Link>
        <Link href="/auth/register" className="btn-secondary text-lg px-8 py-3">
          {ar ? "وظّف مستقلاً" : "Hire a Freelancer"}
        </Link>
      </>
    );
  }

  return (
    <Link href="/auth/register" className={className}>
      {ar ? "ابدأ مجاناً" : "Get Started Free"}
    </Link>
  );
}
