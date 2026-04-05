"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { jobsApi, proposalsApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { backendUrl, getApiError, getApiStatus } from "@/lib/utils";
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

const JOB_TYPE_AR: Record<string, string> = {
  fixed: "سعر ثابت",
  hourly: "بالساعة",
};

function formatBudget(job: JobDetail): string {
  if (job.job_type === "fixed" && job.fixed_price) {
    return `$${job.fixed_price.toLocaleString()}`;
  }
  if (job.budget_min && job.budget_max) {
    return `$${job.budget_min} - $${job.budget_max}/س`;
  }
  if (job.budget_min) return `من $${job.budget_min}/س`;
  return "الميزانية غير محددة";
}

export default function JobDetailClient() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.id as string;
  const { user } = useAuthStore();

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
        setJob(response.data.data);
      } catch (err: unknown) {
        setError(getApiStatus(err) === 404 ? "الوظيفة غير موجودة" : "تعذّر تحميل الوظيفة");
      } finally {
        setIsLoading(false);
      }
    }
    if (jobId) loadJob();
  }, [jobId]);

  const isOwner = user?.id === job?.client?.id;
  const isFreelancer = user?.primary_role === "freelancer";

  const handleClose = async () => {
    if (!job || !confirm("هل أنت متأكد من إغلاق هذه الوظيفة؟")) return;
    try {
      await jobsApi.close(job.id);
      toast.success("تم إغلاق الوظيفة");
      router.push("/dashboard");
    } catch (err: unknown) {
      toast.error(getApiError(err, "تعذّر إغلاق الوظيفة"));
    }
  };

  const handleDelete = async () => {
    if (!job || !confirm("هل أنت متأكد من حذف هذه الوظيفة؟ لا يمكن التراجع عن هذا الإجراء."))
      return;
    try {
      await jobsApi.delete(job.id);
      toast.success("تم حذف الوظيفة");
      router.push("/dashboard");
    } catch (err: unknown) {
      toast.error(getApiError(err, "تعذّر حذف الوظيفة"));
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
      toast.success("تم تقديم عرضك بنجاح!");
      setShowProposalForm(false);
      setCoverLetter("");
      setBidAmount("");
      setEstimatedDuration("");
      const response = await jobsApi.getById(jobId);
      setJob(response.data.data);
    } catch (err: unknown) {
      toast.error(getApiError(err, "تعذّر تقديم العرض"));
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <p className="text-gray-500">جاري تحميل الوظيفة...</p>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-center" dir="rtl">
          <p className="text-xl font-semibold text-gray-900">{error}</p>
          <Link href="/jobs" className="mt-4 inline-block text-brand-500 hover:text-brand-600">
            تصفح الوظائف
          </Link>
        </div>
      </div>
    );
  }

  const clientName = job.client.display_name || `${job.client.first_name} ${job.client.last_name}`;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8" dir="rtl">
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
          { name: "الوظائف", href: "/jobs" },
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
                    {JOB_STATUS_AR[job.status] ?? job.status}
                  </span>
                </div>
                <h1 className="text-2xl font-bold text-gray-900">{job.title}</h1>
              </div>

              {isOwner && job.status === "open" && (
                <div className="flex gap-2 shrink-0 flex-wrap">
                  <Link href={`/dashboard/jobs/${job.id}/proposals`} className="btn-primary py-2 px-4 text-sm">
                    العروض ({job.proposal_count})
                  </Link>
                  <button onClick={handleClose} className="btn-secondary py-2 px-4 text-sm">
                    إغلاق
                  </button>
                  {job.proposal_count === 0 && (
                    <button onClick={handleDelete} className="btn-danger py-2 px-4 text-sm">
                      حذف
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Meta row */}
            <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-sm text-gray-600">
              <div>
                <span className="text-gray-400">الميزانية:</span>{" "}
                <span className="font-semibold text-gray-900">{formatBudget(job)}</span>
              </div>
              <div>
                <span className="text-gray-400">النوع:</span>{" "}
                <span>{JOB_TYPE_AR[job.job_type] ?? job.job_type}</span>
              </div>
              {job.experience_level && (
                <div>
                  <span className="text-gray-400">المستوى:</span>{" "}
                  {EXPERIENCE_LABELS[job.experience_level]}
                </div>
              )}
              {job.duration && (
                <div>
                  <span className="text-gray-400">المدة:</span>{" "}
                  {DURATION_LABELS[job.duration]}
                </div>
              )}
              <div>
                <span className="text-gray-400">نُشر:</span>{" "}
                <time dateTime={job.published_at || job.created_at}>
                  {new Date(job.published_at || job.created_at).toLocaleDateString("ar-IQ", {
                    month: "short", day: "numeric", year: "numeric",
                  })}
                </time>
              </div>
            </div>
          </div>

          {/* Description */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-3">تفاصيل الوظيفة</h2>
            <div className="text-gray-700 whitespace-pre-line leading-relaxed">{job.description}</div>
          </div>

          {/* Skills */}
          {job.skills_required && job.skills_required.length > 0 && (
            <div className="card p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-3">المهارات المطلوبة</h2>
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
            <h2 className="text-lg font-semibold text-gray-900 mb-3">النشاط</h2>
            <div className="flex gap-8 text-sm">
              <div>
                <span className="text-2xl font-bold text-gray-900">{job.proposal_count}</span>
                <p className="text-gray-500">عرض</p>
              </div>
              <div>
                <span className="text-2xl font-bold text-gray-900">{job.view_count}</span>
                <p className="text-gray-500">مشاهدة</p>
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
                  تقديم عرض
                </button>
              ) : (
                <form onSubmit={handleSubmitProposal} className="space-y-4">
                  <h3 className="font-semibold text-gray-900">عرضك</h3>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      مبلغ العرض (USD) *
                    </label>
                    <input
                      type="number"
                      value={bidAmount}
                      onChange={(e) => setBidAmount(e.target.value)}
                      className="input-field"
                      placeholder={job.job_type === "fixed" ? "إجمالي السعر" : "سعر الساعة"}
                      min={5}
                      step={0.5}
                      dir="ltr"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      المدة المتوقعة
                    </label>
                    <input
                      type="text"
                      value={estimatedDuration}
                      onChange={(e) => setEstimatedDuration(e.target.value)}
                      className="input-field"
                      placeholder="مثال: أسبوعان، شهر واحد"
                      maxLength={50}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      خطاب التقديم *
                    </label>
                    <textarea
                      value={coverLetter}
                      onChange={(e) => setCoverLetter(e.target.value)}
                      className="input-field min-h-[150px] resize-y"
                      placeholder="اشرح لماذا أنت مناسب لهذه الوظيفة..."
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
                      {isSubmitting ? "جاري الإرسال..." : "إرسال العرض"}
                    </button>
                    <button
                      type="button"
                      onClick={() => setShowProposalForm(false)}
                      className="btn-secondary py-2.5 px-4"
                    >
                      إلغاء
                    </button>
                  </div>
                </form>
              )}
            </div>
          )}

          {/* Client info */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-gray-500 mb-3">عن العميل</h3>
            <Link href={`/profile/${job.client.username}`} className="flex items-center gap-3 group">
              <div className="w-12 h-12 rounded-full overflow-hidden bg-brand-100 flex items-center justify-center shrink-0">
                {job.client.avatar_url ? (
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
                <span className="text-gray-500">إجمالي الإنفاق</span>
                <span className="font-medium text-gray-900" dir="ltr">${job.client.total_spent.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">التقييم</span>
                <span className="font-medium text-gray-900">
                  {job.client.avg_rating > 0
                    ? `⭐ ${job.client.avg_rating.toFixed(1)} (${job.client.total_reviews})`
                    : "عميل جديد"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">عضو منذ</span>
                <span className="font-medium text-gray-900">
                  {new Date(job.client.created_at).toLocaleDateString("ar-IQ", { month: "short", year: "numeric" })}
                </span>
              </div>
            </div>
          </div>

          {/* Deadline */}
          {job.deadline && (
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-gray-500 mb-2">الموعد النهائي</h3>
              <p className="font-medium text-gray-900">
                <time dateTime={job.deadline}>
                  {new Date(job.deadline).toLocaleDateString("ar-IQ", { month: "long", day: "numeric", year: "numeric" })}
                </time>
              </p>
            </div>
          )}

          {/* Share buttons */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-gray-500 mb-3">شارك هذه الوظيفة</h3>
            <div className="flex gap-2">
              <a
                href={`https://wa.me/?text=${encodeURIComponent(`${job.title} - قدّم عرضك على كاسب: ${canonicalUrl(`/jobs/${job.id}`)}`)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 py-2 px-3 text-sm text-center rounded-lg bg-green-500 text-white hover:bg-green-600 transition-colors"
              >
                واتساب
              </a>
              <a
                href={`https://t.me/share/url?url=${encodeURIComponent(canonicalUrl(`/jobs/${job.id}`))}&text=${encodeURIComponent(job.title)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 py-2 px-3 text-sm text-center rounded-lg bg-blue-500 text-white hover:bg-blue-600 transition-colors"
              >
                تيليغرام
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
