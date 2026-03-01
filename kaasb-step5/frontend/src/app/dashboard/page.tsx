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
  { value: "", label: "All" },
  { value: "active", label: "Active" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
  { value: "disputed", label: "Disputed" },
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
      toast.error("Failed to load contracts");
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter]);

  useEffect(() => {
    fetchContracts();
  }, [fetchContracts]);

  const handleTabChange = (value: string) => {
    setStatusFilter(value);
    setPage(1);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">My Contracts</h1>
          <p className="text-sm text-gray-500 mt-1">
            {total} contract{total !== 1 ? "s" : ""}
          </p>
        </div>
      </div>

      {/* Status tabs */}
      <div className="flex gap-2 mb-6 flex-wrap">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => handleTabChange(tab.value)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              statusFilter === tab.value
                ? "bg-brand-500 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Contracts list */}
      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : contracts.length === 0 ? (
        <div className="card p-12 text-center">
          <p className="text-gray-500 text-lg">No contracts found</p>
          <p className="text-gray-400 text-sm mt-2">
            Contracts are created automatically when a proposal is accepted.
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
        <div className="flex justify-center gap-2 mt-8">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="px-4 py-2 rounded-lg border text-sm disabled:opacity-40"
          >
            Previous
          </button>
          <span className="px-4 py-2 text-sm text-gray-600">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="px-4 py-2 rounded-lg border text-sm disabled:opacity-40"
          >
            Next
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
  const otherLabel = userRole === "client" ? "Freelancer" : "Client";
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
            <div className="flex items-center gap-3 mb-2">
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
                {contract.completed_milestones}/{contract.milestone_count}{" "}
                milestones
              </span>
            </div>
          </div>

          {/* Amount */}
          <div className="text-right shrink-0">
            <p className="text-lg font-bold text-gray-900">
              ${contract.total_amount.toLocaleString()}
            </p>
            <p className="text-xs text-gray-500">
              ${contract.amount_paid.toLocaleString()} paid
            </p>
          </div>
        </div>
      </div>
    </Link>
  );
}
