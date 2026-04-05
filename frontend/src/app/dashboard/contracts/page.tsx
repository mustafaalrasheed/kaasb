"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { contractsApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { toast } from "sonner";
import type { ContractSummary } from "@/types/contract";
import {
  CONTRACT_STATUS_LABELS,
  CONTRACT_STATUS_COLORS,
} from "@/types/contract";

const STATUS_TABS = [
  { value: "", label: "الكل" },
  { value: "active", label: "نشط" },
  { value: "completed", label: "مكتمل" },
  { value: "cancelled", label: "ملغى" },
  { value: "disputed", label: "متنازع عليه" },
];

export default function ContractsPage() {
  const { user } = useAuthStore();
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
      toast.error("تعذّر تحميل العقود");
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter]);

  useEffect(() => {
    fetchContracts();
  }, [fetchContracts]);

  return (
    <div className="space-y-6" dir="rtl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">عقودي</h1>
        <p className="mt-1 text-gray-600">
          {total > 0 ? `${total} عقد` : "لا توجد عقود بعد"}
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

      {/* Contracts list */}
      {loading ? (
        <div className="text-center py-12 text-gray-500">جاري التحميل...</div>
      ) : contracts.length === 0 ? (
        <div className="card p-12 text-center">
          <p className="text-lg font-medium text-gray-900">لا توجد عقود</p>
          <p className="text-sm text-gray-500 mt-2">
            تُنشأ العقود تلقائياً عند قبول عرض ما.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {contracts.map((contract) => (
            <ContractCard
              key={contract.id}
              contract={contract}
              userRole={user?.primary_role || ""}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="btn-secondary py-2 px-4 text-sm disabled:opacity-40"
          >
            السابق
          </button>
          <span className="text-sm text-gray-600 px-4">{page} / {totalPages}</span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="btn-secondary py-2 px-4 text-sm disabled:opacity-40"
          >
            التالي
          </button>
        </div>
      )}
    </div>
  );
}

function ContractCard({
  contract,
  userRole,
}: {
  contract: ContractSummary;
  userRole: string;
}) {
  const otherParty =
    userRole === "client" ? contract.freelancer : contract.client;
  const otherLabel = userRole === "client" ? "المستقل" : "العميل";
  const progress =
    contract.milestone_count > 0
      ? Math.round(
          (contract.completed_milestones / contract.milestone_count) * 100
        )
      : 0;

  return (
    <Link href={`/dashboard/contracts/${contract.id}`}>
      <div className="card p-5 hover:shadow-md transition-shadow cursor-pointer">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-3 mb-2 flex-wrap">
              <h3 className="font-semibold text-gray-900 truncate">
                {contract.title}
              </h3>
              <span
                className={`text-xs px-2 py-0.5 rounded-full border ${
                  CONTRACT_STATUS_COLORS[contract.status] || "bg-gray-100"
                }`}
              >
                {CONTRACT_STATUS_LABELS[contract.status] || contract.status}
              </span>
            </div>

            <p className="text-sm text-gray-500 mb-3">
              {contract.job.category} • {otherLabel}:{" "}
              <span className="font-medium text-gray-700">
                {otherParty.display_name ||
                  `${otherParty.first_name} ${otherParty.last_name}`}
              </span>
            </p>

            {/* Progress bar */}
            <div className="flex items-center gap-3">
              <div className="flex-1 bg-gray-100 rounded-full h-2 max-w-xs">
                <div
                  className="bg-brand-500 h-2 rounded-full transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <span className="text-xs text-gray-500">
                {contract.completed_milestones}/{contract.milestone_count} مراحل
              </span>
            </div>
          </div>

          {/* Amount */}
          <div className="text-left shrink-0">
            <p className="text-lg font-bold text-gray-900">
              ${contract.total_amount.toLocaleString()}
            </p>
            <p className="text-xs text-gray-500">
              ${contract.amount_paid.toLocaleString()} مدفوع
            </p>
          </div>
        </div>
      </div>
    </Link>
  );
}
