"use client";

import { useState, useEffect, useCallback } from "react";
import { reviewsApi, servicesApi } from "@/lib/api";
import type { ReviewSubmitBody } from "@/lib/api/reviews";
import { useAuthStore } from "@/lib/auth-store";
import { useLocale } from "@/providers/locale-provider";
import { toast } from "sonner";

interface RequirementQuestion {
  question: string;
  type: "text" | "file" | "multiple_choice";
  required: boolean;
  options: string[];
}

interface RequirementAnswer {
  question: string;
  answer: string;
}

interface ServiceRef {
  title: string;
  slug: string;
  requirement_questions?: RequirementQuestion[] | null;
}

interface ServiceOrderItem {
  id: string;
  service_id?: string;
  gig_id?: string;
  package_id: string;
  client_id: string;
  freelancer_id: string;
  status: string;
  requirements?: string;
  requirement_answers?: RequirementAnswer[] | null;
  requirements_submitted_at?: string | null;
  price_paid: number;
  delivery_days: number;
  revisions_remaining: number;
  due_date?: string;
  delivered_at?: string;
  completed_at?: string;
  created_at: string;
  service?: ServiceRef;
  gig?: ServiceRef;
  // Populated on list endpoints so the UI can hide the "Leave review" CTA
  // once the calling user has already reviewed this order.
  has_reviewed?: boolean | null;
}

const STATUS_LABELS_AR: Record<string, string> = {
  pending: "معلق",
  pending_requirements: "بانتظار المتطلبات",
  in_progress: "جارٍ",
  delivered: "مُسلَّم",
  revision_requested: "طلب مراجعة",
  completed: "مكتمل",
  cancelled: "ملغى",
  disputed: "متنازع عليه",
};

const STATUS_LABELS_EN: Record<string, string> = {
  pending: "Pending",
  pending_requirements: "Awaiting Requirements",
  in_progress: "In Progress",
  delivered: "Delivered",
  revision_requested: "Revision Requested",
  completed: "Completed",
  cancelled: "Cancelled",
  disputed: "Disputed",
};

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-50 text-yellow-700 border-yellow-200",
  pending_requirements: "bg-amber-50 text-amber-800 border-amber-200",
  in_progress: "bg-blue-50 text-blue-700 border-blue-200",
  delivered: "bg-indigo-50 text-indigo-700 border-indigo-200",
  revision_requested: "bg-orange-50 text-orange-700 border-orange-200",
  completed: "bg-green-50 text-green-700 border-green-200",
  cancelled: "bg-gray-50 text-gray-600 border-gray-200",
  disputed: "bg-red-50 text-red-700 border-red-200",
};

const TABS = [
  { value: "selling", labelAr: "طلباتي للتنفيذ", labelEn: "Selling" },
  { value: "buying", labelAr: "طلباتي المشتراة", labelEn: "Buying" },
];

function getServiceRef(order: ServiceOrderItem): ServiceRef | undefined {
  return order.service ?? order.gig;
}

export default function ServiceOrdersPage() {
  const { user } = useAuthStore();
  const { locale } = useLocale();
  const ar = locale === "ar";

  const [tab, setTab] = useState<"selling" | "buying">("selling");
  const [orders, setOrders] = useState<ServiceOrderItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [requirementsOrder, setRequirementsOrder] = useState<ServiceOrderItem | null>(null);
  const [deliverOrder, setDeliverOrder] = useState<ServiceOrderItem | null>(null);
  const [viewOrder, setViewOrder] = useState<ServiceOrderItem | null>(null);
  const [reviewOrder, setReviewOrder] = useState<ServiceOrderItem | null>(null);

  const isFreelancer = user?.primary_role === "freelancer";
  const statusLabels = ar ? STATUS_LABELS_AR : STATUS_LABELS_EN;

  const fetchOrders = useCallback(async () => {
    setIsLoading(true);
    try {
      const res =
        tab === "selling"
          ? await servicesApi.myOrdersAsSeller()
          : await servicesApi.myOrdersAsBuyer();
      setOrders(res.data);
    } catch {
      setOrders([]);
    } finally {
      setIsLoading(false);
    }
  }, [tab]);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  useEffect(() => {
    if (!isFreelancer) setTab("buying");
  }, [isFreelancer]);

  const handleDeliver = async (
    orderId: string,
    data: { message: string; files: string[] },
  ) => {
    setActionLoading(orderId);
    try {
      await servicesApi.markDelivered(orderId, data);
      toast.success(ar ? "تم تسليم الطلب" : "Order delivered");
      setDeliverOrder(null);
      fetchOrders();
    } catch {
      toast.error(ar ? "تعذّر تسليم الطلب" : "Failed to deliver order");
    } finally {
      setActionLoading(null);
    }
  };

  const handleComplete = async (orderId: string) => {
    if (!confirm(ar ? "هل تريد قبول التسليم وإتمام الطلب؟" : "Accept delivery and complete this order?")) return;
    setActionLoading(orderId);
    try {
      await servicesApi.completeOrder(orderId);
      toast.success(ar ? "تم إتمام الطلب" : "Order completed");
      fetchOrders();
    } catch {
      toast.error(ar ? "تعذّر إتمام الطلب" : "Failed to complete order");
    } finally {
      setActionLoading(null);
    }
  };

  const handleRevision = async (orderId: string) => {
    setActionLoading(orderId);
    try {
      await servicesApi.requestRevision(orderId);
      toast.success(ar ? "تم طلب المراجعة" : "Revision requested");
      fetchOrders();
    } catch {
      toast.error(ar ? "تعذّر طلب المراجعة" : "Failed to request revision");
    } finally {
      setActionLoading(null);
    }
  };

  const handleSubmitRequirements = async (
    orderId: string,
    answers: RequirementAnswer[],
  ) => {
    setActionLoading(orderId);
    try {
      await servicesApi.submitRequirements(orderId, answers);
      toast.success(ar ? "تم إرسال المتطلبات" : "Requirements submitted");
      setRequirementsOrder(null);
      fetchOrders();
    } catch {
      toast.error(ar ? "تعذّر إرسال المتطلبات" : "Failed to submit requirements");
    } finally {
      setActionLoading(null);
    }
  };

  const handleSubmitReview = async (orderId: string, data: ReviewSubmitBody) => {
    setActionLoading(orderId);
    try {
      await reviewsApi.submitOrderReview(orderId, data);
      toast.success(ar ? "تم إرسال التقييم" : "Review submitted");
      setReviewOrder(null);
      fetchOrders();
    } catch {
      toast.error(ar ? "تعذّر إرسال التقييم" : "Failed to submit review");
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          {ar ? "طلبات الخدمات" : "Service Orders"}
        </h1>
        <p className="mt-1 text-gray-600">
          {ar ? "إدارة طلبات الخدمات المرسلة والمستلمة" : "Manage your sent and received service orders"}
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        {TABS.filter((t) => t.value === "selling" ? isFreelancer : true).map((t) => (
          <button
            key={t.value}
            onClick={() => setTab(t.value as "selling" | "buying")}
            className={`px-5 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === t.value
                ? "border-brand-500 text-brand-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {ar ? t.labelAr : t.labelEn}
          </button>
        ))}
      </div>

      {/* Orders list */}
      {isLoading ? (
        <div className="text-center py-16 text-gray-500">
          {ar ? "جاري التحميل..." : "Loading..."}
        </div>
      ) : orders.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-lg font-medium text-gray-900">
            {ar ? "لا توجد طلبات" : "No orders found"}
          </p>
          <p className="mt-2 text-gray-500">
            {tab === "selling"
              ? (ar ? "ستظهر هنا الطلبات التي يرسلها العملاء لخدماتك." : "Orders from clients for your services will appear here.")
              : (ar ? "ستظهر هنا الطلبات التي اشتريتها من المستقلين." : "Services you've ordered from freelancers will appear here.")}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {orders.map((order) => (
            <OrderCard
              key={order.id}
              order={order}
              view={tab}
              ar={ar}
              statusLabels={statusLabels}
              actionLoading={actionLoading}
              onComplete={handleComplete}
              onRevision={handleRevision}
              onOpenRequirements={() => setRequirementsOrder(order)}
              onOpenDeliver={() => setDeliverOrder(order)}
              onViewDelivery={() => setViewOrder(order)}
              onOpenReview={() => setReviewOrder(order)}
            />
          ))}
        </div>
      )}

      {requirementsOrder && (
        <RequirementsModal
          order={requirementsOrder}
          ar={ar}
          isBusy={actionLoading === requirementsOrder.id}
          onClose={() => setRequirementsOrder(null)}
          onSubmit={(answers) => handleSubmitRequirements(requirementsOrder.id, answers)}
        />
      )}

      {deliverOrder && (
        <DeliverModal
          order={deliverOrder}
          ar={ar}
          isBusy={actionLoading === deliverOrder.id}
          onClose={() => setDeliverOrder(null)}
          onSubmit={(data) => handleDeliver(deliverOrder.id, data)}
        />
      )}

      {viewOrder && (
        <DeliveryView
          order={viewOrder}
          ar={ar}
          onClose={() => setViewOrder(null)}
        />
      )}

      {reviewOrder && (
        <ReviewModal
          order={reviewOrder}
          ar={ar}
          isBusy={actionLoading === reviewOrder.id}
          onClose={() => setReviewOrder(null)}
          onSubmit={(data) => handleSubmitReview(reviewOrder.id, data)}
        />
      )}
    </div>
  );
}

function OrderCard({
  order,
  view,
  ar,
  statusLabels,
  actionLoading,
  onComplete,
  onRevision,
  onOpenRequirements,
  onOpenDeliver,
  onViewDelivery,
  onOpenReview,
}: {
  order: ServiceOrderItem;
  view: "selling" | "buying";
  ar: boolean;
  statusLabels: Record<string, string>;
  actionLoading: string | null;
  onComplete: (id: string) => void;
  onRevision: (id: string) => void;
  onOpenRequirements: () => void;
  onOpenDeliver: () => void;
  onViewDelivery: () => void;
  onOpenReview: () => void;
}) {
  const isBusy = actionLoading === order.id;
  const canViewDelivery =
    order.status === "delivered" ||
    order.status === "revision_requested" ||
    order.status === "completed";
  const svc = getServiceRef(order);

  return (
    <div className="card p-5">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="font-semibold text-gray-900 truncate">
              {svc?.title ?? (ar ? "خدمة" : "Service")}
            </span>
            <span className={`shrink-0 px-2.5 py-0.5 text-xs font-medium rounded-full border ${STATUS_COLORS[order.status] ?? "bg-gray-50 text-gray-600 border-gray-200"}`}>
              {statusLabels[order.status] ?? order.status}
            </span>
          </div>

          <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-gray-500 mt-1">
            <span>
              {ar ? "السعر:" : "Price:"}{" "}
              <span className="font-medium text-gray-900" dir="ltr">
                {order.price_paid.toLocaleString(ar ? "ar-IQ" : "en-US")} {ar ? "د.ع" : "IQD"}
              </span>
            </span>
            <span>{ar ? `مدة التسليم: ${order.delivery_days} يوم` : `Delivery: ${order.delivery_days} day${order.delivery_days !== 1 ? "s" : ""}`}</span>
            {order.revisions_remaining >= 0 && (
              <span>{ar ? `المراجعات المتبقية: ${order.revisions_remaining}` : `Revisions left: ${order.revisions_remaining}`}</span>
            )}
            {order.due_date && (
              <span>
                {ar ? "الموعد النهائي: " : "Due: "}
                {new Date(order.due_date).toLocaleDateString(ar ? "ar-IQ" : "en-US", { month: "short", day: "numeric" })}
              </span>
            )}
            <span>
              {ar ? "طُلب " : "Ordered "}
              {new Date(order.created_at).toLocaleDateString(ar ? "ar-IQ" : "en-US", { month: "short", day: "numeric" })}
            </span>
          </div>

          {order.requirements && (
            <p className="mt-2 text-sm text-gray-600 line-clamp-2 bg-gray-50 p-2 rounded">
              {order.requirements}
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-2 shrink-0 flex-wrap">
          {view === "buying" && order.status === "pending_requirements" && (
            <button
              onClick={onOpenRequirements}
              disabled={isBusy}
              className="btn-primary py-1.5 px-4 text-sm disabled:opacity-50"
            >
              {isBusy ? "..." : (ar ? "إرسال المتطلبات" : "Submit Requirements")}
            </button>
          )}
          {view === "selling" &&
            (order.status === "in_progress" || order.status === "revision_requested") && (
              <button
                onClick={onOpenDeliver}
                disabled={isBusy}
                className="btn-primary py-1.5 px-4 text-sm disabled:opacity-50"
              >
                {isBusy
                  ? "..."
                  : order.status === "revision_requested"
                    ? (ar ? "تسليم المراجعة" : "Deliver Revision")
                    : (ar ? "تسليم الطلب" : "Deliver")}
              </button>
            )}
          {canViewDelivery && (
            <button
              onClick={onViewDelivery}
              className="btn-secondary py-1.5 px-4 text-sm"
            >
              {ar ? "عرض التسليم" : "View Delivery"}
            </button>
          )}
          {view === "buying" && order.status === "delivered" && (
            <>
              <button
                onClick={() => onComplete(order.id)}
                disabled={isBusy}
                className="btn-primary py-1.5 px-4 text-sm disabled:opacity-50"
              >
                {isBusy ? "..." : (ar ? "قبول التسليم" : "Accept")}
              </button>
              {order.revisions_remaining > 0 && (
                <button
                  onClick={() => onRevision(order.id)}
                  disabled={isBusy}
                  className="btn-secondary py-1.5 px-4 text-sm disabled:opacity-50"
                >
                  {ar ? "طلب مراجعة" : "Request Revision"}
                </button>
              )}
            </>
          )}
          {order.status === "completed" && order.has_reviewed === false && (
            <button
              onClick={onOpenReview}
              disabled={isBusy}
              className="btn-primary py-1.5 px-4 text-sm disabled:opacity-50"
            >
              {isBusy ? "..." : (ar ? "اترك تقييماً" : "Leave Review")}
            </button>
          )}
          {order.status === "completed" && order.has_reviewed === true && (
            <span className="px-3 py-1.5 text-xs font-medium text-green-700 bg-green-50 border border-green-200 rounded-full">
              {ar ? "تم التقييم ✓" : "Reviewed ✓"}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function RequirementsModal({
  order,
  ar,
  isBusy,
  onClose,
  onSubmit,
}: {
  order: ServiceOrderItem;
  ar: boolean;
  isBusy: boolean;
  onClose: () => void;
  onSubmit: (answers: RequirementAnswer[]) => void;
}) {
  const svc = getServiceRef(order);
  const questions: RequirementQuestion[] = svc?.requirement_questions ?? [];
  const [answers, setAnswers] = useState<string[]>(() =>
    questions.map(() => ""),
  );
  const [error, setError] = useState<string | null>(null);

  const handleChange = (index: number, value: string) => {
    setAnswers((prev) => {
      const next = [...prev];
      next[index] = value;
      return next;
    });
  };

  const handleSubmit = () => {
    for (let i = 0; i < questions.length; i++) {
      const q = questions[i];
      if (q.required && !answers[i].trim()) {
        setError(
          ar
            ? `الرجاء الإجابة على السؤال ${i + 1}`
            : `Please answer question ${i + 1}`,
        );
        return;
      }
    }
    setError(null);
    const payload: RequirementAnswer[] = questions
      .map((q, i) => ({ question: q.question, answer: answers[i].trim() }))
      .filter((a) => a.answer.length > 0);
    if (payload.length === 0) {
      setError(ar ? "يجب إضافة إجابة واحدة على الأقل" : "At least one answer is required");
      return;
    }
    onSubmit(payload);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="text-lg font-semibold text-gray-900">
            {ar ? "متطلبات الطلب" : "Order Requirements"}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
            aria-label={ar ? "إغلاق" : "Close"}
          >
            ×
          </button>
        </div>

        <div className="p-5 space-y-4">
          <p className="text-sm text-gray-600">
            {ar
              ? "يحتاج المستقل إلى هذه المعلومات لبدء العمل على طلبك."
              : "The freelancer needs this information to start working on your order."}
          </p>

          {questions.length === 0 ? (
            <p className="text-sm text-gray-500 italic">
              {ar
                ? "لا توجد أسئلة محددة. يمكنك المتابعة مباشرة."
                : "No specific questions. You can proceed."}
            </p>
          ) : (
            questions.map((q, i) => (
              <div key={i} className="space-y-1.5">
                <label className="block text-sm font-medium text-gray-800">
                  {i + 1}. {q.question}
                  {q.required && <span className="text-red-500 ms-1">*</span>}
                </label>
                {q.type === "multiple_choice" && q.options.length > 0 ? (
                  <select
                    value={answers[i]}
                    onChange={(e) => handleChange(i, e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  >
                    <option value="">
                      {ar ? "اختر إجابة..." : "Select an answer..."}
                    </option>
                    {q.options.map((opt) => (
                      <option key={opt} value={opt}>{opt}</option>
                    ))}
                  </select>
                ) : (
                  <textarea
                    value={answers[i]}
                    onChange={(e) => handleChange(i, e.target.value)}
                    rows={3}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                    placeholder={ar ? "اكتب إجابتك..." : "Type your answer..."}
                  />
                )}
              </div>
            ))
          )}

          {error && (
            <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-3">
              {error}
            </div>
          )}
        </div>

        <div className="flex gap-2 justify-end p-5 border-t bg-gray-50">
          <button
            onClick={onClose}
            disabled={isBusy}
            className="btn-secondary py-2 px-4 text-sm disabled:opacity-50"
          >
            {ar ? "إلغاء" : "Cancel"}
          </button>
          <button
            onClick={handleSubmit}
            disabled={isBusy || questions.length === 0}
            className="btn-primary py-2 px-4 text-sm disabled:opacity-50"
          >
            {isBusy ? (ar ? "جاري الإرسال..." : "Submitting...") : (ar ? "إرسال" : "Submit")}
          </button>
        </div>
      </div>
    </div>
  );
}

function DeliverModal({
  order,
  ar,
  isBusy,
  onClose,
  onSubmit,
}: {
  order: ServiceOrderItem;
  ar: boolean;
  isBusy: boolean;
  onClose: () => void;
  onSubmit: (data: { message: string; files: string[] }) => void;
}) {
  const [message, setMessage] = useState("");
  const [fileUrls, setFileUrls] = useState<string[]>([""]);
  const [error, setError] = useState<string | null>(null);

  const isRevision = order.status === "revision_requested";

  const updateFile = (index: number, value: string) => {
    setFileUrls((prev) => {
      const next = [...prev];
      next[index] = value;
      return next;
    });
  };
  const addFile = () => setFileUrls((prev) => [...prev, ""]);
  const removeFile = (index: number) =>
    setFileUrls((prev) => prev.filter((_, i) => i !== index));

  const handleSubmit = () => {
    if (message.trim().length < 5) {
      setError(ar ? "الرسالة يجب أن تكون 5 أحرف على الأقل" : "Message must be at least 5 characters");
      return;
    }
    const cleanFiles = fileUrls.map((u) => u.trim()).filter((u) => u.length > 0);
    for (const url of cleanFiles) {
      try {
        const parsed = new URL(url);
        if (!["http:", "https:"].includes(parsed.protocol)) {
          throw new Error("bad scheme");
        }
      } catch {
        setError(ar ? `رابط غير صالح: ${url}` : `Invalid URL: ${url}`);
        return;
      }
    }
    setError(null);
    onSubmit({ message: message.trim(), files: cleanFiles });
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="text-lg font-semibold text-gray-900">
            {isRevision
              ? (ar ? "تسليم المراجعة" : "Deliver Revision")
              : (ar ? "تسليم الطلب" : "Deliver Order")}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
            aria-label={ar ? "إغلاق" : "Close"}
          >
            ×
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-800 mb-1.5">
              {ar ? "رسالة التسليم" : "Delivery message"}
              <span className="text-red-500 ms-1">*</span>
            </label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={5}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              placeholder={
                ar
                  ? "اشرح ما تم إنجازه وأي تعليمات للعميل..."
                  : "Describe what was completed and any notes for the client..."
              }
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-800 mb-1.5">
              {ar ? "روابط الملفات (اختياري)" : "File links (optional)"}
            </label>
            <p className="text-xs text-gray-500 mb-2">
              {ar
                ? "ألصق روابط Google Drive أو Dropbox أو أي خدمة مشاركة ملفات."
                : "Paste Google Drive, Dropbox, or any file-share URL."}
            </p>
            <div className="space-y-2">
              {fileUrls.map((url, i) => (
                <div key={i} className="flex gap-2">
                  <input
                    type="url"
                    value={url}
                    onChange={(e) => updateFile(i, e.target.value)}
                    placeholder="https://..."
                    dir="ltr"
                    className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  />
                  {fileUrls.length > 1 && (
                    <button
                      onClick={() => removeFile(i)}
                      className="px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg"
                      aria-label={ar ? "إزالة" : "Remove"}
                    >
                      ×
                    </button>
                  )}
                </div>
              ))}
              <button
                onClick={addFile}
                className="text-sm text-brand-600 hover:underline"
              >
                + {ar ? "إضافة رابط آخر" : "Add another link"}
              </button>
            </div>
          </div>

          {error && (
            <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-3">
              {error}
            </div>
          )}
        </div>

        <div className="flex gap-2 justify-end p-5 border-t bg-gray-50">
          <button
            onClick={onClose}
            disabled={isBusy}
            className="btn-secondary py-2 px-4 text-sm disabled:opacity-50"
          >
            {ar ? "إلغاء" : "Cancel"}
          </button>
          <button
            onClick={handleSubmit}
            disabled={isBusy}
            className="btn-primary py-2 px-4 text-sm disabled:opacity-50"
          >
            {isBusy
              ? (ar ? "جاري التسليم..." : "Delivering...")
              : (ar ? "تسليم" : "Deliver")}
          </button>
        </div>
      </div>
    </div>
  );
}

interface DeliveryRecord {
  id: string;
  order_id: string;
  message: string;
  files: string[];
  revision_number: number;
  created_at: string;
}

function DeliveryView({
  order,
  ar,
  onClose,
}: {
  order: ServiceOrderItem;
  ar: boolean;
  onClose: () => void;
}) {
  const [deliveries, setDeliveries] = useState<DeliveryRecord[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await servicesApi.listDeliveries(order.id);
        if (!cancelled) setDeliveries(res.data);
      } catch {
        if (!cancelled) setError(ar ? "تعذّر تحميل التسليم" : "Failed to load delivery");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [order.id, ar]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="text-lg font-semibold text-gray-900">
            {ar ? "تفاصيل التسليم" : "Delivery Details"}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
            aria-label={ar ? "إغلاق" : "Close"}
          >
            ×
          </button>
        </div>

        <div className="p-5 space-y-4">
          {error && (
            <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-3">
              {error}
            </div>
          )}
          {!error && deliveries === null && (
            <p className="text-sm text-gray-500">{ar ? "جاري التحميل..." : "Loading..."}</p>
          )}
          {deliveries !== null && deliveries.length === 0 && (
            <p className="text-sm text-gray-500">
              {ar ? "لا توجد تسليمات بعد." : "No deliveries yet."}
            </p>
          )}
          {deliveries?.map((d) => (
            <div key={d.id} className="border border-gray-200 rounded-lg p-4 space-y-2">
              <div className="flex items-center justify-between text-xs text-gray-500">
                <span className="font-medium text-gray-700">
                  {d.revision_number === 0
                    ? (ar ? "التسليم الأصلي" : "Original delivery")
                    : (ar ? `مراجعة ${d.revision_number}` : `Revision ${d.revision_number}`)}
                </span>
                <span>
                  {new Date(d.created_at).toLocaleDateString(ar ? "ar-IQ" : "en-US", {
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              </div>
              <p className="text-sm text-gray-800 whitespace-pre-wrap">{d.message}</p>
              {d.files.length > 0 && (
                <div className="space-y-1">
                  <p className="text-xs font-medium text-gray-600">
                    {ar ? "الملفات:" : "Files:"}
                  </p>
                  <ul className="space-y-1">
                    {d.files.map((url, i) => (
                      <li key={i}>
                        <a
                          href={url}
                          target="_blank"
                          rel="noopener noreferrer"
                          dir="ltr"
                          className="text-sm text-brand-600 hover:underline break-all"
                        >
                          {url}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="flex justify-end p-5 border-t bg-gray-50">
          <button onClick={onClose} className="btn-secondary py-2 px-4 text-sm">
            {ar ? "إغلاق" : "Close"}
          </button>
        </div>
      </div>
    </div>
  );
}

function ReviewModal({
  order,
  ar,
  isBusy,
  onClose,
  onSubmit,
}: {
  order: ServiceOrderItem;
  ar: boolean;
  isBusy: boolean;
  onClose: () => void;
  onSubmit: (data: ReviewSubmitBody) => void;
}) {
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [communication, setCommunication] = useState(5);
  const [quality, setQuality] = useState(5);
  const [professionalism, setProfessionalism] = useState(5);
  const [timeliness, setTimeliness] = useState(5);
  const svc = getServiceRef(order);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      rating,
      comment: comment.trim() || undefined,
      communication_rating: communication,
      quality_rating: quality,
      professionalism_rating: professionalism,
      timeliness_rating: timeliness,
    });
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        <div className="p-5 border-b">
          <h2 className="text-lg font-semibold text-gray-900">
            {ar ? "اترك تقييمك" : "Leave a review"}
          </h2>
          <p className="mt-1 text-sm text-gray-500 truncate">
            {svc?.title ?? (ar ? "خدمة" : "Service")}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-5">
          <StarField
            label={ar ? "التقييم العام" : "Overall rating"}
            value={rating}
            onChange={setRating}
            ar={ar}
            required
          />
          <StarField
            label={ar ? "التواصل" : "Communication"}
            value={communication}
            onChange={setCommunication}
            ar={ar}
          />
          <StarField
            label={ar ? "الجودة" : "Quality"}
            value={quality}
            onChange={setQuality}
            ar={ar}
          />
          <StarField
            label={ar ? "الاحترافية" : "Professionalism"}
            value={professionalism}
            onChange={setProfessionalism}
            ar={ar}
          />
          <StarField
            label={ar ? "الالتزام بالوقت" : "Timeliness"}
            value={timeliness}
            onChange={setTimeliness}
            ar={ar}
          />

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {ar ? "تعليقك (اختياري)" : "Your comment (optional)"}
            </label>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              maxLength={2000}
              rows={4}
              placeholder={ar ? "شارك تجربتك..." : "Share your experience..."}
              className="input-field"
            />
            <p className="mt-1 text-xs text-gray-500">
              {comment.length}/2000
            </p>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isBusy}
              className="btn-secondary py-2 px-4 text-sm"
            >
              {ar ? "إلغاء" : "Cancel"}
            </button>
            <button
              type="submit"
              disabled={isBusy}
              className="btn-primary py-2 px-4 text-sm disabled:opacity-50"
            >
              {isBusy ? "..." : (ar ? "إرسال التقييم" : "Submit Review")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function StarField({
  label,
  value,
  onChange,
  ar,
  required = false,
}: {
  label: string;
  value: number;
  onChange: (n: number) => void;
  ar: boolean;
  required?: boolean;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <div className={`flex gap-1 ${ar ? "flex-row-reverse justify-end" : ""}`} dir="ltr">
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            onClick={() => onChange(n)}
            aria-label={`${n} star${n !== 1 ? "s" : ""}`}
            className={`text-2xl transition-colors ${
              n <= value ? "text-yellow-400" : "text-gray-300 hover:text-yellow-300"
            }`}
          >
            ★
          </button>
        ))}
      </div>
    </div>
  );
}
