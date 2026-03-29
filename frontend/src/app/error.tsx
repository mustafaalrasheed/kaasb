"use client";

import Link from "next/link";
import { useEffect } from "react";

// Sentry is optional — only imported if the DSN is configured
// webpackIgnore: @sentry/nextjs is not installed; install it to enable Sentry
let captureException: ((err: unknown) => string) | null = null;
if (typeof window !== "undefined" && process.env.NEXT_PUBLIC_SENTRY_DSN) {
  import(/* webpackIgnore: true */ "@sentry/nextjs" as string).then((Sentry) => {
    captureException = Sentry.captureException;
  });
}

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Always log to console for dev visibility
    console.error("Unhandled error:", error);

    // Report to Sentry (no-op in dev or if DSN is not set)
    if (captureException) {
      captureException(error);
    }
  }, [error]);

  return (
    <div className="min-h-[70vh] flex items-center justify-center px-4">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900">
          Something went wrong
        </h1>
        <p className="mt-3 text-gray-600 max-w-md mx-auto">
          An unexpected error occurred. Please try again or contact support if
          the problem persists.
        </p>
        <div className="mt-8 flex items-center justify-center gap-4">
          <button onClick={reset} className="btn-primary py-2.5 px-6">
            Try Again
          </button>
          <Link href="/" className="btn-secondary py-2.5 px-6">
            Go Home
          </Link>
        </div>
      </div>
    </div>
  );
}
