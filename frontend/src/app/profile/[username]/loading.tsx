export default function ProfileLoading() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-10 space-y-8">
      {/* Profile header */}
      <div className="flex items-start gap-6">
        <div className="w-24 h-24 bg-gray-200 rounded-full animate-pulse shrink-0" />
        <div className="flex-1 space-y-3 pt-2">
          <div className="h-7 w-48 bg-gray-200 rounded animate-pulse" />
          <div className="h-4 w-32 bg-gray-100 rounded animate-pulse" />
          <div className="h-4 w-64 bg-gray-100 rounded animate-pulse" />
        </div>
      </div>
      {/* Bio */}
      <div className="space-y-2">
        <div className="h-4 w-full bg-gray-100 rounded animate-pulse" />
        <div className="h-4 w-5/6 bg-gray-100 rounded animate-pulse" />
        <div className="h-4 w-3/4 bg-gray-100 rounded animate-pulse" />
      </div>
      {/* Skills section */}
      <div className="space-y-3">
        <div className="h-5 w-24 bg-gray-200 rounded animate-pulse" />
        <div className="flex gap-2 flex-wrap">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-7 w-20 bg-gray-100 rounded-full animate-pulse" />
          ))}
        </div>
      </div>
      {/* Portfolio grid */}
      <div className="space-y-3">
        <div className="h-5 w-28 bg-gray-200 rounded animate-pulse" />
        <div className="grid grid-cols-2 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-40 bg-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    </div>
  );
}
