"use client";

interface PendingService {
  id: string;
  title: string;
  slug: string;
  description: string;
  status: string;
  rejection_reason: string | null;
  revision_note: string | null;
  tags: string[] | null;
  created_at: string;
  freelancer: { id: string; username: string; email: string; avg_rating: number };
  packages: { tier: string; price: number; delivery_days: number; name: string }[];
}

interface ServicesTabProps {
  pendingServices: PendingService[];
  loading: boolean;
  actionLoading: string | null;
  modalState: { type: "revision" | "reject"; serviceId: string; serviceTitle: string } | null;
  modalText: string;
  ar: boolean;
  dateLocale: string;
  onApprove: (serviceId: string) => void;
  onOpenModal: (type: "revision" | "reject", serviceId: string, serviceTitle: string) => void;
  onCloseModal: () => void;
  onModalTextChange: (v: string) => void;
  onModalSubmit: () => void;
}

export function ServicesTab({
  pendingServices, loading, actionLoading, modalState, modalText,
  ar, dateLocale,
  onApprove, onOpenModal, onCloseModal, onModalTextChange, onModalSubmit,
}: ServicesTabProps) {
  const statusLabels: Record<string, string> = ar
    ? { pending_review: "قيد المراجعة", needs_revision: "يحتاج تعديل", active: "نشط", rejected: "مرفوض", paused: "موقوف", draft: "مسودة", archived: "مؤرشف" }
    : { pending_review: "Pending Review", needs_revision: "Needs Revision", active: "Active", rejected: "Rejected", paused: "Paused", draft: "Draft", archived: "Archived" };

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-gray-800">
          {ar ? "خدمات قيد المراجعة" : "Services Pending Review"}
        </h2>
        <p className="text-sm text-gray-500 mt-0.5">
          {ar
            ? "راجع كل خدمة وافقها، اطلب تعديلاً، أو ارفضها مع ذكر السبب."
            : "Review each service, approve it, request specific edits, or reject it with a reason."}
        </p>
      </div>

      {loading ? (
        <div className="text-center text-gray-400 py-12">
          {ar ? "جاري التحميل..." : "Loading..."}
        </div>
      ) : pendingServices.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-xl p-12 text-center">
          <div className="text-4xl mb-3">✅</div>
          <p className="text-gray-500 font-medium">
            {ar ? "لا توجد خدمات قيد المراجعة" : "No services pending review"}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {pendingServices.map((service) => (
            <div key={service.id} className="bg-white border border-gray-200 rounded-xl overflow-hidden">
              {/* Header */}
              <div className="flex items-start justify-between gap-4 p-5 border-b border-gray-100">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-semibold text-gray-900 truncate">{service.title}</h3>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      service.status === "pending_review" ? "bg-yellow-50 text-yellow-700" : "bg-blue-50 text-blue-700"
                    }`}>
                      {statusLabels[service.status] ?? service.status}
                    </span>
                  </div>
                  <p className="text-sm text-gray-500 mt-0.5">
                    {ar ? "المستقل:" : "Freelancer:"}{" "}
                    <span className="font-medium text-gray-700">{service.freelancer.username}</span>
                    <span className="text-gray-400 mx-1">·</span>
                    {service.freelancer.email}
                    {service.freelancer.avg_rating > 0 && (
                      <span className="text-gray-400 mx-1">· {service.freelancer.avg_rating}★</span>
                    )}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {ar ? "تاريخ الإنشاء:" : "Submitted:"}{" "}
                    {new Date(service.created_at).toLocaleDateString(dateLocale, {
                      year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
                    })}
                  </p>
                </div>
                <div className="shrink-0 text-end">
                  {service.packages.slice(0, 1).map(pkg => (
                    <div key={pkg.tier}>
                      <span className="text-lg font-bold text-gray-900">
                        {pkg.price.toLocaleString(ar ? "ar-IQ" : "en-US")} {ar ? "د.ع" : "IQD"}
                      </span>
                      <p className="text-xs text-gray-500">{ar ? "البداية من" : "Starting at"}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Description */}
              <div className="px-5 py-4">
                <p className="text-sm text-gray-700 line-clamp-3 leading-relaxed">{service.description}</p>
                {service.tags && service.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-3">
                    {service.tags.map(tag => (
                      <span key={tag} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{tag}</span>
                    ))}
                  </div>
                )}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mt-4">
                  {service.packages.map(pkg => (
                    <div key={pkg.tier} className="border border-gray-200 rounded-lg p-3 text-sm">
                      <div className="font-medium text-gray-900 capitalize">{pkg.tier}</div>
                      <div className="text-gray-600">{pkg.name}</div>
                      <div className="text-gray-800 font-semibold mt-1">
                        {pkg.price.toLocaleString(ar ? "ar-IQ" : "en-US")} {ar ? "د.ع" : "IQD"}
                      </div>
                      <div className="text-gray-400 text-xs">{pkg.delivery_days} {ar ? "يوم" : "days"}</div>
                    </div>
                  ))}
                </div>
                {service.revision_note && (
                  <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm">
                    <span className="font-medium text-blue-700">
                      {ar ? "ملاحظة التعديل السابقة: " : "Previous revision note: "}
                    </span>
                    <span className="text-blue-800">{service.revision_note}</span>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 px-5 py-3 bg-gray-50 border-t border-gray-100">
                <button
                  onClick={() => onApprove(service.id)}
                  disabled={actionLoading === service.id}
                  className="px-4 py-2 text-sm font-medium bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition"
                >
                  {actionLoading === service.id ? "..." : (ar ? "✓ موافقة" : "✓ Approve")}
                </button>
                <button
                  onClick={() => onOpenModal("revision", service.id, service.title)}
                  disabled={actionLoading === service.id}
                  className="px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition"
                >
                  {ar ? "✏️ طلب تعديل" : "✏️ Request Edit"}
                </button>
                <button
                  onClick={() => onOpenModal("reject", service.id, service.title)}
                  disabled={actionLoading === service.id}
                  className="px-4 py-2 text-sm font-medium bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition"
                >
                  {ar ? "✕ رفض" : "✕ Reject"}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal for revision note / rejection reason */}
      {modalState && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
            <h3 className="font-semibold text-gray-900">
              {modalState.type === "revision"
                ? (ar ? "طلب تعديل على الخدمة" : "Request Edits")
                : (ar ? "رفض الخدمة" : "Reject Service")}
            </h3>
            <p className="text-sm text-gray-600">
              <span className="font-medium">{modalState.serviceTitle}</span>
            </p>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {modalState.type === "revision"
                  ? (ar ? "ما التغييرات المطلوبة؟ (يراها المستقل)" : "What needs to change? (freelancer will see this)")
                  : (ar ? "سبب الرفض (يراه المستقل)" : "Reason for rejection (freelancer will see this)")}
              </label>
              <textarea
                value={modalText}
                onChange={(e) => onModalTextChange(e.target.value)}
                rows={4}
                placeholder={modalState.type === "revision"
                  ? (ar ? "مثال: يرجى تحسين وصف الخدمة..." : "e.g. Please improve the description...")
                  : (ar ? "مثال: الخدمة تنتهك سياسة المنصة..." : "e.g. This service violates platform policy...")}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
              {modalText.trim().length < 10 && modalText.length > 0 && (
                <p className="text-xs text-red-500 mt-1">
                  {ar ? "يجب أن يكون النص 10 أحرف على الأقل" : "Must be at least 10 characters"}
                </p>
              )}
            </div>
            <div className="flex gap-2 justify-end">
              <button
                onClick={onCloseModal}
                className="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                {ar ? "إلغاء" : "Cancel"}
              </button>
              <button
                onClick={onModalSubmit}
                disabled={modalText.trim().length < 10 || actionLoading !== null}
                className={`px-4 py-2 text-sm font-medium text-white rounded-lg disabled:opacity-50 transition ${
                  modalState.type === "revision" ? "bg-blue-600 hover:bg-blue-700" : "bg-red-600 hover:bg-red-700"
                }`}
              >
                {actionLoading ? "..." : modalState.type === "revision"
                  ? (ar ? "إرسال طلب التعديل" : "Send Revision Request")
                  : (ar ? "رفض الخدمة" : "Reject Service")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
