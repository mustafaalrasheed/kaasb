"use client";

import { useEffect } from "react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Unhandled error:", error);
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
          <a href="/" className="btn-secondary py-2.5 px-6">
            Go Home
          </a>
        </div>
      </div>
    </div>
  );
}
