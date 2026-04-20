"use client";

import { useCallback, useEffect, useState } from "react";
import { adminApi } from "@/lib/api";
import { getApiError } from "@/lib/utils";
import { toast } from "sonner";

interface PayoutApproval {
  id: string;
  escrow_id: string;
  amount: number;
  currency: string;
  status: string;
  requested_by_id: string | null;
  requested_by_email: string | null;
  decided_by_id: string | null;
  decided_by_email: string | null;
  request_note: string | null;
  decision_note: string | null;
  decided_at: string | null;
  created_at: string;
  freelancer_id: string | null;
  freelancer_email: string | null;
  freelancer_username: string | null;
  gig_order_id: string | null;
  milestone_id: string | null;
}

interface Props {
  ar: boolean;
  dateLocale: string;
  currentAdminId?: string;
}

export function PayoutApprovalsTab({ ar, dateLocale, currentAdminId }: Props) {
  const [approvals, setApprovals] = useState<PayoutApproval[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [rejectModal, setRejectModal] = useState<PayoutApproval | null>(null);
  const [rejectNote, setRejectNote] = useState("");

  const fetchApprovals = useCallback(async () => {
    setLoading(true);
    try {
      const res = await adminApi.getPendingPayoutApprovals();
      setApprovals(res.data.approvals);
    } catch {
      toast.error(ar ? "تعذّر تحميل الموافقات" : "Failed to load approvals");
    } finally {
      setLoading(false);
    }
  }, [ar]);

  useEffect(() => {
    fetchApprovals();
  }, [fetchApprovals]);

  const handleApprove = async (a: PayoutApproval) => {
    const amount = `${a.amount.toLocaleString(ar ? "ar-IQ" : "en-US")} ${a.currency}`;
    const who = a.freelancer_username ?? a.freelancer_email ?? "freelancer";
    const confirmed = confirm(
      ar
        ? `تأكيد: هل أرسلت الدفعة (${amount}) إلى ${who} عبر بطاقة Qi Card؟ ستُحرَّر الضمانة فوراً.`
        : `Confirm: Did you send ${amount} to ${who} via Qi Card? The escrow will be released immediately.`,
    );
    if (!confirmed) return;
    setBusyId(a.id);
    try {
      await adminApi.approvePayoutApproval(a.id);
      toast.success(ar ? "تمت الموافقة وتحرير الضمانة" : "Approved — escrow released");
      fetchApprovals();
    } catch (err) {
      toast.error(getApiError(err, ar ? "تعذّرت الموافقة" : "Failed to approve"));
    } finally {
      setBusyId(null);
    }
  };

  const handleReject = async () => {
    if (!rejectModal) return;
    if (rejectNote.trim().length < 3) {
      toast.error(ar ? "السبب مطلوب (3 أحرف على الأقل)" : "Reason required (min 3 chars)");
      return;
    }
    setBusyId(rejectModal.id);
    try {
      await adminApi.rejectPayoutApproval(rejectModal.id, rejectNote.trim());
      toast.success(ar ? "تم رفض الطلب" : "Payout rejected");
      setRejectModal(null);
      setRejectNote("");
      fetchApprovals();
    } catch (err) {
      toast.error(getApiError(err, ar ? "تعذّر الرفض" : "Failed to reject"));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-800">
        <strong>{ar ? "مراقبة مزدوجة:" : "Dual-Control:"}</strong>{" "}
        {ar
          ? "الدفعات أعلى من الحد الأدنى تتطلب مديراً ثانياً للموافقة. لا يمكن للمدير الذي طلب الإفراج أن يوافق على طلبه."
          : "Payouts above the threshold require a second admin to approve. The admin who requested the release cannot approve their own request."}
      </div>

      {loading ? (
        <div className="bg-white rounded-lg border p-12 text-center text-gray-400">
          {ar ? "جاري التحميل..." : "Loading..."}
        </div>
      ) : approvals.length === 0 ? (
        <div className="bg-white rounded-lg border p-12 text-center text-gray-400">
          {ar ? "لا توجد موافقات معلقة." : "No pending approvals."}
        </div>
      ) : (
        <div className="bg-white rounded-lg border overflow-x-auto">
          <table className="min-w-[900px] w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-start p-3 font-medium text-gray-600">
                  {ar ? "المستقل" : "Freelancer"}
                </th>
                <th className="text-start p-3 font-medium text-gray-600">
                  {ar ? "المبلغ" : "Amount"}
                </th>
                <th className="text-start p-3 font-medium text-gray-600">
                  {ar ? "طلب من" : "Requested by"}
                </th>
                <th className="text-start p-3 font-medium text-gray-600">
                  {ar ? "ملاحظة" : "Note"}
                </th>
                <th className="text-start p-3 font-medium text-gray-600">
                  {ar ? "التاريخ" : "Created"}
                </th>
                <th className="text-end p-3 font-medium text-gray-600">
                  {ar ? "إجراء" : "Action"}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {approvals.map((a) => {
                const isSelf = a.requested_by_id === currentAdminId;
                const isBusy = busyId === a.id;
                return (
                  <tr key={a.id} className="hover:bg-gray-50">
                    <td className="p-3">
                      <div className="font-medium text-gray-900">
                        {a.freelancer_username ?? "—"}
                      </div>
                      <div className="text-xs text-gray-500">{a.freelancer_email ?? ""}</div>
                    </td>
                    <td className="p-3 font-semibold text-gray-900" dir="ltr">
                      {a.amount.toLocaleString(ar ? "ar-IQ" : "en-US")} {a.currency}
                    </td>
                    <td className="p-3 text-gray-700 text-xs">
                      {a.requested_by_email ?? "—"}
                    </td>
                    <td className="p-3 text-gray-700 max-w-[220px] truncate">
                      {a.request_note || <span className="text-gray-400">—</span>}
                    </td>
                    <td className="p-3 text-gray-500 text-xs">
                      {new Date(a.created_at).toLocaleString(dateLocale, {
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </td>
                    <td className="p-3">
                      <div className="flex justify-end gap-2">
                        {isSelf ? (
                          <span className="text-xs text-gray-400 italic">
                            {ar ? "أنت الطالب" : "You requested this"}
                          </span>
                        ) : (
                          <>
                            <button
                              onClick={() => handleApprove(a)}
                              disabled={isBusy}
                              className="px-3 py-1.5 text-xs font-medium bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 whitespace-nowrap"
                            >
                              {isBusy ? "..." : ar ? "موافقة" : "Approve"}
                            </button>
                            <button
                              onClick={() => {
                                setRejectModal(a);
                                setRejectNote("");
                              }}
                              disabled={isBusy}
                              className="px-3 py-1.5 text-xs font-medium bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 whitespace-nowrap"
                            >
                              {ar ? "رفض" : "Reject"}
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {rejectModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h3 className="text-lg font-semibold mb-2">
              {ar ? "رفض طلب الدفع" : "Reject payout request"}
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              {ar
                ? "يرجى إدخال سبب الرفض (سيظهر في السجل للمدير الطالب)."
                : "Please enter a reason (will be recorded in the audit log and shown to the requester)."}
            </p>
            <textarea
              value={rejectNote}
              onChange={(e) => setRejectNote(e.target.value)}
              placeholder={ar ? "مثال: المبلغ غير مطابق للعقد" : "e.g. Amount doesn't match the order"}
              className="w-full border border-gray-300 rounded p-2 text-sm min-h-[100px]"
              autoFocus
            />
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => {
                  setRejectModal(null);
                  setRejectNote("");
                }}
                className="px-4 py-2 text-sm border rounded hover:bg-gray-50"
              >
                {ar ? "إلغاء" : "Cancel"}
              </button>
              <button
                onClick={handleReject}
                disabled={busyId === rejectModal.id || rejectNote.trim().length < 3}
                className="px-4 py-2 text-sm bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
              >
                {busyId === rejectModal.id ? "..." : ar ? "تأكيد الرفض" : "Confirm Reject"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
