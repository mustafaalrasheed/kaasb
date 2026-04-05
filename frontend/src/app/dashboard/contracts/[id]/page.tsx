"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { contractsApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { toast } from "sonner";
import type { ContractDetail, MilestoneDetail } from "@/types/contract";
import {
  CONTRACT_STATUS_LABELS,
  CONTRACT_STATUS_COLORS,
  MILESTONE_STATUS_LABELS,
  MILESTONE_STATUS_COLORS,
} from "@/types/contract";

export default function ContractDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const { user } = useAuthStore();
  const [contract, setContract] = useState<ContractDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [showAddMilestone, setShowAddMilestone] = useState(false);

  const userRole =
    user?.id === contract?.client.id ? "client" : "freelancer";

  const fetchContract = useCallback(async () => {
    try {
      const res = await contractsApi.getById(id as string);
      setContract(res.data);
    } catch {
      toast.error("تعذّر تحميل العقد");
      router.push("/dashboard/contracts");
    } finally {
      setLoading(false);
    }
  }, [id, router]);

  useEffect(() => {
    fetchContract();
  }, [fetchContract]);

  if (loading) {
    return (
      <div className="text-center py-12 text-gray-500">جاري التحميل...</div>
    );
  }

  if (!contract) return null;

  const progress =
    contract.milestones.length > 0
      ? Math.round(
          (contract.milestones.filter((m) => m.status === "paid").length /
            contract.milestones.length) *
            100
        )
      : 0;

  return (
    <div className="space-y-6" dir="rtl">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link
            href="/dashboard/contracts"
            className="text-sm text-brand-600 hover:text-brand-700 mb-2 inline-block"
          >
            → العودة إلى العقود
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">{contract.title}</h1>
          <div className="flex items-center gap-3 mt-2 flex-wrap">
            <span
              className={`text-xs px-2.5 py-0.5 rounded-full border ${
                CONTRACT_STATUS_COLORS[contract.status] || "bg-gray-100"
              }`}
            >
              {CONTRACT_STATUS_LABELS[contract.status] || contract.status}
            </span>
            <span className="text-sm text-gray-500">
              بدأ{" "}
              {new Date(contract.started_at).toLocaleDateString("ar-IQ", {
                year: "numeric",
                month: "short",
                day: "numeric",
              })}
            </span>
          </div>
        </div>
        <div className="text-left shrink-0">
          <p className="text-2xl font-bold text-gray-900">
            ${contract.total_amount.toLocaleString()}
          </p>
          <p className="text-sm text-gray-500">
            ${contract.amount_paid.toLocaleString()} مدفوع
          </p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="card p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">التقدم</span>
          <span className="text-sm text-gray-500">{progress}%</span>
        </div>
        <div className="bg-gray-100 rounded-full h-3">
          <div
            className="bg-brand-500 h-3 rounded-full transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Parties info */}
      <div className="grid md:grid-cols-2 gap-4">
        <div className="card p-4">
          <p className="text-xs text-gray-500 mb-2">العميل</p>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-brand-100 flex items-center justify-center text-sm font-bold text-brand-600 shrink-0">
              {contract.client.first_name[0]}
              {contract.client.last_name[0]}
            </div>
            <div>
              <p className="font-medium text-gray-900 text-sm">
                {contract.client.display_name ||
                  `${contract.client.first_name} ${contract.client.last_name}`}
              </p>
              <p className="text-xs text-gray-500">@{contract.client.username}</p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <p className="text-xs text-gray-500 mb-2">المستقل</p>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-green-100 flex items-center justify-center text-sm font-bold text-green-600 shrink-0">
              {contract.freelancer.first_name[0]}
              {contract.freelancer.last_name[0]}
            </div>
            <div>
              <p className="font-medium text-gray-900 text-sm">
                {contract.freelancer.display_name ||
                  `${contract.freelancer.first_name} ${contract.freelancer.last_name}`}
              </p>
              <p className="text-xs text-gray-500">@{contract.freelancer.username}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Milestones section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">
            المراحل ({contract.milestones.length})
          </h2>
          {userRole === "client" && contract.status === "active" && (
            <button
              onClick={() => setShowAddMilestone(true)}
              className="btn-primary text-sm py-2 px-4"
            >
              + إضافة مرحلة
            </button>
          )}
        </div>

        {contract.milestones.length === 0 ? (
          <div className="card p-8 text-center">
            <p className="text-gray-500">لا توجد مراحل بعد</p>
            {userRole === "client" && (
              <p className="text-sm text-gray-400 mt-1">
                أضف مراحل لتقسيم المشروع إلى مراحل قابلة للتسليم
              </p>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {contract.milestones.map((milestone) => (
              <MilestoneCard
                key={milestone.id}
                milestone={milestone}
                userRole={userRole}
                contractStatus={contract.status}
                onUpdate={fetchContract}
              />
            ))}
          </div>
        )}
      </div>

      {/* Add Milestone Modal */}
      {showAddMilestone && (
        <AddMilestoneModal
          contractId={contract.id}
          onClose={() => setShowAddMilestone(false)}
          onAdded={fetchContract}
        />
      )}
    </div>
  );
}

// === Milestone Card ===

function MilestoneCard({
  milestone,
  userRole,
  contractStatus,
  onUpdate,
}: {
  milestone: MilestoneDetail;
  userRole: string;
  contractStatus: string;
  onUpdate: () => void;
}) {
  const [actionLoading, setActionLoading] = useState(false);
  const [showReview, setShowReview] = useState(false);
  const [showSubmit, setShowSubmit] = useState(false);

  const handleAction = async (
    action: string,
    data?: Record<string, unknown>
  ) => {
    setActionLoading(true);
    try {
      if (action === "start") {
        await contractsApi.startMilestone(milestone.id);
        toast.success("تم بدء المرحلة");
      } else if (action === "submit") {
        await contractsApi.submitMilestone(milestone.id, data || {});
        toast.success("تم تقديم المرحلة للمراجعة");
        setShowSubmit(false);
      } else if (action === "review") {
        await contractsApi.reviewMilestone(milestone.id, {
          action: (data?.action as string) ?? "approve",
          feedback: data?.feedback as string | undefined,
        });
        toast.success(
          data?.action === "approve"
            ? "تمت الموافقة على المرحلة والدفع"
            : "تم طلب المراجعة"
        );
        setShowReview(false);
      } else if (action === "delete") {
        await contractsApi.deleteMilestone(milestone.id);
        toast.success("تم حذف المرحلة");
      }
      onUpdate();
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response
              ?.data?.detail
          : undefined;
      toast.error(msg || "تعذّر تنفيذ الإجراء");
    } finally {
      setActionLoading(false);
    }
  };

  const isActive = contractStatus === "active";

  return (
    <div className="card p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="text-xs text-gray-400 font-mono">
              #{milestone.order + 1}
            </span>
            <h3 className="font-medium text-gray-900">{milestone.title}</h3>
            <span
              className={`text-xs px-2 py-0.5 rounded-full ${
                MILESTONE_STATUS_COLORS[milestone.status] || "bg-gray-100"
              }`}
            >
              {MILESTONE_STATUS_LABELS[milestone.status] || milestone.status}
            </span>
          </div>

          {milestone.description && (
            <p className="text-sm text-gray-500 mb-2">{milestone.description}</p>
          )}

          {milestone.due_date && (
            <p className="text-xs text-gray-400">
              الموعد النهائي:{" "}
              {new Date(milestone.due_date).toLocaleDateString("ar-IQ", {
                year: "numeric",
                month: "short",
                day: "numeric",
              })}
            </p>
          )}

          {milestone.submission_note && (
            <div className="mt-2 p-2 bg-purple-50 rounded text-sm text-purple-700">
              <span className="font-medium">ملاحظة التسليم: </span>
              {milestone.submission_note}
            </div>
          )}

          {milestone.feedback && (
            <div className="mt-2 p-2 bg-orange-50 rounded text-sm text-orange-700">
              <span className="font-medium">الملاحظات: </span>
              {milestone.feedback}
            </div>
          )}
        </div>

        <div className="text-left shrink-0">
          <p className="font-bold text-gray-900">
            ${milestone.amount.toLocaleString()}
          </p>

          {/* Actions */}
          {isActive && !actionLoading && (
            <div className="mt-2 flex flex-col gap-1">
              {/* Freelancer: start */}
              {userRole === "freelancer" && milestone.status === "pending" && (
                <button
                  onClick={() => handleAction("start")}
                  className="text-xs px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
                >
                  بدء
                </button>
              )}

              {/* Freelancer: submit */}
              {userRole === "freelancer" &&
                (milestone.status === "in_progress" ||
                  milestone.status === "revision_requested") && (
                  <button
                    onClick={() => setShowSubmit(true)}
                    className="text-xs px-3 py-1 bg-purple-500 text-white rounded hover:bg-purple-600"
                  >
                    تسليم
                  </button>
                )}

              {/* Client: review submitted milestone */}
              {userRole === "client" && milestone.status === "submitted" && (
                <button
                  onClick={() => setShowReview(true)}
                  className="text-xs px-3 py-1 bg-brand-500 text-white rounded hover:bg-brand-600"
                >
                  مراجعة
                </button>
              )}

              {/* Client: delete pending milestone */}
              {userRole === "client" && milestone.status === "pending" && (
                <button
                  onClick={() => {
                    if (confirm("هل تريد حذف هذه المرحلة؟"))
                      handleAction("delete");
                  }}
                  className="text-xs px-3 py-1 text-red-600 border border-red-200 rounded hover:bg-red-50"
                >
                  حذف
                </button>
              )}
            </div>
          )}

          {actionLoading && (
            <p className="text-xs text-gray-400 mt-2">جاري...</p>
          )}

          {milestone.status === "paid" && (
            <span className="text-xs text-green-600 font-medium">✓ مدفوع</span>
          )}
        </div>
      </div>

      {/* Submit modal */}
      {showSubmit && (
        <SubmitModal
          onClose={() => setShowSubmit(false)}
          onSubmit={(note) =>
            handleAction("submit", { submission_note: note || null })
          }
        />
      )}

      {/* Review modal */}
      {showReview && (
        <ReviewModal
          onClose={() => setShowReview(false)}
          onReview={(action, feedback) =>
            handleAction("review", { action, feedback: feedback || null })
          }
        />
      )}
    </div>
  );
}

// === Add Milestone Modal ===

function AddMilestoneModal({
  contractId,
  onClose,
  onAdded,
}: {
  contractId: string;
  onClose: () => void;
  onAdded: () => void;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!title.trim() || !amount) return;
    setSubmitting(true);
    try {
      await contractsApi.addMilestones(contractId, {
        milestones: [
          {
            title: title.trim(),
            description: description.trim() || undefined,
            amount: parseFloat(amount),
            due_date: dueDate || undefined,
          },
        ],
      });
      toast.success("تمت إضافة المرحلة");
      onAdded();
      onClose();
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response
              ?.data?.detail
          : undefined;
      toast.error(msg || "تعذّر إضافة المرحلة");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl p-6 w-full max-w-md" dir="rtl">
        <h3 className="text-lg font-semibold mb-4">إضافة مرحلة</h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              العنوان *
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="input-field"
              placeholder="مثال: تطوير واجهة برمجة التطبيقات"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              الوصف
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="input-field"
              rows={3}
              placeholder="ما تشمله هذه المرحلة..."
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                المبلغ ($) *
              </label>
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="input-field"
                min={1}
                step={0.01}
                dir="ltr"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                الموعد النهائي
              </label>
              <input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="input-field"
                dir="ltr"
              />
            </div>
          </div>
        </div>

        <div className="flex gap-3 mt-6">
          <button onClick={onClose} className="btn-secondary flex-1">
            إلغاء
          </button>
          <button
            onClick={handleSubmit}
            disabled={!title.trim() || !amount || submitting}
            className="btn-primary flex-1 disabled:opacity-50"
          >
            {submitting ? "جاري الإضافة..." : "إضافة المرحلة"}
          </button>
        </div>
      </div>
    </div>
  );
}

// === Submit Modal ===

function SubmitModal({
  onClose,
  onSubmit,
}: {
  onClose: () => void;
  onSubmit: (note: string) => void;
}) {
  const [note, setNote] = useState("");

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl p-6 w-full max-w-md" dir="rtl">
        <h3 className="text-lg font-semibold mb-4">تسليم المرحلة</h3>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          ملاحظة التسليم (اختياري)
        </label>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          className="input-field"
          rows={4}
          placeholder="صف ما أنجزته..."
        />
        <div className="flex gap-3 mt-4">
          <button onClick={onClose} className="btn-secondary flex-1">
            إلغاء
          </button>
          <button
            onClick={() => onSubmit(note)}
            className="btn-primary flex-1"
          >
            تقديم للمراجعة
          </button>
        </div>
      </div>
    </div>
  );
}

// === Review Modal ===

function ReviewModal({
  onClose,
  onReview,
}: {
  onClose: () => void;
  onReview: (action: string, feedback: string) => void;
}) {
  const [feedback, setFeedback] = useState("");

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl p-6 w-full max-w-md" dir="rtl">
        <h3 className="text-lg font-semibold mb-4">مراجعة المرحلة</h3>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          ملاحظات (اختياري)
        </label>
        <textarea
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          className="input-field"
          rows={3}
          placeholder="أضف ملاحظاتك..."
        />
        <div className="flex gap-3 mt-4">
          <button onClick={onClose} className="btn-secondary flex-1">
            إلغاء
          </button>
          <button
            onClick={() => onReview("request_revision", feedback)}
            className="flex-1 px-4 py-2 border border-orange-300 text-orange-600 rounded-lg hover:bg-orange-50 text-sm font-medium"
          >
            طلب مراجعة
          </button>
          <button
            onClick={() => onReview("approve", feedback)}
            className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm font-medium"
          >
            موافقة ودفع
          </button>
        </div>
      </div>
    </div>
  );
}
