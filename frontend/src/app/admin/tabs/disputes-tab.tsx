"use client";

import { useCallback, useEffect, useState } from "react";
import { adminApi, servicesApi } from "@/lib/api";
import { toast } from "sonner";
import { getApiError } from "@/lib/utils";
import type { MessageDetail } from "@/types/message";

interface DisputedOrder {
  id: string;
  status: string;
  dispute_reason: string | null;
  dispute_opened_at: string | null;
  dispute_resolution: string | null;
  dispute_resolved_at: string | null;
  service: { title: string; slug: string } | null;
  /** @deprecated — backend emits `gig` during rename deprecation window */
  gig?: { title: string; slug: string } | null;
  client: { id: string; username: string; first_name: string; last_name: string } | null;
  freelancer: { id: string; username: string; first_name: string; last_name: string } | null;
  package: { name: string; price: number } | null;
}

interface DisputesTabProps {
  ar: boolean;
  dateLocale: string;
}

export function DisputesTab({ ar, dateLocale }: DisputesTabProps) {
  const [orders, setOrders] = useState<DisputedOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<DisputedOrder | null>(null);
  const [mobileDetailOpen, setMobileDetailOpen] = useState(false);

  // Order conversation view
  const [chatMessages, setChatMessages] = useState<MessageDetail[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [showChat, setShowChat] = useState(false);

  // Resolve modal
  const [resolveModal, setResolveModal] = useState(false);
  const [resolution, setResolution] = useState<"release" | "refund">("release");
  const [adminNote, setAdminNote] = useState("");
  const [resolving, setResolving] = useState(false);

  const fetchDisputes = useCallback(async () => {
    try {
      setLoading(true);
      const res = await servicesApi.listDisputedOrders();
      setOrders(res.data);
    } catch (err) {
      toast.error(getApiError(err, ar ? "تعذّر تحميل النزاعات" : "Failed to load disputes"));
    } finally {
      setLoading(false);
    }
  }, [ar]);

  useEffect(() => {
    fetchDisputes();
  }, [fetchDisputes]);

  const loadOrderChat = async (orderId: string) => {
    setChatMessages([]);
    setShowChat(true);
    setChatLoading(true);
    try {
      const res = await adminApi.getOrderConversation(orderId);
      setChatMessages((res.data.messages as MessageDetail[]).slice().reverse());
    } catch {
      // No conversation yet — normal for orders that never used chat
      setChatMessages([]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleResolve = async () => {
    if (!selected || resolving) return;
    setResolving(true);
    try {
      await servicesApi.resolveDispute(selected.id, resolution, adminNote);
      toast.success(ar ? "تم حل النزاع" : "Dispute resolved");
      setResolveModal(false);
      setAdminNote("");
      setSelected(null);
      setShowChat(false);
      fetchDisputes();
    } catch (err) {
      toast.error(getApiError(err, ar ? "تعذّر حل النزاع" : "Failed to resolve dispute"));
    } finally {
      setResolving(false);
    }
  };

  const fmt = (iso: string | null) =>
    iso
      ? new Date(iso).toLocaleString(dateLocale, {
          year: "numeric",
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        })
      : "—";

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-gray-900">
            {ar ? "النزاعات المفتوحة" : "Open Disputes"}
          </h2>
          <p className="text-xs text-gray-500 mt-0.5">
            {ar
              ? `${orders.length} نزاع نشط`
              : `${orders.length} active dispute${orders.length !== 1 ? "s" : ""}`}
          </p>
        </div>
        <button
          onClick={fetchDisputes}
          className="text-sm text-blue-600 hover:text-blue-700 font-medium"
        >
          {ar ? "تحديث" : "Refresh"}
        </button>
      </div>

      <div className="flex h-[70vh]">
        {/* Dispute list — hidden on mobile when detail panel is open */}
        <div className={`
          shrink-0 ${ar ? "border-l" : "border-r"} border-gray-200 overflow-y-auto
          w-full md:w-80
          ${mobileDetailOpen ? "hidden md:block" : "block"}
        `}>
          {loading ? (
            <div className="p-4 space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex gap-3 animate-pulse">
                  <div className="w-10 h-10 rounded-full bg-gray-200 shrink-0" />
                  <div className="flex-1 space-y-1.5 pt-1">
                    <div className="h-3 bg-gray-200 rounded w-2/3" />
                    <div className="h-2.5 bg-gray-100 rounded w-full" />
                  </div>
                </div>
              ))}
            </div>
          ) : orders.length === 0 ? (
            <div className="p-8 text-center text-gray-400 text-sm">
              {ar ? "لا توجد نزاعات مفتوحة" : "No open disputes"}
            </div>
          ) : (
            orders.map((o) => (
              <button
                key={o.id}
                onClick={() => { setSelected(o); setShowChat(false); setMobileDetailOpen(true); }}
                className={`w-full p-3 text-start border-b border-gray-50 hover:bg-gray-50 transition-colors ${
                  selected?.id === o.id ? "bg-orange-50" : ""
                }`}
              >
                <div className="flex items-start gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-orange-400 mt-1.5 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {(o.service ?? o.gig)?.title ?? (ar ? "خدمة محذوفة" : "Deleted service")}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5 truncate">
                      {o.client?.username} → {o.freelancer?.username}
                    </p>
                    <p className="text-xs text-orange-600 mt-1 line-clamp-2">
                      {o.dispute_reason ?? "—"}
                    </p>
                    <p className="text-[10px] text-gray-400 mt-1">
                      {fmt(o.dispute_opened_at)}
                    </p>
                  </div>
                </div>
              </button>
            ))
          )}
        </div>

        {/* Detail panel — hidden on mobile when list is shown */}
        <div className={`
          flex-1 flex flex-col min-w-0 bg-gray-50 overflow-y-auto
          ${mobileDetailOpen ? "block" : "hidden md:flex"}
        `}>
          {!selected ? (
            <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
              {ar ? "اختر نزاعاً للمراجعة" : "Select a dispute to review"}
            </div>
          ) : (
            <div className="p-5 space-y-4">
              {/* Back button — mobile only */}
              <button
                onClick={() => setMobileDetailOpen(false)}
                className="md:hidden flex items-center gap-1.5 text-sm text-gray-600 hover:text-gray-900 mb-2"
              >
                <svg className={`w-4 h-4 ${ar ? "rotate-180" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                {ar ? "رجوع إلى القائمة" : "Back to list"}
              </button>
              {/* Order summary */}
              <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
                <h3 className="font-semibold text-gray-900">
                  {(selected.service ?? selected.gig)?.title ?? (ar ? "خدمة محذوفة" : "Deleted service")}
                </h3>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-xs text-gray-400">{ar ? "العميل" : "Client"}</p>
                    <p className="font-medium">{selected.client?.first_name} {selected.client?.last_name}</p>
                    <p className="text-xs text-gray-500">@{selected.client?.username}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400">{ar ? "المستقل" : "Freelancer"}</p>
                    <p className="font-medium">{selected.freelancer?.first_name} {selected.freelancer?.last_name}</p>
                    <p className="text-xs text-gray-500">@{selected.freelancer?.username}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400">{ar ? "الباقة" : "Package"}</p>
                    <p className="font-medium">{selected.package?.name ?? "—"}</p>
                    <p className="text-xs text-gray-500">
                      {selected.package?.price != null
                        ? `${selected.package.price.toLocaleString()} IQD`
                        : "—"}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400">{ar ? "تاريخ النزاع" : "Opened"}</p>
                    <p className="font-medium text-orange-600">{fmt(selected.dispute_opened_at)}</p>
                  </div>
                </div>
              </div>

              {/* Dispute reason */}
              <div className="bg-orange-50 border border-orange-200 rounded-xl p-4">
                <p className="text-xs font-semibold text-orange-700 mb-1">
                  {ar ? "سبب النزاع" : "Dispute Reason"}
                </p>
                <p className="text-sm text-orange-900 whitespace-pre-wrap">
                  {selected.dispute_reason ?? "—"}
                </p>
              </div>

              {/* Action buttons */}
              {selected.status === "disputed" && (
                <div className="flex gap-3">
                  <button
                    onClick={() => { loadOrderChat(selected.id); }}
                    className="flex-1 px-4 py-2 text-sm border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    {ar ? "عرض محادثة الطلب" : "View Order Chat"}
                  </button>
                  <button
                    onClick={() => setResolveModal(true)}
                    className="flex-1 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    {ar ? "حل النزاع" : "Resolve Dispute"}
                  </button>
                </div>
              )}

              {/* Contact client/freelancer via support */}
              <div className="flex gap-2 text-xs text-gray-500">
                <span>{ar ? "تواصل مع:" : "Contact:"}</span>
                {selected.client && (
                  <a
                    href={`/dashboard/messages?with=${selected.client.id}`}
                    className="text-blue-600 hover:underline"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {ar ? "العميل" : "Client"}
                  </a>
                )}
                <span>·</span>
                {selected.freelancer && (
                  <a
                    href={`/dashboard/messages?with=${selected.freelancer.id}`}
                    className="text-blue-600 hover:underline"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {ar ? "المستقل" : "Freelancer"}
                  </a>
                )}
              </div>

              {/* Order chat panel */}
              {showChat && (
                <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                  <div className="px-4 py-2.5 border-b border-gray-100 bg-gray-50 flex items-center justify-between">
                    <p className="text-xs font-semibold text-gray-700">
                      {ar ? "محادثة الطلب (للقراءة فقط)" : "Order Conversation (read-only)"}
                    </p>
                    <button
                      onClick={() => setShowChat(false)}
                      className="text-gray-400 hover:text-gray-600 text-lg leading-none"
                    >
                      ×
                    </button>
                  </div>
                  <div className="p-3 space-y-2 max-h-80 overflow-y-auto" dir="ltr">
                    {chatLoading ? (
                      <p className="text-center text-sm text-gray-400 py-4">
                        {ar ? "جاري التحميل..." : "Loading..."}
                      </p>
                    ) : chatMessages.length === 0 ? (
                      <p className="text-center text-sm text-gray-400 py-4">
                        {ar ? "لا توجد رسائل في محادثة الطلب" : "No messages in order conversation"}
                      </p>
                    ) : (
                      chatMessages.map((m) => {
                        const isSystem = m.is_system || m.sender_role === "system";
                        if (isSystem) {
                          return (
                            <div key={m.id} className="flex justify-center">
                              <div className="max-w-[85%] bg-gray-100 text-gray-600 text-xs px-3 py-1.5 rounded-full text-center whitespace-pre-wrap">
                                {m.content}
                              </div>
                            </div>
                          );
                        }
                        const isFreelancer = m.sender_role === "freelancer";
                        return (
                          <div key={m.id} className={`flex ${isFreelancer ? "justify-end" : "justify-start"}`}>
                            <div className={`max-w-[75%] rounded-xl px-3 py-2 text-xs ${
                              isFreelancer
                                ? "bg-brand-500 text-white"
                                : "bg-gray-100 text-gray-800"
                            }`}>
                              <p className={`text-[10px] mb-0.5 ${isFreelancer ? "text-brand-100" : "text-gray-500"}`}>
                                {m.sender.first_name} ({m.sender_role})
                              </p>
                              <p className="whitespace-pre-wrap">{m.content}</p>
                              <p className={`text-[9px] mt-1 ${isFreelancer ? "text-brand-200" : "text-gray-400"}`}>
                                {new Date(m.created_at).toLocaleString(dateLocale, {
                                  month: "short", day: "numeric",
                                  hour: "2-digit", minute: "2-digit",
                                })}
                              </p>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Resolve modal */}
      {resolveModal && selected && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <h3 className="font-bold text-gray-900 mb-1">
              {ar ? "حل النزاع" : "Resolve Dispute"}
            </h3>
            <p className="text-sm text-gray-500 mb-4">
              {(selected.service ?? selected.gig)?.title}
            </p>

            <div className="space-y-3 mb-4">
              <label className="flex items-start gap-3 p-3 border rounded-xl cursor-pointer hover:bg-green-50 transition-colors">
                <input
                  type="radio"
                  name="resolution"
                  value="release"
                  checked={resolution === "release"}
                  onChange={() => setResolution("release")}
                  className="mt-0.5"
                />
                <div>
                  <p className="text-sm font-semibold text-green-700">
                    {ar ? "إصدار المبلغ للمستقل" : "Release to Freelancer"}
                  </p>
                  <p className="text-xs text-gray-500">
                    {ar
                      ? "الطلب مكتمل — تُحرَّر الأموال للمستقل (بعد خصم العمولة)."
                      : "Work accepted — funds released to freelancer (minus platform fee)."}
                  </p>
                </div>
              </label>

              <label className="flex items-start gap-3 p-3 border rounded-xl cursor-pointer hover:bg-red-50 transition-colors">
                <input
                  type="radio"
                  name="resolution"
                  value="refund"
                  checked={resolution === "refund"}
                  onChange={() => setResolution("refund")}
                  className="mt-0.5"
                />
                <div>
                  <p className="text-sm font-semibold text-red-700">
                    {ar ? "استرداد المبلغ للعميل" : "Refund to Client"}
                  </p>
                  <p className="text-xs text-gray-500">
                    {ar
                      ? "العمل غير مقبول — يُلغى الطلب وتُحرَّر الأموال للعميل (يدوياً عبر لوحة Qi Card)."
                      : "Work not accepted — order cancelled, funds returned to client (manual via Qi Card portal)."}
                  </p>
                </div>
              </label>
            </div>

            <textarea
              value={adminNote}
              onChange={(e) => setAdminNote(e.target.value)}
              placeholder={ar ? "ملاحظة داخلية (اختياري)..." : "Admin note (optional)..."}
              rows={2}
              maxLength={1000}
              className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4"
            />

            <div className="flex gap-2 justify-end">
              <button
                onClick={() => { setResolveModal(false); setAdminNote(""); }}
                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              >
                {ar ? "إلغاء" : "Cancel"}
              </button>
              <button
                onClick={handleResolve}
                disabled={resolving}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-40 transition-colors"
              >
                {resolving ? "..." : (ar ? "تأكيد" : "Confirm")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
