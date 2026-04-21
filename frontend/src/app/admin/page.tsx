"use client";

import { Suspense, useState, useEffect, useCallback } from "react";
import { adminApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { useLocale } from "@/providers/locale-provider";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { getApiError } from "@/lib/utils";
import { StatsTab } from "./tabs/stats-tab";
import { UsersTab } from "./tabs/users-tab";
import { JobsTab } from "./tabs/jobs-tab";
import { ServicesTab } from "./tabs/services-tab";
import { TransactionsTab } from "./tabs/transactions-tab";
import { PayoutsTab } from "./tabs/payouts-tab";
import { SupportTab } from "./tabs/support-tab";
import { DisputesTab } from "./tabs/disputes-tab";
import { PayoutApprovalsTab } from "./tabs/payout-approvals-tab";
import { AuditLogTab } from "./tabs/audit-log-tab";

// ─── Types ───────────────────────────────────────────────────────────────────

interface PlatformStats {
  users: { total: number; active_30d: number; new_7d: number; by_role: Record<string, number> };
  jobs: { total: number; open: number; new_7d: number };
  contracts: { total: number; active: number; completed: number };
  proposals: { total: number };
  financials: { total_volume: number; platform_fees_earned: number; pending_escrow: number };
  reviews: { total: number; average_rating: number };
  messages: { total: number };
}

interface AdminUser {
  id: string; username: string; email: string;
  first_name: string; last_name: string;
  primary_role: string; status: string; is_superuser: boolean;
  avg_rating: number; total_reviews: number; total_earnings: number;
  jobs_completed: number; created_at: string;
}

interface AdminJob {
  id: string; title: string; status: string; job_type: string;
  budget_min: number | null; budget_max: number | null;
  category: string | null; proposal_count: number; created_at: string;
}

interface AdminTransaction {
  id: string; transaction_type: string; status: string;
  amount: number; currency: string; platform_fee: number;
  net_amount: number; description: string | null; created_at: string;
}

interface AdminEscrow {
  escrow_id: string; contract_id: string; milestone_id: string;
  milestone_title: string; amount: number; platform_fee: number;
  freelancer_amount: number; currency: string; funded_at: string | null;
  freelancer: {
    id: string; username: string; email: string;
    phone: string | null;
    qi_card_phone: string | null;
    qi_card_holder_name: string | null;
  };
}

interface PendingGig {
  id: string; title: string; slug: string; description: string;
  status: string; rejection_reason: string | null; revision_note: string | null;
  tags: string[] | null; created_at: string;
  freelancer: { id: string; username: string; email: string; avg_rating: number };
  packages: { tier: string; price: number; delivery_days: number; name: string }[];
}

type Tab =
  | "stats"
  | "users"
  | "jobs"
  | "gigs"
  | "transactions"
  | "payouts"
  | "approvals"
  | "disputes"
  | "support"
  | "audit";

// ─── Page ─────────────────────────────────────────────────────────────────────

function AdminPageContent() {
  const { user, isLoading: authLoading } = useAuthStore();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { locale } = useLocale();
  const ar = locale === "ar";

  // Derive tab from URL so refresh always restores the correct tab
  const tab: Tab = (searchParams.get("tab") as Tab) || "stats";
  const switchTab = useCallback((t: Tab) => {
    router.replace(`/admin?tab=${t}`, { scroll: false });
  }, [router]);

  // ── Stats ──
  const [stats, setStats] = useState<PlatformStats | null>(null);

  // ── Users ──
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [userTotal, setUserTotal] = useState(0);
  const [userSearch, setUserSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");

  // ── Jobs ──
  const [jobs, setJobs] = useState<AdminJob[]>([]);
  const [jobTotal, setJobTotal] = useState(0);
  const [jobSearch, setJobSearch] = useState("");
  const [jobStatusFilter, setJobStatusFilter] = useState("");

  // ── Transactions ──
  const [transactions, setTransactions] = useState<AdminTransaction[]>([]);
  const [txTotal, setTxTotal] = useState(0);
  const [txTypeFilter, setTxTypeFilter] = useState("");
  const [txStatusFilter, setTxStatusFilter] = useState("");

  // ── Payouts (escrows) ──
  const [escrows, setEscrows] = useState<AdminEscrow[]>([]);
  const [escrowActionLoading, setEscrowActionLoading] = useState<string | null>(null);

  // ── Gig review ──
  const [pendingGigs, setPendingGigs] = useState<PendingGig[]>([]);
  const [gigActionLoading, setGigActionLoading] = useState<string | null>(null);
  const [gigModalState, setGigModalState] = useState<{
    type: "revision" | "reject"; gigId: string; gigTitle: string;
  } | null>(null);
  const [gigModalText, setGigModalText] = useState("");

  // ── Shared loading ──
  const [loading, setLoading] = useState(true);

  const dateLocale = ar ? "ar-IQ" : "en-GB";

  const isAdmin = !!user?.is_superuser;
  const isStaff = isAdmin || !!user?.is_support;

  // ─── Auth guard ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (authLoading) return;
    if (!user) { router.push("/auth/login"); return; }
    if (!user.is_superuser && !user.is_support) {
      toast.error(ar ? "صلاحية الموظفين مطلوبة" : "Staff access required");
      router.push("/dashboard");
    }
  }, [user, authLoading, router, ar]);

  // ─── Fetch functions ─────────────────────────────────────────────────────────
  const fetchStats = useCallback(async () => {
    try {
      setLoading(true);
      const res = await adminApi.getStats();
      setStats(res.data);
    } catch {
      toast.error(ar ? "تعذّر تحميل الإحصاءات" : "Failed to load stats");
    } finally { setLoading(false); }
  }, [ar]);

  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true);
      const params: Record<string, string> = {};
      if (userSearch) params.search = userSearch;
      if (roleFilter) params.role = roleFilter;
      const res = await adminApi.getUsers(params);
      setUsers(res.data.users);
      setUserTotal(res.data.total);
    } catch {
      toast.error(ar ? "تعذّر تحميل المستخدمين" : "Failed to load users");
    } finally { setLoading(false); }
  }, [userSearch, roleFilter, ar]);

  const fetchJobs = useCallback(async () => {
    try {
      setLoading(true);
      const params: Record<string, string> = {};
      if (jobSearch) params.search = jobSearch;
      if (jobStatusFilter) params.status = jobStatusFilter;
      const res = await adminApi.getJobs(params);
      setJobs(res.data.jobs);
      setJobTotal(res.data.total);
    } catch {
      toast.error(ar ? "تعذّر تحميل الوظائف" : "Failed to load jobs");
    } finally { setLoading(false); }
  }, [jobSearch, jobStatusFilter, ar]);

  const fetchTransactions = useCallback(async () => {
    try {
      setLoading(true);
      const params: Record<string, string> = {};
      if (txTypeFilter) params.type = txTypeFilter;
      if (txStatusFilter) params.status = txStatusFilter;
      const res = await adminApi.getTransactions(params);
      setTransactions(res.data.transactions);
      setTxTotal(res.data.total);
    } catch {
      toast.error(ar ? "تعذّر تحميل المعاملات" : "Failed to load transactions");
    } finally { setLoading(false); }
  }, [txTypeFilter, txStatusFilter, ar]);

  const fetchEscrows = useCallback(async () => {
    try {
      setLoading(true);
      const res = await adminApi.getEscrows();
      setEscrows(res.data);
    } catch {
      toast.error(ar ? "تعذّر تحميل المدفوعات المعلقة" : "Failed to load pending payouts");
    } finally { setLoading(false); }
  }, [ar]);

  const fetchPendingGigs = useCallback(async () => {
    try {
      setLoading(true);
      const res = await adminApi.getPendingGigs();
      setPendingGigs(res.data);
    } catch {
      toast.error(ar ? "تعذّر تحميل الخدمات المعلقة" : "Failed to load pending gigs");
    } finally { setLoading(false); }
  }, [ar]);

  // ─── Load on tab change ──────────────────────────────────────────────────────
  useEffect(() => {
    if (tab === "stats") fetchStats();
    if (tab === "users") fetchUsers();
    if (tab === "jobs") fetchJobs();
    if (tab === "gigs") fetchPendingGigs();
    if (tab === "transactions") fetchTransactions();
    if (tab === "payouts") fetchEscrows();
  }, [tab, fetchStats, fetchUsers, fetchJobs, fetchPendingGigs, fetchTransactions, fetchEscrows]);

  // Fetch gig count on mount for tab badge
  useEffect(() => {
    adminApi.getPendingGigs().then(res => setPendingGigs(res.data)).catch(() => {});
  }, []);

  // ─── Action handlers ──────────────────────────────────────────────────────────
  const handleStatusUpdate = async (userId: string, status: string) => {
    try {
      await adminApi.updateUserStatus(userId, { status });
      toast.success(ar ? "تم تحديث حالة المستخدم" : "User status updated");
      fetchUsers();
    } catch (err: unknown) {
      toast.error(getApiError(err, ar ? "تعذّر التحديث" : "Failed to update"));
    }
  };

  const handleToggleAdmin = async (userId: string, isCurrentlyAdmin: boolean) => {
    try {
      await adminApi.toggleAdmin(userId);
      toast.success(isCurrentlyAdmin
        ? (ar ? "تم إلغاء صلاحية المدير" : "Admin access revoked")
        : (ar ? "تمت ترقية المستخدم إلى مدير" : "User promoted to admin"));
      fetchUsers();
    } catch (err: unknown) {
      toast.error(getApiError(err, ar ? "تعذّر تغيير الصلاحية" : "Failed to change role"));
    }
  };

  const handleToggleSupport = async (userId: string, isCurrentlySupport: boolean) => {
    try {
      await adminApi.toggleSupport(userId);
      toast.success(isCurrentlySupport
        ? (ar ? "تم إلغاء صلاحية الدعم" : "Support access revoked")
        : (ar ? "تم تعيين المستخدم في فريق الدعم" : "User granted support role"));
      fetchUsers();
    } catch (err: unknown) {
      toast.error(getApiError(err, ar ? "تعذّر تغيير الصلاحية" : "Failed to change role"));
    }
  };

  const handleUnsuspendChat = async (userId: string) => {
    try {
      await adminApi.unsuspendChat(userId);
      toast.success(ar ? "تم رفع إيقاف الدردشة" : "Chat suspension lifted");
      fetchUsers();
    } catch (err: unknown) {
      toast.error(getApiError(err, ar ? "تعذّر رفع الإيقاف" : "Failed to lift suspension"));
    }
  };

  const handleApproveGig = async (gigId: string) => {
    setGigActionLoading(gigId);
    try {
      await adminApi.approveGig(gigId);
      toast.success(ar ? "تمت الموافقة على الخدمة" : "Gig approved — now live");
      fetchPendingGigs();
    } catch (err: unknown) {
      toast.error(getApiError(err, ar ? "تعذّرت الموافقة" : "Failed to approve"));
    } finally { setGigActionLoading(null); }
  };

  const handleGigModalSubmit = async () => {
    if (!gigModalState || gigModalText.trim().length < 10) return;
    setGigActionLoading(gigModalState.gigId);
    try {
      if (gigModalState.type === "revision") {
        await adminApi.requestGigRevision(gigModalState.gigId, gigModalText.trim());
        toast.success(ar ? "تم إرسال طلب التعديل للمستقل" : "Revision request sent to freelancer");
      } else {
        await adminApi.rejectGig(gigModalState.gigId, gigModalText.trim());
        toast.success(ar ? "تم رفض الخدمة" : "Gig rejected");
      }
      setGigModalState(null);
      setGigModalText("");
      fetchPendingGigs();
    } catch (err: unknown) {
      toast.error(getApiError(err, ar ? "تعذّر الإجراء" : "Action failed"));
    } finally { setGigActionLoading(null); }
  };

  const handleReleaseEscrow = async (escrow: AdminEscrow) => {
    const freelancerName = escrow.freelancer.username;
    const amount = `${escrow.freelancer_amount.toLocaleString(ar ? "ar-IQ" : "en-US")} ${escrow.currency}`;
    const confirmed = confirm(
      ar
        ? `هل أرسلت الدفعة (${amount}) إلى ${freelancerName} عبر بطاقة Qi Card؟ سيتم تحديث السجل فوراً. قد يتطلب المبلغ الكبير موافقة مديرٍ ثانٍ.`
        : `Confirm: Did you send ${amount} to ${freelancerName} via Qi Card? This will update the ledger. Large amounts may require a second admin to approve.`
    );
    if (!confirmed) return;

    setEscrowActionLoading(escrow.escrow_id);
    try {
      const res = await adminApi.releaseEscrow(escrow.escrow_id);
      const status = res.data?.status;
      if (status === "pending_second_approval") {
        toast.success(
          ar
            ? "تم إنشاء طلب موافقة — يحتاج مديرٌ ثانٍ إلى الموافقة قبل تحويل المبلغ"
            : "Approval request created — a second admin must approve before the money moves"
        );
      } else {
        toast.success(
          ar
            ? `تم تسجيل الدفعة إلى ${freelancerName} بنجاح`
            : `Payout to ${freelancerName} recorded successfully`
        );
      }
      fetchEscrows();
    } catch {
      toast.error(ar ? "تعذّر تسجيل الدفعة" : "Failed to record payout");
    } finally {
      setEscrowActionLoading(null);
    }
  };

  // ─── Auth loading guard ───────────────────────────────────────────────────────
  if (authLoading || !isStaff) {
    return (
      <div className="p-6 text-center text-gray-500">
        {authLoading
          ? (ar ? "جاري التحميل..." : "Loading...")
          : (ar ? "جاري التحقق من الصلاحية..." : "Verifying access...")}
      </div>
    );
  }

  // ─── Tab definitions ─────────────────────────────────────────────────────────
  // Support staff get a reduced surface: no gig moderation (admin-only) and
  // no payouts/approvals (financial actions stay on admins).
  const ALL_TABS: { value: Tab; label: string; adminOnly?: boolean }[] = [
    { value: "stats", label: ar ? "📊 نظرة عامة" : "📊 Overview" },
    { value: "users", label: ar ? "👥 المستخدمون" : "👥 Users" },
    { value: "jobs", label: ar ? "📋 الوظائف" : "📋 Jobs" },
    {
      value: "gigs",
      label: ar
        ? `🛍️ مراجعة الخدمات${pendingGigs.length > 0 ? ` (${pendingGigs.length})` : ""}`
        : `🛍️ Gig Review${pendingGigs.length > 0 ? ` (${pendingGigs.length})` : ""}`,
      adminOnly: true,
    },
    { value: "transactions", label: ar ? "💳 المعاملات" : "💳 Transactions" },
    { value: "payouts", label: ar ? "💸 المدفوعات المعلقة" : "💸 Pending Payouts", adminOnly: true },
    { value: "approvals", label: ar ? "✅ موافقات الدفع" : "✅ Payout Approvals", adminOnly: true },
    { value: "disputes", label: ar ? "⚠️ النزاعات" : "⚠️ Disputes" },
    { value: "support", label: ar ? "🛟 الدعم" : "🛟 Support" },
    { value: "audit", label: ar ? "📜 سجل الإجراءات" : "📜 Audit Log" },
  ];
  const TABS = ALL_TABS.filter((t) => isAdmin || !t.adminOnly);

  // ─── Render ───────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <h1 className="text-2xl font-bold text-gray-900">
          {ar ? "لوحة الإدارة" : "Admin Dashboard"}
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          {ar ? "إدارة منصة كاسب" : "Manage the Kaasb platform"}
        </p>
      </div>

      {/* Tabs */}
      <div className="bg-white border-b border-gray-200 px-6">
        <div className="flex gap-6 overflow-x-auto">
          {TABS.map((t) => (
            <button
              key={t.value}
              onClick={() => switchTab(t.value)}
              className={`py-3 text-sm font-medium border-b-2 transition whitespace-nowrap ${
                tab === t.value
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="p-6 max-w-7xl mx-auto">
        {tab === "stats" && stats && (
          <StatsTab stats={stats} ar={ar} />
        )}

        {tab === "users" && (
          <UsersTab
            users={users}
            total={userTotal}
            loading={loading}
            search={userSearch}
            roleFilter={roleFilter}
            currentUserId={user?.id}
            ar={ar}
            dateLocale={dateLocale}
            onSearchChange={setUserSearch}
            onRoleFilterChange={setRoleFilter}
            onSearch={fetchUsers}
            onStatusUpdate={handleStatusUpdate}
            onToggleAdmin={handleToggleAdmin}
            onToggleSupport={handleToggleSupport}
            onUnsuspendChat={handleUnsuspendChat}
          />
        )}

        {tab === "jobs" && (
          <JobsTab
            jobs={jobs}
            total={jobTotal}
            loading={loading}
            search={jobSearch}
            statusFilter={jobStatusFilter}
            ar={ar}
            dateLocale={dateLocale}
            onSearchChange={setJobSearch}
            onStatusFilterChange={setJobStatusFilter}
            onSearch={fetchJobs}
            onRefresh={fetchJobs}
          />
        )}

        {tab === "gigs" && (
          <ServicesTab
            pendingServices={pendingGigs}
            loading={loading}
            actionLoading={gigActionLoading}
            modalState={
              gigModalState
                ? { type: gigModalState.type, serviceId: gigModalState.gigId, serviceTitle: gigModalState.gigTitle }
                : null
            }
            modalText={gigModalText}
            ar={ar}
            dateLocale={dateLocale}
            onApprove={handleApproveGig}
            onOpenModal={(type: "revision" | "reject", serviceId: string, serviceTitle: string) => {
              setGigModalState({ type, gigId: serviceId, gigTitle: serviceTitle });
              setGigModalText("");
            }}
            onCloseModal={() => { setGigModalState(null); setGigModalText(""); }}
            onModalTextChange={setGigModalText}
            onModalSubmit={handleGigModalSubmit}
          />
        )}

        {tab === "transactions" && (
          <TransactionsTab
            transactions={transactions}
            total={txTotal}
            loading={loading}
            typeFilter={txTypeFilter}
            statusFilter={txStatusFilter}
            ar={ar}
            dateLocale={dateLocale}
            onTypeFilterChange={setTxTypeFilter}
            onStatusFilterChange={setTxStatusFilter}
            onFilter={fetchTransactions}
          />
        )}

        {tab === "payouts" && (
          <PayoutsTab
            escrows={escrows}
            loading={loading}
            actionLoading={escrowActionLoading}
            ar={ar}
            dateLocale={dateLocale}
            onRelease={handleReleaseEscrow}
          />
        )}

        {tab === "approvals" && (
          <PayoutApprovalsTab ar={ar} dateLocale={dateLocale} currentAdminId={user?.id} />
        )}

        {tab === "disputes" && (
          <DisputesTab ar={ar} dateLocale={dateLocale} />
        )}

        {tab === "support" && (
          <SupportTab ar={ar} dateLocale={dateLocale} />
        )}

        {tab === "audit" && (
          <AuditLogTab ar={ar} dateLocale={dateLocale} />
        )}
      </div>
    </div>
  );
}

export default function AdminPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-10 h-10 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <AdminPageContent />
    </Suspense>
  );
}
