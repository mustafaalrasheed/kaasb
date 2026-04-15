"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { jobsApi, proposalsApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { backendUrl, getApiError, getApiStatus } from "@/lib/utils";
import { useLocale } from "@/providers/locale-provider";
import { toast } from "sonner";
import type { JobDetail } from "@/types/job";
import { DURATION_LABELS, EXPERIENCE_LABELS } from "@/types/job";
import { Breadcrumbs } from "@/components/seo/breadcrumbs";
import { JobPostingJsonLd } from "@/components/seo/json-ld";
import { canonicalUrl } from "@/lib/seo";

const JOB_STATUS_AR: Record<string, string> = {
  open: "مفتوح",
  in_progress: "جارٍ",
  completed: "مكتمل",
  closed: "مغلق",
  cancelled: "ملغى",
  draft: "مسودة",
};

const JOB_STATUS_EN: Record<string, string> = {
  open: "Open",
  in_progress: "In Progress",
  completed: "Completed",
  closed: "Closed",
  cancelled: "Cancelled",
  draft: "Draft",
};

const JOB_TYPE_AR: Record<string, string> = {
  fixed: "سعر ثابت",
  hourly: "بالساعة",
};

const JOB_TYPE_EN: Record<string, string> = {
  fixed: "Fixed Price",
  hourly: "Hourly",
};

const EXPERIENCE_LABELS_AR: Record<string, string> = {
  entry: "مبتدئ",
  intermediate: "متوسط",
  expert: "خبير",
};

const DURATION_LABELS_AR: Record<string, string> = {
  "less_than_1_week": "أقل من أسبوع",
  "1_to_4_weeks": "١-٤ أسابيع",
  "1_to_3_months": "١-٣ أشهر",
  "3_to_6_months": "٣-٦ أشهر",
  "more_than_6_months": "أكثر من ٦ أشهر",
};

function formatBudget(job: JobDetail, ar: boolean): string {
  const numLocale = ar ? "ar-IQ" : "en-US";
  const currency = ar ? "د.ع" : "IQD";
  const perHour = ar ? "د.ع/س" : "IQD/hr";
  if (job.job_type === "fixed" && job.fixed_price) {
    return `${job.fixed_price.toLocaleString(numLocale)} ${currency}`;
  }
  if (job.budget_min && job.budget_max) {
    return `${job.budget_min.toLocaleString(numLocale)} - ${job.budget_max.toLocaleString(numLocale)} ${perHour}`;
  }
  if (job.budget_min) return `${ar ? "من " : "From "}${job.budget_min.toLocaleString(numLocale)} ${perHour}`;
  return ar ? "الميزانية غير محددة" : "Budget not specified";
}

export default function JobDetailClient() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.id as string;
  const { user } = useAuthStore();
  const { locale } = useLocale();
  const ar = locale === "ar";

  const [job, setJob] = useState<JobDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const [showProposalForm, setShowProposalForm] = useState(false);
  const [coverLetter, setCoverLetter] = useState("");
  const [bidAmount, setBidAmount] = useState("");
  const [estimatedDuration, setEstimatedDuration] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    async function loadJob() {
      try {
        const response = await jobsApi.getById(jobId);
        const payload = response.data as unknown as JobDetail & { data?: JobDetail };
        setJob(payload.data ?? payload);
      } catch (err: unknown) {
        setError(
          getApiStatus(err) === 404
            ? ar ? "الوظيفة غير موجودة" : "Job not found"
            : ar ? "تعذّر تحميل الوظيفة" : "Failed to load job"
        );
      } finally {
        setIsLoading(false);
      }
    }
    if (jobId) loadJob();
  }, [jobId]); // eslint-disable-line react-hooks/exhaustive-deps

  const isOwner = user?.id === job?.client?.id;
  const isFreelancer = user?.primary_role === "freelancer";

  const handleClose = async () => {
    if (!job || !confirm(ar ? "هل أنت متأكد من إغلاق هذه الوظيفة؟" : "Are you sure you want to close this job?")) return;
    try {
      await jobsApi.close(job.id);
      toast.success(ar ? "تم إغلاق الوظيفة" : "Job closed");
      router.push("/dashboard");
    } catch (err: unknown) {
      toast.error(getApiError(err, ar ? "تعذّر إغلاق الوظيفة" : "Failed to close job"));
    }
  };

  const handleDelete = async () => {
    if (!job || !confirm(ar
      ? "هل أنت متأكد من حذف هذه الوظيفة؟ لا يمكن التراجع عن هذا الإجراء."
      : "Are you sure you want to delete this job? This cannot be undone."
    )) return;
    try {
      await jobsApi.delete(job.id);
      toast.success(ar ? "تم حذف الوظيفة" : "Job deleted");
      router.push("/dashboard");
    } catch (err: unknown) {
      toast.error(getApiError(err, ar ? "تعذّر حذف الوظيفة" : "Failed to delete job"));
    }
  };

  const handleSubmitProposal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!job) return;
    setIsSubmitting(true);
    try {
      const data: { cover_letter: string; bid_amount: number; estimated_duration?: string } = {
        cover_letter: coverLetter,
        bid_amount: parseFloat(bidAmount),
      };
      if (estimatedDuration.trim()) data.estimated_duration = estimatedDuration.trim();

      await proposalsApi.submit(job.id, data);
      toast.success(ar ? "تم تقديم عرضك بنجاح!" : "Proposal submitted successfully!");
      setShowProposalForm(false);
      setCoverLetter("");
      setBidAmount("");
      setEstimatedDuration("");
      const response = await jobsApi.getById(jobId);
      const payload = response.data as unknown as JobDetail & { data?: JobDetail };
      setJob(payload.data ?? payload);
    } catch (err: unknown) {
      toast.error(getApiError(err, ar ? "تعذّر تقديم العرض" : "Failed to submit proposal"));
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <p className="text-gray-500">{ar ? "جاري تحميل الوظيفة..." : "Loading job..."}</p>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-center">
          <p className="text-xl font-semibold text-gray-900">{error}</p>
          <Link href="/jobs" className="mt-4 inline-block text-brand-500 hover:text-brand-600">
            {ar ? "تصفح الوظائف" : "Browse Jobs"}
          </Link>
        </div>
      </div>
    );
  }

  const clientName = job.client.display_name || `${job.client.first_name} ${job.client.last_name}`;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <JobPostingJsonLd
        title={job.title}
        description={job.description}
        publishedAt={job.published_at || job.created_at}
        category={job.category}
        jobType={job.job_type}
        budgetMin={job.budget_min}
        budgetMax={job.budget_max}
        fixedPrice={job.fixed_price}
        experienceLevel={job.experience_level}
        skills={job.skills_required}
        deadline={job.deadline}
        clientName={clientName}
        jobUrl={canonicalUrl(`/jobs/${job.id}`)}
      />

      <Breadcrumbs
        items={[
          { name: ar ? "الوظائف" : "Jobs", href: "/jobs" },
          { name: job.title, href: `/jobs/${job.id}` },
        ]}
        className="mb-4"
      />

      <div className="flex flex-col lg:flex-row gap-8">
        {/* Main Content */}
        <div className="flex-1 min-w-0 space-y-6">
          {/* Header */}
          <div className="card p-6">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2 flex-wrap">
                  <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-brand-50 text-brand-700 border border-brand-200">
                    {job.category}
                  </span>
                  <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${
                    job.status === "open"
                      ? "bg-success-50 text-success-700 border border-green-200"
                      : "bg-gray-100 text-gray-600 border border-gray-200"
                  }`}>
                    {ar ? (JOB_STATUS_AR[job.status] ?? job.status) : (JOB_STATUS_EN[job.status] ?? job.status)}
                  </span>
                </div>
                <h1 className="text-2xl font-bold text-gray-900">{job.title}</h1>
              </div>

              {isOwner && job.status === "open" && (
                <div className="flex gap-2 shrink-0 flex-wrap">
                  <Link href={`/dashboard/jobs/${job.id}/proposals`} className="btn-primary py-2 px-4 text-sm">
                    {ar ? `العروض (${job.proposal_count})` : `Proposals (${job.proposal_count})`}
                  </Link>
                  <button onClick={handleClose} className="btn-secondary py-2 px-4 text-sm">
                    {ar ? "إغلاق" : "Close"}
                  </button>
                  {job.proposal_count === 0 && (
                    <button onClick={handleDelete} className="btn-danger py-2 px-4 text-sm">
                      {ar ? "حذف" : "Delete"}
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Meta row */}
            <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-sm text-gray-600">
              <div>
                <span className="text-gray-400">{ar ? "الميزانية:" : "Budget:"}</span>{" "}
                <span className="font-semibold text-gray-900">{formatBudget(job, ar)}</span>
              </div>
              <div>
                <span className="text-gray-400">{ar ? "النوع:" : "Type:"}</span>{" "}
                <span>{ar ? (JOB_TYPE_AR[job.job_type] ?? job.job_type) : (JOB_TYPE_EN[job.job_type] ?? job.job_type)}</span>
              </div>
              {job.experience_level && (
                <div>
                  <span className="text-gray-400">{ar ? "المستوى:" : "Level:"}</span>{" "}
                  {ar ? (EXPERIENCE_LABELS_AR[job.experience_level] || job.experience_level) : (EXPERIENCE_LABELS[job.experience_level] || job.experience_level)}
                </div>
              )}
              {job.duration && (
                <div>
                  <span className="text-gray-400">{ar ? "المدة:" : "Duration:"}</span>{" "}
                  {ar ? (DURATION_LABELS_AR[job.duration] || job.duration) : (DURATION_LABELS[job.duration] || job.duration)}
                </div>
              )}
              <div>
                <span className="text-gray-400">{ar ? "نُشر:" : "Posted:"}</span>{" "}
                <time dateTime={job.published_at || job.created_at}>
                  {new Date(job.published_at || job.created_at).toLocaleDateString(ar ? "ar-IQ" : "en-US", {
                    month: "short", day: "numeric", year: "numeric",
                  })}
                </time>
              </div>
            </div>
          </div>

          {/* Description */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-3">
              {ar ? "تفاصيل الوظيفة" : "Job Details"}
            </h2>
            <div className="text-gray-700 whitespace-pre-line leading-relaxed">{job.description}</div>
          </div>

          {/* Skills */}
          {job.skills_required && job.skills_required.length > 0 && (
            <div className="card p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-3">
                {ar ? "المهارات المطلوبة" : "Required Skills"}
              </h2>
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
            <h2 className="text-lg font-semibold text-gray-900 mb-3">
              {ar ? "النشاط" : "Activity"}
            </h2>
            <div className="flex gap-8 text-sm">
              <div>
                <span className="text-2xl font-bold text-gray-900">{job.proposal_count}</span>
                <p className="text-gray-500">{ar ? "عرض" : "proposals"}</p>
              </div>
              <div>
                <span className="text-2xl font-bold text-gray-900">{job.view_count}</span>
                <p className="text-gray-500">{ar ? "مشاهدة" : "views"}</p>
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
                  {ar ? "تقديم عرض" : "Submit Proposal"}
                </button>
              ) : (
                <form onSubmit={handleSubmitProposal} className="space-y-4">
                  <h3 className="font-semibold text-gray-900">
                    {ar ? "عرضك" : "Your Proposal"}
                  </h3>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {ar ? "مبلغ العرض (د.ع) *" : "Bid Amount (IQD) *"}
                    </label>
                    <input
                      type="number"
                      value={bidAmount}
                      onChange={(e) => setBidAmount(e.target.value)}
                      className="input-field"
                      placeholder={ar
                        ? (job.job_type === "fixed" ? "إجمالي السعر" : "سعر الساعة")
                        : (job.job_type === "fixed" ? "Total price" : "Hourly rate")}
                      min={5}
                      step={0.5}
                      dir="ltr"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {ar ? "المدة المتوقعة" : "Estimated Duration"}
                    </label>
                    <input
                      type="text"
                      value={estimatedDuration}
                      onChange={(e) => setEstimatedDuration(e.target.value)}
                      className="input-field"
                      placeholder={ar ? "مثال: أسبوعان، شهر واحد" : "e.g. 2 weeks, 1 month"}
                      maxLength={50}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {ar ? "خطاب التقديم *" : "Cover Letter *"}
                    </label>
                    <textarea
                      value={coverLetter}
                      onChange={(e) => setCoverLetter(e.target.value)}
                      className="input-field min-h-[150px] resize-y"
                      placeholder={ar
                        ? "اشرح لماذا أنت مناسب لهذه الوظيفة..."
                        : "Explain why you are a great fit for this job..."}
                      minLength={50}
                      maxLength={5000}
                      rows={6}
                      required
                    />
                    <p className="mt-1 text-xs text-gray-500 text-left">
                      {coverLetter.length}/5,000
                    </p>
                  </div>

                  <div className="flex gap-2">
                    <button type="submit" disabled={isSubmitting} className="btn-primary flex-1 py-2.5">
                      {isSubmitting
                        ? (ar ? "جاري الإرسال..." : "Submitting...")
                        : (ar ? "إرسال العرض" : "Submit Proposal")}
                    </button>
                    <button
                      type="button"
                      onClick={() => setShowProposalForm(false)}
                      className="btn-secondary py-2.5 px-4"
                    >
                      {ar ? "إلغاء" : "Cancel"}
                    </button>
                  </div>
                </form>
              )}
            </div>
          )}

          {/* Client info */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-gray-500 mb-3">
              {ar ? "عن العميل" : "About the Client"}
            </h3>
            <Link href={`/profile/${job.client.username}`} className="flex items-center gap-3 group">
              <div className="w-12 h-12 rounded-full overflow-hidden bg-brand-100 flex items-center justify-center shrink-0">
                {job.client.avatar_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={backendUrl(job.client.avatar_url)} alt={clientName} className="w-full h-full object-cover" />
                ) : (
                  <span className="text-lg font-bold text-brand-500">
                    {job.client.first_name[0]}{job.client.last_name[0]}
                  </span>
                )}
              </div>
              <div>
                <p className="font-medium text-gray-900 group-hover:text-brand-600 transition-colors">
                  {clientName}
                </p>
                {job.client.country && <p className="text-sm text-gray-500">📍 {job.client.country}</p>}
              </div>
            </Link>

            <div className="mt-4 pt-4 border-t border-gray-100 space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">{ar ? "إجمالي الإنفاق" : "Total Spent"}</span>
                <span className="font-medium text-gray-900">{job.client.total_spent.toLocaleString(ar ? "ar-IQ" : "en-US")} {ar ? "د.ع" : "IQD"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">{ar ? "التقييم" : "Rating"}</span>
                <span className="font-medium text-gray-900">
                  {job.client.avg_rating > 0
                    ? `⭐ ${job.client.avg_rating.toFixed(1)} (${job.client.total_reviews})`
                    : (ar ? "عميل جديد" : "New client")}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">{ar ? "عضو منذ" : "Member since"}</span>
                <span className="font-medium text-gray-900">
                  {new Date(job.client.created_at).toLocaleDateString(ar ? "ar-IQ" : "en-US", { month: "short", year: "numeric" })}
                </span>
              </div>
            </div>
          </div>

          {/* Deadline */}
          {job.deadline && (
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-gray-500 mb-2">
                {ar ? "الموعد النهائي" : "Deadline"}
              </h3>
              <p className="font-medium text-gray-900">
                <time dateTime={job.deadline}>
                  {new Date(job.deadline).toLocaleDateString(ar ? "ar-IQ" : "en-US", { month: "long", day: "numeric", year: "numeric" })}
                </time>
              </p>
            </div>
          )}

          {/* Share buttons */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-gray-500 mb-3">
              {ar ? "شارك هذه الوظيفة" : "Share this Job"}
            </h3>
            <div className="flex gap-2">
              <a
                href={`https://wa.me/?text=${encodeURIComponent(ar
                  ? `${job.title} - قدّم عرضك على كاسب: ${canonicalUrl(`/jobs/${job.id}`)}`
                  : `${job.title} - Submit your proposal on Kaasb: ${canonicalUrl(`/jobs/${job.id}`)}`
                )}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 py-2 px-3 text-sm text-center rounded-lg bg-green-500 text-white hover:bg-green-600 transition-colors"
              >
                {ar ? "واتساب" : "WhatsApp"}
              </a>
              <a
                href={`https://t.me/share/url?url=${encodeURIComponent(canonicalUrl(`/jobs/${job.id}`))}&text=${encodeURIComponent(job.title)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 py-2 px-3 text-sm text-center rounded-lg bg-blue-500 text-white hover:bg-blue-600 transition-colors"
              >
                {ar ? "تيليغرام" : "Telegram"}
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
