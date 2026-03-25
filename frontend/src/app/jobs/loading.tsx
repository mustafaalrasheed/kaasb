export default function JobsLoading() {
  return (
    <div className="max-w-5xl mx-auto px-4 py-10">
      {/* Header skeleton */}
      <div className="mb-8 space-y-3">
        <div className="h-8 w-48 bg-gray-200 rounded animate-pulse" />
        <div className="h-4 w-72 bg-gray-100 rounded animate-pulse" />
      </div>
      {/* Filter bar skeleton */}
      <div className="flex gap-3 mb-6">
        <div className="h-10 w-64 bg-gray-200 rounded animate-pulse" />
        <div className="h-10 w-32 bg-gray-200 rounded animate-pulse" />
        <div className="h-10 w-32 bg-gray-200 rounded animate-pulse" />
      </div>
      {/* Job card skeletons */}
      <div className="space-y-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="border border-gray-100 rounded-xl p-6 space-y-3 bg-white shadow-sm">
            <div className="flex items-start justify-between">
              <div className="h-5 w-2/3 bg-gray-200 rounded animate-pulse" />
              <div className="h-5 w-20 bg-gray-100 rounded animate-pulse" />
            </div>
            <div className="h-4 w-full bg-gray-100 rounded animate-pulse" />
            <div className="h-4 w-4/5 bg-gray-100 rounded animate-pulse" />
            <div className="flex gap-2 pt-1">
              <div className="h-6 w-16 bg-gray-100 rounded-full animate-pulse" />
              <div className="h-6 w-20 bg-gray-100 rounded-full animate-pulse" />
              <div className="h-6 w-14 bg-gray-100 rounded-full animate-pulse" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
