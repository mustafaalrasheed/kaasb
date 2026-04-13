"use client";

import { useState, useEffect, useCallback } from "react";
import { adminApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { useLocale } from "@/providers/locale-provider";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { getApiError } from "@/lib/utils";

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
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  primary_role: string;
  status: string;
  is_superuser: boolean;
  avg_rating: number;
  total_reviews: number;
  total_earnings: number;
  jobs_completed: number;
  created_at: string;
}

interface AdminJob {
  id: string;
  title: string;
  status: string;
  job_type: string;
  budget_min: number | null;
  budget_max: number | null;
  category: string | null;
  proposal_count: number;
  created_at: string;
}

interface AdminTransaction {
  id: string;
  transaction_type: string;
  status: string;
  amount: number;
  currency: string;
  platform_fee: number;
  net_amount: number;
  description: string | null;
  created_at: string;
}

interface AdminEscrow {
  escrow_id: string;
  contract_id: string;
  milestone_id: string;
  milestone_title: string;
  amount: number;
  platform_fee: number;
  freelancer_amount: number;
  currency: string;
  funded_at: string | null;
  freelancer: {
    id: string;
    username: string;
    email: string;
    phone: string | null;
    qi_card_phone: string | null;
  };
}

type Tab = "stats" | "users" | "jobs" | "gigs" | "transactions" | "payouts";

interface PendingGig {
  id: string;
  title: string;
  slug: string;
  description: string;
  status: string;
  rejection_reason: string | null;
  revision_note: string | null;
  tags: string[] | null;
  created_at: string;
  freelancer: {
    id: string;
    username: string;
    email: string;
    avg_rating: number;
  };
  packages: { tier: string; price: number; delivery_days: number; name: string }[];
}

export default function AdminPage() {
  const { user, isLoading: authLoading } = useAuthStore();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { locale } = useLocale();
  const ar = locale === "ar";

  const [tab, setTab] = useState<Tab>((searchParams.get("tab") as Tab) || "stats");

  const switchTab = useCallback((t: Tab) => {
    setTab(t);
    router.replace(`/admin?tab=${t}`, { scroll: false });
  }, [router]);
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [userTotal, setUserTotal] = useState(0);
  const [userSearch, setUserSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [jobs, setJobs] = useState<AdminJob[]>([]);
  const [jobTotal, setJobTotal] = useState(0);
  const [jobSearch, setJobSearch] = useState("");
  const [jobStatusFilter, setJobStatusFilter] = useState("");
  const [transactions, setTransactions] = useState<AdminTransaction[]>([]);
  const [txTotal, setTxTotal] = useState(0);
  const [txTypeFilter, setTxTypeFilter] = useState("");
  const [txStatusFilter, setTxStatusFilter] = useState("");
  const [escrows, setEscrows] = useState<AdminEscrow[]>([]);
  const [escrowActionLoading, setEscrowActionLoading] = useState<string | null>(null);
  const [pendingGigs, setPendingGigs] = useState<PendingGig[]>([]);
  const [gigActionLoading, setGigActionLoading] = useState<string | null>(null);
  const [gigModalState, setGigModalState] = useState<{
    type: "revision" | "reject";
    gigId: string;
    gigTitle: string;
  } | null>(null);
  const [gigModalText, setGigModalText] = useState("");

  const GIG_STATUS_LABELS: Record<string, string> = ar
    ? { pending_review: "قيد المراجعة", needs_revision: "يحتاج تعديل", active: "نشط", rejected: "مرفوض", paused: "موقوف", draft: "مسودة", archived: "مؤرشف" }
    : { pending_review: "Pending Review", needs_revision: "Needs Revision", active: "Active", rejected: "Rejected", paused: "Paused", draft: "Draft", archived: "Archived" };

  const ROLE_LABELS: Record<string, string> = ar
    ? { client: "عميل", freelancer: "مستقل", admin: "مدير" }
    : { client: "Client", freelancer: "Freelancer", admin: "Admin" };

  const USER_STATUS_LABELS: Record<string, string> = ar
    ? { active: "نشط", suspended: "موقوف", deactivated: "مُلغى", pending_verification: "قيد التحقق" }
    : { active: "Active", suspended: "Suspended", deactivated: "Deactivated", pending_verification: "Pending Verification" };

  const JOB_STATUS_LABELS: Record<string, string> = ar
    ? { open: "مفتوح", in_progress: "جارٍ", completed: "مكتمل", closed: "مغلق", cancelled: "ملغى", draft: "مسودة" }
    : { open: "Open", in_progress: "In Progress", completed: "Completed", closed: "Closed", cancelled: "Cancelled", draft: "Draft" };

  const TX_TYPE_LABELS: Record<string, string> = ar
    ? { escrow_fund: "تمويل ضمان", escrow_release: "تحرير ضمان", escrow_refund: "استرداد ضمان", platform_fee: "عمولة المنصة", payout: "سحب" }
    : { escrow_fund: "Escrow Fund", escrow_release: "Escrow Release", escrow_refund: "Escrow Refund", platform_fee: "Platform Fee", payout: "Payout" };

  const TX_STATUS_LABELS: Record<string, string> = ar
    ? { pending: "معلق", processing: "جارٍ", completed: "مكتمل", failed: "فشل", refunded: "مسترد" }
    : { pending: "Pending", processing: "Processing", completed: "Completed", failed: "Failed", refunded: "Refunded" };

  const TABS = [
    { value: "stats" as Tab, label: ar ? "📊 نظرة عامة" : "📊 Overview" },
    { value: "users" as Tab, label: ar ? "👥 المستخدمون" : "👥 Users" },
    { value: "jobs" as Tab, label: ar ? "📋 الوظائف" : "📋 Jobs" },
    { value: "gigs" as Tab, label: ar
      ? `🛍️ مراجعة الخدمات${pendingGigs.length > 0 ? ` (${pendingGigs.length})` : ""}`
      : `🛍️ Gig Review${pendingGigs.length > 0 ? ` (${pendingGigs.length})` : ""}` },
    { value: "transactions" as Tab, label: ar ? "💳 المعاملات" : "💳 Transactions" },
    { value: "payouts" as Tab, label: ar ? "💸 المدفوعات المعلقة" : "💸 Pending Payouts" },
  ];

  const dateLocale = ar ? "ar-IQ" : "en-GB";

  useEffect(() => {
    if (authLoading) return;
    if (!user) { router.push("/auth/login"); return; }
    if (!user.is_superuser) {
      toast.error(ar ? "صلاحية المدير مطلوبة" : "Admin access required");
      router.push("/dashboard");
    }
  }, [user, authLoading, router, ar]);

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
        ? `هل أرسلت الدفعة (${amount}) إلى ${freelancerName} عبر بطاقة Qi Card؟ سيتم تحديث السجل فوراً.`
        : `Confirm: Did you send ${amount} to ${freelancerName} via Qi Card? This will update the ledger immediately.`
    );
    if (!confirmed) return;

    setEscrowActionLoading(escrow.escrow_id);
    try {
      await adminApi.releaseEscrow(escrow.escrow_id);
      toast.success(
        ar
          ? `تم تسجيل الدفعة إلى ${freelancerName} بنجاح`
          : `Payout to ${freelancerName} recorded successfully`
      );
      fetchEscrows();
    } catch {
      toast.error(ar ? "تعذّر تسجيل الدفعة" : "Failed to record payout");
    } finally {
      setEscrowActionLoading(null);
    }
  };

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

  if (authLoading || !user?.is_superuser) {
    return (
      <div className="p-6 text-center text-gray-500">
        {authLoading
          ? (ar ? "جاري التحميل..." : "Loading...")
          : (ar ? "جاري التحقق من الصلاحية..." : "Verifying access...")}
      </div>
    );
  }

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
        <div className="flex gap-6">
          {TABS.map((t) => (
            <button
              key={t.value}
              onClick={() => switchTab(t.value)}
              className={`py-3 text-sm font-medium border-b-2 transition whitespace-nowrap ${
                tab === t.value ? "border-blue-500 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="p-6 max-w-7xl mx-auto">
        {/* Stats Tab */}
        {tab === "stats" && stats && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard label={ar ? "إجمالي المستخدمين" : "Total Users"} value={stats.users.total} icon="👥" />
              <StatCard label={ar ? "النشطون (30 يوم)" : "Active (30d)"} value={stats.users.active_30d} icon="🟢" />
              <StatCard label={ar ? "الوظائف المفتوحة" : "Open Jobs"} value={stats.jobs.open} icon="📋" />
              <StatCard label={ar ? "العقود النشطة" : "Active Contracts"} value={stats.contracts.active} icon="📝" />
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <StatCard label={ar ? "إجمالي حجم التداول" : "Total Volume"} value={`${stats.financials.total_volume.toLocaleString(ar ? "ar-IQ" : "en-US")} ${ar ? "د.ع" : "IQD"}`} icon="💰" isText />
              <StatCard label={ar ? "عمولات المنصة" : "Platform Fees"} value={`${stats.financials.platform_fees_earned.toLocaleString(ar ? "ar-IQ" : "en-US")} ${ar ? "د.ع" : "IQD"}`} icon="🏦" isText />
              <StatCard label={ar ? "في الضمان" : "In Escrow"} value={`${stats.financials.pending_escrow.toLocaleString(ar ? "ar-IQ" : "en-US")} ${ar ? "د.ع" : "IQD"}`} icon="🔒" isText />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-white rounded-lg border p-4">
                <h3 className="font-semibold text-gray-900 mb-3">
                  {ar ? "المستخدمون حسب الدور" : "Users by Role"}
                </h3>
                {Object.entries(stats.users.by_role).map(([role, count]) => (
                  <div key={role} className="flex justify-between text-sm py-1">
                    <span className="text-gray-600">{ROLE_LABELS[role] ?? role}</span>
                    <span className="font-medium">{count}</span>
                  </div>
                ))}
                <div className="flex justify-between text-sm py-1 border-t mt-2 pt-2">
                  <span className="text-gray-600">{ar ? "جدد (7 أيام)" : "New (7 days)"}</span>
                  <span className="font-medium text-green-600">+{stats.users.new_7d}</span>
                </div>
              </div>

              <div className="bg-white rounded-lg border p-4">
                <h3 className="font-semibold text-gray-900 mb-3">{ar ? "السوق" : "Marketplace"}</h3>
                <div className="flex justify-between text-sm py-1">
                  <span className="text-gray-600">{ar ? "إجمالي الوظائف" : "Total Jobs"}</span>
                  <span className="font-medium">{stats.jobs.total}</span>
                </div>
                <div className="flex justify-between text-sm py-1">
                  <span className="text-gray-600">{ar ? "إجمالي العروض" : "Total Proposals"}</span>
                  <span className="font-medium">{stats.proposals.total}</span>
                </div>
                <div className="flex justify-between text-sm py-1">
                  <span className="text-gray-600">{ar ? "العقود المكتملة" : "Completed Contracts"}</span>
                  <span className="font-medium">{stats.contracts.completed}</span>
                </div>
                <div className="flex justify-between text-sm py-1">
                  <span className="text-gray-600">{ar ? "وظائف جديدة (7 أيام)" : "New Jobs (7 days)"}</span>
                  <span className="font-medium text-green-600">+{stats.jobs.new_7d}</span>
                </div>
              </div>

              <div className="bg-white rounded-lg border p-4">
                <h3 className="font-semibold text-gray-900 mb-3">{ar ? "المجتمع" : "Community"}</h3>
                <div className="flex justify-between text-sm py-1">
                  <span className="text-gray-600">{ar ? "التقييمات" : "Reviews"}</span>
                  <span className="font-medium">{stats.reviews.total}</span>
                </div>
                <div className="flex justify-between text-sm py-1">
                  <span className="text-gray-600">{ar ? "متوسط التقييم" : "Avg. Rating"}</span>
                  <span className="font-medium">{stats.reviews.average_rating}★</span>
                </div>
                <div className="flex justify-between text-sm py-1">
                  <span className="text-gray-600">{ar ? "الرسائل" : "Messages"}</span>
                  <span className="font-medium">{stats.messages.total}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Users Tab */}
        {tab === "users" && (
          <div className="space-y-4">
            <div className="flex gap-3 flex-wrap">
              <input type="text" value={userSearch} onChange={(e) => setUserSearch(e.target.value)}
                placeholder={ar ? "بحث عن مستخدم..." : "Search users..."}
                className="flex-1 min-w-[200px] border border-gray-300 rounded-lg px-4 py-2 text-sm"
                onKeyDown={(e) => e.key === "Enter" && fetchUsers()} />
              <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
                <option value="">{ar ? "كل الأدوار" : "All Roles"}</option>
                <option value="client">{ar ? "عميل" : "Client"}</option>
                <option value="freelancer">{ar ? "مستقل" : "Freelancer"}</option>
                <option value="admin">{ar ? "مدير" : "Admin"}</option>
              </select>
              <button onClick={fetchUsers} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">
                {ar ? "بحث" : "Search"}
              </button>
            </div>

            <div className="bg-white rounded-lg border overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="text-start p-3 font-medium text-gray-600">{ar ? "المستخدم" : "User"}</th>
                    <th className="text-start p-3 font-medium text-gray-600">{ar ? "الدور" : "Role"}</th>
                    <th className="text-start p-3 font-medium text-gray-600">{ar ? "الحالة" : "Status"}</th>
                    <th className="text-start p-3 font-medium text-gray-600">{ar ? "التقييم" : "Rating"}</th>
                    <th className="text-start p-3 font-medium text-gray-600">{ar ? "تاريخ الانضمام" : "Joined"}</th>
                    <th className="text-end p-3 font-medium text-gray-600">{ar ? "الإجراءات" : "Actions"}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {users.map((u) => (
                    <tr key={u.id} className="hover:bg-gray-50">
                      <td className="p-3">
                        <div className="font-medium text-gray-900">
                          {u.first_name} {u.last_name}
                          {u.is_superuser && (
                            <span className="ms-1 text-xs bg-red-100 text-red-600 px-1.5 py-0.5 rounded">
                              {ar ? "مدير" : "Admin"}
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-gray-500">{u.email}</div>
                      </td>
                      <td className="p-3 text-gray-600">{ROLE_LABELS[u.primary_role] ?? u.primary_role}</td>
                      <td className="p-3">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          u.status === "active" ? "bg-green-50 text-green-700" :
                          u.status === "suspended" ? "bg-red-50 text-red-700" :
                          "bg-gray-100 text-gray-500"
                        }`}>
                          {USER_STATUS_LABELS[u.status] ?? u.status}
                        </span>
                      </td>
                      <td className="p-3 text-gray-600">{u.avg_rating > 0 ? `${u.avg_rating}★` : "—"}</td>
                      <td className="p-3 text-gray-500">
                        {new Date(u.created_at).toLocaleDateString(dateLocale, {
                          year: "numeric", month: "short", day: "numeric",
                        })}
                      </td>
                      <td className="p-3">
                        <div className="flex gap-1 justify-end">
                          {u.status === "active" && !u.is_superuser && (
                            <button onClick={() => handleStatusUpdate(u.id, "suspended")}
                              className="px-2 py-1 text-xs bg-red-50 text-red-600 rounded hover:bg-red-100">
                              {ar ? "إيقاف" : "Suspend"}
                            </button>
                          )}
                          {(u.status === "suspended" || u.status === "deactivated") && (
                            <button onClick={() => handleStatusUpdate(u.id, "active")}
                              className="px-2 py-1 text-xs bg-green-50 text-green-600 rounded hover:bg-green-100">
                              {ar ? "تفعيل" : "Activate"}
                            </button>
                          )}
                          {u.id !== user?.id && !u.is_superuser && (
                            <button onClick={() => handleToggleAdmin(u.id, false)}
                              className="px-2 py-1 text-xs bg-blue-50 text-blue-600 rounded hover:bg-blue-100">
                              {ar ? "ترقية لمدير" : "Make Admin"}
                            </button>
                          )}
                          {u.id !== user?.id && u.is_superuser && (
                            <button onClick={() => handleToggleAdmin(u.id, true)}
                              className="px-2 py-1 text-xs bg-orange-50 text-orange-600 rounded hover:bg-orange-100">
                              {ar ? "إلغاء صلاحية المدير" : "Revoke Admin"}
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {users.length === 0 && !loading && (
                <div className="p-8 text-center text-gray-400">
                  {ar ? "لا يوجد مستخدمون" : "No users found"}
                </div>
              )}
            </div>
            <p className="text-sm text-gray-500">
              {ar ? `${userTotal} مستخدم إجمالاً` : `${userTotal} user(s) total`}
            </p>
          </div>
        )}

        {/* Jobs Tab */}
        {tab === "jobs" && (
          <div className="space-y-4">
            <div className="flex gap-3 flex-wrap">
              <input type="text" value={jobSearch} onChange={(e) => setJobSearch(e.target.value)}
                placeholder={ar ? "بحث عن وظيفة..." : "Search jobs..."}
                className="flex-1 min-w-[200px] border border-gray-300 rounded-lg px-4 py-2 text-sm"
                onKeyDown={(e) => e.key === "Enter" && fetchJobs()} />
              <select value={jobStatusFilter} onChange={(e) => setJobStatusFilter(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
                <option value="">{ar ? "كل الحالات" : "All Statuses"}</option>
                <option value="open">{ar ? "مفتوح" : "Open"}</option>
                <option value="in_progress">{ar ? "جارٍ" : "In Progress"}</option>
                <option value="completed">{ar ? "مكتمل" : "Completed"}</option>
                <option value="closed">{ar ? "مغلق" : "Closed"}</option>
                <option value="cancelled">{ar ? "ملغى" : "Cancelled"}</option>
              </select>
              <button onClick={fetchJobs} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">
                {ar ? "بحث" : "Search"}
              </button>
            </div>

            <div className="bg-white rounded-lg border overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="text-start p-3 font-medium text-gray-600">{ar ? "العنوان" : "Title"}</th>
                    <th className="text-start p-3 font-medium text-gray-600">{ar ? "النوع" : "Type"}</th>
                    <th className="text-start p-3 font-medium text-gray-600">{ar ? "الميزانية" : "Budget"}</th>
                    <th className="text-start p-3 font-medium text-gray-600">{ar ? "الحالة" : "Status"}</th>
                    <th className="text-start p-3 font-medium text-gray-600">{ar ? "العروض" : "Proposals"}</th>
                    <th className="text-start p-3 font-medium text-gray-600">{ar ? "تاريخ النشر" : "Posted"}</th>
                    <th className="text-end p-3 font-medium text-gray-600">{ar ? "إجراءات" : "Actions"}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {jobs.map((j) => (
                    <tr key={j.id} className="hover:bg-gray-50">
                      <td className="p-3 font-medium text-gray-900 max-w-xs truncate">{j.title}</td>
                      <td className="p-3 text-gray-600">
                        {j.job_type === "fixed" ? (ar ? "ثابت" : "Fixed") : (ar ? "بالساعة" : "Hourly")}
                      </td>
                      <td className="p-3 text-gray-600 text-xs" dir="ltr">
                        {j.budget_min != null && j.budget_max != null
                          ? `${j.budget_min.toLocaleString()}–${j.budget_max.toLocaleString()} IQD`
                          : j.budget_min != null ? `from ${j.budget_min.toLocaleString()} IQD` : "—"}
                      </td>
                      <td className="p-3">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          j.status === "open" ? "bg-green-50 text-green-700" :
                          j.status === "in_progress" ? "bg-blue-50 text-blue-700" :
                          j.status === "completed" ? "bg-purple-50 text-purple-700" :
                          "bg-gray-100 text-gray-500"
                        }`}>
                          {JOB_STATUS_LABELS[j.status] ?? j.status}
                        </span>
                      </td>
                      <td className="p-3 text-gray-600">{j.proposal_count}</td>
                      <td className="p-3 text-gray-500">
                        {new Date(j.created_at).toLocaleDateString(dateLocale, { month: "short", day: "numeric" })}
                      </td>
                      <td className="p-3">
                        <div className="flex justify-end">
                          {j.status === "open" && (
                            <button
                              onClick={async () => {
                                try {
                                  await adminApi.updateJobStatus(j.id, { status: "closed" });
                                  toast.success(ar ? "تم إغلاق الوظيفة" : "Job closed");
                                  fetchJobs();
                                } catch {
                                  toast.error(ar ? "تعذّر إغلاق الوظيفة" : "Failed to close job");
                                }
                              }}
                              className="px-2 py-1 text-xs bg-red-50 text-red-600 rounded hover:bg-red-100">
                              {ar ? "إغلاق" : "Close"}
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {jobs.length === 0 && !loading && (
                <div className="p-8 text-center text-gray-400">{ar ? "لا توجد وظائف" : "No jobs found"}</div>
              )}
            </div>
            <p className="text-sm text-gray-500">
              {ar ? `${jobTotal} وظيفة إجمالاً` : `${jobTotal} job(s) total`}
            </p>
          </div>
        )}

        {/* Gig Review Tab */}
        {tab === "gigs" && (
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-800">
                {ar ? "خدمات قيد المراجعة" : "Gigs Pending Review"}
              </h2>
              <p className="text-sm text-gray-500 mt-0.5">
                {ar
                  ? "راجع كل خدمة وافقها، اطلب تعديلاً، أو ارفضها مع ذكر السبب."
                  : "Review each gig, approve it, request specific edits, or reject it with a reason."}
              </p>
            </div>

            {loading ? (
              <div className="text-center text-gray-400 py-12">
                {ar ? "جاري التحميل..." : "Loading..."}
              </div>
            ) : pendingGigs.length === 0 ? (
              <div className="bg-white border border-gray-200 rounded-xl p-12 text-center">
                <div className="text-4xl mb-3">✅</div>
                <p className="text-gray-500 font-medium">
                  {ar ? "لا توجد خدمات قيد المراجعة" : "No gigs pending review"}
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {pendingGigs.map((gig) => (
                  <div key={gig.id} className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                    {/* Header */}
                    <div className="flex items-start justify-between gap-4 p-5 border-b border-gray-100">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h3 className="font-semibold text-gray-900 truncate">{gig.title}</h3>
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                            gig.status === "pending_review"
                              ? "bg-yellow-50 text-yellow-700"
                              : "bg-blue-50 text-blue-700"
                          }`}>
                            {GIG_STATUS_LABELS[gig.status] ?? gig.status}
                          </span>
                        </div>
                        <p className="text-sm text-gray-500 mt-0.5">
                          {ar ? "المستقل:" : "Freelancer:"}{" "}
                          <span className="font-medium text-gray-700">{gig.freelancer.username}</span>
                          <span className="text-gray-400 mx-1">·</span>
                          {gig.freelancer.email}
                          {gig.freelancer.avg_rating > 0 && (
                            <span className="text-gray-400 mx-1">· {gig.freelancer.avg_rating}★</span>
                          )}
                        </p>
                        <p className="text-xs text-gray-400 mt-0.5">
                          {ar ? "تاريخ الإنشاء:" : "Submitted:"}{" "}
                          {new Date(gig.created_at).toLocaleDateString(dateLocale, {
                            year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
                          })}
                        </p>
                      </div>
                      {/* Packages summary */}
                      <div className="shrink-0 text-end">
                        {gig.packages.slice(0, 1).map(pkg => (
                          <div key={pkg.tier}>
                            <span className="text-lg font-bold text-gray-900">
                              {pkg.price.toLocaleString(ar ? "ar-IQ" : "en-US")} {ar ? "د.ع" : "IQD"}
                            </span>
                            <p className="text-xs text-gray-500">{ar ? "البداية من" : "Starting at"}</p>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Description */}
                    <div className="px-5 py-4">
                      <p className="text-sm text-gray-700 line-clamp-3 leading-relaxed">
                        {gig.description}
                      </p>
                      {gig.tags && gig.tags.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-3">
                          {gig.tags.map(tag => (
                            <span key={tag} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                      {/* Packages */}
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mt-4">
                        {gig.packages.map(pkg => (
                          <div key={pkg.tier} className="border border-gray-200 rounded-lg p-3 text-sm">
                            <div className="font-medium text-gray-900 capitalize">{pkg.tier}</div>
                            <div className="text-gray-600">{pkg.name}</div>
                            <div className="text-gray-800 font-semibold mt-1">
                              {pkg.price.toLocaleString(ar ? "ar-IQ" : "en-US")} {ar ? "د.ع" : "IQD"}
                            </div>
                            <div className="text-gray-400 text-xs">{pkg.delivery_days} {ar ? "يوم" : "days"}</div>
                          </div>
                        ))}
                      </div>
                      {/* Previous revision note if any */}
                      {gig.revision_note && (
                        <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm">
                          <span className="font-medium text-blue-700">{ar ? "ملاحظة التعديل السابقة: " : "Previous revision note: "}</span>
                          <span className="text-blue-800">{gig.revision_note}</span>
                        </div>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 px-5 py-3 bg-gray-50 border-t border-gray-100">
                      <button
                        onClick={() => handleApproveGig(gig.id)}
                        disabled={gigActionLoading === gig.id}
                        className="px-4 py-2 text-sm font-medium bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition"
                      >
                        {gigActionLoading === gig.id ? "..." : (ar ? "✓ موافقة" : "✓ Approve")}
                      </button>
                      <button
                        onClick={() => { setGigModalState({ type: "revision", gigId: gig.id, gigTitle: gig.title }); setGigModalText(""); }}
                        disabled={gigActionLoading === gig.id}
                        className="px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition"
                      >
                        {ar ? "✏️ طلب تعديل" : "✏️ Request Edit"}
                      </button>
                      <button
                        onClick={() => { setGigModalState({ type: "reject", gigId: gig.id, gigTitle: gig.title }); setGigModalText(""); }}
                        disabled={gigActionLoading === gig.id}
                        className="px-4 py-2 text-sm font-medium bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition"
                      >
                        {ar ? "✕ رفض" : "✕ Reject"}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Modal for revision note / rejection reason */}
            {gigModalState && (
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
                  <h3 className="font-semibold text-gray-900">
                    {gigModalState.type === "revision"
                      ? (ar ? "طلب تعديل على الخدمة" : "Request Edits")
                      : (ar ? "رفض الخدمة" : "Reject Gig")}
                  </h3>
                  <p className="text-sm text-gray-600">
                    <span className="font-medium">{gigModalState.gigTitle}</span>
                  </p>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {gigModalState.type === "revision"
                        ? (ar ? "ما التغييرات المطلوبة؟ (يراها المستقل)" : "What needs to change? (freelancer will see this)")
                        : (ar ? "سبب الرفض (يراه المستقل)" : "Reason for rejection (freelancer will see this)")}
                    </label>
                    <textarea
                      value={gigModalText}
                      onChange={(e) => setGigModalText(e.target.value)}
                      rows={4}
                      placeholder={gigModalState.type === "revision"
                        ? (ar ? "مثال: يرجى تحسين وصف الخدمة وإضافة أمثلة عملية على العمل..." : "e.g. Please improve the description and add real work samples...")
                        : (ar ? "مثال: الخدمة تنتهك سياسة المنصة بسبب..." : "e.g. This gig violates platform policy because...")}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                    />
                    {gigModalText.trim().length < 10 && gigModalText.length > 0 && (
                      <p className="text-xs text-red-500 mt-1">
                        {ar ? "يجب أن يكون النص 10 أحرف على الأقل" : "Must be at least 10 characters"}
                      </p>
                    )}
                  </div>
                  <div className="flex gap-2 justify-end">
                    <button
                      onClick={() => { setGigModalState(null); setGigModalText(""); }}
                      className="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50"
                    >
                      {ar ? "إلغاء" : "Cancel"}
                    </button>
                    <button
                      onClick={handleGigModalSubmit}
                      disabled={gigModalText.trim().length < 10 || gigActionLoading !== null}
                      className={`px-4 py-2 text-sm font-medium text-white rounded-lg disabled:opacity-50 transition ${
                        gigModalState.type === "revision" ? "bg-blue-600 hover:bg-blue-700" : "bg-red-600 hover:bg-red-700"
                      }`}
                    >
                      {gigActionLoading ? "..." : gigModalState.type === "revision"
                        ? (ar ? "إرسال طلب التعديل" : "Send Revision Request")
                        : (ar ? "رفض الخدمة" : "Reject Gig")}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Transactions Tab */}
        {tab === "transactions" && (
          <div className="space-y-4">
            <div className="flex gap-3 flex-wrap">
              <select value={txTypeFilter} onChange={(e) => setTxTypeFilter(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
                <option value="">{ar ? "كل الأنواع" : "All Types"}</option>
                <option value="escrow_fund">{ar ? "تمويل ضمان" : "Escrow Fund"}</option>
                <option value="escrow_release">{ar ? "تحرير ضمان" : "Escrow Release"}</option>
                <option value="escrow_refund">{ar ? "استرداد ضمان" : "Escrow Refund"}</option>
                <option value="platform_fee">{ar ? "عمولة المنصة" : "Platform Fee"}</option>
                <option value="payout">{ar ? "سحب" : "Payout"}</option>
              </select>
              <select value={txStatusFilter} onChange={(e) => setTxStatusFilter(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
                <option value="">{ar ? "كل الحالات" : "All Statuses"}</option>
                <option value="pending">{ar ? "معلق" : "Pending"}</option>
                <option value="processing">{ar ? "جارٍ" : "Processing"}</option>
                <option value="completed">{ar ? "مكتمل" : "Completed"}</option>
                <option value="failed">{ar ? "فشل" : "Failed"}</option>
                <option value="refunded">{ar ? "مسترد" : "Refunded"}</option>
              </select>
              <button onClick={fetchTransactions} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">
                {ar ? "تصفية" : "Filter"}
              </button>
            </div>

            <div className="bg-white rounded-lg border overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="text-start p-3 font-medium text-gray-600">{ar ? "النوع" : "Type"}</th>
                    <th className="text-start p-3 font-medium text-gray-600">{ar ? "المبلغ" : "Amount"}</th>
                    <th className="text-start p-3 font-medium text-gray-600">{ar ? "العمولة" : "Fee"}</th>
                    <th className="text-start p-3 font-medium text-gray-600">{ar ? "الصافي" : "Net"}</th>
                    <th className="text-start p-3 font-medium text-gray-600">{ar ? "الحالة" : "Status"}</th>
                    <th className="text-start p-3 font-medium text-gray-600">{ar ? "الوصف" : "Description"}</th>
                    <th className="text-start p-3 font-medium text-gray-600">{ar ? "التاريخ" : "Date"}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {transactions.map((tx) => (
                    <tr key={tx.id} className="hover:bg-gray-50">
                      <td className="p-3 text-gray-900">{TX_TYPE_LABELS[tx.transaction_type] ?? tx.transaction_type}</td>
                      <td className="p-3 font-medium" dir="ltr">{tx.amount.toLocaleString()} {tx.currency}</td>
                      <td className="p-3 text-gray-500" dir="ltr">{tx.platform_fee.toLocaleString()}</td>
                      <td className="p-3 text-green-700 font-medium" dir="ltr">{tx.net_amount.toLocaleString()}</td>
                      <td className="p-3">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          tx.status === "completed" ? "bg-green-50 text-green-700" :
                          tx.status === "pending" ? "bg-yellow-50 text-yellow-700" :
                          tx.status === "failed" ? "bg-red-50 text-red-700" :
                          "bg-gray-100 text-gray-500"
                        }`}>
                          {TX_STATUS_LABELS[tx.status] ?? tx.status}
                        </span>
                      </td>
                      <td className="p-3 text-gray-500 max-w-xs truncate">{tx.description || "—"}</td>
                      <td className="p-3 text-gray-500">
                        {new Date(tx.created_at).toLocaleDateString(dateLocale, { month: "short", day: "numeric" })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {transactions.length === 0 && !loading && (
                <div className="p-8 text-center text-gray-400">{ar ? "لا توجد معاملات" : "No transactions found"}</div>
              )}
            </div>
            <p className="text-sm text-gray-500">
              {ar ? `${txTotal} معاملة إجمالاً` : `${txTotal} transaction(s) total`}
            </p>
          </div>
        )}

        {/* Payouts Tab */}
        {tab === "payouts" && (
          <div className="space-y-4">
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-800">
              <strong>{ar ? "تعليمات:" : "Instructions:"}</strong>{" "}
              {ar
                ? "لكل صف أدناه، انتقل إلى لوحة Qi Card وأرسل المبلغ المُحدد إلى رقم هاتف Qi Card للمستقل. بعد إرسال الدفعة، اضغط «تأكيد الدفع» لتحديث السجل."
                : "For each row below, go to your Qi Card merchant portal and send the listed amount to the freelancer's Qi Card phone. After sending, click \"Confirm Payout\" to update the ledger."}
            </div>

            {loading ? (
              <div className="bg-white rounded-lg border p-12 text-center text-gray-400">
                {ar ? "جاري التحميل..." : "Loading..."}
              </div>
            ) : escrows.length === 0 ? (
              <div className="bg-white rounded-lg border p-12 text-center text-gray-400">
                {ar ? "لا توجد مدفوعات معلقة — كل العقود تمت تسويتها." : "No pending payouts — all contracts are settled."}
              </div>
            ) : (
              <div className="bg-white rounded-lg border overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="text-start p-3 font-medium text-gray-600">{ar ? "المستقل" : "Freelancer"}</th>
                      <th className="text-start p-3 font-medium text-gray-600">{ar ? "رقم Qi Card" : "Qi Card Phone"}</th>
                      <th className="text-start p-3 font-medium text-gray-600">{ar ? "المرحلة" : "Milestone"}</th>
                      <th className="text-start p-3 font-medium text-gray-600">{ar ? "المبلغ الكلي" : "Total"}</th>
                      <th className="text-start p-3 font-medium text-gray-600">{ar ? "عمولة المنصة" : "Platform Fee"}</th>
                      <th className="text-start p-3 font-medium text-gray-600">{ar ? "صافي للمستقل" : "Net to Freelancer"}</th>
                      <th className="text-start p-3 font-medium text-gray-600">{ar ? "تاريخ التمويل" : "Funded"}</th>
                      <th className="text-end p-3 font-medium text-gray-600">{ar ? "إجراء" : "Action"}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {escrows.map((escrow) => {
                      const isBusy = escrowActionLoading === escrow.escrow_id;
                      const qiPhone = escrow.freelancer.qi_card_phone || escrow.freelancer.phone;
                      return (
                        <tr key={escrow.escrow_id} className="hover:bg-gray-50">
                          <td className="p-3">
                            <div className="font-medium text-gray-900">{escrow.freelancer.username}</div>
                            <div className="text-xs text-gray-500">{escrow.freelancer.email}</div>
                          </td>
                          <td className="p-3">
                            {qiPhone ? (
                              <span className="font-mono text-gray-900 bg-yellow-50 border border-yellow-200 px-2 py-0.5 rounded text-xs" dir="ltr">
                                {qiPhone}
                              </span>
                            ) : (
                              <span className="text-red-500 text-xs">{ar ? "غير مسجل" : "Not registered"}</span>
                            )}
                          </td>
                          <td className="p-3 text-gray-700 max-w-[180px] truncate">{escrow.milestone_title}</td>
                          <td className="p-3 font-medium text-gray-900" dir="ltr">
                            {escrow.amount.toLocaleString(ar ? "ar-IQ" : "en-US")} {escrow.currency}
                          </td>
                          <td className="p-3 text-red-600" dir="ltr">
                            -{escrow.platform_fee.toLocaleString(ar ? "ar-IQ" : "en-US")} {escrow.currency}
                          </td>
                          <td className="p-3 font-bold text-green-700" dir="ltr">
                            {escrow.freelancer_amount.toLocaleString(ar ? "ar-IQ" : "en-US")} {escrow.currency}
                          </td>
                          <td className="p-3 text-gray-500 text-xs">
                            {escrow.funded_at
                              ? new Date(escrow.funded_at).toLocaleDateString(dateLocale, { month: "short", day: "numeric", year: "numeric" })
                              : "—"}
                          </td>
                          <td className="p-3">
                            <div className="flex justify-end">
                              <button
                                onClick={() => handleReleaseEscrow(escrow)}
                                disabled={isBusy}
                                className="px-3 py-1.5 text-xs font-medium bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 whitespace-nowrap"
                              >
                                {isBusy ? "..." : (ar ? "تأكيد الدفع" : "Confirm Payout")}
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            <p className="text-sm text-gray-500">
              {ar
                ? `${escrows.length} دفعة معلقة — إجمالي الصافي: ${escrows.reduce((s, e) => s + e.freelancer_amount, 0).toLocaleString("ar-IQ")} IQD`
                : `${escrows.length} pending payout(s) — total net: ${escrows.reduce((s, e) => s + e.freelancer_amount, 0).toLocaleString("en-US")} IQD`}
            </p>
          </div>
        )}

      </div>
    </div>
  );
}

function StatCard({ label, value, icon, isText = false }: {
  label: string; value: number | string; icon: string; isText?: boolean;
}) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <span className="text-2xl">{icon}</span>
      <div className={`mt-2 ${isText ? "text-lg" : "text-2xl"} font-bold text-gray-900`}>{value}</div>
      <div className="text-sm text-gray-500 mt-0.5">{label}</div>
    </div>
  );
}
