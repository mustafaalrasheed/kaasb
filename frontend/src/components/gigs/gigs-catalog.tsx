"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { gigsApi } from "@/lib/api";
import { useLocale } from "@/providers/locale-provider";
import { backendUrl, useDebouncedCallback } from "@/lib/utils";

// ---- Types ----

interface GigCategory {
  id: string;
  name_ar: string;
  name_en: string;
  slug: string;
  icon?: string;
  subcategories?: GigSubcategory[];
}

interface GigSubcategory {
  id: string;
  name_ar: string;
  name_en: string;
}

interface GigFreelancer {
  id: string;
  username: string;
  first_name: string;
  last_name: string;
  display_name?: string;
  avatar_url?: string;
}

interface GigPackageSummary {
  price: number;
  delivery_days: number;
}

interface GigSummary {
  id: string;
  slug: string;
  title: string;
  thumbnail_url?: string;
  freelancer: GigFreelancer;
  avg_rating?: number;
  total_orders?: number;
  review_count?: number;
  starting_price?: number;
  min_delivery_days?: number;
  packages?: GigPackageSummary[];
}

// ---- Strings ----

const t = {
  ar: {
    title: "استعرض الخدمات",
    subtitle: (n: number) => n > 0 ? `${n.toLocaleString("ar")} خدمة متاحة` : "اكتشف أفضل المستقلين",
    allCategories: "جميع الفئات",
    searchPlaceholder: "ابحث عن خدمة...",
    search: "بحث",
    sortNewest: "الأحدث",
    sortRating: "الأعلى تقييماً",
    sortOrders: "الأكثر طلباً",
    sortLabel: "ترتيب حسب",
    minPrice: "السعر من (د.ع)",
    maxPrice: "السعر إلى (د.ع)",
    startingAt: "يبدأ من",
    currency: "د.ع",
    days: "أيام",
    day: "يوم",
    orders: "طلب",
    noGigs: "لم يتم العثور على خدمات",
    noGigsHint: "جرب تعديل معايير البحث أو الفلاتر.",
    previous: "السابق",
    next: "التالي",
    page: "صفحة",
    of: "من",
    loading: "جارٍ التحميل...",
  },
  en: {
    title: "Browse Services",
    subtitle: (n: number) => n > 0 ? `${n.toLocaleString()} services available` : "Discover top freelancers",
    allCategories: "All Categories",
    searchPlaceholder: "Search for a service...",
    search: "Search",
    sortNewest: "Newest",
    sortRating: "Top Rated",
    sortOrders: "Most Orders",
    sortLabel: "Sort by",
    minPrice: "Min Price (IQD)",
    maxPrice: "Max Price (IQD)",
    startingAt: "Starting at",
    currency: "IQD",
    days: "days",
    day: "day",
    orders: "orders",
    noGigs: "No services found",
    noGigsHint: "Try adjusting your search or filters.",
    previous: "Previous",
    next: "Next",
    page: "Page",
    of: "of",
    loading: "Loading...",
  },
};

const SORT_OPTIONS = (locale: "ar" | "en") => [
  { value: "newest", label: t[locale].sortNewest },
  { value: "rating", label: t[locale].sortRating },
  { value: "orders", label: t[locale].sortOrders },
];

// ---- Skeleton ----

function GigCardSkeleton() {
  return (
    <div className="card overflow-hidden animate-pulse">
      <div className="aspect-video bg-gray-200" />
      <div className="p-4 space-y-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-gray-200" />
          <div className="h-3 bg-gray-200 rounded w-24" />
        </div>
        <div className="space-y-2">
          <div className="h-3 bg-gray-200 rounded w-full" />
          <div className="h-3 bg-gray-200 rounded w-3/4" />
        </div>
        <div className="h-3 bg-gray-200 rounded w-1/2" />
        <div className="pt-2 border-t border-gray-100 flex justify-between">
          <div className="h-3 bg-gray-200 rounded w-20" />
          <div className="h-3 bg-gray-200 rounded w-16" />
        </div>
      </div>
    </div>
  );
}

// ---- Gig Card ----

function GigCard({ gig, locale }: { gig: GigSummary; locale: "ar" | "en" }) {
  const str = t[locale];
  const freelancerName = gig.freelancer.display_name ||
    `${gig.freelancer.first_name} ${gig.freelancer.last_name}`;
  const price = gig.starting_price ??
    (gig.packages && gig.packages.length > 0
      ? Math.min(...gig.packages.map((p) => p.price))
      : 0);
  const deliveryDays = gig.min_delivery_days ??
    (gig.packages && gig.packages.length > 0
      ? Math.min(...gig.packages.map((p) => p.delivery_days))
      : null);

  return (
    <Link
      href={`/gigs/${gig.slug}`}
      className="card overflow-hidden hover:shadow-md transition-shadow block group"
    >
      <article>
        {/* Thumbnail */}
        <div className="aspect-video bg-gray-100 overflow-hidden">
          {gig.thumbnail_url ? (
            <img
              src={backendUrl(gig.thumbnail_url)}
              alt={gig.title}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <svg className="w-12 h-12 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
          )}
        </div>

        {/* Body */}
        <div className="p-4">
          {/* Freelancer */}
          <div className="flex items-center gap-2 mb-2">
            <div className="w-7 h-7 rounded-full overflow-hidden bg-brand-100 flex items-center justify-center shrink-0">
              {gig.freelancer.avatar_url ? (
                <img
                  src={backendUrl(gig.freelancer.avatar_url)}
                  alt={freelancerName}
                  className="w-full h-full object-cover"
                />
              ) : (
                <span className="text-[10px] font-bold text-brand-500">
                  {gig.freelancer.first_name[0]}{gig.freelancer.last_name[0]}
                </span>
              )}
            </div>
            <span className="text-sm text-gray-500 truncate">{freelancerName}</span>
          </div>

          {/* Title */}
          <h2 className="font-medium text-gray-900 line-clamp-2 text-sm leading-snug mb-2 group-hover:text-brand-600 transition-colors">
            {gig.title}
          </h2>

          {/* Rating */}
          {gig.avg_rating && gig.avg_rating > 0 ? (
            <div className="flex items-center gap-1 text-sm mb-2">
              <span className="text-yellow-400">★</span>
              <span className="font-medium text-gray-800">{gig.avg_rating.toFixed(1)}</span>
              {gig.review_count ? (
                <span className="text-gray-400">({gig.review_count.toLocaleString(locale === "ar" ? "ar" : "en")})</span>
              ) : null}
            </div>
          ) : null}

          {/* Footer */}
          <div className="pt-3 border-t border-gray-100 flex items-end justify-between gap-2">
            <div>
              <p className="text-xs text-gray-400">
                {str.startingAt}
              </p>
              <p className="font-semibold text-gray-900 text-sm">
                {price.toLocaleString(locale === "ar" ? "ar" : "en")} {str.currency}
              </p>
            </div>
            {deliveryDays !== null && (
              <p className="text-xs text-gray-500 shrink-0">
                {deliveryDays} {deliveryDays === 1 ? str.day : str.days}
              </p>
            )}
          </div>
        </div>
      </article>
    </Link>
  );
}

// ---- Main Component ----

interface GigsCatalogProps {
  initialCategories: unknown[];
}

export function GigsCatalog({ initialCategories }: GigsCatalogProps) {
  const { locale } = useLocale();
  const str = t[locale];

  const categories = initialCategories as GigCategory[];

  const [gigs, setGigs] = useState<GigSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  const [selectedCategory, setSelectedCategory] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("newest");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [page, setPage] = useState(1);

  const fetchGigs = useCallback(async () => {
    setIsLoading(true);
    try {
      const params: Record<string, unknown> = {
        sort_by: sortBy,
        page,
        page_size: 9,
      };
      if (searchQuery) params.q = searchQuery;
      if (selectedCategory) params.category_id = selectedCategory;
      if (minPrice) params.min_price = parseFloat(minPrice);
      if (maxPrice) params.max_price = parseFloat(maxPrice);

      const res = await gigsApi.search(params as Parameters<typeof gigsApi.search>[0]);
      const data = res.data;
      setGigs(data?.gigs || data?.data || []);
      setTotal(data?.total || 0);
      setTotalPages(data?.total_pages || 1);
    } catch {
      setGigs([]);
    } finally {
      setIsLoading(false);
    }
  }, [searchQuery, selectedCategory, sortBy, minPrice, maxPrice, page]);

  useEffect(() => {
    fetchGigs();
  }, [fetchGigs]);

  const debouncedSearch = useDebouncedCallback((value: string) => {
    setSearchQuery(value);
    setPage(1);
  }, 300);

  const handleCategoryChange = (catId: string) => {
    setSelectedCategory(catId);
    setPage(1);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">{str.title}</h1>
        <p className="mt-2 text-gray-600">{str.subtitle(total)}</p>
      </div>

      {/* Category tabs */}
      {categories.length > 0 && (
        <div className="flex gap-2 overflow-x-auto pb-2 mb-6 scrollbar-hide">
          <button
            onClick={() => handleCategoryChange("")}
            className={`shrink-0 flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-medium border transition-colors ${
              selectedCategory === ""
                ? "bg-brand-500 text-white border-brand-500"
                : "bg-white text-gray-600 border-gray-200 hover:border-brand-300"
            }`}
          >
            {str.allCategories}
          </button>
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => handleCategoryChange(cat.id)}
              className={`shrink-0 flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-medium border transition-colors ${
                selectedCategory === cat.id
                  ? "bg-brand-500 text-white border-brand-500"
                  : "bg-white text-gray-600 border-gray-200 hover:border-brand-300"
              }`}
            >
              {cat.icon && <span>{cat.icon}</span>}
              {locale === "ar" ? cat.name_ar : cat.name_en}
            </button>
          ))}
        </div>
      )}

      {/* Filters bar */}
      <div className="card p-4 mb-6">
        <div className="flex flex-col sm:flex-row gap-3">
          <input
            type="search"
            defaultValue={searchQuery}
            onChange={(e) => debouncedSearch(e.target.value)}
            className="input-field flex-1"
            placeholder={str.searchPlaceholder}
            aria-label={str.searchPlaceholder}
          />
          <select
            value={sortBy}
            onChange={(e) => { setSortBy(e.target.value); setPage(1); }}
            className="input-field sm:w-44"
            aria-label={str.sortLabel}
          >
            {SORT_OPTIONS(locale).map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <input
            type="number"
            value={minPrice}
            onChange={(e) => { setMinPrice(e.target.value); setPage(1); }}
            className="input-field sm:w-36"
            placeholder={str.minPrice}
            min={0}
            aria-label={str.minPrice}
          />
          <input
            type="number"
            value={maxPrice}
            onChange={(e) => { setMaxPrice(e.target.value); setPage(1); }}
            className="input-field sm:w-36"
            placeholder={str.maxPrice}
            min={0}
            aria-label={str.maxPrice}
          />
        </div>
      </div>

      {/* Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {Array.from({ length: 9 }).map((_, i) => (
            <GigCardSkeleton key={i} />
          ))}
        </div>
      ) : gigs.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-lg font-medium text-gray-900">{str.noGigs}</p>
          <p className="mt-2 text-gray-500">{str.noGigsHint}</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {gigs.map((gig) => (
              <GigCard key={gig.id} gig={gig} locale={locale} />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <nav
              aria-label={locale === "ar" ? "تنقل بين صفحات الخدمات" : "Gig results pagination"}
              className="mt-8 flex items-center justify-center gap-2"
            >
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="btn-secondary py-2 px-4 text-sm disabled:opacity-40"
              >
                {str.previous}
              </button>
              <span className="text-sm text-gray-600 px-4">
                {str.page} {page} {str.of} {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="btn-secondary py-2 px-4 text-sm disabled:opacity-40"
              >
                {str.next}
              </button>
            </nav>
          )}
        </>
      )}
    </div>
  );
}
