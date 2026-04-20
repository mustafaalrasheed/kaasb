"use client";

import { useEffect, useState, useCallback } from "react";
import { useLocale } from "@/providers/locale-provider";
import { buyerRequestsApi, gigsApi } from "@/lib/api";
import type {
  BuyerRequest,
  BuyerRequestOffer,
} from "@/types/buyer_request";

interface Category {
  id: string;
  name_en: string;
  name_ar: string;
}

type Tab = "list" | "create";

interface CreateFormState {
  title: string;
  description: string;
  category_id: string;
  budget_min: string;
  budget_max: string;
  delivery_days: string;
}

const EMPTY_FORM: CreateFormState = {
  title: "",
  description: "",
  category_id: "",
  budget_min: "",
  budget_max: "",
  delivery_days: "",
};

export default function DashboardRequestsPage() {
  const { locale } = useLocale();
  const ar = locale === "ar";

  const [tab, setTab] = useState<Tab>("list");
  const [requests, setRequests] = useState<BuyerRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [categories, setCategories] = useState<Category[]>([]);

  // Create form
  const [form, setForm] = useState<CreateFormState>(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [createError, setCreateError] = useState("");
  const [createSuccess, setCreateSuccess] = useState(false);

  // Offer detail modal
  const [offersModal, setOffersModal] = useState<BuyerRequest | null>(null);
  const [offers, setOffers] = useState<BuyerRequestOffer[]>([]);
  const [offersLoading, setOffersLoading] = useState(false);
  const [actionError, setActionError] = useState("");

  const fetchRequests = useCallback(async () => {
    setLoading(true);
    try {
      const res = await buyerRequestsApi.myRequests();
      setRequests(res.data || []);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRequests();
    gigsApi.getCategories().then((r) => setCategories(r.data)).catch(() => {});
  }, [fetchRequests]);

  const handleCreate = async () => {
    setCreateError("");
    const budgetMin = parseFloat(form.budget_min);
    const budgetMax = parseFloat(form.budget_max);
    const days = parseInt(form.delivery_days, 10);
    if (!form.title.trim() || form.title.length < 10) {
      setCreateError(ar ? "العنوان قصير (10 أحرف على الأقل)" : "Title too short (min 10 chars)");
      return;
    }
    if (!form.description.trim() || form.description.length < 20) {
      setCreateError(ar ? "الوصف قصير (20 حرفاً على الأقل)" : "Description too short (min 20 chars)");
      return;
    }
    if (!budgetMin || !budgetMax || budgetMin > budgetMax) {
      setCreateError(ar ? "تحقق من الميزانية" : "Check budget values");
      return;
    }
    if (!days || days < 1) {
      setCreateError(ar ? "أدخل مدة التسليم" : "Enter delivery days");
      return;
    }
    setSubmitting(true);
    try {
      await buyerRequestsApi.create({
        title: form.title.trim(),
        description: form.description.trim(),
        budget_min: budgetMin,
        budget_max: budgetMax,
        delivery_days: days,
        ...(form.category_id ? { category_id: form.category_id } : {}),
      });
      setCreateSuccess(true);
      setForm(EMPTY_FORM);
      await fetchRequests();
      setTimeout(() => {
        setCreateSuccess(false);
        setTab("list");
      }, 1500);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setCreateError(msg || (ar ? "فشل نشر الطلب" : "Failed to post request"));
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = async (id: string) => {
    if (!confirm(ar ? "هل تريد إلغاء هذا الطلب؟" : "Cancel this request?")) return;
    try {
      await buyerRequestsApi.cancel(id);
      await fetchRequests();
    } catch {
      // silent
    }
  };

  const openOffersModal = async (req: BuyerRequest) => {
    setOffersModal(req);
    setActionError("");
    setOffersLoading(true);
    try {
      const res = await buyerRequestsApi.listOffers(req.id);
      setOffers(res.data || []);
    } catch {
      setOffers([]);
    } finally {
      setOffersLoading(false);
    }
  };

  const handleAcceptOffer = async (offerId: string) => {
    if (!offersModal) return;
    setActionError("");
    try {
      await buyerRequestsApi.acceptOffer(offersModal.id, offerId);
      await fetchRequests();
      const res = await buyerRequestsApi.listOffers(offersModal.id);
      setOffers(res.data || []);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setActionError(msg || (ar ? "فشل قبول العرض" : "Failed to accept offer"));
    }
  };

  const handleRejectOffer = async (offerId: string) => {
    if (!offersModal) return;
    setActionError("");
    try {
      await buyerRequestsApi.rejectOffer(offersModal.id, offerId);
      const res = await buyerRequestsApi.listOffers(offersModal.id);
      setOffers(res.data || []);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setActionError(msg || (ar ? "فشل رفض العرض" : "Failed to reject offer"));
    }
  };

  const statusLabel = (s: string) => {
    const map: Record<string, { en: string; ar: string; color: string }> = {
      open:      { en: "Open",      ar: "مفتوح",    color: "bg-green-100 text-green-700" },
      filled:    { en: "Filled",    ar: "مكتمل",    color: "bg-blue-100 text-blue-700" },
      expired:   { en: "Expired",   ar: "منتهي",    color: "bg-gray-100 text-gray-600" },
      cancelled: { en: "Cancelled", ar: "ملغي",      color: "bg-red-100 text-red-600" },
    };
    const entry = map[s] ?? { en: s, ar: s, color: "bg-gray-100 text-gray-600" };
    return (
      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${entry.color}`}>
        {ar ? entry.ar : entry.en}
      </span>
    );
  };

  const offerStatusLabel = (s: string) => {
    const map: Record<string, { en: string; ar: string; color: string }> = {
      pending:  { en: "Pending",  ar: "بانتظار القرار", color: "bg-yellow-100 text-yellow-700" },
      accepted: { en: "Accepted", ar: "مقبول",          color: "bg-green-100 text-green-700" },
      rejected: { en: "Rejected", ar: "مرفوض",          color: "bg-red-100 text-red-600" },
    };
    const entry = map[s] ?? { en: s, ar: s, color: "bg-gray-100 text-gray-600" };
    return (
      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${entry.color}`}>
        {ar ? entry.ar : entry.en}
      </span>
    );
  };

  return (
    <div dir={ar ? "rtl" : "ltr"} className="max-w-3xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">
          {ar ? "طلباتي" : "My Requests"}
        </h1>
        <button
          onClick={() => setTab(tab === "create" ? "list" : "create")}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
        >
          {tab === "create"
            ? (ar ? "العودة للقائمة" : "Back to List")
            : (ar ? "+ نشر طلب جديد" : "+ Post New Request")}
        </button>
      </div>

      {/* Create Form */}
      {tab === "create" && (
        <div className="bg-white border border-gray-200 rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4 text-gray-800">
            {ar ? "نشر طلب جديد" : "Post a New Request"}
          </h2>
          {createSuccess ? (
            <div className="text-center py-8">
              <div className="text-4xl mb-2">✅</div>
              <p className="text-green-600 font-medium">
                {ar ? "تم نشر طلبك بنجاح!" : "Request posted successfully!"}
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {ar ? "العنوان" : "Title"}
                </label>
                <input
                  type="text"
                  value={form.title}
                  onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  placeholder={ar ? "مثال: أحتاج تصميم شعار لمطعم عراقي" : "e.g. Need a logo for an Iraqi restaurant"}
                  maxLength={200}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {ar ? "الوصف التفصيلي" : "Description"}
                </label>
                <textarea
                  rows={4}
                  value={form.description}
                  onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none resize-none"
                  placeholder={ar ? "اشرح ما تحتاجه بالتفصيل..." : "Describe what you need in detail..."}
                  maxLength={2000}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {ar ? "التصنيف (اختياري)" : "Category (optional)"}
                </label>
                <select
                  value={form.category_id}
                  onChange={(e) => setForm((f) => ({ ...f, category_id: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                >
                  <option value="">{ar ? "اختر تصنيفاً" : "Select category"}</option>
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>
                      {ar ? c.name_ar : c.name_en}
                    </option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {ar ? "الميزانية من (دينار)" : "Budget Min (IQD)"}
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={form.budget_min}
                    onChange={(e) => setForm((f) => ({ ...f, budget_min: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    placeholder="10000"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {ar ? "الميزانية إلى (دينار)" : "Budget Max (IQD)"}
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={form.budget_max}
                    onChange={(e) => setForm((f) => ({ ...f, budget_max: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    placeholder="50000"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {ar ? "أيام التسليم المطلوبة" : "Required Delivery Days"}
                </label>
                <input
                  type="number"
                  min="1"
                  max="90"
                  value={form.delivery_days}
                  onChange={(e) => setForm((f) => ({ ...f, delivery_days: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  placeholder="7"
                />
              </div>

              {createError && (
                <p className="text-red-500 text-sm">{createError}</p>
              )}

              <button
                onClick={handleCreate}
                disabled={submitting}
                className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium py-2.5 rounded-lg text-sm transition-colors"
              >
                {submitting
                  ? (ar ? "جاري النشر..." : "Posting...")
                  : (ar ? "نشر الطلب" : "Post Request")}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Request List */}
      {tab === "list" && (
        <>
          {loading ? (
            <div className="space-y-4">
              {[1, 2].map((i) => (
                <div key={i} className="bg-white border border-gray-200 rounded-xl p-5 animate-pulse">
                  <div className="h-5 bg-gray-200 rounded w-1/2 mb-3" />
                  <div className="h-4 bg-gray-100 rounded w-full mb-2" />
                </div>
              ))}
            </div>
          ) : requests.length === 0 ? (
            <div className="text-center py-16 text-gray-500">
              <p className="text-lg">{ar ? "لم تنشر أي طلب بعد" : "You haven't posted any requests yet"}</p>
              <button
                onClick={() => setTab("create")}
                className="mt-4 text-blue-600 hover:underline text-sm"
              >
                {ar ? "انشر أول طلب الآن" : "Post your first request"}
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {requests.map((req) => (
                <div key={req.id} className="bg-white border border-gray-200 rounded-xl p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold text-gray-900 text-base truncate">{req.title}</span>
                        {statusLabel(req.status)}
                      </div>
                      <p className="text-gray-600 text-sm mt-1 line-clamp-2">{req.description}</p>
                      <div className="flex flex-wrap gap-4 mt-2 text-sm text-gray-500">
                        <span>💰 {req.budget_min.toLocaleString()} – {req.budget_max.toLocaleString()} {ar ? "دينار" : "IQD"}</span>
                        <span>📅 {req.delivery_days} {ar ? "يوم" : "d"}</span>
                        <span>{req.offer_count} {ar ? "عروض" : "offers"}</span>
                      </div>
                    </div>
                    <div className="flex flex-col gap-2 shrink-0">
                      {req.offer_count > 0 && (
                        <button
                          onClick={() => openOffersModal(req)}
                          className="text-sm text-blue-600 hover:underline whitespace-nowrap"
                        >
                          {ar ? "عرض العروض" : "View Offers"}
                        </button>
                      )}
                      {req.status === "open" && (
                        <button
                          onClick={() => handleCancel(req.id)}
                          className="text-sm text-red-500 hover:underline whitespace-nowrap"
                        >
                          {ar ? "إلغاء" : "Cancel"}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Offers Modal */}
      {offersModal && (
        <div
          className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50 p-4"
          onClick={(e) => { if (e.target === e.currentTarget) setOffersModal(null); }}
        >
          <div
            dir={ar ? "rtl" : "ltr"}
            className="bg-white w-full max-w-lg rounded-t-2xl sm:rounded-2xl p-6 max-h-[90vh] overflow-y-auto"
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-900">
                {ar ? "العروض المستلمة" : "Received Offers"}
              </h2>
              <button
                onClick={() => setOffersModal(null)}
                className="text-gray-400 hover:text-gray-600 text-xl leading-none"
              >
                ✕
              </button>
            </div>
            <p className="text-sm text-gray-500 mb-4 line-clamp-1">{offersModal.title}</p>

            {actionError && (
              <p className="text-red-500 text-sm mb-3">{actionError}</p>
            )}

            {offersLoading ? (
              <div className="text-center py-6 text-gray-400">
                {ar ? "جاري التحميل..." : "Loading..."}
              </div>
            ) : offers.length === 0 ? (
              <div className="text-center py-6 text-gray-400">
                {ar ? "لا توجد عروض بعد" : "No offers yet"}
              </div>
            ) : (
              <div className="space-y-4">
                {offers.map((offer) => (
                  <div key={offer.id} className="border border-gray-200 rounded-xl p-4">
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <div className="flex items-center gap-2">
                        {offer.freelancer?.avatar_url ? (
                          <img
                            src={offer.freelancer.avatar_url}
                            alt=""
                            className="w-8 h-8 rounded-full object-cover"
                          />
                        ) : (
                          <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-sm text-gray-500">
                            {offer.freelancer?.first_name?.[0] ?? "?"}
                          </div>
                        )}
                        <div>
                          <p className="text-sm font-medium text-gray-900">
                            {offer.freelancer?.first_name} {offer.freelancer?.last_name}
                          </p>
                          {offer.freelancer?.avg_rating && offer.freelancer.avg_rating > 0 && (
                            <p className="text-xs text-yellow-500">
                              ★ {offer.freelancer.avg_rating.toFixed(1)}
                            </p>
                          )}
                        </div>
                      </div>
                      {offerStatusLabel(offer.status)}
                    </div>

                    <p className="text-sm text-gray-700 mb-2">{offer.message}</p>

                    <div className="flex gap-4 text-sm text-gray-500 mb-3">
                      <span>💰 {offer.price.toLocaleString()} {ar ? "دينار" : "IQD"}</span>
                      <span>📅 {offer.delivery_days} {ar ? "يوم" : "days"}</span>
                    </div>

                    {offer.gig && (
                      <a
                        href={`/gigs/${offer.gig.slug}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-blue-600 hover:underline"
                      >
                        🔗 {offer.gig.title}
                      </a>
                    )}

                    {offer.status === "pending" && offersModal.status === "open" && (
                      <div className="flex gap-2 mt-3">
                        <button
                          onClick={() => handleAcceptOffer(offer.id)}
                          className="flex-1 bg-green-600 hover:bg-green-700 text-white text-sm font-medium py-1.5 rounded-lg transition-colors"
                        >
                          {ar ? "قبول" : "Accept"}
                        </button>
                        <button
                          onClick={() => handleRejectOffer(offer.id)}
                          className="flex-1 border border-red-300 text-red-600 hover:bg-red-50 text-sm font-medium py-1.5 rounded-lg transition-colors"
                        >
                          {ar ? "رفض" : "Reject"}
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
