import Link from "next/link";

export default function NotFound() {
  return (
    <div className="min-h-[70vh] flex items-center justify-center px-4">
      <div className="text-center">
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
    </div>
  );
}
