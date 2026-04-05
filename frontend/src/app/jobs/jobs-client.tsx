"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { jobsApi } from "@/lib/api";
import { backendUrl, useDebouncedCallback } from "@/lib/utils";
import type { JobSummary, JobListResponse } from "@/types/job";
import { JOB_CATEGORIES, DURATION_LABELS, EXPERIENCE_LABELS } from "@/types/job";
import { Breadcrumbs } from "@/components/seo/breadcrumbs";

const SORT_OPTIONS = [
  { value: "newest", label: "الأحدث أولاً" },
  { value: "oldest", label: "الأقدم أولاً" },
  { value: "budget_high", label: "الميزانية: الأعلى أولاً" },
  { value: "budget_low", label: "الميزانية: الأقل أولاً" },
  { value: "most_proposals", label: "الأكثر عروضاً" },
];

const JOB_TYPE_AR: Record<string, string> = {
  fixed: "سعر ثابت",
  hourly: "بالساعة",
};

function formatBudget(job: JobSummary): string {
  if (job.job_type === "fixed" && job.fixed_price) {
    return `$${job.fixed_price.toLocaleString()}`;
  }
  if (job.budget_min && job.budget_max) {
    return `$${job.budget_min} - $${job.budget_max}/س`;
  }
  if (job.budget_min) return `من $${job.budget_min}/س`;
  return "الميزانية غير محددة";
}

export default function JobsClient() {
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  const [searchQuery, setSearchQuery] = useState("");
  const [category, setCategory] = useState("");
  const [jobType, setJobType] = useState("");
  const [experienceLevel, setExperienceLevel] = useState("");
  const [sortBy, setSortBy] = useState("newest");
  const [page, setPage] = useState(1);

  const fetchJobs = useCallback(async () => {
    setIsLoading(true);
    try {
      const params: Record<string, unknown> = {
        sort_by: sortBy,
        page,
        page_size: 12,
      };
      if (searchQuery) params.q = searchQuery;
      if (category) params.category = category;
      if (jobType) params.job_type = jobType;
      if (experienceLevel) params.experience_level = experienceLevel;

      const response = await jobsApi.search(params as any);
      const data: JobListResponse = response.data;
      setJobs(data.jobs);
      setTotal(data.total);
      setTotalPages(data.total_pages);
    } catch {
      setJobs([]);
    } finally {
      setIsLoading(false);
    }
  }, [searchQuery, category, jobType, experienceLevel, sortBy, page]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  const debouncedSearch = useDebouncedCallback((value: unknown) => {
    setSearchQuery(value as string);
    setPage(1);
  }, 300);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchJobs();
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8" dir="rtl">
      {/* Breadcrumbs */}
      <Breadcrumbs
        items={[{ name: "الوظائف", href: "/jobs" }]}
        className="mb-4"
      />

      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">تصفّح الوظائف</h1>
        <p className="mt-2 text-gray-600">
          {total > 0
            ? `${total.toLocaleString("ar-IQ")} وظيفة متاحة`
            : "ابحث عن فرصتك القادمة"}
        </p>
      </div>

      {/* Search & Filters */}
      <div className="card p-4 mb-6">
        <form onSubmit={handleSearch} className="space-y-3">
          <div className="flex flex-col sm:flex-row gap-3">
            <input
              defaultValue={searchQuery}
              onChange={(e) => debouncedSearch(e.target.value)}
              className="input-field flex-1"
              placeholder="ابحث بالعنوان أو الوصف أو المهارات..."
              aria-label="البحث في الوظائف"
            />
            <button
              type="submit"
              className="btn-primary py-2.5 px-6 whitespace-nowrap"
            >
              بحث
            </button>
          </div>
          <div className="flex flex-col sm:flex-row gap-3">
            <select
              value={category}
              onChange={(e) => {
                setCategory(e.target.value);
                setPage(1);
              }}
              className="input-field sm:w-48"
              aria-label="تصفية حسب التصنيف"
            >
              <option value="">كل التصنيفات</option>
              {JOB_CATEGORIES.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
            <select
              value={jobType}
              onChange={(e) => {
                setJobType(e.target.value);
                setPage(1);
              }}
              className="input-field sm:w-36"
              aria-label="تصفية حسب نوع الوظيفة"
            >
              <option value="">كل الأنواع</option>
              <option value="fixed">سعر ثابت</option>
              <option value="hourly">بالساعة</option>
            </select>
            <select
              value={experienceLevel}
              onChange={(e) => {
                setExperienceLevel(e.target.value);
                setPage(1);
              }}
              className="input-field sm:w-40"
              aria-label="تصفية حسب مستوى الخبرة"
            >
              <option value="">كل المستويات</option>
              <option value="entry">مبتدئ</option>
              <option value="intermediate">متوسط</option>
              <option value="expert">خبير</option>
            </select>
            <select
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value);
                setPage(1);
              }}
              className="input-field sm:w-44"
              aria-label="ترتيب الوظائف"
            >
              {SORT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </form>
      </div>

      {/* Results */}
      {isLoading ? (
        <div className="text-center py-12 text-gray-500">
          جاري تحميل الوظائف...
        </div>
      ) : jobs.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-lg font-medium text-gray-900">لا توجد وظائف مطابقة</p>
          <p className="mt-2 text-gray-600">
            جرّب تعديل معايير البحث أو الفلاتر.
          </p>
        </div>
      ) : (
        <>
          <div className="space-y-4">
            {jobs.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <nav
              aria-label="ترقيم صفحات الوظائف"
              className="mt-8 flex items-center justify-center gap-2"
            >
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="btn-secondary py-2 px-4 text-sm disabled:opacity-40"
              >
                السابق
              </button>
              <span className="text-sm text-gray-600 px-4">
                صفحة {page} من {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="btn-secondary py-2 px-4 text-sm disabled:opacity-40"
              >
                التالي
              </button>
            </nav>
          )}
        </>
      )}
    </div>
  );
}

function JobCard({ job }: { job: JobSummary }) {
  return (
    <Link
      href={`/jobs/${job.id}`}
      className="card p-5 hover:shadow-md transition-shadow block"
    >
      <article>
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-brand-50 text-brand-700 border border-brand-200">
                {job.category}
              </span>
              <span className="text-xs text-gray-400">
                {job.job_type === "fixed" ? "سعر ثابت" : "بالساعة"}
              </span>
            </div>
            <h2 className="text-lg font-semibold text-gray-900">
              {job.title}
            </h2>
            <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm text-gray-500">
              <span className="font-medium text-gray-900">
                {formatBudget(job)}
              </span>
              {job.experience_level && (
                <span>{EXPERIENCE_LABELS[job.experience_level]}</span>
              )}
              {job.duration && <span>{DURATION_LABELS[job.duration]}</span>}
              <span>
                {job.proposal_count} عرض
              </span>
            </div>
          </div>
        </div>

        {/* Skills */}
        {job.skills_required && job.skills_required.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {job.skills_required.slice(0, 6).map((skill) => (
              <span
                key={skill}
                className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-600"
              >
                {skill}
              </span>
            ))}
            {job.skills_required.length > 6 && (
              <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-400">
                +{job.skills_required.length - 6}
              </span>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between text-sm text-gray-400">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-full overflow-hidden bg-brand-100 flex items-center justify-center shrink-0">
                {job.client.avatar_url ? (
                  <img
                    src={backendUrl(job.client.avatar_url)}
                    alt={`${job.client.first_name} ${job.client.last_name}`}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <span className="text-[10px] font-bold text-brand-500">
                    {job.client.first_name[0]}
                    {job.client.last_name[0]}
                  </span>
                )}
              </div>
              <span>
                {job.client.display_name ||
                  `${job.client.first_name} ${job.client.last_name}`}
              </span>
            </div>
            {job.client.country && <span>📍 {job.client.country}</span>}
          </div>
          <time dateTime={job.published_at || job.created_at}>
            {new Date(job.published_at || job.created_at).toLocaleDateString(
              "ar-IQ",
              { month: "short", day: "numeric" }
            )}
          </time>
        </div>
      </article>
    </Link>
  );
}
