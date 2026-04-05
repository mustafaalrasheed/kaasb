"use client";

import { useState, useEffect, useCallback } from "react";
import { adminApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
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

const ROLE_LABELS: Record<string, string> = {
  client: "عميل",
  freelancer: "مستقل",
  admin: "مدير",
};

const USER_STATUS_LABELS: Record<string, string> = {
  active: "نشط",
  suspended: "موقوف",
  deactivated: "مُلغى",
  pending_verification: "قيد التحقق",
};

const JOB_STATUS_LABELS: Record<string, string> = {
  open: "مفتوح",
  in_progress: "جارٍ",
  completed: "مكتمل",
  closed: "مغلق",
  cancelled: "ملغى",
  draft: "مسودة",
};

const TX_TYPE_LABELS: Record<string, string> = {
  escrow_fund: "تمويل ضمان",
  escrow_release: "تحرير ضمان",
  escrow_refund: "استرداد ضمان",
  platform_fee: "عمولة المنصة",
  payout: "سحب",
};

const TX_STATUS_LABELS: Record<string, string> = {
  pending: "معلق",
  processing: "جارٍ",
  completed: "مكتمل",
  failed: "فشل",
  refunded: "مسترد",
};

export default function AdminPage() {
  const { user, isLoading: authLoading } = useAuthStore();
  const router = useRouter();
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

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.push("/auth/login");
      return;
    }
    if (!user.is_superuser) {
      toast.error("صلاحية المدير مطلوبة");
      router.push("/dashboard");
    }
  }, [user, authLoading, router]);

  const fetchStats = useCallback(async () => {
    try {
      setLoading(true);
      const res = await adminApi.getStats();
      setStats(res.data);
    } catch {
      toast.error("تعذّر تحميل الإحصاءات");
    } finally {
      setLoading(false);
    }
  }, []);

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
      toast.error("تعذّر تحميل المستخدمين");
    } finally {
      setLoading(false);
    }
  }, [userSearch, roleFilter]);

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
      toast.error("تعذّر تحميل الوظائف");
    } finally {
      setLoading(false);
    }
  }, [jobSearch, jobStatusFilter]);

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
      toast.error("تعذّر تحميل المعاملات");
    } finally {
      setLoading(false);
    }
  }, [txTypeFilter, txStatusFilter]);

  useEffect(() => {
    if (tab === "stats") fetchStats();
    if (tab === "users") fetchUsers();
    if (tab === "jobs") fetchJobs();
    if (tab === "transactions") fetchTransactions();
  }, [tab, fetchStats, fetchUsers, fetchJobs, fetchTransactions]);

  const handleStatusUpdate = async (userId: string, status: string) => {
    try {
      await adminApi.updateUserStatus(userId, { status });
      toast.success("تم تحديث حالة المستخدم");
      fetchUsers();
    } catch (err: unknown) {
      toast.error(getApiError(err, "تعذّر التحديث"));
    }
  };

  const handleToggleAdmin = async (userId: string) => {
    try {
      await adminApi.toggleAdmin(userId);
      toast.success("تم تغيير صلاحية المدير");
      fetchUsers();
    } catch (err: unknown) {
      toast.error(getApiError(err, "تعذّر تغيير الصلاحية"));
    }
  };

  if (authLoading || !user?.is_superuser) {
    return (
      <div className="p-6 text-center text-gray-500">
        {authLoading ? "جاري التحميل..." : "جاري التحقق من الصلاحية..."}
      </div>
    );
  }

  const TABS = [
    { value: "stats" as Tab, label: "📊 نظرة عامة" },
    { value: "users" as Tab, label: "👥 المستخدمون" },
    { value: "jobs" as Tab, label: "📋 الوظائف" },
    { value: "transactions" as Tab, label: "💳 المعاملات" },
  ];

  return (
    <div className="min-h-screen bg-gray-50" dir="rtl">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <h1 className="text-2xl font-bold text-gray-900">لوحة الإدارة</h1>
        <p className="text-sm text-gray-500 mt-1">إدارة منصة كاسب</p>
      </div>

      {/* Tabs */}
      <div className="bg-white border-b border-gray-200 px-6">
        <div className="flex gap-6">
          {TABS.map((t) => (
            <button
              key={t.value}
              onClick={() => setTab(t.value)}
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
        {/* Stats Tab */}
        {tab === "stats" && stats && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard label="إجمالي المستخدمين" value={stats.users.total} icon="👥" />
              <StatCard label="النشطون (30 يوم)" value={stats.users.active_30d} icon="🟢" />
              <StatCard label="الوظائف المفتوحة" value={stats.jobs.open} icon="📋" />
              <StatCard label="العقود النشطة" value={stats.contracts.active} icon="📝" />
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <StatCard label="إجمالي حجم التداول" value={`$${stats.financials.total_volume.toFixed(2)}`} icon="💰" isText />
              <StatCard label="عمولات المنصة" value={`$${stats.financials.platform_fees_earned.toFixed(2)}`} icon="🏦" isText />
              <StatCard label="في الضمان" value={`$${stats.financials.pending_escrow.toFixed(2)}`} icon="🔒" isText />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-white rounded-lg border p-4">
                <h3 className="font-semibold text-gray-900 mb-3">المستخدمون حسب الدور</h3>
                {Object.entries(stats.users.by_role).map(([role, count]) => (
                  <div key={role} className="flex justify-between text-sm py-1">
                    <span className="text-gray-600">{ROLE_LABELS[role] ?? role}</span>
                    <span className="font-medium">{count}</span>
                  </div>
                ))}
                <div className="flex justify-between text-sm py-1 border-t mt-2 pt-2">
                  <span className="text-gray-600">جدد (7 أيام)</span>
                  <span className="font-medium text-green-600">+{stats.users.new_7d}</span>
                </div>
              </div>

              <div className="bg-white rounded-lg border p-4">
                <h3 className="font-semibold text-gray-900 mb-3">السوق</h3>
                <div className="flex justify-between text-sm py-1">
                  <span className="text-gray-600">إجمالي الوظائف</span>
                  <span className="font-medium">{stats.jobs.total}</span>
                </div>
                <div className="flex justify-between text-sm py-1">
                  <span className="text-gray-600">إجمالي العروض</span>
                  <span className="font-medium">{stats.proposals.total}</span>
                </div>
                <div className="flex justify-between text-sm py-1">
                  <span className="text-gray-600">العقود المكتملة</span>
                  <span className="font-medium">{stats.contracts.completed}</span>
                </div>
                <div className="flex justify-between text-sm py-1">
                  <span className="text-gray-600">وظائف جديدة (7 أيام)</span>
                  <span className="font-medium text-green-600">+{stats.jobs.new_7d}</span>
                </div>
              </div>

              <div className="bg-white rounded-lg border p-4">
                <h3 className="font-semibold text-gray-900 mb-3">المجتمع</h3>
                <div className="flex justify-between text-sm py-1">
                  <span className="text-gray-600">التقييمات</span>
                  <span className="font-medium">{stats.reviews.total}</span>
                </div>
                <div className="flex justify-between text-sm py-1">
                  <span className="text-gray-600">متوسط التقييم</span>
                  <span className="font-medium">{stats.reviews.average_rating}★</span>
                </div>
                <div className="flex justify-between text-sm py-1">
                  <span className="text-gray-600">الرسائل</span>
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
              <input
                type="text"
                value={userSearch}
                onChange={(e) => setUserSearch(e.target.value)}
                placeholder="بحث عن مستخدم..."
                className="flex-1 min-w-[200px] border border-gray-300 rounded-lg px-4 py-2 text-sm"
                dir="rtl"
                onKeyDown={(e) => e.key === "Enter" && fetchUsers()}
              />
              <select
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
              >
                <option value="">كل الأدوار</option>
                <option value="client">عميل</option>
                <option value="freelancer">مستقل</option>
                <option value="admin">مدير</option>
              </select>
              <button
                onClick={fetchUsers}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
              >
                بحث
              </button>
            </div>

            <div className="bg-white rounded-lg border overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="text-right p-3 font-medium text-gray-600">المستخدم</th>
                    <th className="text-right p-3 font-medium text-gray-600">الدور</th>
                    <th className="text-right p-3 font-medium text-gray-600">الحالة</th>
                    <th className="text-right p-3 font-medium text-gray-600">التقييم</th>
                    <th className="text-right p-3 font-medium text-gray-600">تاريخ الانضمام</th>
                    <th className="text-left p-3 font-medium text-gray-600">الإجراءات</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {users.map((u) => (
                    <tr key={u.id} className="hover:bg-gray-50">
                      <td className="p-3">
                        <div className="font-medium text-gray-900">
                          {u.first_name} {u.last_name}
                          {u.is_superuser && (
                            <span className="mr-1 text-xs bg-red-100 text-red-600 px-1.5 py-0.5 rounded">
                              مدير
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-gray-500">{u.email}</div>
                      </td>
                      <td className="p-3 text-gray-600">
                        {ROLE_LABELS[u.primary_role] ?? u.primary_role}
                      </td>
                      <td className="p-3">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          u.status === "active" ? "bg-green-50 text-green-700" :
                          u.status === "suspended" ? "bg-red-50 text-red-700" :
                          "bg-gray-100 text-gray-500"
                        }`}>
                          {USER_STATUS_LABELS[u.status] ?? u.status}
                        </span>
                      </td>
                      <td className="p-3 text-gray-600">
                        {u.avg_rating > 0 ? `${u.avg_rating}★` : "—"}
                      </td>
                      <td className="p-3 text-gray-500">
                        {new Date(u.created_at).toLocaleDateString("ar-IQ", {
                          year: "numeric",
                          month: "short",
                          day: "numeric",
                        })}
                      </td>
                      <td className="p-3">
                        <div className="flex gap-1">
                          {u.status === "active" && !u.is_superuser && (
                            <button
                              onClick={() => handleStatusUpdate(u.id, "suspended")}
                              className="px-2 py-1 text-xs bg-red-50 text-red-600 rounded hover:bg-red-100"
                            >
                              إيقاف
                            </button>
                          )}
                          {u.status === "suspended" && (
                            <button
                              onClick={() => handleStatusUpdate(u.id, "active")}
                              className="px-2 py-1 text-xs bg-green-50 text-green-600 rounded hover:bg-green-100"
                            >
                              تفعيل
                            </button>
                          )}
                          {!u.is_superuser && (
                            <button
                              onClick={() => handleToggleAdmin(u.id)}
                              className="px-2 py-1 text-xs bg-blue-50 text-blue-600 rounded hover:bg-blue-100"
                            >
                              صلاحية مدير
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {users.length === 0 && !loading && (
                <div className="p-8 text-center text-gray-400">لا يوجد مستخدمون</div>
              )}
            </div>
            <p className="text-sm text-gray-500">{userTotal} مستخدم إجمالاً</p>
          </div>
        )}

        {/* Jobs Tab */}
        {tab === "jobs" && (
          <div className="space-y-4">
            <div className="flex gap-3 flex-wrap">
              <input
                type="text"
                value={jobSearch}
                onChange={(e) => setJobSearch(e.target.value)}
                placeholder="بحث عن وظيفة..."
                className="flex-1 min-w-[200px] border border-gray-300 rounded-lg px-4 py-2 text-sm"
                dir="rtl"
                onKeyDown={(e) => e.key === "Enter" && fetchJobs()}
              />
              <select
                value={jobStatusFilter}
                onChange={(e) => setJobStatusFilter(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
              >
                <option value="">كل الحالات</option>
                <option value="open">مفتوح</option>
                <option value="in_progress">جارٍ</option>
                <option value="completed">مكتمل</option>
                <option value="closed">مغلق</option>
                <option value="cancelled">ملغى</option>
              </select>
              <button
                onClick={fetchJobs}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
              >
                بحث
              </button>
            </div>

            <div className="bg-white rounded-lg border overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="text-right p-3 font-medium text-gray-600">العنوان</th>
                    <th className="text-right p-3 font-medium text-gray-600">النوع</th>
                    <th className="text-right p-3 font-medium text-gray-600">الميزانية</th>
                    <th className="text-right p-3 font-medium text-gray-600">الحالة</th>
                    <th className="text-right p-3 font-medium text-gray-600">العروض</th>
                    <th className="text-right p-3 font-medium text-gray-600">تاريخ النشر</th>
                    <th className="text-left p-3 font-medium text-gray-600">إجراءات</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {jobs.map((j) => (
                    <tr key={j.id} className="hover:bg-gray-50">
                      <td className="p-3 font-medium text-gray-900 max-w-xs truncate">
                        {j.title}
                      </td>
                      <td className="p-3 text-gray-600">
                        {j.job_type === "fixed" ? "ثابت" : "بالساعة"}
                      </td>
                      <td className="p-3 text-gray-600 text-xs" dir="ltr">
                        {j.budget_min != null && j.budget_max != null
                          ? `$${j.budget_min}–$${j.budget_max}`
                          : j.budget_min != null
                          ? `from $${j.budget_min}`
                          : "—"}
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
                        {new Date(j.created_at).toLocaleDateString("ar-IQ", {
                          month: "short",
                          day: "numeric",
                        })}
                      </td>
                      <td className="p-3">
                        {j.status === "open" && (
                          <button
                            onClick={async () => {
                              try {
                                await adminApi.updateJobStatus(j.id, { status: "closed" });
                                toast.success("تم إغلاق الوظيفة");
                                fetchJobs();
                              } catch {
                                toast.error("تعذّر إغلاق الوظيفة");
                              }
                            }}
                            className="px-2 py-1 text-xs bg-red-50 text-red-600 rounded hover:bg-red-100"
                          >
                            إغلاق
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {jobs.length === 0 && !loading && (
                <div className="p-8 text-center text-gray-400">لا توجد وظائف</div>
              )}
            </div>
            <p className="text-sm text-gray-500">{jobTotal} وظيفة إجمالاً</p>
          </div>
        )}

        {/* Transactions Tab */}
        {tab === "transactions" && (
          <div className="space-y-4">
            <div className="flex gap-3 flex-wrap">
              <select
                value={txTypeFilter}
                onChange={(e) => setTxTypeFilter(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
              >
                <option value="">كل الأنواع</option>
                <option value="escrow_fund">تمويل ضمان</option>
                <option value="escrow_release">تحرير ضمان</option>
                <option value="escrow_refund">استرداد ضمان</option>
                <option value="platform_fee">عمولة المنصة</option>
                <option value="payout">سحب</option>
              </select>
              <select
                value={txStatusFilter}
                onChange={(e) => setTxStatusFilter(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
              >
                <option value="">كل الحالات</option>
                <option value="pending">معلق</option>
                <option value="processing">جارٍ</option>
                <option value="completed">مكتمل</option>
                <option value="failed">فشل</option>
                <option value="refunded">مسترد</option>
              </select>
              <button
                onClick={fetchTransactions}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
              >
                تصفية
              </button>
            </div>

            <div className="bg-white rounded-lg border overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="text-right p-3 font-medium text-gray-600">النوع</th>
                    <th className="text-right p-3 font-medium text-gray-600">المبلغ</th>
                    <th className="text-right p-3 font-medium text-gray-600">العمولة</th>
                    <th className="text-right p-3 font-medium text-gray-600">الصافي</th>
                    <th className="text-right p-3 font-medium text-gray-600">الحالة</th>
                    <th className="text-right p-3 font-medium text-gray-600">الوصف</th>
                    <th className="text-right p-3 font-medium text-gray-600">التاريخ</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {transactions.map((tx) => (
                    <tr key={tx.id} className="hover:bg-gray-50">
                      <td className="p-3 text-gray-900">
                        {TX_TYPE_LABELS[tx.transaction_type] ?? tx.transaction_type}
                      </td>
                      <td className="p-3 font-medium" dir="ltr">
                        {tx.amount.toLocaleString()} {tx.currency}
                      </td>
                      <td className="p-3 text-gray-500" dir="ltr">
                        {tx.platform_fee.toLocaleString()}
                      </td>
                      <td className="p-3 text-green-700 font-medium" dir="ltr">
                        {tx.net_amount.toLocaleString()}
                      </td>
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
                      <td className="p-3 text-gray-500 max-w-xs truncate">
                        {tx.description || "—"}
                      </td>
                      <td className="p-3 text-gray-500">
                        {new Date(tx.created_at).toLocaleDateString("ar-IQ", {
                          month: "short",
                          day: "numeric",
                        })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {transactions.length === 0 && !loading && (
                <div className="p-8 text-center text-gray-400">لا توجد معاملات</div>
              )}
            </div>
            <p className="text-sm text-gray-500">{txTotal} معاملة إجمالاً</p>
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="text-gray-400">جاري التحميل...</div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  icon,
  isText = false,
}: {
  label: string;
  value: number | string;
  icon: string;
  isText?: boolean;
}) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <span className="text-2xl">{icon}</span>
      <div className={`mt-2 ${isText ? "text-lg" : "text-2xl"} font-bold text-gray-900`}>
        {value}
      </div>
      <div className="text-sm text-gray-500 mt-0.5">{label}</div>
    </div>
  );
}
