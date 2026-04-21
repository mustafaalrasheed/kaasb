"use client";

import { useState, useEffect, useCallback } from "react";
import { paymentsApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { useLocale } from "@/providers/locale-provider";
import { toast } from "sonner";
import { getApiError } from "@/lib/utils";
import type { PaymentSummary, TransactionDetail } from "@/types/payment";
import {
  TRANSACTION_TYPE_LABELS,
  TRANSACTION_STATUS_COLORS,
  PROVIDER_LABELS,
} from "@/types/payment";

const TX_SIGN: Record<string, string> = {
  escrow_fund: "-",
  platform_fee: "-",
};

export default function PaymentsPage() {
  const { user } = useAuthStore();
  const { locale } = useLocale();
  const ar = locale === "ar";

  const [summary, setSummary] = useState<PaymentSummary | null>(null);
  const [transactions, setTransactions] = useState<TransactionDetail[]>([]);
  const [totalTx, setTotalTx] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const [showSetup, setShowSetup] = useState(false);
  const [qiCardPhone, setQiCardPhone] = useState("");
  const [qiCardHolderName, setQiCardHolderName] = useState("");

  const [showPayout, setShowPayout] = useState(false);
  const [payoutAmount, setPayoutAmount] = useState("");
  const [payoutAccountId, setPayoutAccountId] = useState("");

  const ACCOUNT_STATUS_LABELS: Record<string, string> = ar
    ? { verified: "موثَّق", pending: "قيد المراجعة", rejected: "مرفوض" }
    : { verified: "Verified", pending: "Pending Review", rejected: "Rejected" };

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [summaryRes, txRes] = await Promise.all([
        paymentsApi.getSummary(),
        paymentsApi.getTransactions({ page, page_size: 10 }),
      ]);
      setSummary(summaryRes.data);
      setTransactions(txRes.data.transactions);
      setTotalTx(txRes.data.total);
    } catch {
      toast.error(ar ? "تعذّر تحميل بيانات المدفوعات" : "Failed to load payment data");
    } finally {
      setLoading(false);
    }
  }, [page, ar]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleSetupAccount = async () => {
    try {
      await paymentsApi.setupAccount({
        provider: "qi_card",
        ...(qiCardPhone ? { qi_card_phone: qiCardPhone } : {}),
        ...(qiCardHolderName.trim() ? { qi_card_holder_name: qiCardHolderName.trim() } : {}),
      });
      toast.success(ar ? "تم حفظ تفاصيل حساب Qi Card" : "Qi Card account saved");
      setShowSetup(false);
      setQiCardPhone("");
      setQiCardHolderName("");
      fetchData();
    } catch (err: unknown) {
      toast.error(getApiError(err, ar ? "تعذّر حفظ الحساب" : "Failed to save account"));
    }
  };

  const handlePayout = async () => {
    const amount = parseFloat(payoutAmount);
    if (isNaN(amount) || amount <= 0) {
      toast.error(ar ? "أدخل مبلغاً صحيحاً" : "Enter a valid amount");
      return;
    }
    if (!payoutAccountId) {
      toast.error(ar ? "اختر حساب الدفع" : "Select a payment account");
      return;
    }
    try {
      const res = await paymentsApi.requestPayout({ amount, payment_account_id: payoutAccountId });
      toast.success(res.data.message);
      setShowPayout(false);
      setPayoutAmount("");
      fetchData();
    } catch (err: unknown) {
      toast.error(getApiError(err, ar ? "تعذّر طلب السحب" : "Failed to request payout"));
    }
  };

  if (loading && !summary) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-48 bg-gray-200 rounded" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => <div key={i} className="h-24 bg-gray-100 rounded-lg" />)}
          </div>
        </div>
      </div>
    );
  }

  const isFreelancer = user?.primary_role === "freelancer";
  const totalPages = Math.ceil(totalTx / 10);
  const dateLocale = ar ? "ar-IQ" : "en-GB";

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-2xl font-bold text-gray-900">
          {ar ? "المدفوعات" : "Payments"}
        </h1>
        <div className="flex gap-2">
          <button
            onClick={() => setShowSetup(!showSetup)}
            className="px-4 py-2 text-sm bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            {ar ? "+ إضافة حساب" : "+ Add Account"}
          </button>
          {isFreelancer && (
            <button
              onClick={() => setShowPayout(!showPayout)}
              className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              {ar ? "طلب سحب" : "Request Payout"}
            </button>
          )}
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {isFreelancer ? (
            <>
              <SummaryCard
                label={ar ? "متاح للسحب" : "Available to Withdraw"}
                value={summary.available_balance}
                color="green"
                ar={ar}
              />
              <SummaryCard
                label={ar ? "قيد السحب" : "Pending Payout"}
                value={summary.pending_payout}
                color="yellow"
                ar={ar}
              />
              <SummaryCard label={ar ? "محتجز في الضمان" : "In Escrow"} value={summary.pending_escrow} color="blue" ar={ar} />
              <SummaryCard label={ar ? "إجمالي الأرباح" : "Total Earned"} value={summary.total_earned} color="gray" ar={ar} />
            </>
          ) : (
            <>
              <SummaryCard label={ar ? "إجمالي الإنفاق" : "Total Spent"} value={summary.total_spent} color="red" ar={ar} />
              <SummaryCard label={ar ? "في الضمان" : "In Escrow"} value={summary.pending_escrow} color="blue" ar={ar} />
              <SummaryCard label={ar ? "عمولة المنصة" : "Platform Fees"} value={summary.total_platform_fees} color="yellow" ar={ar} />
              <SummaryCard label={ar ? "المعاملات" : "Transactions"} value={summary.transaction_count} isCurrency={false} color="gray" ar={ar} />
            </>
          )}
        </div>
      )}

      {/* Setup Account Form */}
      {showSetup && (
        <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
          <h3 className="font-semibold text-gray-900">
            {ar ? "حساب Qi Card لاستلام الأرباح" : "Qi Card Payout Account"}
          </h3>
          <p className="text-sm text-gray-500">
            {ar
              ? "الدفع من العملاء يتم عبر بوابة Qi Card تلقائياً. للاستلام منكم، يحوّل الأدمن المبلغ يدوياً عبر تطبيق Qi Card إلى نفس الرقم والاسم الموجود على البطاقة — تأكد من تطابق الاسم والرقم مع ما هو مسجّل لدى Qi Card."
              : "Client payments go through Qi Card automatically. For payouts, the admin transfers the amount manually via the Qi Card app to the phone + cardholder name below — both must match what's registered with Qi Card exactly."}
          </p>
          <div className="grid md:grid-cols-2 gap-3">
            <div>
              <label className="block text-sm text-gray-600 mb-1">
                {ar ? "رقم هاتف Qi Card" : "Qi Card phone number"}
              </label>
              <input
                type="tel"
                value={qiCardPhone}
                onChange={(e) => setQiCardPhone(e.target.value)}
                placeholder="+964 7XX XXX XXXX"
                dir="ltr"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">
                {ar ? "اسم صاحب البطاقة (كما هو مسجّل)" : "Cardholder name (as registered)"}
              </label>
              <input
                type="text"
                value={qiCardHolderName}
                onChange={(e) => setQiCardHolderName(e.target.value)}
                placeholder={ar ? "مصطفى غسّان عبد" : "Mustafa Ghassan Abd"}
                maxLength={128}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div className="flex justify-end">
            <button
              onClick={handleSetupAccount}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              {ar ? "حفظ" : "Save"}
            </button>
          </div>
        </div>
      )}

      {/* Payout Form */}
      {showPayout && summary && (
        <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
          <h3 className="font-semibold text-gray-900">
            {ar ? "طلب سحب" : "Request Payout"}
          </h3>
          <div className="flex gap-3 items-end flex-wrap">
            <div>
              <label className="block text-sm text-gray-600 mb-1">
                {ar ? "المبلغ (د.ع)" : "Amount (IQD)"}
              </label>
              <input
                type="number"
                value={payoutAmount}
                onChange={(e) => setPayoutAmount(e.target.value)}
                placeholder="10000"
                min="1"
                step="1"
                dir="ltr"
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm w-32"
              />
            </div>
            <div className="flex-1 min-w-[160px]">
              <label className="block text-sm text-gray-600 mb-1">
                {ar ? "إلى الحساب" : "To Account"}
              </label>
              <select
                value={payoutAccountId}
                onChange={(e) => setPayoutAccountId(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              >
                <option value="">{ar ? "اختر الحساب..." : "Select account..."}</option>
                {summary.payment_accounts.map((acc) => (
                  <option key={acc.id} value={acc.id}>
                    {PROVIDER_LABELS[acc.provider] || acc.provider}
                    {acc.qi_card_phone ? ` (${acc.qi_card_phone})` : ""}
                  </option>
                ))}
              </select>
            </div>
            <button
              onClick={handlePayout}
              className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              {ar ? "تأكيد السحب" : "Confirm Payout"}
            </button>
          </div>
        </div>
      )}

      {/* Payment Accounts */}
      {summary && summary.payment_accounts.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h3 className="font-semibold text-gray-900 mb-3">
            {ar ? "حسابات الدفع" : "Payment Accounts"}
          </h3>
          <div className="space-y-2">
            {summary.payment_accounts.map((acc) => {
              const payoutReady = Boolean(acc.qi_card_phone && acc.qi_card_holder_name);
              return (
                <div key={acc.id} className="p-3 bg-gray-50 rounded-lg space-y-2">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <span className="text-lg">💳</span>
                      <div>
                        <div className="font-medium text-gray-900">
                          {PROVIDER_LABELS[acc.provider] || acc.provider}
                        </div>
                        {acc.qi_card_phone && (
                          <div className="text-xs text-gray-500" dir="ltr">{acc.qi_card_phone}</div>
                        )}
                        {acc.qi_card_holder_name && (
                          <div className="text-xs text-gray-500">{acc.qi_card_holder_name}</div>
                        )}
                      </div>
                    </div>
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      acc.status === "verified" ? "bg-green-50 text-green-700" : "bg-yellow-50 text-yellow-700"
                    }`}>
                      {ACCOUNT_STATUS_LABELS[acc.status] || acc.status}
                    </span>
                  </div>
                  {!payoutReady && (
                    <div className="text-xs bg-amber-50 text-amber-800 rounded-md px-2 py-1.5">
                      {ar
                        ? "لن يتمكّن الأدمن من تحويل أرباحك حتى تُدخل رقم هاتف Qi Card واسم صاحب البطاقة."
                        : "Admin can't release payouts until both the Qi Card phone and cardholder name are set."}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Transaction History */}
      <div className="bg-white border border-gray-200 rounded-lg">
        <div className="p-4 border-b border-gray-100">
          <h3 className="font-semibold text-gray-900">
            {ar ? `سجل المعاملات (${totalTx})` : `Transaction History (${totalTx})`}
          </h3>
        </div>
        {transactions.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            {ar ? "لا توجد معاملات بعد" : "No transactions yet"}
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {transactions.map((tx) => (
              <div key={tx.id} className="p-4 flex items-center justify-between">
                <div>
                  <div className="font-medium text-gray-900">
                    {TRANSACTION_TYPE_LABELS[tx.transaction_type] || tx.transaction_type}
                  </div>
                  <div className="text-sm text-gray-500">{tx.description || "—"}</div>
                  <div className="text-xs text-gray-400 mt-1">
                    {new Date(tx.created_at).toLocaleDateString(dateLocale, {
                      month: "short", day: "numeric", year: "numeric",
                      hour: "2-digit", minute: "2-digit",
                    })}
                  </div>
                </div>
                <div className="text-end">
                  <div className="font-semibold text-gray-900">
                    {TX_SIGN[tx.transaction_type] ?? "+"}{tx.amount.toLocaleString(ar ? "ar-IQ" : "en-US")} {ar ? "د.ع" : "IQD"}
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${TRANSACTION_STATUS_COLORS[tx.status] || "bg-gray-100"}`}>
                    {tx.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

        {totalTx > 10 && (
          <div className="p-4 border-t border-gray-100 flex items-center justify-center gap-2">
            <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
              className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50">
              {ar ? "السابق" : "Previous"}
            </button>
            <span className="text-sm text-gray-600">{page} / {totalPages}</span>
            <button onClick={() => setPage((p) => p + 1)} disabled={page >= totalPages}
              className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50">
              {ar ? "التالي" : "Next"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function SummaryCard({ label, value, color, isCurrency = true, ar = false }: {
  label: string; value: number; color: string; isCurrency?: boolean; ar?: boolean;
}) {
  const colorMap: Record<string, string> = {
    green: "bg-green-50 border-green-200",
    blue: "bg-blue-50 border-blue-200",
    red: "bg-red-50 border-red-200",
    yellow: "bg-yellow-50 border-yellow-200",
    gray: "bg-gray-50 border-gray-200",
  };
  return (
    <div className={`p-4 rounded-lg border ${colorMap[color] || colorMap.gray}`}>
      <div className="text-sm text-gray-600">{label}</div>
      <div className="text-xl font-bold text-gray-900 mt-1" dir="ltr">
        {isCurrency
          ? `${value.toLocaleString(ar ? "ar-IQ" : "en-US")} ${ar ? "د.ع" : "IQD"}`
          : value}
      </div>
    </div>
  );
}
