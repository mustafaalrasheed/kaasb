import Link from "next/link";
import type { Metadata } from "next";
import { ExploreLinks } from "@/components/seo/related-links";

export const metadata: Metadata = {
  title: "Page Not Found",
  description: "The page you are looking for does not exist or has been moved.",
  robots: { index: false, follow: true },
};

export default function NotFound() {
  return (
    <div className="min-h-[70vh] px-4 py-16">
      <div className="max-w-3xl mx-auto">
        {/* Error Message */}
        <div className="text-center mb-12">
          <h1 className="text-6xl font-bold text-brand-500">404</h1>
          <h2 className="mt-4 text-2xl font-semibold text-gray-900">
            Page not found
          </h2>
          <p className="mt-2 text-gray-600 max-w-md mx-auto">
            The page you are looking for does not exist or has been moved.
          </p>
          <div className="mt-8 flex items-center justify-center gap-4">
            <Link href="/" className="btn-primary py-2.5 px-6">
              Go Home
            </Link>
            <Link href="/jobs" className="btn-secondary py-2.5 px-6">
              Browse Jobs
            </Link>
          </div>
        </div>

        {/* Helpful explore links — provides crawlable internal links for SEO */}
        <ExploreLinks className="mt-8" />
      </div>
    </div>
  );
}
