"use client";

interface PlatformStats {
  users: { total: number; active_30d: number; new_7d: number; by_role: Record<string, number> };
  jobs: { total: number; open: number; new_7d: number };
  contracts: { total: number; active: number; completed: number };
  proposals: { total: number };
  financials: { total_volume: number; platform_fees_earned: number; pending_escrow: number };
  reviews: { total: number; average_rating: number };
  messages: { total: number };
}

function StatCard({ label, value, icon, isText = false }: {
  label: string; value: number | string; icon: string; isText?: boolean;
}) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <span className="text-2xl">{icon}</span>
      <div className={`mt-2 ${isText ? "text-lg" : "text-2xl"} font-bold text-gray-900`}>{value}</div>
      <div className="text-sm text-gray-500 mt-0.5">{label}</div>
    </div>
  );
}

export function StatsTab({ stats, ar }: { stats: PlatformStats; ar: boolean }) {
  const roleLabels: Record<string, string> = ar
    ? { client: "عميل", freelancer: "مستقل", admin: "مدير" }
    : { client: "Client", freelancer: "Freelancer", admin: "Admin" };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label={ar ? "إجمالي المستخدمين" : "Total Users"} value={stats.users.total} icon="👥" />
        <StatCard label={ar ? "النشطون (30 يوم)" : "Active (30d)"} value={stats.users.active_30d} icon="🟢" />
        <StatCard label={ar ? "الوظائف المفتوحة" : "Open Jobs"} value={stats.jobs.open} icon="📋" />
        <StatCard label={ar ? "العقود النشطة" : "Active Contracts"} value={stats.contracts.active} icon="📝" />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <StatCard label={ar ? "إجمالي حجم التداول" : "Total Volume"} value={`${stats.financials.total_volume.toLocaleString(ar ? "ar-IQ" : "en-US")} ${ar ? "د.ع" : "IQD"}`} icon="💰" isText />
        <StatCard label={ar ? "عمولات المنصة" : "Platform Fees"} value={`${stats.financials.platform_fees_earned.toLocaleString(ar ? "ar-IQ" : "en-US")} ${ar ? "د.ع" : "IQD"}`} icon="🏦" isText />
        <StatCard label={ar ? "في الضمان" : "In Escrow"} value={`${stats.financials.pending_escrow.toLocaleString(ar ? "ar-IQ" : "en-US")} ${ar ? "د.ع" : "IQD"}`} icon="🔒" isText />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg border p-4">
          <h3 className="font-semibold text-gray-900 mb-3">
            {ar ? "المستخدمون حسب الدور" : "Users by Role"}
          </h3>
          {Object.entries(stats.users.by_role).map(([role, count]) => (
            <div key={role} className="flex justify-between text-sm py-1">
              <span className="text-gray-600">{roleLabels[role] ?? role}</span>
              <span className="font-medium">{count}</span>
            </div>
          ))}
          <div className="flex justify-between text-sm py-1 border-t mt-2 pt-2">
            <span className="text-gray-600">{ar ? "جدد (7 أيام)" : "New (7 days)"}</span>
            <span className="font-medium text-green-600">+{stats.users.new_7d}</span>
          </div>
        </div>

        <div className="bg-white rounded-lg border p-4">
          <h3 className="font-semibold text-gray-900 mb-3">{ar ? "السوق" : "Marketplace"}</h3>
          <div className="flex justify-between text-sm py-1">
            <span className="text-gray-600">{ar ? "إجمالي الوظائف" : "Total Jobs"}</span>
            <span className="font-medium">{stats.jobs.total}</span>
          </div>
          <div className="flex justify-between text-sm py-1">
            <span className="text-gray-600">{ar ? "إجمالي العروض" : "Total Proposals"}</span>
            <span className="font-medium">{stats.proposals.total}</span>
          </div>
          <div className="flex justify-between text-sm py-1">
            <span className="text-gray-600">{ar ? "العقود المكتملة" : "Completed Contracts"}</span>
            <span className="font-medium">{stats.contracts.completed}</span>
          </div>
          <div className="flex justify-between text-sm py-1">
            <span className="text-gray-600">{ar ? "وظائف جديدة (7 أيام)" : "New Jobs (7 days)"}</span>
            <span className="font-medium text-green-600">+{stats.jobs.new_7d}</span>
          </div>
        </div>

        <div className="bg-white rounded-lg border p-4">
          <h3 className="font-semibold text-gray-900 mb-3">{ar ? "المجتمع" : "Community"}</h3>
          <div className="flex justify-between text-sm py-1">
            <span className="text-gray-600">{ar ? "التقييمات" : "Reviews"}</span>
            <span className="font-medium">{stats.reviews.total}</span>
          </div>
          <div className="flex justify-between text-sm py-1">
            <span className="text-gray-600">{ar ? "متوسط التقييم" : "Avg. Rating"}</span>
            <span className="font-medium">{stats.reviews.average_rating}★</span>
          </div>
          <div className="flex justify-between text-sm py-1">
            <span className="text-gray-600">{ar ? "الرسائل" : "Messages"}</span>
            <span className="font-medium">{stats.messages.total}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
