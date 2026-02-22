"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { proposalsApi } from "@/lib/api";
import { toast } from "sonner";
import type { ProposalSummary } from "@/types/proposal";
import { PROPOSAL_STATUS_LABELS, PROPOSAL_STATUS_COLORS } from "@/types/proposal";

const STATUS_TABS = [
  { value: "", label: "All" },
  { value: "pending", label: "Pending" },
  { value: "shortlisted", label: "Shortlisted" },
  { value: "accepted", label: "Accepted" },
  { value: "rejected", label: "Rejected" },
  { value: "withdrawn", label: "Withdrawn" },
];

function formatBudget(job: ProposalSummary["job"]): string {
  if (job.job_type === "fixed" && job.fixed_price) return `$${job.fixed_price.toLocaleString()}`;
  if (job.budget_min && job.budget_max) return `$${job.budget_min} - $${job.budget_max}/hr`;
  if (job.budget_min) return `From $${job.budget_min}/hr`;
  return "—";
}

export default function MyProposalsPage() {
  const [proposals, setProposals] = useState<ProposalSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);

  const fetchProposals = useCallback(async () => {
    setIsLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 15 };
      if (statusFilter) params.status = statusFilter;
      const response = await proposalsApi.getMyProposals(params as any);
      setProposals(response.data.proposals);
      setTotal(response.data.total);
      setTotalPages(response.data.total_pages);
    } catch {
      setProposals([]);
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter, page]);

  useEffect(() => {
    fetchProposals();
  }, [fetchProposals]);

  const handleWithdraw = async (proposalId: string) => {
    if (!confirm("Withdraw this proposal? You won't be able to resubmit.")) return;
    try {
      await proposalsApi.withdraw(proposalId);
      toast.success("Proposal withdrawn");
      fetchProposals();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to withdraw");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">My Proposals</h1>
        <p className="mt-1 text-gray-600">
          {total > 0 ? `${total} proposals submitted` : "Track your submitted proposals"}
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

      {/* Proposals list */}
      {isLoading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : proposals.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-lg font-medium text-gray-900">No proposals found</p>
          <p className="mt-2 text-gray-600">
            {statusFilter ? "No proposals with this status." : "You haven't submitted any proposals yet."}
          </p>
          <Link href="/jobs" className="inline-block mt-4 btn-primary py-2 px-5 text-sm">
            Browse Jobs
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {proposals.map((proposal) => (
            <div key={proposal.id} className="card p-5">
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Link
                      href={`/jobs/${proposal.job.id}`}
                      className="font-semibold text-gray-900 hover:text-brand-600 truncate"
                    >
                      {proposal.job.title}
                    </Link>
                    <span className={`shrink-0 px-2 py-0.5 text-xs font-medium rounded-full border ${PROPOSAL_STATUS_COLORS[proposal.status]}`}>
                      {PROPOSAL_STATUS_LABELS[proposal.status]}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-gray-500">
                    <span>{proposal.job.category}</span>
                    <span>Job budget: {formatBudget(proposal.job)}</span>
                    <span>Your bid: <span className="font-medium text-gray-900">${proposal.bid_amount.toLocaleString()}</span></span>
                    {proposal.estimated_duration && <span>Est: {proposal.estimated_duration}</span>}
                    <span>
                      Submitted {new Date(proposal.submitted_at).toLocaleDateString("en-US", {
                        month: "short", day: "numeric",
                      })}
                    </span>
                  </div>
                </div>

                <div className="flex gap-2 shrink-0">
                  <Link href={`/jobs/${proposal.job.id}`} className="btn-secondary py-1.5 px-3 text-xs">
                    View Job
                  </Link>
                  {(proposal.status === "pending" || proposal.status === "shortlisted") && (
                    <button
                      onClick={() => handleWithdraw(proposal.id)}
                      className="text-xs text-danger-500 hover:text-danger-700 px-2"
                    >
                      Withdraw
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="btn-secondary py-2 px-4 text-sm disabled:opacity-40"
          >
            Previous
          </button>
          <span className="text-sm text-gray-600 px-4">Page {page} of {totalPages}</span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="btn-secondary py-2 px-4 text-sm disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
