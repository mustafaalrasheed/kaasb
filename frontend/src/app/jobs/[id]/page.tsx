"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { jobsApi, proposalsApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { toast } from "sonner";
import type { JobDetail } from "@/types/job";
import { DURATION_LABELS, EXPERIENCE_LABELS } from "@/types/job";

function formatBudget(job: JobDetail): string {
  if (job.job_type === "fixed" && job.fixed_price) {
    return `$${job.fixed_price.toLocaleString()}`;
  }
  if (job.budget_min && job.budget_max) {
    return `$${job.budget_min} - $${job.budget_max}/hr`;
  }
  if (job.budget_min) return `From $${job.budget_min}/hr`;
  return "Budget not set";
}

export default function JobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.id as string;
  const { user } = useAuthStore();

  const [job, setJob] = useState<JobDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  // Proposal form state
  const [showProposalForm, setShowProposalForm] = useState(false);
  const [coverLetter, setCoverLetter] = useState("");
  const [bidAmount, setBidAmount] = useState("");
  const [estimatedDuration, setEstimatedDuration] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    async function loadJob() {
      try {
        const response = await jobsApi.getById(jobId);
        setJob(response.data);
      } catch (err: any) {
        setError(
          err.response?.status === 404
            ? "Job not found"
            : "Failed to load job"
        );
      } finally {
        setIsLoading(false);
      }
    }
    if (jobId) loadJob();
  }, [jobId]);

  const isOwner = user?.id === job?.client?.id;
  const isFreelancer = user?.primary_role === "freelancer";

  const handleClose = async () => {
    if (!job || !confirm("Are you sure you want to close this job?")) return;
    try {
      await jobsApi.close(job.id);
      toast.success("Job closed");
      router.push("/dashboard");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to close job");
    }
  };

  const handleDelete = async () => {
    if (!job || !confirm("Are you sure you want to delete this job? This cannot be undone."))
      return;
    try {
      await jobsApi.delete(job.id);
      toast.success("Job deleted");
      router.push("/dashboard");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to delete job");
    }
  };

  const handleSubmitProposal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!job) return;
    setIsSubmitting(true);
    try {
      const data: any = {
        cover_letter: coverLetter,
        bid_amount: parseFloat(bidAmount),
      };
      if (estimatedDuration.trim()) data.estimated_duration = estimatedDuration.trim();

      await proposalsApi.submit(job.id, data);
      toast.success("Proposal submitted!");
      setShowProposalForm(false);
      setCoverLetter("");
      setBidAmount("");
      setEstimatedDuration("");
      // Refresh job to update proposal count
      const response = await jobsApi.getById(jobId);
      setJob(response.data);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        toast.error(detail.map((d: any) => d.msg).join(", "));
      } else {
        toast.error(detail || "Failed to submit proposal");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <p className="text-gray-500">Loading job...</p>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-center">
          <p className="text-xl font-semibold text-gray-900">{error}</p>
          <Link href="/jobs" className="mt-4 inline-block text-brand-500 hover:text-brand-600">
            Browse jobs
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex flex-col lg:flex-row gap-8">
        {/* Main Content */}
        <div className="flex-1 min-w-0 space-y-6">
          {/* Header */}
          <div className="card p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-brand-50 text-brand-700 border border-brand-200">
                    {job.category}
                  </span>
                  <span
                    className={`px-2.5 py-1 text-xs font-medium rounded-full ${
                      job.status === "open"
                        ? "bg-success-50 text-success-700 border border-green-200"
                        : "bg-gray-100 text-gray-600 border border-gray-200"
                    }`}
                  >
                    {job.status.charAt(0).toUpperCase() + job.status.slice(1).replace("_", " ")}
                  </span>
                </div>
                <h1 className="text-2xl font-bold text-gray-900">
                  {job.title}
                </h1>
              </div>

              {isOwner && job.status === "open" && (
                <div className="flex gap-2 shrink-0">
                  <Link href={`/dashboard/jobs/${job.id}/proposals`} className="btn-primary py-2 px-4 text-sm">
                    View Proposals ({job.proposal_count})
                  </Link>
                  <button onClick={handleClose} className="btn-secondary py-2 px-4 text-sm">
                    Close
                  </button>
                  {job.proposal_count === 0 && (
                    <button onClick={handleDelete} className="btn-danger py-2 px-4 text-sm">
                      Delete
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Meta row */}
            <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-sm text-gray-600">
              <div>
                <span className="text-gray-400">Budget:</span>{" "}
                <span className="font-semibold text-gray-900">{formatBudget(job)}</span>
              </div>
              <div>
                <span className="text-gray-400">Type:</span>{" "}
                <span className="capitalize">{job.job_type} price</span>
              </div>
              {job.experience_level && (
                <div>
                  <span className="text-gray-400">Level:</span>{" "}
                  {EXPERIENCE_LABELS[job.experience_level]}
                </div>
              )}
              {job.duration && (
                <div>
                  <span className="text-gray-400">Duration:</span>{" "}
                  {DURATION_LABELS[job.duration]}
                </div>
              )}
              <div>
                <span className="text-gray-400">Posted:</span>{" "}
                {new Date(job.published_at || job.created_at).toLocaleDateString("en-US", {
                  month: "short", day: "numeric", year: "numeric",
                })}
              </div>
            </div>
          </div>

          {/* Description */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-3">Job Description</h2>
            <div className="text-gray-700 whitespace-pre-line leading-relaxed">
              {job.description}
            </div>
          </div>

          {/* Skills */}
          {job.skills_required && job.skills_required.length > 0 && (
            <div className="card p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-3">Skills Required</h2>
              <div className="flex flex-wrap gap-2">
                {job.skills_required.map((skill) => (
                  <span key={skill} className="px-3 py-1.5 rounded-full text-sm font-medium bg-gray-100 text-gray-700 border border-gray-200">
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Activity */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-3">Activity</h2>
            <div className="flex gap-8 text-sm">
              <div>
                <span className="text-2xl font-bold text-gray-900">{job.proposal_count}</span>
                <p className="text-gray-500">Proposals</p>
              </div>
              <div>
                <span className="text-2xl font-bold text-gray-900">{job.view_count}</span>
                <p className="text-gray-500">Views</p>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="w-full lg:w-80 shrink-0 space-y-6">
          {/* Submit Proposal (freelancers) */}
          {isFreelancer && job.status === "open" && !isOwner && (
            <div className="card p-5">
              {!showProposalForm ? (
                <button
                  onClick={() => setShowProposalForm(true)}
                  className="btn-primary w-full py-3 text-lg"
                >
                  Submit Proposal
                </button>
              ) : (
                <form onSubmit={handleSubmitProposal} className="space-y-4">
                  <h3 className="font-semibold text-gray-900">Your Proposal</h3>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Bid Amount (USD) *
                    </label>
                    <input
                      type="number"
                      value={bidAmount}
                      onChange={(e) => setBidAmount(e.target.value)}
                      className="input-field"
                      placeholder={job.job_type === "fixed" ? "Your total price" : "Your hourly rate"}
                      min={5}
                      step={0.5}
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Estimated Duration
                    </label>
                    <input
                      type="text"
                      value={estimatedDuration}
                      onChange={(e) => setEstimatedDuration(e.target.value)}
                      className="input-field"
                      placeholder="e.g., 2 weeks, 1 month"
                      maxLength={50}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Cover Letter *
                    </label>
                    <textarea
                      value={coverLetter}
                      onChange={(e) => setCoverLetter(e.target.value)}
                      className="input-field min-h-[150px] resize-y"
                      placeholder="Explain why you're the right fit for this job..."
                      minLength={50}
                      maxLength={5000}
                      rows={6}
                      required
                    />
                    <p className="mt-1 text-xs text-gray-500 text-right">
                      {coverLetter.length}/5,000
                    </p>
                  </div>

                  <div className="flex gap-2">
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="btn-primary flex-1 py-2.5"
                    >
                      {isSubmitting ? "Submitting..." : "Submit"}
                    </button>
                    <button
                      type="button"
                      onClick={() => setShowProposalForm(false)}
                      className="btn-secondary py-2.5 px-4"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              )}
            </div>
          )}

          {/* Client info */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
              About the Client
            </h3>
            <Link href={`/profile/${job.client.username}`} className="flex items-center gap-3 group">
              <div className="w-12 h-12 rounded-full overflow-hidden bg-brand-100 flex items-center justify-center shrink-0">
                {job.client.avatar_url ? (
                  <img src={`http://localhost:8000${job.client.avatar_url}`} alt="" className="w-full h-full object-cover" />
                ) : (
                  <span className="text-lg font-bold text-brand-500">
                    {job.client.first_name[0]}{job.client.last_name[0]}
                  </span>
                )}
              </div>
              <div>
                <p className="font-medium text-gray-900 group-hover:text-brand-600 transition-colors">
                  {job.client.display_name || `${job.client.first_name} ${job.client.last_name}`}
                </p>
                {job.client.country && <p className="text-sm text-gray-500">📍 {job.client.country}</p>}
              </div>
            </Link>

            <div className="mt-4 pt-4 border-t border-gray-100 space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Total spent</span>
                <span className="font-medium text-gray-900">${job.client.total_spent.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Rating</span>
                <span className="font-medium text-gray-900">
                  {job.client.avg_rating > 0
                    ? `⭐ ${job.client.avg_rating.toFixed(1)} (${job.client.total_reviews})`
                    : "New client"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Member since</span>
                <span className="font-medium text-gray-900">
                  {new Date(job.client.created_at).toLocaleDateString("en-US", { month: "short", year: "numeric" })}
                </span>
              </div>
            </div>
          </div>

          {/* Deadline */}
          {job.deadline && (
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">Deadline</h3>
              <p className="font-medium text-gray-900">
                {new Date(job.deadline).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
