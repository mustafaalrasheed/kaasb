"use client";

import { useState, useEffect, useCallback } from "react";
import { paymentsApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { toast } from "sonner";
import type {
  PaymentSummary,
  TransactionDetail,
  PaymentAccount,
} from "@/types/payment";
import {
  TRANSACTION_TYPE_LABELS,
  TRANSACTION_STATUS_COLORS,
  PROVIDER_LABELS,
} from "@/types/payment";

export default function PaymentsPage() {
  const { user } = useAuthStore();
  const [summary, setSummary] = useState<PaymentSummary | null>(null);
  const [transactions, setTransactions] = useState<TransactionDetail[]>([]);
  const [totalTx, setTotalTx] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  // Setup account form
  const [showSetup, setShowSetup] = useState(false);
  const [setupProvider, setSetupProvider] = useState("stripe");
  const [wiseEmail, setWiseEmail] = useState("");

  // Payout form
  const [showPayout, setShowPayout] = useState(false);
  const [payoutAmount, setPayoutAmount] = useState("");
  const [payoutAccountId, setPayoutAccountId] = useState("");

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
      toast.error("Failed to load payment data");
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSetupAccount = async () => {
    try {
      const data: Record<string, string> = { provider: setupProvider };
      if (setupProvider === "wise") {
        if (!wiseEmail) {
          toast.error("Wise email is required");
          return;
        }
        data.wise_email = wiseEmail;
      }
      await paymentsApi.setupAccount(data);
      toast.success(`${PROVIDER_LABELS[setupProvider]} account created`);
      setShowSetup(false);
      setWiseEmail("");
      fetchData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to setup account");
    }
  };

  const handlePayout = async () => {
    try {
      const amount = parseFloat(payoutAmount);
      if (isNaN(amount) || amount < 10) {
        toast.error("Minimum payout is $10");
        return;
      }
      if (!payoutAccountId) {
        toast.error("Select a payment account");
        return;
      }
      const res = await paymentsApi.requestPayout({
        amount,
        payment_account_id: payoutAccountId,
      });
      toast.success(res.data.message);
      setShowPayout(false);
      setPayoutAmount("");
      fetchData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Payout failed");
    }
  };

  if (loading && !summary) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-48 bg-gray-200 rounded" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-24 bg-gray-100 rounded-lg" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  const isFreelancer = user?.primary_role === "freelancer";

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Payments</h1>
        <div className="flex gap-2">
          <button
            onClick={() => setShowSetup(!showSetup)}
            className="px-4 py-2 text-sm bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            + Add Account
          </button>
          {isFreelancer && (
            <button
              onClick={() => setShowPayout(!showPayout)}
              className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              Request Payout
            </button>
          )}
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {isFreelancer ? (
            <>
              <SummaryCard label="Total Earned" value={summary.total_earned} color="green" />
              <SummaryCard label="Pending Escrow" value={summary.pending_escrow} color="blue" />
              <SummaryCard label="Platform Fees" value={summary.total_platform_fees} color="yellow" />
              <SummaryCard label="Transactions" value={summary.transaction_count} isCurrency={false} color="gray" />
            </>
          ) : (
            <>
              <SummaryCard label="Total Spent" value={summary.total_spent} color="red" />
              <SummaryCard label="In Escrow" value={summary.pending_escrow} color="blue" />
              <SummaryCard label="Platform Fees" value={summary.total_platform_fees} color="yellow" />
              <SummaryCard label="Transactions" value={summary.transaction_count} isCurrency={false} color="gray" />
            </>
          )}
        </div>
      )}

      {/* Setup Account Form */}
      {showSetup && (
        <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
          <h3 className="font-semibold text-gray-900">Setup Payment Account</h3>
          <div className="flex gap-3 items-end">
            <div>
              <label className="block text-sm text-gray-600 mb-1">Provider</label>
              <select
                value={setupProvider}
                onChange={(e) => setSetupProvider(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
              >
                <option value="stripe">Stripe (Cards)</option>
                <option value="wise">Wise (Iraq/International)</option>
              </select>
            </div>
            {setupProvider === "wise" && (
              <div className="flex-1">
                <label className="block text-sm text-gray-600 mb-1">Wise Email</label>
                <input
                  type="email"
                  value={wiseEmail}
                  onChange={(e) => setWiseEmail(e.target.value)}
                  placeholder="your@email.com"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                />
              </div>
            )}
            <button
              onClick={handleSetupAccount}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Create Account
            </button>
          </div>
        </div>
      )}

      {/* Payout Form */}
      {showPayout && summary && (
        <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
          <h3 className="font-semibold text-gray-900">Request Payout</h3>
          <div className="flex gap-3 items-end">
            <div>
              <label className="block text-sm text-gray-600 mb-1">Amount ($)</label>
              <input
                type="number"
                value={payoutAmount}
                onChange={(e) => setPayoutAmount(e.target.value)}
                placeholder="100.00"
                min="10"
                step="0.01"
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm w-32"
              />
            </div>
            <div className="flex-1">
              <label className="block text-sm text-gray-600 mb-1">To Account</label>
              <select
                value={payoutAccountId}
                onChange={(e) => setPayoutAccountId(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              >
                <option value="">Select account...</option>
                {summary.payment_accounts.map((acc) => (
                  <option key={acc.id} value={acc.id}>
                    {PROVIDER_LABELS[acc.provider] || acc.provider}
                    {acc.wise_email ? ` (${acc.wise_email})` : ""}
                  </option>
                ))}
              </select>
            </div>
            <button
              onClick={handlePayout}
              className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              Send Payout
            </button>
          </div>
        </div>
      )}

      {/* Payment Accounts */}
      {summary && summary.payment_accounts.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h3 className="font-semibold text-gray-900 mb-3">Payment Accounts</h3>
          <div className="space-y-2">
            {summary.payment_accounts.map((acc) => (
              <div
                key={acc.id}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <span className="text-lg">{acc.provider === "stripe" ? "💳" : "🌍"}</span>
                  <div>
                    <span className="font-medium text-gray-900">
                      {PROVIDER_LABELS[acc.provider] || acc.provider}
                    </span>
                    {acc.wise_email && (
                      <span className="text-sm text-gray-500 ml-2">{acc.wise_email}</span>
                    )}
                  </div>
                </div>
                <span
                  className={`text-xs px-2 py-1 rounded-full ${
                    acc.status === "verified"
                      ? "bg-green-50 text-green-700"
                      : "bg-yellow-50 text-yellow-700"
                  }`}
                >
                  {acc.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Transaction History */}
      <div className="bg-white border border-gray-200 rounded-lg">
        <div className="p-4 border-b border-gray-100">
          <h3 className="font-semibold text-gray-900">
            Transaction History ({totalTx})
          </h3>
        </div>
        {transactions.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            No transactions yet
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {transactions.map((tx) => (
              <div key={tx.id} className="p-4 flex items-center justify-between">
                <div>
                  <div className="font-medium text-gray-900">
                    {TRANSACTION_TYPE_LABELS[tx.transaction_type] || tx.transaction_type}
                  </div>
                  <div className="text-sm text-gray-500">
                    {tx.description || "—"}
                  </div>
                  <div className="text-xs text-gray-400 mt-1">
                    {new Date(tx.created_at).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-semibold text-gray-900">
                    {tx.transaction_type === "escrow_fund" ||
                    tx.transaction_type === "platform_fee"
                      ? "-"
                      : "+"}
                    ${tx.amount.toFixed(2)}
                  </div>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${
                      TRANSACTION_STATUS_COLORS[tx.status] || "bg-gray-100"
                    }`}
                  >
                    {tx.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        {totalTx > 10 && (
          <div className="p-4 border-t border-gray-100 flex items-center justify-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50"
            >
              Previous
            </button>
            <span className="text-sm text-gray-600">
              Page {page} of {Math.ceil(totalTx / 10)}
            </span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={page >= Math.ceil(totalTx / 10)}
              className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// === Summary Card Component ===

function SummaryCard({
  label,
  value,
  color,
  isCurrency = true,
}: {
  label: string;
  value: number;
  color: string;
  isCurrency?: boolean;
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
      <div className="text-xl font-bold text-gray-900 mt-1">
        {isCurrency ? `$${value.toFixed(2)}` : value}
      </div>
    </div>
  );
}
