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
    qi_card_holder_name: string | null;
  };
}

interface ProcessingPayout {
  transaction_id: string;
  amount: number;
  currency: string;
  requested_at: string;
  provider: string | null;
  description: string | null;
  freelancer: {
    id: string;
    username: string;
    email: string;
    phone: string | null;
    qi_card_phone: string | null;
  };
}

interface StuckPendingTransaction {
  transaction_id: string;
  external_order_id: string | null;
  amount: number;
  currency: string;
  transaction_type: string;
  created_at: string;
  age_minutes: number;
  provider: string | null;
  description: string | null;
  payer: { id: string; username: string; email: string } | null;
}

interface PayoutsTabProps {
  escrows: AdminEscrow[];
  loading: boolean;
  actionLoading: string | null;
  ar: boolean;
  dateLocale: string;
  onRelease: (escrow: AdminEscrow) => void;
  processingPayouts?: ProcessingPayout[];
  markPaidLoading?: string | null;
  onMarkPaid?: (payout: ProcessingPayout) => void;
  stuckPending?: StuckPendingTransaction[];
}

export function PayoutsTab({
  escrows,
  loading,
  actionLoading,
  ar,
  dateLocale,
  onRelease,
  processingPayouts = [],
  markPaidLoading = null,
  onMarkPaid,
  stuckPending = [],
}: PayoutsTabProps) {
  const totalNet = escrows.reduce((s, e) => s + e.freelancer_amount, 0);
  const totalPending = processingPayouts.reduce((s, p) => s + p.amount, 0);

  return (
    <div className="space-y-6">
      {/* ── Section 0: PENDING transactions that never confirmed (reconciliation queue) ── */}
      {stuckPending.length > 0 && (
        <div className="space-y-3">
          <h3 className="font-semibold text-gray-900">
            {ar ? "مدفوعات معلقة بدون تأكيد" : "Payments pending without confirmation"}
          </h3>
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-800">
            {ar
              ? "هذه طلبات دفع عميل وصلت إلى Qi Card لكن لم يعد أي تأكيد. افتح لوحة Qi Card وتحقق يدوياً: إذا تم الدفع فعلاً قم بإنجاز العملية، وإذا لم يتم فاسترد الطلب."
              : "These client payments were sent to Qi Card but no success callback came back. Look each one up in the Qi Card merchant dashboard — if the charge went through, reconcile manually; if not, refund."}
          </div>
          <div className="bg-white rounded-lg border overflow-x-auto">
            <table className="min-w-[900px] w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-start p-3 font-medium text-gray-600">{ar ? "الدافع" : "Payer"}</th>
                  <th className="text-start p-3 font-medium text-gray-600">{ar ? "مرجع الطلب" : "Order ref"}</th>
                  <th className="text-start p-3 font-medium text-gray-600">{ar ? "المبلغ" : "Amount"}</th>
                  <th className="text-start p-3 font-medium text-gray-600">{ar ? "النوع" : "Type"}</th>
                  <th className="text-start p-3 font-medium text-gray-600">{ar ? "عمر الطلب" : "Age"}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {stuckPending.map((t) => (
                  <tr key={t.transaction_id} className="hover:bg-gray-50">
                    <td className="p-3">
                      <div className="font-medium text-gray-900">{t.payer?.username ?? "—"}</div>
                      <div className="text-xs text-gray-500">{t.payer?.email ?? ""}</div>
                    </td>
                    <td className="p-3 font-mono text-xs text-gray-700 break-all">
                      {t.external_order_id ?? t.transaction_id}
                    </td>
                    <td className="p-3 font-semibold text-gray-900" dir="ltr">
                      {t.amount.toLocaleString(ar ? "ar-IQ" : "en-US")} {t.currency}
                    </td>
                    <td className="p-3 text-gray-700 text-xs">{t.transaction_type}</td>
                    <td className="p-3 text-gray-500 text-xs">
                      {t.age_minutes < 60
                        ? (ar ? `${t.age_minutes} دقيقة` : `${t.age_minutes}m`)
                        : (ar
                            ? `${Math.floor(t.age_minutes / 60)} ساعة`
                            : `${Math.floor(t.age_minutes / 60)}h`)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Section 1: freelancer-initiated payouts awaiting mark-paid ── */}
      {processingPayouts.length > 0 && onMarkPaid && (
        <div className="space-y-3">
          <h3 className="font-semibold text-gray-900">
            {ar ? "طلبات سحب بانتظار التأكيد" : "Payout requests awaiting confirmation"}
          </h3>
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-800">
            {ar
              ? "هذه طلبات سحب أطلقها المستقل من لوحته. أرسل المبلغ عبر Qi Card ثم اضغط «تأكيد الدفع» — الدفعة ستظهر كمكتملة في حساب المستقل ويُرسَل له إشعار."
              : 'These are payouts the freelancer initiated. Send the amount via Qi Card, then click "Mark Paid" — the freelancer will see it as completed and receive a notification.'}
          </div>
          <div className="bg-white rounded-lg border overflow-x-auto">
            <table className="min-w-[900px] w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-start p-3 font-medium text-gray-600">{ar ? "المستقل" : "Freelancer"}</th>
                  <th className="text-start p-3 font-medium text-gray-600">{ar ? "رقم Qi Card" : "Qi Card Phone"}</th>
                  <th className="text-start p-3 font-medium text-gray-600">{ar ? "المبلغ" : "Amount"}</th>
                  <th className="text-start p-3 font-medium text-gray-600">{ar ? "طُلب في" : "Requested"}</th>
                  <th className="text-end p-3 font-medium text-gray-600">{ar ? "إجراء" : "Action"}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {processingPayouts.map((p) => {
                  const isBusy = markPaidLoading === p.transaction_id;
                  const qiPhone = p.freelancer.qi_card_phone || p.freelancer.phone;
                  return (
                    <tr key={p.transaction_id} className="hover:bg-gray-50">
                      <td className="p-3">
                        <div className="font-medium text-gray-900">{p.freelancer.username}</div>
                        <div className="text-xs text-gray-500">{p.freelancer.email}</div>
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
                      <td className="p-3 font-bold text-green-700" dir="ltr">
                        {p.amount.toLocaleString(ar ? "ar-IQ" : "en-US")} {p.currency}
                      </td>
                      <td className="p-3 text-gray-500 text-xs">
                        {new Date(p.requested_at).toLocaleDateString(dateLocale, {
                          month: "short",
                          day: "numeric",
                          year: "numeric",
                        })}
                      </td>
                      <td className="p-3">
                        <div className="flex justify-end">
                          <button
                            onClick={() => onMarkPaid(p)}
                            disabled={isBusy}
                            className="px-3 py-1.5 text-xs font-medium bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 whitespace-nowrap"
                          >
                            {isBusy ? "..." : ar ? "تأكيد الدفع" : "Mark Paid"}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="text-sm text-gray-500">
            {ar
              ? `${processingPayouts.length} طلب سحب معلق — إجمالي: ${totalPending.toLocaleString("ar-IQ")} IQD`
              : `${processingPayouts.length} pending payout request(s) — total: ${totalPending.toLocaleString("en-US")} IQD`}
          </p>
        </div>
      )}

      {/* ── Section 2: FUNDED escrows awaiting release ── */}
      <h3 className="font-semibold text-gray-900">
        {ar ? "مدفوعات ضمان جاهزة للتحرير" : "Escrows ready to release"}
      </h3>
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
                <th className="text-start p-3 font-medium text-gray-600">{ar ? "بيانات Qi Card" : "Qi Card Payout"}</th>
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
                const holderName = escrow.freelancer.qi_card_holder_name;
                const payoutReady = Boolean(escrow.freelancer.qi_card_phone && holderName);
                return (
                  <tr key={escrow.escrow_id} className="hover:bg-gray-50">
                    <td className="p-3">
                      <div className="font-medium text-gray-900">{escrow.freelancer.username}</div>
                      <div className="text-xs text-gray-500">{escrow.freelancer.email}</div>
                    </td>
                    <td className="p-3">
                      {qiPhone ? (
                        <div className="space-y-1">
                          <span className="font-mono text-gray-900 bg-yellow-50 border border-yellow-200 px-2 py-0.5 rounded text-xs inline-block" dir="ltr">
                            {qiPhone}
                          </span>
                          {holderName ? (
                            <div className="text-xs text-gray-700">{holderName}</div>
                          ) : (
                            <div className="text-xs text-amber-700">
                              {ar ? "اسم صاحب البطاقة غير محدد" : "Cardholder name missing"}
                            </div>
                          )}
                        </div>
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
                          disabled={isBusy || !payoutReady}
                          title={!payoutReady ? (ar ? "يحتاج المستقل إلى إكمال بيانات Qi Card" : "Freelancer must complete Qi Card details") : undefined}
                          className="px-3 py-1.5 text-xs font-medium bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
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
