export default function FreelancersLoading() {
  return (
    <div className="max-w-6xl mx-auto px-4 py-10">
      {/* Header skeleton */}
      <div className="mb-8 space-y-3">
        <div className="h-8 w-56 bg-gray-200 rounded animate-pulse" />
        <div className="h-4 w-80 bg-gray-100 rounded animate-pulse" />
      </div>
      {/* Grid skeletons */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {Array.from({ length: 9 }).map((_, i) => (
          <div key={i} className="border border-gray-100 rounded-xl p-6 bg-white shadow-sm space-y-4">
            {/* Avatar */}
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-gray-200 rounded-full animate-pulse shrink-0" />
              <div className="space-y-2 flex-1">
                <div className="h-4 w-3/4 bg-gray-200 rounded animate-pulse" />
                <div className="h-3 w-1/2 bg-gray-100 rounded animate-pulse" />
              </div>
            </div>
            {/* Bio lines */}
            <div className="h-3 w-full bg-gray-100 rounded animate-pulse" />
            <div className="h-3 w-5/6 bg-gray-100 rounded animate-pulse" />
            {/* Skills */}
            <div className="flex gap-2 flex-wrap">
              <div className="h-5 w-14 bg-gray-100 rounded-full animate-pulse" />
              <div className="h-5 w-18 bg-gray-100 rounded-full animate-pulse" />
              <div className="h-5 w-16 bg-gray-100 rounded-full animate-pulse" />
            </div>
            {/* Rate */}
            <div className="h-5 w-24 bg-gray-200 rounded animate-pulse" />
          </div>
        ))}
      </div>
    </div>
  );
}
