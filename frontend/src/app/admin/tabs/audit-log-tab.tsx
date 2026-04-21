"use client";

import { useCallback, useEffect, useState } from "react";
import { adminApi } from "@/lib/api";
import { toast } from "sonner";

interface AuditEntry {
  id: string;
  admin_id: string | null;
  admin_email: string | null;
  action: string;
  target_type: string;
  target_id: string | null;
  amount: number | null;
  currency: string | null;
  ip_address: string | null;
  details: Record<string, unknown> | null;
  created_at: string;
}

interface Props {
  ar: boolean;
  dateLocale: string;
}

const ACTION_COLORS: Record<string, string> = {
  escrow_released: "bg-green-100 text-green-800",
  escrow_refunded: "bg-yellow-100 text-yellow-800",
  escrow_release_requested: "bg-blue-100 text-blue-800",
  payout_approved: "bg-green-100 text-green-800",
  payout_rejected: "bg-red-100 text-red-800",
  user_status_changed: "bg-gray-100 text-gray-800",
  user_promoted_admin: "bg-purple-100 text-purple-800",
  user_demoted_admin: "bg-orange-100 text-orange-800",
  service_approved: "bg-green-100 text-green-800",
  service_rejected: "bg-red-100 text-red-800",
  dispute_resolved: "bg-blue-100 text-blue-800",
};

export function AuditLogTab({ ar, dateLocale }: Props) {
  const [logs, setLogs] = useState<AuditEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const pageSize = 50;

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await adminApi.getAuditLogs({ page, page_size: pageSize });
      setLogs(res.data.logs);
      setTotal(res.data.total);
    } catch {
      toast.error(ar ? "تعذّر تحميل السجل" : "Failed to load audit log");
    } finally {
      setLoading(false);
    }
  }, [page, ar]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="space-y-4">
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm text-gray-700">
        {ar
          ? "سجل جميع إجراءات المديرين الحساسة (تحرير الضمانات، تغيير حالة المستخدمين، الترقيات، الموافقات على الدفع). للقراءة فقط."
          : "Append-only log of all privileged admin actions (escrow releases, user status changes, promotions, payout approvals). Read-only."}
      </div>

      {loading ? (
        <div className="bg-white rounded-lg border p-12 text-center text-gray-400">
          {ar ? "جاري التحميل..." : "Loading..."}
        </div>
      ) : logs.length === 0 ? (
        <div className="bg-white rounded-lg border p-12 text-center text-gray-400">
          {ar ? "لا توجد سجلات بعد." : "No audit entries yet."}
        </div>
      ) : (
        <div className="bg-white rounded-lg border overflow-x-auto">
          <table className="min-w-[900px] w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-start p-3 font-medium text-gray-600">
                  {ar ? "الوقت" : "When"}
                </th>
                <th className="text-start p-3 font-medium text-gray-600">
                  {ar ? "المدير" : "Admin"}
                </th>
                <th className="text-start p-3 font-medium text-gray-600">
                  {ar ? "الإجراء" : "Action"}
                </th>
                <th className="text-start p-3 font-medium text-gray-600">
                  {ar ? "الهدف" : "Target"}
                </th>
                <th className="text-start p-3 font-medium text-gray-600">
                  {ar ? "المبلغ" : "Amount"}
                </th>
                <th className="text-start p-3 font-medium text-gray-600">
                  {ar ? "عنوان IP" : "IP"}
                </th>
                <th className="text-start p-3 font-medium text-gray-600">
                  {ar ? "التفاصيل" : "Details"}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50 align-top">
                  <td className="p-3 text-gray-500 text-xs whitespace-nowrap">
                    {new Date(log.created_at).toLocaleString(dateLocale, {
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </td>
                  <td className="p-3 text-gray-700 text-xs">
                    {log.admin_email ?? <span className="text-gray-400">—</span>}
                  </td>
                  <td className="p-3">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                        ACTION_COLORS[log.action] ?? "bg-gray-100 text-gray-800"
                      }`}
                    >
                      {log.action}
                    </span>
                  </td>
                  <td className="p-3 text-gray-700 text-xs">
                    <div>{log.target_type}</div>
                    {log.target_id && (
                      <div className="text-gray-400 font-mono text-[10px]" dir="ltr">
                        {log.target_id.slice(0, 8)}…
                      </div>
                    )}
                  </td>
                  <td className="p-3 text-gray-700 text-xs whitespace-nowrap" dir="ltr">
                    {log.amount != null
                      ? `${log.amount.toLocaleString(ar ? "ar-IQ" : "en-US")} ${log.currency ?? ""}`
                      : "—"}
                  </td>
                  <td className="p-3 text-gray-500 text-xs font-mono" dir="ltr">
                    {log.ip_address ?? "—"}
                  </td>
                  <td className="p-3 text-gray-600 text-xs max-w-[260px]">
                    {log.details ? (
                      <details>
                        <summary className="cursor-pointer text-blue-600 hover:underline">
                          {ar ? "عرض" : "View"}
                        </summary>
                        <pre className="whitespace-pre-wrap mt-1 bg-gray-50 p-2 rounded text-[11px]" dir="ltr">
                          {JSON.stringify(log.details, null, 2)}
                        </pre>
                      </details>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-500">
            {ar
              ? `صفحة ${page} من ${totalPages} — ${total} سجل`
              : `Page ${page} of ${totalPages} — ${total} entries`}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="px-3 py-1.5 border rounded text-sm disabled:opacity-40"
            >
              {ar ? "السابق" : "Prev"}
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="px-3 py-1.5 border rounded text-sm disabled:opacity-40"
            >
              {ar ? "التالي" : "Next"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
