"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { jobsApi } from "@/lib/api";
import { backendUrl, useDebouncedCallback } from "@/lib/utils";
import type { JobSummary, JobListResponse } from "@/types/job";
import { JOB_CATEGORIES, DURATION_LABELS, EXPERIENCE_LABELS } from "@/types/job";
import { Breadcrumbs } from "@/components/seo/breadcrumbs";
import { useLocale } from "@/providers/locale-provider";

const SORT_OPTIONS_AR = [
  { value: "newest", label: "الأحدث أولاً" },
  { value: "oldest", label: "الأقدم أولاً" },
  { value: "budget_high", label: "الميزانية: الأعلى أولاً" },
  { value: "budget_low", label: "الميزانية: الأقل أولاً" },
  { value: "most_proposals", label: "الأكثر عروضاً" },
];

const SORT_OPTIONS_EN = [
  { value: "newest", label: "Newest First" },
  { value: "oldest", label: "Oldest First" },
  { value: "budget_high", label: "Budget: High to Low" },
  { value: "budget_low", label: "Budget: Low to High" },
  { value: "most_proposals", label: "Most Proposals" },
];

const EXPERIENCE_LABELS_EN: Record<string, string> = {
  entry: "Entry Level",
  intermediate: "Intermediate",
  expert: "Expert",
};

const DURATION_LABELS_EN: Record<string, string> = {
  "less_than_1_week": "< 1 Week",
  "1_to_2_weeks": "1-2 Weeks",
  "2_to_4_weeks": "2-4 Weeks",
  "1_to_3_months": "1-3 Months",
  "3_to_6_months": "3-6 Months",
  "more_than_6_months": "6+ Months",
};

function formatBudget(job: JobSummary, ar: boolean): string {
  if (job.job_type === "fixed" && job.fixed_price) {
    return `$${job.fixed_price.toLocaleString()}`;
  }
  if (job.budget_min && job.budget_max) {
    return `$${job.budget_min} - $${job.budget_max}/${ar ? "س" : "hr"}`;
  }
  if (job.budget_min) return `${ar ? "من" : "From"} $${job.budget_min}/${ar ? "س" : "hr"}`;
  return ar ? "الميزانية غير محددة" : "Budget not specified";
}

export default function JobsClient() {
  const { locale } = useLocale();
  const ar = locale === "ar";

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

  const sortOptions = ar ? SORT_OPTIONS_AR : SORT_OPTIONS_EN;

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
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Breadcrumbs */}
      <Breadcrumbs
        items={[{ name: ar ? "الوظائف" : "Jobs", href: "/jobs" }]}
        className="mb-4"
      />

      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">
          {ar ? "تصفّح الوظائف" : "Browse Jobs"}
        </h1>
        <p className="mt-2 text-gray-600">
          {total > 0
            ? ar
              ? `${total.toLocaleString("ar-IQ")} وظيفة متاحة`
              : `${total.toLocaleString()} jobs available`
            : ar
            ? "ابحث عن فرصتك القادمة"
            : "Find your next opportunity"}
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
              placeholder={ar ? "ابحث بالعنوان أو الوصف أو المهارات..." : "Search by title, description, or skills..."}
              aria-label={ar ? "البحث في الوظائف" : "Search jobs"}
            />
            <button
              type="submit"
              className="btn-primary py-2.5 px-6 whitespace-nowrap"
            >
              {ar ? "بحث" : "Search"}
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
              aria-label={ar ? "تصفية حسب التصنيف" : "Filter by category"}
            >
              <option value="">{ar ? "كل التصنيفات" : "All Categories"}</option>
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
              aria-label={ar ? "تصفية حسب نوع الوظيفة" : "Filter by job type"}
            >
              <option value="">{ar ? "كل الأنواع" : "All Types"}</option>
              <option value="fixed">{ar ? "سعر ثابت" : "Fixed Price"}</option>
              <option value="hourly">{ar ? "بالساعة" : "Hourly"}</option>
            </select>
            <select
              value={experienceLevel}
              onChange={(e) => {
                setExperienceLevel(e.target.value);
                setPage(1);
              }}
              className="input-field sm:w-40"
              aria-label={ar ? "تصفية حسب مستوى الخبرة" : "Filter by experience"}
            >
              <option value="">{ar ? "كل المستويات" : "All Levels"}</option>
              <option value="entry">{ar ? "مبتدئ" : "Entry Level"}</option>
              <option value="intermediate">{ar ? "متوسط" : "Intermediate"}</option>
              <option value="expert">{ar ? "خبير" : "Expert"}</option>
            </select>
            <select
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value);
                setPage(1);
              }}
              className="input-field sm:w-44"
              aria-label={ar ? "ترتيب الوظائف" : "Sort jobs"}
            >
              {sortOptions.map((opt) => (
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
          {ar ? "جاري تحميل الوظائف..." : "Loading jobs..."}
        </div>
      ) : jobs.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-lg font-medium text-gray-900">
            {ar ? "لا توجد وظائف مطابقة" : "No matching jobs found"}
          </p>
          <p className="mt-2 text-gray-600">
            {ar
              ? "جرّب تعديل معايير البحث أو الفلاتر."
              : "Try adjusting your search criteria or filters."}
          </p>
        </div>
      ) : (
        <>
          <div className="space-y-4">
            {jobs.map((job) => (
              <JobCard key={job.id} job={job} ar={ar} />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <nav
              aria-label={ar ? "ترقيم صفحات الوظائف" : "Job pagination"}
              className="mt-8 flex items-center justify-center gap-2"
            >
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="btn-secondary py-2 px-4 text-sm disabled:opacity-40"
              >
                {ar ? "السابق" : "Previous"}
              </button>
              <span className="text-sm text-gray-600 px-4">
                {ar
                  ? `صفحة ${page} من ${totalPages}`
                  : `Page ${page} of ${totalPages}`}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="btn-secondary py-2 px-4 text-sm disabled:opacity-40"
              >
                {ar ? "التالي" : "Next"}
              </button>
            </nav>
          )}
        </>
      )}
    </div>
  );
}

function JobCard({ job, ar }: { job: JobSummary; ar: boolean }) {
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
                {job.job_type === "fixed"
                  ? ar ? "سعر ثابت" : "Fixed Price"
                  : ar ? "بالساعة" : "Hourly"}
              </span>
            </div>
            <h2 className="text-lg font-semibold text-gray-900">
              {job.title}
            </h2>
            <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm text-gray-500">
              <span className="font-medium text-gray-900">
                {formatBudget(job, ar)}
              </span>
              {job.experience_level && (
                <span>
                  {ar
                    ? EXPERIENCE_LABELS[job.experience_level]
                    : EXPERIENCE_LABELS_EN[job.experience_level] || job.experience_level}
                </span>
              )}
              {job.duration && (
                <span>
                  {ar
                    ? DURATION_LABELS[job.duration]
                    : DURATION_LABELS_EN[job.duration] || job.duration}
                </span>
              )}
              <span>
                {job.proposal_count} {ar ? "عرض" : "proposals"}
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
                    {job.client.first_name?.[0]}
                    {job.client.last_name?.[0]}
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
              ar ? "ar-IQ" : "en-US",
              { month: "short", day: "numeric" }
            )}
          </time>
        </div>
      </article>
    </Link>
  );
}
