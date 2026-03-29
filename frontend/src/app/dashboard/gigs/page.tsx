"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { gigsApi } from "@/lib/api";
import { useLocale } from "@/providers/locale-provider";
import { toast } from "sonner";

// ---- Types ----

interface GigPackageSummary {
  price: number;
  delivery_days: number;
}

interface MyGig {
  id: string;
  slug: string;
  title: string;
  status: "draft" | "pending_review" | "active" | "paused" | "rejected" | "archived";
  total_orders?: number;
  avg_rating?: number;
  review_count?: number;
  packages?: GigPackageSummary[];
  rejection_reason?: string;
}

// ---- Strings ----

const t = {
  ar: {
    title: "خدماتي",
    subtitle: (n: number) => n > 0 ? `${n} خدمة` : "أدر خدماتك",
    createNew: "إنشاء خدمة جديدة",
    loading: "جارٍ التحميل...",
    noGigs: "لا توجد خدمات بعد",
    noGigsHint: "ابدأ بإنشاء خدمتك الأولى لتبدأ في استقبال الطلبات.",
    createFirst: "أنشئ خدمتك الأولى",
    colTitle: "الخدمة",
    colStatus: "الحالة",
    colOrders: "الطلبات",
    colRating: "التقييم",
    colActions: "الإجراءات",
    edit: "تعديل",
    pause: "إيقاف",
    resume: "تفعيل",
    delete: "حذف",
    deleteConfirm: "هل أنت متأكد من حذف هذه الخدمة؟ لا يمكن التراجع عن هذا الإجراء.",
    pauseConfirm: "هل تريد إيقاف هذه الخدمة مؤقتاً؟",
    deleteSuccess: "تم حذف الخدمة",
    pauseSuccess: "تم إيقاف الخدمة مؤقتاً",
    resumeSuccess: "تم تفعيل الخدمة",
    deleteError: "حدث خطأ أثناء الحذف",
    pauseError: "حدث خطأ",
    status_active: "نشطة",
    status_pending_review: "قيد المراجعة",
    status_paused: "موقوفة",
    status_rejected: "مرفوضة",
    status_draft: "مسودة",
    status_archived: "مؤرشفة",
    rejectionReason: "سبب الرفض:",
    noRating: "—",
    currency: "د.ع",
    startingAt: "يبدأ من",
  },
  en: {
    title: "My Gigs",
    subtitle: (n: number) => n > 0 ? `${n} gig${n !== 1 ? "s" : ""}` : "Manage your services",
    createNew: "Create New Gig",
    loading: "Loading...",
    noGigs: "No gigs yet",
    noGigsHint: "Start by creating your first gig to receive orders.",
    createFirst: "Create Your First Gig",
    colTitle: "Gig",
    colStatus: "Status",
    colOrders: "Orders",
    colRating: "Rating",
    colActions: "Actions",
    edit: "Edit",
    pause: "Pause",
    resume: "Resume",
    delete: "Delete",
    deleteConfirm: "Are you sure you want to delete this gig? This cannot be undone.",
    pauseConfirm: "Pause this gig? It will no longer appear in search results.",
    deleteSuccess: "Gig deleted",
    pauseSuccess: "Gig paused",
    resumeSuccess: "Gig resumed",
    deleteError: "Failed to delete gig",
    pauseError: "Action failed",
    status_active: "Active",
    status_pending_review: "Pending Review",
    status_paused: "Paused",
    status_rejected: "Rejected",
    status_draft: "Draft",
    status_archived: "Archived",
    rejectionReason: "Reason:",
    noRating: "—",
    currency: "IQD",
    startingAt: "From",
  },
};

// ---- Status Badge ----

const STATUS_STYLES: Record<string, string> = {
  active: "bg-green-50 text-green-700 border-green-200",
  pending_review: "bg-yellow-50 text-yellow-700 border-yellow-200",
  paused: "bg-gray-100 text-gray-600 border-gray-200",
  rejected: "bg-red-50 text-red-700 border-red-200",
  draft: "bg-slate-100 text-slate-600 border-slate-200",
  archived: "bg-gray-100 text-gray-400 border-gray-100",
};

function StatusBadge({ status, locale }: { status: string; locale: "ar" | "en" }) {
  const str = t[locale];
  const key = `status_${status}` as keyof typeof str;
  const label = (str[key] as string) || status;
  const style = STATUS_STYLES[status] || STATUS_STYLES.draft;

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${style}`}>
      {label}
    </span>
  );
}

// ---- Main Page ----

export default function MyGigsPage() {
  const { locale } = useLocale();
  const str = t[locale];

  const [gigs, setGigs] = useState<MyGig[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchGigs = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await gigsApi.myGigs();
      setGigs(res.data?.gigs || res.data?.data || res.data || []);
    } catch {
      setGigs([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGigs();
  }, [fetchGigs]);

  const handlePause = async (gigId: string) => {
    if (!confirm(str.pauseConfirm)) return;
    try {
      await gigsApi.pause(gigId);
      toast.success(str.pauseSuccess);
      fetchGigs();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      toast.error(axiosErr?.response?.data?.detail || str.pauseError);
    }
  };

  const handleResume = async (gigId: string) => {
    try {
      await gigsApi.resume(gigId);
      toast.success(str.resumeSuccess);
      fetchGigs();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      toast.error(axiosErr?.response?.data?.detail || str.pauseError);
    }
  };

  const handleDelete = async (gigId: string) => {
    if (!confirm(str.deleteConfirm)) return;
    try {
      await gigsApi.delete(gigId);
      toast.success(str.deleteSuccess);
      fetchGigs();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      toast.error(axiosErr?.response?.data?.detail || str.deleteError);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{str.title}</h1>
          <p className="mt-1 text-gray-600">{str.subtitle(gigs.length)}</p>
        </div>
        <Link href="/dashboard/gigs/new" className="btn-primary py-2 px-5 text-sm">
          {str.createNew}
        </Link>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="text-center py-16 text-gray-500">{str.loading}</div>
      ) : gigs.length === 0 ? (
        <div className="text-center py-16 card">
          <svg className="w-14 h-14 text-gray-200 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          <p className="text-lg font-medium text-gray-900">{str.noGigs}</p>
          <p className="mt-2 text-gray-500 max-w-sm mx-auto">{str.noGigsHint}</p>
          <Link href="/dashboard/gigs/new" className="inline-block mt-5 btn-primary py-2.5 px-6">
            {str.createFirst}
          </Link>
        </div>
      ) : (
        <div className="card overflow-hidden">
          {/* Table header — desktop */}
          <div className="hidden md:grid grid-cols-[1fr_140px_80px_90px_160px] gap-4 px-5 py-3 bg-gray-50 border-b border-gray-100 text-xs font-semibold text-gray-500 uppercase tracking-wide">
            <span>{str.colTitle}</span>
            <span>{str.colStatus}</span>
            <span className="text-center">{str.colOrders}</span>
            <span className="text-center">{str.colRating}</span>
            <span className="text-end">{str.colActions}</span>
          </div>

          {/* Rows */}
          <div className="divide-y divide-gray-100">
            {gigs.map((gig) => {
              const startingPrice = gig.packages && gig.packages.length > 0
                ? Math.min(...gig.packages.map((p) => p.price))
                : null;

              return (
                <div
                  key={gig.id}
                  className="flex flex-col md:grid md:grid-cols-[1fr_140px_80px_90px_160px] gap-3 md:gap-4 md:items-center px-5 py-4"
                >
                  {/* Title + price */}
                  <div className="min-w-0">
                    <Link
                      href={`/gigs/${gig.slug}`}
                      className="font-medium text-gray-900 hover:text-brand-600 truncate block transition-colors"
                    >
                      {gig.title}
                    </Link>
                    {startingPrice !== null && (
                      <p className="text-xs text-gray-400 mt-0.5">
                        {str.startingAt} {startingPrice.toLocaleString(locale === "ar" ? "ar" : "en")} {str.currency}
                      </p>
                    )}
                    {gig.status === "rejected" && gig.rejection_reason && (
                      <p className="text-xs text-red-600 mt-1">
                        {str.rejectionReason} {gig.rejection_reason}
                      </p>
                    )}
                  </div>

                  {/* Status */}
                  <div className="flex items-center gap-2 md:block">
                    <StatusBadge status={gig.status} locale={locale} />
                  </div>

                  {/* Orders */}
                  <div className="text-sm text-gray-700 md:text-center">
                    {gig.total_orders ?? 0}
                  </div>

                  {/* Rating */}
                  <div className="text-sm text-gray-700 md:text-center">
                    {gig.avg_rating && gig.avg_rating > 0 ? (
                      <span className="flex items-center gap-1 md:justify-center">
                        <span className="text-yellow-400">★</span>
                        {gig.avg_rating.toFixed(1)}
                      </span>
                    ) : (
                      str.noRating
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 md:justify-end">
                    <Link
                      href={`/dashboard/gigs/${gig.id}/edit`}
                      className="btn-secondary py-1.5 px-3 text-xs"
                    >
                      {str.edit}
                    </Link>

                    {gig.status === "active" && (
                      <button
                        onClick={() => handlePause(gig.id)}
                        className="btn-secondary py-1.5 px-3 text-xs"
                      >
                        {str.pause}
                      </button>
                    )}

                    {gig.status === "paused" && (
                      <button
                        onClick={() => handleResume(gig.id)}
                        className="btn-secondary py-1.5 px-3 text-xs"
                      >
                        {str.resume}
                      </button>
                    )}

                    {(gig.status === "draft" || gig.status === "rejected") && (
                      <button
                        onClick={() => handleDelete(gig.id)}
                        className="py-1.5 px-3 text-xs text-red-600 hover:text-red-700 transition-colors"
                      >
                        {str.delete}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
