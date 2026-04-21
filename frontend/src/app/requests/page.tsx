"use client";

import { useEffect, useState, useCallback } from "react";
import { useLocale } from "@/providers/locale-provider";
import { buyerRequestsApi, servicesApi } from "@/lib/api";
import type { BuyerRequest, BuyerRequestOffer, BuyerRequestListResponse } from "@/types/buyer_request";

interface Category {
  id: string;
  name_en: string;
  name_ar: string;
}

interface OfferFormState {
  price: string;
  delivery_days: string;
  message: string;
  service_id: string;
}

export default function RequestsPage() {
  const { locale } = useLocale();
  const ar = locale === "ar";

  const [requests, setRequests] = useState<BuyerRequest[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Offer modal state
  const [offerModalRequest, setOfferModalRequest] = useState<BuyerRequest | null>(null);
  const [offerForm, setOfferForm] = useState<OfferFormState>({
    price: "",
    delivery_days: "",
    message: "",
    service_id: "",
  });
  const [myServices, setMyServices] = useState<{ id: string; title: string }[]>([]);
  const [submittingOffer, setSubmittingOffer] = useState(false);
  const [offerSuccess, setOfferSuccess] = useState("");
  const [offerError, setOfferError] = useState("");

  const PAGE_SIZE = 20;

  const fetchRequests = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await buyerRequestsApi.list({
        page,
        page_size: PAGE_SIZE,
        ...(selectedCategory ? { category_id: selectedCategory } : {}),
      });
      const data: BuyerRequestListResponse = res.data;
      setRequests(data.items);
      setTotal(data.total);
    } catch {
      setError(ar ? "فشل في تحميل الطلبات" : "Failed to load requests");
    } finally {
      setLoading(false);
    }
  }, [page, selectedCategory, ar]);

  useEffect(() => {
    fetchRequests();
  }, [fetchRequests]);

  useEffect(() => {
    servicesApi.getCategories().then((r) => setCategories(r.data)).catch(() => {});
    servicesApi.myServices().then((r) => {
      const list = r.data || [];
      setMyServices(list.map((s: { id: string; title: string }) => ({ id: s.id, title: s.title })));
    }).catch(() => {});
  }, []);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const openOfferModal = (req: BuyerRequest) => {
    setOfferModalRequest(req);
    setOfferForm({ price: "", delivery_days: "", message: "", service_id: "" });
    setOfferError("");
    setOfferSuccess("");
  };

  const closeOfferModal = () => {
    setOfferModalRequest(null);
    setOfferError("");
    setOfferSuccess("");
  };

  const submitOffer = async () => {
    if (!offerModalRequest) return;
    const price = parseFloat(offerForm.price);
    const deliveryDays = parseInt(offerForm.delivery_days, 10);
    if (!price || price <= 0) {
      setOfferError(ar ? "أدخل سعراً صحيحاً" : "Enter a valid price");
      return;
    }
    if (!deliveryDays || deliveryDays < 1) {
      setOfferError(ar ? "أدخل عدد أيام التسليم" : "Enter delivery days");
      return;
    }
    if (offerForm.message.trim().length < 20) {
      setOfferError(ar ? "الرسالة قصيرة جداً (20 حرف على الأقل)" : "Message too short (min 20 chars)");
      return;
    }
    setSubmittingOffer(true);
    setOfferError("");
    try {
      await buyerRequestsApi.sendOffer(offerModalRequest.id, {
        price,
        delivery_days: deliveryDays,
        message: offerForm.message.trim(),
        ...(offerForm.service_id ? { service_id: offerForm.service_id } : {}),
      });
      setOfferSuccess(ar ? "تم إرسال عرضك بنجاح!" : "Offer sent successfully!");
      setTimeout(() => {
        closeOfferModal();
        fetchRequests();
      }, 1500);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setOfferError(msg || (ar ? "فشل إرسال العرض" : "Failed to send offer"));
    } finally {
      setSubmittingOffer(false);
    }
  };

  const formatBudget = (min: number, max: number) =>
    `${min.toLocaleString()} – ${max.toLocaleString()} ${ar ? "دينار" : "IQD"}`;

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString(ar ? "ar-IQ" : "en-US", {
      day: "numeric",
      month: "short",
    });

  return (
    <div dir={ar ? "rtl" : "ltr"} className="max-w-4xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">
          {ar ? "طلبات المشترين" : "Buyer Requests"}
        </h1>
        <p className="text-gray-500 mt-1 text-sm">
          {ar
            ? "تصفح الطلبات المفتوحة وأرسل عرضك المناسب"
            : "Browse open requests and send your best offer"}
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <select
          value={selectedCategory}
          onChange={(e) => { setSelectedCategory(e.target.value); setPage(1); }}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
        >
          <option value="">{ar ? "جميع التصنيفات" : "All Categories"}</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {ar ? c.name_ar : c.name_en}
            </option>
          ))}
        </select>
      </div>

      {/* Content */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white border border-gray-200 rounded-xl p-5 animate-pulse">
              <div className="h-5 bg-gray-200 rounded w-2/3 mb-3" />
              <div className="h-4 bg-gray-100 rounded w-full mb-2" />
              <div className="h-4 bg-gray-100 rounded w-4/5" />
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="text-center py-12 text-red-500">{error}</div>
      ) : requests.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <p className="text-lg">{ar ? "لا توجد طلبات مفتوحة حالياً" : "No open requests right now"}</p>
          <p className="text-sm mt-1">{ar ? "تحقق مجدداً لاحقاً" : "Check back later"}</p>
        </div>
      ) : (
        <div className="space-y-4">
          {requests.map((req) => (
            <div
              key={req.id}
              className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <h2 className="font-semibold text-gray-900 text-base truncate">{req.title}</h2>
                  <p className="text-gray-600 text-sm mt-1 line-clamp-2">{req.description}</p>

                  <div className="flex flex-wrap gap-4 mt-3 text-sm text-gray-500">
                    <span>
                      💰 {formatBudget(req.budget_min, req.budget_max)}
                    </span>
                    <span>
                      📅 {req.delivery_days} {ar ? "يوم" : "days"}
                    </span>
                    {req.category && (
                      <span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full text-xs">
                        {ar ? req.category.name_ar : req.category.name_en}
                      </span>
                    )}
                    <span className="text-gray-400">
                      {req.offer_count} {ar ? "عروض" : "offers"}
                    </span>
                    <span className="text-gray-400">
                      {ar ? "ينتهي" : "Expires"} {formatDate(req.expires_at)}
                    </span>
                  </div>

                  {req.client && (
                    <div className="flex items-center gap-2 mt-3">
                      {req.client.avatar_url ? (
                        <img
                          src={req.client.avatar_url}
                          alt=""
                          className="w-6 h-6 rounded-full object-cover"
                        />
                      ) : (
                        <div className="w-6 h-6 rounded-full bg-gray-200 flex items-center justify-center text-xs text-gray-500">
                          {req.client.first_name[0]}
                        </div>
                      )}
                      <span className="text-xs text-gray-500">
                        {req.client.first_name} {req.client.last_name}
                      </span>
                    </div>
                  )}
                </div>

                <button
                  onClick={() => openOfferModal(req)}
                  className="shrink-0 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
                >
                  {ar ? "أرسل عرضاً" : "Send Offer"}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2 mt-8">
          <button
            disabled={page === 1}
            onClick={() => setPage((p) => p - 1)}
            className="px-4 py-2 border border-gray-300 rounded-lg text-sm disabled:opacity-40 hover:bg-gray-50"
          >
            {ar ? "السابق" : "Previous"}
          </button>
          <span className="px-4 py-2 text-sm text-gray-600">
            {page} / {totalPages}
          </span>
          <button
            disabled={page === totalPages}
            onClick={() => setPage((p) => p + 1)}
            className="px-4 py-2 border border-gray-300 rounded-lg text-sm disabled:opacity-40 hover:bg-gray-50"
          >
            {ar ? "التالي" : "Next"}
          </button>
        </div>
      )}

      {/* Offer Modal */}
      {offerModalRequest && (
        <div
          className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50 p-4"
          onClick={(e) => { if (e.target === e.currentTarget) closeOfferModal(); }}
        >
          <div
            dir={ar ? "rtl" : "ltr"}
            className="bg-white w-full max-w-lg rounded-t-2xl sm:rounded-2xl p-6 max-h-[90vh] overflow-y-auto"
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-900">
                {ar ? "أرسل عرضاً" : "Send Offer"}
              </h2>
              <button
                onClick={closeOfferModal}
                className="text-gray-400 hover:text-gray-600 text-xl leading-none"
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            <p className="text-sm text-gray-500 mb-4 line-clamp-2">
              {offerModalRequest.title}
            </p>

            {offerSuccess ? (
              <div className="text-center py-6">
                <div className="text-4xl mb-2">✅</div>
                <p className="text-green-600 font-medium">{offerSuccess}</p>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {ar ? "السعر (دينار)" : "Price (IQD)"}
                    </label>
                    <input
                      type="number"
                      min="1"
                      value={offerForm.price}
                      onChange={(e) => setOfferForm((f) => ({ ...f, price: e.target.value }))}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                      placeholder="50000"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {ar ? "أيام التسليم" : "Delivery Days"}
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="90"
                      value={offerForm.delivery_days}
                      onChange={(e) => setOfferForm((f) => ({ ...f, delivery_days: e.target.value }))}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                      placeholder="7"
                    />
                  </div>
                </div>

                {myServices.length > 0 && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {ar ? "ربط بخدمة (اختياري)" : "Link to a Service (optional)"}
                    </label>
                    <select
                      value={offerForm.service_id}
                      onChange={(e) => setOfferForm((f) => ({ ...f, service_id: e.target.value }))}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    >
                      <option value="">{ar ? "بدون ربط" : "No service link"}</option>
                      {myServices.map((s) => (
                        <option key={s.id} value={s.id}>{s.title}</option>
                      ))}
                    </select>
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {ar ? "رسالتك للعميل" : "Your Message"}
                  </label>
                  <textarea
                    rows={4}
                    value={offerForm.message}
                    onChange={(e) => setOfferForm((f) => ({ ...f, message: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none resize-none"
                    placeholder={
                      ar
                        ? "اشرح كيف ستنجز هذا الطلب وما يميز عرضك..."
                        : "Explain how you'll complete this request and what sets your offer apart..."
                    }
                    autoFocus
                  />
                  <p className="text-xs text-gray-400 mt-1">{offerForm.message.length}/1000</p>
                </div>

                {offerError && (
                  <p className="text-red-500 text-sm">{offerError}</p>
                )}

                <div className="flex gap-3 pt-2">
                  <button
                    onClick={submitOffer}
                    disabled={submittingOffer}
                    className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium py-2.5 rounded-lg text-sm transition-colors"
                  >
                    {submittingOffer
                      ? (ar ? "جاري الإرسال..." : "Sending...")
                      : (ar ? "أرسل العرض" : "Send Offer")}
                  </button>
                  <button
                    onClick={closeOfferModal}
                    className="px-4 py-2.5 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50"
                  >
                    {ar ? "إلغاء" : "Cancel"}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
