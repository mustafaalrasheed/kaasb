"use client";

interface AdminEscrow {
  escrow_id: string;
  contract_id: string;
  milestone_id: string;
  milestone_title: string;
  amount: number;
  platform_fee: number;
  freelancer_amount: number;
  currency: string;
  funded_at: string | null;
  freelancer: {
    id: string;
    username: string;
    email: string;
    phone: string | null;
    qi_card_phone: string | null;
  };
}

interface PayoutsTabProps {
  escrows: AdminEscrow[];
  loading: boolean;
  actionLoading: string | null;
  ar: boolean;
  dateLocale: string;
  onRelease: (escrow: AdminEscrow) => void;
}

export function PayoutsTab({ escrows, loading, actionLoading, ar, dateLocale, onRelease }: PayoutsTabProps) {
  const totalNet = escrows.reduce((s, e) => s + e.freelancer_amount, 0);

  return (
    <div className="space-y-4">
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-800">
        <strong>{ar ? "تعليمات:" : "Instructions:"}</strong>{" "}
        {ar
          ? "لكل صف أدناه، انتقل إلى لوحة Qi Card وأرسل المبلغ المُحدد إلى رقم هاتف Qi Card للمستقل. بعد إرسال الدفعة، اضغط «تأكيد الدفع» لتحديث السجل."
          : "For each row below, go to your Qi Card merchant portal and send the listed amount to the freelancer's Qi Card phone. After sending, click \"Confirm Payout\" to update the ledger."}
      </div>

      {loading ? (
        <div className="bg-white rounded-lg border p-12 text-center text-gray-400">
          {ar ? "جاري التحميل..." : "Loading..."}
        </div>
      ) : escrows.length === 0 ? (
        <div className="bg-white rounded-lg border p-12 text-center text-gray-400">
          {ar ? "لا توجد مدفوعات معلقة — كل العقود تمت تسويتها." : "No pending payouts — all contracts are settled."}
        </div>
      ) : (
        <div className="bg-white rounded-lg border overflow-x-auto">
          <table className="min-w-[900px] w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-start p-3 font-medium text-gray-600">{ar ? "المستقل" : "Freelancer"}</th>
                <th className="text-start p-3 font-medium text-gray-600">{ar ? "رقم Qi Card" : "Qi Card Phone"}</th>
                <th className="text-start p-3 font-medium text-gray-600">{ar ? "المرحلة" : "Milestone"}</th>
                <th className="text-start p-3 font-medium text-gray-600">{ar ? "المبلغ الكلي" : "Total"}</th>
                <th className="text-start p-3 font-medium text-gray-600">{ar ? "عمولة المنصة" : "Platform Fee"}</th>
                <th className="text-start p-3 font-medium text-gray-600">{ar ? "صافي للمستقل" : "Net to Freelancer"}</th>
                <th className="text-start p-3 font-medium text-gray-600">{ar ? "تاريخ التمويل" : "Funded"}</th>
                <th className="text-end p-3 font-medium text-gray-600">{ar ? "إجراء" : "Action"}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {escrows.map((escrow) => {
                const isBusy = actionLoading === escrow.escrow_id;
                const qiPhone = escrow.freelancer.qi_card_phone || escrow.freelancer.phone;
                return (
                  <tr key={escrow.escrow_id} className="hover:bg-gray-50">
                    <td className="p-3">
                      <div className="font-medium text-gray-900">{escrow.freelancer.username}</div>
                      <div className="text-xs text-gray-500">{escrow.freelancer.email}</div>
                    </td>
                    <td className="p-3">
                      {qiPhone ? (
                        <span className="font-mono text-gray-900 bg-yellow-50 border border-yellow-200 px-2 py-0.5 rounded text-xs" dir="ltr">
                          {qiPhone}
                        </span>
                      ) : (
                        <span className="text-red-500 text-xs">{ar ? "غير مسجل" : "Not registered"}</span>
                      )}
                    </td>
                    <td className="p-3 text-gray-700 max-w-[180px] truncate">{escrow.milestone_title}</td>
                    <td className="p-3 font-medium text-gray-900" dir="ltr">
                      {escrow.amount.toLocaleString(ar ? "ar-IQ" : "en-US")} {escrow.currency}
                    </td>
                    <td className="p-3 text-red-600" dir="ltr">
                      -{escrow.platform_fee.toLocaleString(ar ? "ar-IQ" : "en-US")} {escrow.currency}
                    </td>
                    <td className="p-3 font-bold text-green-700" dir="ltr">
                      {escrow.freelancer_amount.toLocaleString(ar ? "ar-IQ" : "en-US")} {escrow.currency}
                    </td>
                    <td className="p-3 text-gray-500 text-xs">
                      {escrow.funded_at
                        ? new Date(escrow.funded_at).toLocaleDateString(dateLocale, { month: "short", day: "numeric", year: "numeric" })
                        : "—"}
                    </td>
                    <td className="p-3">
                      <div className="flex justify-end">
                        <button
                          onClick={() => onRelease(escrow)}
                          disabled={isBusy}
                          className="px-3 py-1.5 text-xs font-medium bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 whitespace-nowrap"
                        >
                          {isBusy ? "..." : (ar ? "تأكيد الدفع" : "Confirm Payout")}
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-sm text-gray-500">
        {ar
          ? `${escrows.length} دفعة معلقة — إجمالي الصافي: ${totalNet.toLocaleString("ar-IQ")} IQD`
          : `${escrows.length} pending payout(s) — total net: ${totalNet.toLocaleString("en-US")} IQD`}
      </p>
    </div>
  );
}
