"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { usersApi } from "@/lib/api";
import { backendUrl } from "@/lib/utils";
import type { UserProfile } from "@/types/user";
import { Breadcrumbs } from "@/components/seo/breadcrumbs";
import { useLocale } from "@/providers/locale-provider";

const SORT_OPTIONS_AR = [
  { value: "rating", label: "الأعلى تقييماً" },
  { value: "rate_low", label: "السعر: الأقل أولاً" },
  { value: "rate_high", label: "السعر: الأعلى أولاً" },
  { value: "newest", label: "الأحدث" },
];

const SORT_OPTIONS_EN = [
  { value: "rating", label: "Highest Rated" },
  { value: "rate_low", label: "Rate: Low to High" },
  { value: "rate_high", label: "Rate: High to Low" },
  { value: "newest", label: "Newest" },
];

export default function FreelancersClient() {
  const { locale } = useLocale();
  const ar = locale === "ar";

  const [freelancers, setFreelancers] = useState<UserProfile[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  const [searchQuery, setSearchQuery] = useState("");
  const [skills, setSkills] = useState("");
  const [experienceLevel, setExperienceLevel] = useState("");
  const [sortBy, setSortBy] = useState("rating");
  const [page, setPage] = useState(1);

  const sortOptions = ar ? SORT_OPTIONS_AR : SORT_OPTIONS_EN;

  const fetchFreelancers = useCallback(async () => {
    setIsLoading(true);
    try {
      const params: Record<string, unknown> = {
        sort_by: sortBy,
        page,
        page_size: 12,
      };
      if (searchQuery) params.q = searchQuery;
      if (skills) params.skills = skills;
      if (experienceLevel) params.experience_level = experienceLevel;

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const response = await usersApi.searchFreelancers(params as any);
      setFreelancers(response.data.users);
      setTotal(response.data.total);
      setTotalPages(response.data.total_pages);
    } catch {
      setFreelancers([]);
    } finally {
      setIsLoading(false);
    }
  }, [searchQuery, skills, experienceLevel, sortBy, page]);

  useEffect(() => {
    fetchFreelancers();
  }, [fetchFreelancers]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchFreelancers();
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Breadcrumbs */}
      <Breadcrumbs
        items={[{ name: ar ? "المستقلون" : "Freelancers", href: "/freelancers" }]}
        className="mb-4"
      />

      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">
          {ar ? "ابحث عن مستقل" : "Find Freelancers"}
        </h1>
        <p className="mt-2 text-gray-600">
          {total > 0
            ? ar
              ? `تصفّح ${total.toLocaleString("ar-IQ")} مستقلاً موهوباً جاهزاً للعمل على مشروعك.`
              : `Browse ${total.toLocaleString()} talented freelancers ready to work on your project.`
            : ar
            ? "تصفّح المستقلين الموهوبين"
            : "Browse talented freelancers"}
        </p>
      </div>

      {/* Search & Filters */}
      <div className="card p-4 mb-6">
        <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-3">
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input-field flex-1"
            placeholder={ar ? "ابحث بالاسم أو العنوان أو المهارات..." : "Search by name, title, or skills..."}
            aria-label={ar ? "البحث في المستقلين" : "Search freelancers"}
          />
          <input
            value={skills}
            onChange={(e) => setSkills(e.target.value)}
            className="input-field sm:w-48"
            placeholder={ar ? "مهارات (مثال: Python,React)" : "Skills (e.g. Python,React)"}
            aria-label={ar ? "تصفية حسب المهارات" : "Filter by skills"}
            dir="ltr"
          />
          <select
            value={experienceLevel}
            onChange={(e) => {
              setExperienceLevel(e.target.value);
              setPage(1);
            }}
            className="input-field sm:w-40"
            aria-label={ar ? "تصفية حسب مستوى الخبرة" : "Filter by experience level"}
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
            aria-label={ar ? "ترتيب المستقلين" : "Sort freelancers"}
          >
            {sortOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <button
            type="submit"
            className="btn-primary py-2.5 px-6 whitespace-nowrap"
          >
            {ar ? "بحث" : "Search"}
          </button>
        </form>
      </div>

      {/* Results */}
      {isLoading ? (
        <div className="text-center py-12 text-gray-500">
          {ar ? "جاري تحميل المستقلين..." : "Loading freelancers..."}
        </div>
      ) : freelancers.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-lg font-medium text-gray-900">
            {ar ? "لا يوجد مستقلون مطابقون" : "No matching freelancers found"}
          </p>
          <p className="mt-2 text-gray-600">
            {ar
              ? "جرّب تعديل معايير البحث أو الفلاتر."
              : "Try adjusting your search criteria or filters."}
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {freelancers.map((freelancer) => (
              <FreelancerCard key={freelancer.id} user={freelancer} ar={ar} />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <nav
              aria-label={ar ? "ترقيم صفحات المستقلين" : "Freelancer pagination"}
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
                {ar ? `صفحة ${page} من ${totalPages}` : `Page ${page} of ${totalPages}`}
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

function FreelancerCard({ user, ar }: { user: UserProfile; ar: boolean }) {
  return (
    <Link
      href={`/profile/${user.username}`}
      className="card p-5 hover:shadow-md transition-shadow"
    >
      <article>
        <div className="flex items-start gap-4">
          <div className="w-14 h-14 shrink-0 rounded-full overflow-hidden bg-brand-100 flex items-center justify-center">
            {user.avatar_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={backendUrl(user.avatar_url)}
                alt={`${user.first_name} ${user.last_name}`}
                className="w-full h-full object-cover"
              />
            ) : (
              <span className="text-xl font-bold text-brand-500">
                {user.first_name[0]}
                {user.last_name[0]}
              </span>
            )}
          </div>
          <div className="min-w-0 flex-1">
            <h2 className="font-semibold text-gray-900 truncate">
              {user.display_name || `${user.first_name} ${user.last_name}`}
            </h2>
            {user.title && (
              <p className="text-sm text-gray-600 truncate">{user.title}</p>
            )}
            <div className="mt-1 flex items-center gap-3 text-sm text-gray-500">
              {user.hourly_rate && (
                <span dir="ltr">${user.hourly_rate}/hr</span>
              )}
              {user.avg_rating > 0 && (
                <span>
                  ⭐ {user.avg_rating.toFixed(1)} ({user.total_reviews})
                </span>
              )}
            </div>
          </div>
          <span
            className={`shrink-0 w-2.5 h-2.5 rounded-full mt-1 ${
              user.is_online ? "bg-success-500" : "bg-gray-300"
            }`}
            aria-label={ar ? (user.is_online ? "متصل" : "غير متصل") : (user.is_online ? "Online" : "Offline")}
          />
        </div>

        {user.skills && user.skills.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {user.skills.slice(0, 5).map((skill) => (
              <span
                key={skill}
                className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-600"
              >
                {skill}
              </span>
            ))}
            {user.skills.length > 5 && (
              <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-400">
                +{user.skills.length - 5}
              </span>
            )}
          </div>
        )}

        {user.country && (
          <p className="mt-2 text-xs text-gray-400">📍 {user.country}</p>
        )}
      </article>
    </Link>
  );
}
