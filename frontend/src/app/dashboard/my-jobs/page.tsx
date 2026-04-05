"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { jobsApi } from "@/lib/api";
import { toast } from "sonner";
import { getApiError } from "@/lib/utils";
import type { JobSummary } from "@/types/job";

const STATUS_TABS = [
  { value: "", label: "الكل" },
  { value: "open", label: "مفتوح" },
  { value: "in_progress", label: "جارٍ" },
  { value: "completed", label: "مكتمل" },
  { value: "closed", label: "مغلق" },
];

const STATUS_LABELS: Record<string, string> = {
  open: "مفتوح",
  draft: "مسودة",
  in_progress: "جارٍ",
  completed: "مكتمل",
  closed: "مغلق",
  cancelled: "ملغي",
};

const STATUS_COLORS: Record<string, string> = {
  open: "bg-success-50 text-success-700 border-green-200",
  draft: "bg-gray-100 text-gray-600 border-gray-200",
  in_progress: "bg-blue-50 text-blue-700 border-blue-200",
  completed: "bg-purple-50 text-purple-700 border-purple-200",
  closed: "bg-gray-100 text-gray-500 border-gray-200",
  cancelled: "bg-danger-50 text-danger-700 border-red-200",
};

function formatBudget(job: JobSummary): string {
  if (job.job_type === "fixed" && job.fixed_price) {
    return `${job.fixed_price.toLocaleString("ar-IQ")} د.ع`;
  }
  if (job.budget_min && job.budget_max) {
    return `${job.budget_min.toLocaleString("ar-IQ")} - ${job.budget_max.toLocaleString("ar-IQ")} د.ع/س`;
  }
  if (job.budget_min) return `من ${job.budget_min.toLocaleString("ar-IQ")} د.ع/س`;
  return "—";
}

export default function MyJobsPage() {
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);

  const fetchJobs = useCallback(async () => {
    setIsLoading(true);
    try {
      const params: Record<string, string | number> = { page, page_size: 15 };
      if (statusFilter) params.status = statusFilter;
      const response = await jobsApi.getMyJobs(params);
      setJobs(response.data.jobs);
      setTotal(response.data.total);
      setTotalPages(response.data.total_pages);
    } catch {
      setJobs([]);
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter, page]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  const handleClose = async (jobId: string) => {
    if (!confirm("هل تريد إغلاق هذه الوظيفة؟ لن يتم قبول عروض جديدة.")) return;
    try {
      await jobsApi.close(jobId);
      toast.success("تم إغلاق الوظيفة");
      fetchJobs();
    } catch (err: unknown) {
      toast.error(getApiError(err, "تعذّر إغلاق الوظيفة"));
    }
  };

  const handleDelete = async (jobId: string) => {
    if (!confirm("هل تريد حذف هذه الوظيفة؟ لا يمكن التراجع عن هذا.")) return;
    try {
      await jobsApi.delete(jobId);
      toast.success("تم حذف الوظيفة");
      fetchJobs();
    } catch (err: unknown) {
      toast.error(getApiError(err, "تعذّر حذف الوظيفة"));
    }
  };

  return (
    <div className="space-y-6" dir="rtl">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">وظائفي</h1>
          <p className="mt-1 text-gray-600">
            {total > 0 ? `${total} وظيفة` : "إدارة وظائفك المنشورة"}
          </p>
        </div>
        <Link href="/jobs/new" className="btn-primary py-2 px-5 text-sm">
          نشر وظيفة جديدة
        </Link>
      </div>

      {/* Status tabs */}
      <div className="flex gap-1 border-b border-gray-200 overflow-x-auto">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => { setStatusFilter(tab.value); setPage(1); }}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
              statusFilter === tab.value
                ? "border-brand-500 text-brand-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Job list */}
      {isLoading ? (
        <div className="text-center py-12 text-gray-500">جاري التحميل...</div>
      ) : jobs.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-lg font-medium text-gray-900">لا توجد وظائف</p>
          <p className="mt-2 text-gray-600">
            {statusFilter
              ? "لا توجد وظائف بهذه الحالة."
              : "لم تنشر أي وظائف بعد."}
          </p>
          <Link
            href="/jobs/new"
            className="inline-block mt-4 btn-primary py-2 px-5 text-sm"
          >
            انشر وظيفتك الأولى
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {jobs.map((job) => (
            <div
              key={job.id}
              className="card p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <Link
                    href={`/jobs/${job.id}`}
                    className="font-semibold text-gray-900 hover:text-brand-600 truncate"
                  >
                    {job.title}
                  </Link>
                  <span
                    className={`shrink-0 px-2 py-0.5 text-xs font-medium rounded-full border ${
                      STATUS_COLORS[job.status] || STATUS_COLORS.draft
                    }`}
                  >
                    {STATUS_LABELS[job.status] || job.status}
                  </span>
                </div>
                <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-gray-500">
                  <span>{job.category}</span>
                  <span>{formatBudget(job)}</span>
                  <span>📨 {job.proposal_count} عرض</span>
                  <span>👁 {job.view_count} مشاهدة</span>
                  <span>
                    {new Date(job.created_at).toLocaleDateString("ar-IQ", {
                      month: "short",
                      day: "numeric",
                    })}
                  </span>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-2 shrink-0">
                <Link
                  href={`/jobs/${job.id}`}
                  className="btn-secondary py-1.5 px-3 text-xs"
                >
                  عرض
                </Link>
                {job.status === "open" && (
                  <>
                    <button
                      onClick={() => handleClose(job.id)}
                      className="btn-secondary py-1.5 px-3 text-xs"
                    >
                      إغلاق
                    </button>
                    {job.proposal_count === 0 && (
                      <button
                        onClick={() => handleDelete(job.id)}
                        className="text-xs text-danger-500 hover:text-danger-700 px-2"
                      >
                        حذف
                      </button>
                    )}
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="btn-secondary py-2 px-4 text-sm disabled:opacity-40"
          >
            السابق
          </button>
          <span className="text-sm text-gray-600 px-4">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="btn-secondary py-2 px-4 text-sm disabled:opacity-40"
          >
            التالي
          </button>
        </div>
      )}
    </div>
  );
}
