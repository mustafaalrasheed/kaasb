"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { contractsApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { useLocale } from "@/providers/locale-provider";
import { toast } from "sonner";
import type { ContractSummary } from "@/types/contract";
import { CONTRACT_STATUS_COLORS } from "@/types/contract";

export default function ContractsPage() {
  const { user } = useAuthStore();
  const { locale } = useLocale();
  const ar = locale === "ar";

  const STATUS_TABS = [
    { value: "", label: ar ? "الكل" : "All" },
    { value: "active", label: ar ? "نشط" : "Active" },
    { value: "completed", label: ar ? "مكتمل" : "Completed" },
    { value: "cancelled", label: ar ? "ملغى" : "Cancelled" },
    { value: "disputed", label: ar ? "متنازع عليه" : "Disputed" },
  ];

  const CONTRACT_STATUS_LABELS_LOCALE: Record<string, string> = ar
    ? { active: "نشط", completed: "مكتمل", cancelled: "ملغى", disputed: "متنازع عليه", pending: "قيد الانتظار" }
    : { active: "Active", completed: "Completed", cancelled: "Cancelled", disputed: "Disputed", pending: "Pending" };

  const [contracts, setContracts] = useState<ContractSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);

  const fetchContracts = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = { page, page_size: 15 };
      if (statusFilter) params.status = statusFilter;
      const res = await contractsApi.getMyContracts(params);
      setContracts(res.data.contracts);
      setTotal(res.data.total);
      setTotalPages(res.data.total_pages);
    } catch {
      toast.error(ar ? "تعذّر تحميل العقود" : "Failed to load contracts");
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter, ar]);

  useEffect(() => { fetchContracts(); }, [fetchContracts]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          {ar ? "عقودي" : "My Contracts"}
        </h1>
        <p className="mt-1 text-gray-600">
          {total > 0
            ? (ar ? `${total} عقد` : `${total} contract${total !== 1 ? "s" : ""}`)
            : (ar ? "لا توجد عقود بعد" : "No contracts yet")}
        </p>
      </div>

      {/* Status tabs */}
      <div className="flex gap-1 border-b border-gray-200 overflow-x-auto">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => { setStatusFilter(tab.value); setPage(1); }}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
              statusFilter === tab.value
                ? "border-brand-500 text-brand-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">
          {ar ? "جاري التحميل..." : "Loading..."}
        </div>
      ) : contracts.length === 0 ? (
        <div className="card p-12 text-center">
          <p className="text-lg font-medium text-gray-900">
            {ar ? "لا توجد عقود" : "No contracts"}
          </p>
          <p className="text-sm text-gray-500 mt-2">
            {ar ? "تُنشأ العقود تلقائياً عند قبول عرض ما."
                 : "Contracts are created automatically when a proposal is accepted."}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {contracts.map((contract) => (
            <ContractCard
              key={contract.id}
              contract={contract}
              userRole={user?.primary_role || ""}
              ar={ar}
              statusLabels={CONTRACT_STATUS_LABELS_LOCALE}
            />
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}
            className="btn-secondary py-2 px-4 text-sm disabled:opacity-40">
            {ar ? "السابق" : "Previous"}
          </button>
          <span className="text-sm text-gray-600 px-4">{page} / {totalPages}</span>
          <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
            className="btn-secondary py-2 px-4 text-sm disabled:opacity-40">
            {ar ? "التالي" : "Next"}
          </button>
        </div>
      )}
    </div>
  );
}

function ContractCard({ contract, userRole, ar, statusLabels }: {
  contract: ContractSummary;
  userRole: string;
  ar: boolean;
  statusLabels: Record<string, string>;
}) {
  const otherParty = userRole === "client" ? contract.freelancer : contract.client;
  const otherLabel = userRole === "client" ? (ar ? "المستقل" : "Freelancer") : (ar ? "العميل" : "Client");
  const progress = contract.milestone_count > 0
    ? Math.round((contract.completed_milestones / contract.milestone_count) * 100)
    : 0;

  return (
    <Link href={`/dashboard/contracts/${contract.id}`}>
      <div className="card p-5 hover:shadow-md transition-shadow cursor-pointer">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-3 mb-2 flex-wrap">
              <h3 className="font-semibold text-gray-900 truncate">{contract.title}</h3>
              <span className={`text-xs px-2 py-0.5 rounded-full border ${CONTRACT_STATUS_COLORS[contract.status] || "bg-gray-100"}`}>
                {statusLabels[contract.status] || contract.status}
              </span>
            </div>
            <p className="text-sm text-gray-500 mb-3">
              {contract.job.category} • {otherLabel}:{" "}
              <span className="font-medium text-gray-700">
                {otherParty.display_name || `${otherParty.first_name} ${otherParty.last_name}`}
              </span>
            </p>
            <div className="flex items-center gap-3">
              <div className="flex-1 bg-gray-100 rounded-full h-2 max-w-xs">
                <div className="bg-brand-500 h-2 rounded-full transition-all" style={{ width: `${progress}%` }} />
              </div>
              <span className="text-xs text-gray-500">
                {contract.completed_milestones}/{contract.milestone_count} {ar ? "مراحل" : "milestones"}
              </span>
            </div>
          </div>
          <div className="text-end shrink-0">
            <p className="text-lg font-bold text-gray-900">${contract.total_amount.toLocaleString()}</p>
            <p className="text-xs text-gray-500">
              ${contract.amount_paid.toLocaleString()} {ar ? "مدفوع" : "paid"}
            </p>
          </div>
        </div>
      </div>
    </Link>
  );
}
