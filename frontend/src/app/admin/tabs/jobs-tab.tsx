"use client";

import { adminApi } from "@/lib/api";
import { toast } from "sonner";

interface AdminJob {
  id: string;
  title: string;
  status: string;
  job_type: string;
  budget_min: number | null;
  budget_max: number | null;
  category: string | null;
  proposal_count: number;
  created_at: string;
}

interface JobsTabProps {
  jobs: AdminJob[];
  total: number;
  loading: boolean;
  search: string;
  statusFilter: string;
  ar: boolean;
  dateLocale: string;
  onSearchChange: (v: string) => void;
  onStatusFilterChange: (v: string) => void;
  onSearch: () => void;
  onRefresh: () => void;
}

export function JobsTab({
  jobs, total, loading, search, statusFilter,
  ar, dateLocale,
  onSearchChange, onStatusFilterChange, onSearch, onRefresh,
}: JobsTabProps) {
  const statusLabels: Record<string, string> = ar
    ? { open: "مفتوح", in_progress: "جارٍ", completed: "مكتمل", closed: "مغلق", cancelled: "ملغى", draft: "مسودة" }
    : { open: "Open", in_progress: "In Progress", completed: "Completed", closed: "Closed", cancelled: "Cancelled", draft: "Draft" };

  return (
    <div className="space-y-4">
      <div className="flex gap-3 flex-wrap">
        <input
          type="text" value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder={ar ? "بحث عن وظيفة..." : "Search jobs..."}
          className="flex-1 min-w-[200px] border border-gray-300 rounded-lg px-4 py-2 text-sm"
          onKeyDown={(e) => e.key === "Enter" && onSearch()}
        />
        <select
          value={statusFilter} onChange={(e) => onStatusFilterChange(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
        >
          <option value="">{ar ? "كل الحالات" : "All Statuses"}</option>
          <option value="open">{ar ? "مفتوح" : "Open"}</option>
          <option value="in_progress">{ar ? "جارٍ" : "In Progress"}</option>
          <option value="completed">{ar ? "مكتمل" : "Completed"}</option>
          <option value="closed">{ar ? "مغلق" : "Closed"}</option>
          <option value="cancelled">{ar ? "ملغى" : "Cancelled"}</option>
        </select>
        <button onClick={onSearch} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">
          {ar ? "بحث" : "Search"}
        </button>
      </div>

      <div className="bg-white rounded-lg border overflow-x-auto">
        <table className="min-w-[650px] w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-start p-3 font-medium text-gray-600">{ar ? "العنوان" : "Title"}</th>
              <th className="text-start p-3 font-medium text-gray-600">{ar ? "النوع" : "Type"}</th>
              <th className="text-start p-3 font-medium text-gray-600">{ar ? "الميزانية" : "Budget"}</th>
              <th className="text-start p-3 font-medium text-gray-600">{ar ? "الحالة" : "Status"}</th>
              <th className="text-start p-3 font-medium text-gray-600">{ar ? "العروض" : "Proposals"}</th>
              <th className="text-start p-3 font-medium text-gray-600">{ar ? "تاريخ النشر" : "Posted"}</th>
              <th className="text-end p-3 font-medium text-gray-600">{ar ? "إجراءات" : "Actions"}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {jobs.map((j) => (
              <tr key={j.id} className="hover:bg-gray-50">
                <td className="p-3 font-medium text-gray-900 max-w-xs truncate">{j.title}</td>
                <td className="p-3 text-gray-600">
                  {j.job_type === "fixed" ? (ar ? "ثابت" : "Fixed") : (ar ? "بالساعة" : "Hourly")}
                </td>
                <td className="p-3 text-gray-600 text-xs" dir="ltr">
                  {j.budget_min != null && j.budget_max != null
                    ? `${j.budget_min.toLocaleString()}–${j.budget_max.toLocaleString()} IQD`
                    : j.budget_min != null ? `from ${j.budget_min.toLocaleString()} IQD` : "—"}
                </td>
                <td className="p-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    j.status === "open" ? "bg-green-50 text-green-700" :
                    j.status === "in_progress" ? "bg-blue-50 text-blue-700" :
                    j.status === "completed" ? "bg-purple-50 text-purple-700" :
                    "bg-gray-100 text-gray-500"
                  }`}>
                    {statusLabels[j.status] ?? j.status}
                  </span>
                </td>
                <td className="p-3 text-gray-600">{j.proposal_count}</td>
                <td className="p-3 text-gray-500">
                  {new Date(j.created_at).toLocaleDateString(dateLocale, { month: "short", day: "numeric" })}
                </td>
                <td className="p-3">
                  <div className="flex justify-end">
                    {j.status === "open" && (
                      <button
                        onClick={async () => {
                          try {
                            await adminApi.updateJobStatus(j.id, { status: "closed" });
                            toast.success(ar ? "تم إغلاق الوظيفة" : "Job closed");
                            onRefresh();
                          } catch {
                            toast.error(ar ? "تعذّر إغلاق الوظيفة" : "Failed to close job");
                          }
                        }}
                        className="px-2 py-1 text-xs bg-red-50 text-red-600 rounded hover:bg-red-100"
                      >
                        {ar ? "إغلاق" : "Close"}
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {jobs.length === 0 && !loading && (
          <div className="p-8 text-center text-gray-400">
            {ar ? "لا توجد وظائف" : "No jobs found"}
          </div>
        )}
      </div>
      <p className="text-sm text-gray-500">
        {ar ? `${total} وظيفة إجمالاً` : `${total} job(s) total`}
      </p>
    </div>
  );
}
