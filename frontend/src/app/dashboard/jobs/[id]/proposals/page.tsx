"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { jobsApi, proposalsApi } from "@/lib/api";
import { backendUrl } from "@/lib/utils";
import { toast } from "sonner";
import type { ProposalSummary } from "@/types/proposal";
import type { JobDetail } from "@/types/job";
import { PROPOSAL_STATUS_LABELS, PROPOSAL_STATUS_COLORS } from "@/types/proposal";

const STATUS_TABS = [
  { value: "", label: "All" },
  { value: "pending", label: "Pending" },
  { value: "shortlisted", label: "Shortlisted" },
  { value: "accepted", label: "Accepted" },
  { value: "rejected", label: "Rejected" },
];

const SORT_OPTIONS = [
  { value: "newest", label: "Newest First" },
  { value: "oldest", label: "Oldest First" },
  { value: "bid_low", label: "Bid: Low to High" },
  { value: "bid_high", label: "Bid: High to Low" },
];

export default function JobProposalsPage() {
  const params = useParams();
  const jobId = params.id as string;

  const [job, setJob] = useState<JobDetail | null>(null);
  const [proposals, setProposals] = useState<ProposalSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [sortBy, setSortBy] = useState("newest");
  const [page, setPage] = useState(1);

  // Response modal
  const [respondingTo, setRespondingTo] = useState<string | null>(null);
  const [responseAction, setResponseAction] = useState("");
  const [clientNote, setClientNote] = useState("");

  useEffect(() => {
    async function loadJob() {
      try {
        const response = await jobsApi.getById(jobId);
        setJob(response.data);
      } catch {
        setJob(null);
      }
    }
    if (jobId) loadJob();
  }, [jobId]);

  const fetchProposals = useCallback(async () => {
    setIsLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 15, sort_by: sortBy };
      if (statusFilter) params.status = statusFilter;
      const response = await proposalsApi.getJobProposals(jobId, params as any);
      setProposals(response.data.proposals);
      setTotal(response.data.total);
      setTotalPages(response.data.total_pages);
    } catch {
      setProposals([]);
    } finally {
      setIsLoading(false);
    }
  }, [jobId, statusFilter, sortBy, page]);

  useEffect(() => {
    fetchProposals();
  }, [fetchProposals]);

  const handleRespond = async () => {
    if (!respondingTo || !responseAction) return;
    try {
      const data: any = { status: responseAction };
      if (clientNote.trim()) data.client_note = clientNote.trim();
      await proposalsApi.respond(respondingTo, data);

      const label = responseAction === "shortlisted" ? "Shortlisted" : responseAction === "accepted" ? "Accepted" : "Rejected";
      toast.success(`Proposal ${label.toLowerCase()}`);
      setRespondingTo(null);
      setResponseAction("");
      setClientNote("");
      fetchProposals();

      // Refresh job if accepted
      if (responseAction === "accepted") {
        const jobRes = await jobsApi.getById(jobId);
        setJob(jobRes.data);
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to respond");
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link href={`/jobs/${jobId}`} className="text-sm text-brand-500 hover:text-brand-600 mb-2 inline-block">
          ← Back to job
        </Link>
        <h1 className="text-2xl font-bold text-gray-900">
          Proposals {job ? `for "${job.title}"` : ""}
        </h1>
        <p className="mt-1 text-gray-600">
          {total > 0 ? `${total} proposals received` : "No proposals yet"}
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between">
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
        <select
          value={sortBy}
          onChange={(e) => { setSortBy(e.target.value); setPage(1); }}
          className="input-field w-44"
        >
          {SORT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      {/* Proposals */}
      {isLoading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : proposals.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-lg font-medium text-gray-900">No proposals yet</p>
          <p className="mt-2 text-gray-600">Proposals from freelancers will appear here.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {proposals.map((proposal) => (
            <ProposalCard
              key={proposal.id}
              proposal={proposal}
              onRespond={(id, action) => {
                setRespondingTo(id);
                setResponseAction(action);
                setClientNote("");
              }}
            />
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

      {/* Response Modal */}
      {respondingTo && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-lg font-semibold text-gray-900">
              {responseAction === "shortlisted" && "Shortlist this proposal?"}
              {responseAction === "accepted" && "Accept this proposal?"}
              {responseAction === "rejected" && "Reject this proposal?"}
            </h3>

            {responseAction === "accepted" && (
              <p className="text-sm text-amber-600 bg-amber-50 p-3 rounded-lg">
                Accepting will assign this freelancer to the job and auto-reject all other pending proposals.
              </p>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Note to freelancer (optional)
              </label>
              <textarea
                value={clientNote}
                onChange={(e) => setClientNote(e.target.value)}
                className="input-field min-h-[80px] resize-y"
                placeholder="Add a message..."
                maxLength={2000}
              />
            </div>

            <div className="flex gap-2 justify-end">
              <button
                onClick={() => { setRespondingTo(null); setResponseAction(""); }}
                className="btn-secondary py-2 px-4"
              >
                Cancel
              </button>
              <button
                onClick={handleRespond}
                className={`py-2 px-6 rounded-lg font-medium text-white ${
                  responseAction === "rejected"
                    ? "bg-red-500 hover:bg-red-600"
                    : "bg-brand-500 hover:bg-brand-600"
                }`}
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ProposalCard({
  proposal,
  onRespond,
}: {
  proposal: ProposalSummary;
  onRespond: (id: string, action: string) => void;
}) {
  const f = proposal.freelancer;
  const canRespond = proposal.status === "pending" || proposal.status === "shortlisted";

  return (
    <div className="card p-5">
      {/* Freelancer header */}
      <div className="flex items-start justify-between gap-4">
        <Link href={`/profile/${f.username}`} className="flex items-center gap-3 group">
          <div className="w-11 h-11 rounded-full overflow-hidden bg-brand-100 flex items-center justify-center shrink-0">
            {f.avatar_url ? (
              <img src={backendUrl(f.avatar_url)} alt={`${f.first_name} ${f.last_name}`} className="w-full h-full object-cover" />
            ) : (
              <span className="text-sm font-bold text-brand-500">
                {f.first_name[0]}{f.last_name[0]}
              </span>
            )}
          </div>
          <div>
            <p className="font-medium text-gray-900 group-hover:text-brand-600 transition-colors">
              {f.display_name || `${f.first_name} ${f.last_name}`}
            </p>
            <p className="text-sm text-gray-500">{f.title || "Freelancer"}</p>
          </div>
        </Link>

        <span className={`px-2.5 py-1 text-xs font-medium rounded-full border ${PROPOSAL_STATUS_COLORS[proposal.status]}`}>
          {PROPOSAL_STATUS_LABELS[proposal.status]}
        </span>
      </div>

      {/* Freelancer stats */}
      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-sm text-gray-500">
        {f.hourly_rate && <span>${f.hourly_rate}/hr</span>}
        {f.avg_rating > 0 && <span>⭐ {f.avg_rating.toFixed(1)} ({f.total_reviews})</span>}
        <span>{f.jobs_completed} jobs done</span>
        {f.country && <span>📍 {f.country}</span>}
        {f.experience_level && <span className="capitalize">{f.experience_level}</span>}
      </div>

      {/* Skills */}
      {f.skills && f.skills.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {f.skills.slice(0, 5).map((s) => (
            <span key={s} className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-600">{s}</span>
          ))}
          {f.skills.length > 5 && (
            <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-400">+{f.skills.length - 5}</span>
          )}
        </div>
      )}

      {/* Bid details */}
      <div className="mt-4 pt-3 border-t border-gray-100 flex flex-wrap items-center gap-x-6 gap-y-2">
        <div>
          <span className="text-sm text-gray-400">Bid:</span>{" "}
          <span className="text-lg font-semibold text-gray-900">${proposal.bid_amount.toLocaleString()}</span>
        </div>
        {proposal.estimated_duration && (
          <div>
            <span className="text-sm text-gray-400">Duration:</span>{" "}
            <span className="text-sm font-medium text-gray-700">{proposal.estimated_duration}</span>
          </div>
        )}
        <div className="text-sm text-gray-400">
          Submitted {new Date(proposal.submitted_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
        </div>
      </div>

      {/* Actions */}
      {canRespond && (
        <div className="mt-4 flex gap-2">
          {proposal.status === "pending" && (
            <button
              onClick={() => onRespond(proposal.id, "shortlisted")}
              className="btn-secondary py-1.5 px-4 text-sm"
            >
              Shortlist
            </button>
          )}
          <button
            onClick={() => onRespond(proposal.id, "accepted")}
            className="btn-primary py-1.5 px-4 text-sm"
          >
            Accept
          </button>
          <button
            onClick={() => onRespond(proposal.id, "rejected")}
            className="text-sm text-red-500 hover:text-red-700 px-3"
          >
            Reject
          </button>
        </div>
      )}
    </div>
  );
}
