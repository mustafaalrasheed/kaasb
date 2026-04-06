"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { proposalsApi } from "@/lib/api";
import { useLocale } from "@/providers/locale-provider";
import { toast } from "sonner";
import { getApiError } from "@/lib/utils";
import type { ProposalSummary } from "@/types/proposal";
import { PROPOSAL_STATUS_LABELS, PROPOSAL_STATUS_COLORS } from "@/types/proposal";

export default function MyProposalsPage() {
  const { locale } = useLocale();
  const ar = locale === "ar";

  const STATUS_TABS = [
    { value: "", label: ar ? "الكل" : "All" },
    { value: "pending", label: ar ? "معلق" : "Pending" },
    { value: "shortlisted", label: ar ? "قائمة مختصرة" : "Shortlisted" },
    { value: "accepted", label: ar ? "مقبول" : "Accepted" },
    { value: "rejected", label: ar ? "مرفوض" : "Rejected" },
    { value: "withdrawn", label: ar ? "مسحوب" : "Withdrawn" },
  ];

  const formatBudget = (job: ProposalSummary["job"]): string => {
    const numLocale = ar ? "ar-IQ" : "en-US";
    const currency = ar ? "د.ع" : "IQD";
    const perHour = ar ? "د.ع/س" : "IQD/hr";
    const from = ar ? "من " : "from ";
    if (job.job_type === "fixed" && job.fixed_price)
      return `${job.fixed_price.toLocaleString(numLocale)} ${currency}`;
    if (job.budget_min && job.budget_max)
      return `${job.budget_min.toLocaleString(numLocale)} - ${job.budget_max.toLocaleString(numLocale)} ${perHour}`;
    if (job.budget_min) return `${from}${job.budget_min.toLocaleString(numLocale)} ${perHour}`;
    return "—";
  };

  const [proposals, setProposals] = useState<ProposalSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);

  const fetchProposals = useCallback(async () => {
    setIsLoading(true);
    try {
      const params: Record<string, string | number> = { page, page_size: 15 };
      if (statusFilter) params.status = statusFilter;
      const response = await proposalsApi.getMyProposals(params);
      setProposals(response.data.proposals);
      setTotal(response.data.total);
      setTotalPages(response.data.total_pages);
    } catch {
      setProposals([]);
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter, page]);

  useEffect(() => { fetchProposals(); }, [fetchProposals]);

  const handleWithdraw = async (proposalId: string) => {
    const msg = ar
      ? "هل تريد سحب هذا العرض؟ لن تتمكن من إعادة تقديمه."
      : "Withdraw this proposal? You won't be able to resubmit it.";
    if (!confirm(msg)) return;
    try {
      await proposalsApi.withdraw(proposalId);
      toast.success(ar ? "تم سحب العرض" : "Proposal withdrawn");
      fetchProposals();
    } catch (err: unknown) {
      toast.error(getApiError(err, ar ? "تعذّر سحب العرض" : "Failed to withdraw proposal"));
    }
  };

  const dateLocale = ar ? "ar-IQ" : "en-GB";
  const numLocale = ar ? "ar-IQ" : "en-US";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          {ar ? "عروضي" : "My Proposals"}
        </h1>
        <p className="mt-1 text-gray-600">
          {total > 0
            ? (ar ? `${total} عرض مقدَّم` : `${total} proposal${total !== 1 ? "s" : ""} submitted`)
            : (ar ? "تتبع عروضك المقدمة" : "Track your submitted proposals")}
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

      {isLoading ? (
        <div className="text-center py-12 text-gray-500">
          {ar ? "جاري التحميل..." : "Loading..."}
        </div>
      ) : proposals.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-lg font-medium text-gray-900">
            {ar ? "لا توجد عروض" : "No proposals found"}
          </p>
          <p className="mt-2 text-gray-600">
            {statusFilter
              ? (ar ? "لا توجد عروض بهذه الحالة." : "No proposals with this status.")
              : (ar ? "لم تقدم أي عروض بعد." : "You haven't submitted any proposals yet.")}
          </p>
          <Link href="/jobs" className="inline-block mt-4 btn-primary py-2 px-5 text-sm">
            {ar ? "تصفح الوظائف" : "Browse Jobs"}
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {proposals.map((proposal) => (
            <div key={proposal.id} className="card p-5">
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <Link href={`/jobs/${proposal.job.id}`}
                      className="font-semibold text-gray-900 hover:text-brand-600 truncate">
                      {proposal.job.title}
                    </Link>
                    <span className={`shrink-0 px-2 py-0.5 text-xs font-medium rounded-full border ${PROPOSAL_STATUS_COLORS[proposal.status]}`}>
                      {PROPOSAL_STATUS_LABELS[proposal.status]}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-gray-500">
                    <span>{proposal.job.category}</span>
                    <span>
                      {ar ? "ميزانية الوظيفة:" : "Job budget:"} {formatBudget(proposal.job)}
                    </span>
                    <span>
                      {ar ? "عرضك:" : "Your bid:"}{" "}
                      <span className="font-medium text-gray-900">
                        {proposal.bid_amount.toLocaleString(numLocale)} {ar ? "د.ع" : "IQD"}
                      </span>
                    </span>
                    {proposal.estimated_duration && (
                      <span>
                        {ar ? "المدة المقدَّرة:" : "Est. duration:"} {proposal.estimated_duration}
                      </span>
                    )}
                    <span>
                      {ar ? "قُدِّم " : "Submitted "}
                      {new Date(proposal.submitted_at).toLocaleDateString(dateLocale, {
                        month: "short", day: "numeric",
                      })}
                    </span>
                  </div>
                </div>

                <div className="flex gap-2 shrink-0">
                  <Link href={`/jobs/${proposal.job.id}`} className="btn-secondary py-1.5 px-3 text-xs">
                    {ar ? "عرض الوظيفة" : "View Job"}
                  </Link>
                  {(proposal.status === "pending" || proposal.status === "shortlisted") && (
                    <button onClick={() => handleWithdraw(proposal.id)}
                      className="text-xs text-danger-500 hover:text-danger-700 px-2">
                      {ar ? "سحب" : "Withdraw"}
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
            className="btn-secondary py-2 px-4 text-sm disabled:opacity-40">
            {ar ? "السابق" : "Previous"}
          </button>
          <span className="text-sm text-gray-600 px-4">{page} / {totalPages}</span>
          <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}
            className="btn-secondary py-2 px-4 text-sm disabled:opacity-40">
            {ar ? "التالي" : "Next"}
          </button>
        </div>
      )}
    </div>
  );
}
