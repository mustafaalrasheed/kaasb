"use client";

import { useState, useEffect, useCallback } from "react";
import { adminApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { useLocale } from "@/providers/locale-provider";
import { useRouter } from "next/navigation";
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

type Tab = "stats" | "users" | "jobs" | "transactions";

export default function AdminPage() {
  const { user, isLoading: authLoading } = useAuthStore();
  const router = useRouter();
  const { locale } = useLocale();
  const ar = locale === "ar";

  const [tab, setTab] = useState<Tab>("stats");
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
    { value: "transactions" as Tab, label: ar ? "💳 المعاملات" : "💳 Transactions" },
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
      if (txTypeFilter) params.transaction_type = txTypeFilter;
      if (txStatusFilter) params.status = txStatusFilter;
      const res = await adminApi.getTransactions(params);
      setTransactions(res.data.transactions);
      setTxTotal(res.data.total);
    } catch {
      toast.error(ar ? "تعذّر تحميل المعاملات" : "Failed to load transactions");
    } finally { setLoading(false); }
  }, [txTypeFilter, txStatusFilter, ar]);

  useEffect(() => {
    if (tab === "stats") fetchStats();
    if (tab === "users") fetchUsers();
    if (tab === "jobs") fetchJobs();
    if (tab === "transactions") fetchTransactions();
  }, [tab, fetchStats, fetchUsers, fetchJobs, fetchTransactions]);

  const handleStatusUpdate = async (userId: string, status: string) => {
    try {
      await adminApi.updateUserStatus(userId, { status });
      toast.success(ar ? "تم تحديث حالة المستخدم" : "User status updated");
      fetchUsers();
    } catch (err: unknown) {
      toast.error(getApiError(err, ar ? "تعذّر التحديث" : "Failed to update"));
    }
  };

  const handleToggleAdmin = async (userId: string) => {
    try {
      await adminApi.toggleAdmin(userId);
      toast.success(ar ? "تم تغيير صلاحية المدير" : "Admin role toggled");
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
              onClick={() => setTab(t.value)}
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
              <StatCard label={ar ? "إجمالي حجم التداول" : "Total Volume"} value={`$${stats.financials.total_volume.toFixed(2)}`} icon="💰" isText />
              <StatCard label={ar ? "عمولات المنصة" : "Platform Fees"} value={`$${stats.financials.platform_fees_earned.toFixed(2)}`} icon="🏦" isText />
              <StatCard label={ar ? "في الضمان" : "In Escrow"} value={`$${stats.financials.pending_escrow.toFixed(2)}`} icon="🔒" isText />
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
                          {!u.is_superuser && (
                            <button onClick={() => handleToggleAdmin(u.id)}
                              className="px-2 py-1 text-xs bg-blue-50 text-blue-600 rounded hover:bg-blue-100">
                              {ar ? "صلاحية مدير" : "Toggle Admin"}
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
                          ? `$${j.budget_min}–$${j.budget_max}`
                          : j.budget_min != null ? `from $${j.budget_min}` : "—"}
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

        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="text-gray-400">{ar ? "جاري التحميل..." : "Loading..."}</div>
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
