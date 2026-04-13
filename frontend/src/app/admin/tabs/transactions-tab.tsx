"use client";

interface AdminTransaction {
  id: string;
  transaction_type: string;
  status: string;
  amount: number;
  currency: string;
  platform_fee: number;
  net_amount: number;
  description: string | null;
  created_at: string;
}

interface TransactionsTabProps {
  transactions: AdminTransaction[];
  total: number;
  loading: boolean;
  typeFilter: string;
  statusFilter: string;
  ar: boolean;
  dateLocale: string;
  onTypeFilterChange: (v: string) => void;
  onStatusFilterChange: (v: string) => void;
  onFilter: () => void;
}

export function TransactionsTab({
  transactions, total, loading, typeFilter, statusFilter,
  ar, dateLocale,
  onTypeFilterChange, onStatusFilterChange, onFilter,
}: TransactionsTabProps) {
  const typeLabels: Record<string, string> = ar
    ? { escrow_fund: "تمويل ضمان", escrow_release: "تحرير ضمان", escrow_refund: "استرداد ضمان", platform_fee: "عمولة المنصة", payout: "سحب" }
    : { escrow_fund: "Escrow Fund", escrow_release: "Escrow Release", escrow_refund: "Escrow Refund", platform_fee: "Platform Fee", payout: "Payout" };

  const statusLabels: Record<string, string> = ar
    ? { pending: "معلق", processing: "جارٍ", completed: "مكتمل", failed: "فشل", refunded: "مسترد" }
    : { pending: "Pending", processing: "Processing", completed: "Completed", failed: "Failed", refunded: "Refunded" };

  return (
    <div className="space-y-4">
      <div className="flex gap-3 flex-wrap">
        <select
          value={typeFilter} onChange={(e) => onTypeFilterChange(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
        >
          <option value="">{ar ? "كل الأنواع" : "All Types"}</option>
          <option value="escrow_fund">{ar ? "تمويل ضمان" : "Escrow Fund"}</option>
          <option value="escrow_release">{ar ? "تحرير ضمان" : "Escrow Release"}</option>
          <option value="escrow_refund">{ar ? "استرداد ضمان" : "Escrow Refund"}</option>
          <option value="platform_fee">{ar ? "عمولة المنصة" : "Platform Fee"}</option>
          <option value="payout">{ar ? "سحب" : "Payout"}</option>
        </select>
        <select
          value={statusFilter} onChange={(e) => onStatusFilterChange(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
        >
          <option value="">{ar ? "كل الحالات" : "All Statuses"}</option>
          <option value="pending">{ar ? "معلق" : "Pending"}</option>
          <option value="processing">{ar ? "جارٍ" : "Processing"}</option>
          <option value="completed">{ar ? "مكتمل" : "Completed"}</option>
          <option value="failed">{ar ? "فشل" : "Failed"}</option>
          <option value="refunded">{ar ? "مسترد" : "Refunded"}</option>
        </select>
        <button onClick={onFilter} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">
          {ar ? "تصفية" : "Filter"}
        </button>
      </div>

      <div className="bg-white rounded-lg border overflow-x-auto">
        <table className="min-w-[700px] w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-start p-3 font-medium text-gray-600">{ar ? "النوع" : "Type"}</th>
              <th className="text-start p-3 font-medium text-gray-600">{ar ? "المبلغ" : "Amount"}</th>
              <th className="text-start p-3 font-medium text-gray-600">{ar ? "العمولة" : "Fee"}</th>
              <th className="text-start p-3 font-medium text-gray-600">{ar ? "الصافي" : "Net"}</th>
              <th className="text-start p-3 font-medium text-gray-600">{ar ? "الحالة" : "Status"}</th>
              <th className="text-start p-3 font-medium text-gray-600">{ar ? "الوصف" : "Description"}</th>
              <th className="text-start p-3 font-medium text-gray-600">{ar ? "التاريخ" : "Date"}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {transactions.map((tx) => (
              <tr key={tx.id} className="hover:bg-gray-50">
                <td className="p-3 text-gray-900">{typeLabels[tx.transaction_type] ?? tx.transaction_type}</td>
                <td className="p-3 font-medium" dir="ltr">{tx.amount.toLocaleString()} {tx.currency}</td>
                <td className="p-3 text-gray-500" dir="ltr">{tx.platform_fee.toLocaleString()}</td>
                <td className="p-3 text-green-700 font-medium" dir="ltr">{tx.net_amount.toLocaleString()}</td>
                <td className="p-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    tx.status === "completed" ? "bg-green-50 text-green-700" :
                    tx.status === "pending" ? "bg-yellow-50 text-yellow-700" :
                    tx.status === "failed" ? "bg-red-50 text-red-700" :
                    "bg-gray-100 text-gray-500"
                  }`}>
                    {statusLabels[tx.status] ?? tx.status}
                  </span>
                </td>
                <td className="p-3 text-gray-500 max-w-xs truncate">{tx.description || "—"}</td>
                <td className="p-3 text-gray-500">
                  {new Date(tx.created_at).toLocaleDateString(dateLocale, { month: "short", day: "numeric" })}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {transactions.length === 0 && !loading && (
          <div className="p-8 text-center text-gray-400">
            {ar ? "لا توجد معاملات" : "No transactions found"}
          </div>
        )}
      </div>
      <p className="text-sm text-gray-500">
        {ar ? `${total} معاملة إجمالاً` : `${total} transaction(s) total`}
      </p>
    </div>
  );
}
