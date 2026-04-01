"use client";

import { useState, useEffect, useCallback } from "react";
import { adminApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

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

  // Check admin access — wait for auth to initialize first
  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.push("/auth/login");
      return;
    }
    if (!user.is_superuser) {
      toast.error("Admin access required");
      router.push("/dashboard");
    }
  }, [user, authLoading, router]);

  const fetchStats = useCallback(async () => {
    try {
      setLoading(true);
      const res = await adminApi.getStats();
      setStats(res.data);
    } catch {
      toast.error("Failed to load stats");
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
      toast.error("Failed to load users");
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
      toast.error("Failed to load jobs");
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
      toast.error("Failed to load transactions");
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
      toast.success(`User status updated to ${status}`);
      fetchUsers();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to update");
    }
  };

  const handleToggleAdmin = async (userId: string) => {
    try {
      await adminApi.toggleAdmin(userId);
      toast.success("Admin status toggled");
      fetchUsers();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to toggle admin");
    }
  };

  if (authLoading || !user?.is_superuser) {
    return (
      <div className="p-6 text-center text-gray-500">
        {authLoading ? "Loading..." : "Checking admin access..."}
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">Kaasb Platform Administration</p>
      </div>

      {/* Tabs */}
      <div className="bg-white border-b border-gray-200 px-6">
        <div className="flex gap-6">
          {(["stats", "users", "jobs", "transactions"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`py-3 text-sm font-medium border-b-2 transition ${
                tab === t
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {t === "stats" ? "📊 Overview" : t === "users" ? "👥 Users" : t === "jobs" ? "📋 Jobs" : "💳 Transactions"}
            </button>
          ))}
        </div>
      </div>

      <div className="p-6 max-w-7xl mx-auto">
        {/* Stats Tab */}
        {tab === "stats" && stats && (
          <div className="space-y-6">
            {/* Top row: key metrics */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard label="Total Users" value={stats.users.total} icon="👥" />
              <StatCard label="Active (30d)" value={stats.users.active_30d} icon="🟢" />
              <StatCard label="Open Jobs" value={stats.jobs.open} icon="📋" />
              <StatCard label="Active Contracts" value={stats.contracts.active} icon="📝" />
            </div>

            {/* Financial row */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <StatCard label="Total Volume" value={`$${stats.financials.total_volume.toFixed(2)}`} icon="💰" isText />
              <StatCard label="Platform Fees" value={`$${stats.financials.platform_fees_earned.toFixed(2)}`} icon="🏦" isText />
              <StatCard label="In Escrow" value={`$${stats.financials.pending_escrow.toFixed(2)}`} icon="🔒" isText />
            </div>

            {/* Details grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-white rounded-lg border p-4">
                <h3 className="font-semibold text-gray-900 mb-3">Users by Role</h3>
                {Object.entries(stats.users.by_role).map(([role, count]) => (
                  <div key={role} className="flex justify-between text-sm py-1">
                    <span className="text-gray-600 capitalize">{role}</span>
                    <span className="font-medium">{count}</span>
                  </div>
                ))}
                <div className="flex justify-between text-sm py-1 border-t mt-2 pt-2">
                  <span className="text-gray-600">New (7d)</span>
                  <span className="font-medium text-green-600">+{stats.users.new_7d}</span>
                </div>
              </div>

              <div className="bg-white rounded-lg border p-4">
                <h3 className="font-semibold text-gray-900 mb-3">Marketplace</h3>
                <div className="flex justify-between text-sm py-1">
                  <span className="text-gray-600">Total Jobs</span>
                  <span className="font-medium">{stats.jobs.total}</span>
                </div>
                <div className="flex justify-between text-sm py-1">
                  <span className="text-gray-600">Total Proposals</span>
                  <span className="font-medium">{stats.proposals.total}</span>
                </div>
                <div className="flex justify-between text-sm py-1">
                  <span className="text-gray-600">Completed Contracts</span>
                  <span className="font-medium">{stats.contracts.completed}</span>
                </div>
                <div className="flex justify-between text-sm py-1">
                  <span className="text-gray-600">New Jobs (7d)</span>
                  <span className="font-medium text-green-600">+{stats.jobs.new_7d}</span>
                </div>
              </div>

              <div className="bg-white rounded-lg border p-4">
                <h3 className="font-semibold text-gray-900 mb-3">Community</h3>
                <div className="flex justify-between text-sm py-1">
                  <span className="text-gray-600">Reviews</span>
                  <span className="font-medium">{stats.reviews.total}</span>
                </div>
                <div className="flex justify-between text-sm py-1">
                  <span className="text-gray-600">Avg Rating</span>
                  <span className="font-medium">{stats.reviews.average_rating}★</span>
                </div>
                <div className="flex justify-between text-sm py-1">
                  <span className="text-gray-600">Messages</span>
                  <span className="font-medium">{stats.messages.total}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Users Tab */}
        {tab === "users" && (
          <div className="space-y-4">
            <div className="flex gap-3">
              <input
                type="text"
                value={userSearch}
                onChange={(e) => setUserSearch(e.target.value)}
                placeholder="Search users..."
                className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm"
              />
              <select
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
              >
                <option value="">All roles</option>
                <option value="client">Client</option>
                <option value="freelancer">Freelancer</option>
                <option value="admin">Admin</option>
              </select>
              <button
                onClick={fetchUsers}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
              >
                Search
              </button>
            </div>

            <div className="bg-white rounded-lg border overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="text-left p-3 font-medium text-gray-600">User</th>
                    <th className="text-left p-3 font-medium text-gray-600">Role</th>
                    <th className="text-left p-3 font-medium text-gray-600">Status</th>
                    <th className="text-left p-3 font-medium text-gray-600">Rating</th>
                    <th className="text-left p-3 font-medium text-gray-600">Joined</th>
                    <th className="text-right p-3 font-medium text-gray-600">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {users.map((u) => (
                    <tr key={u.id} className="hover:bg-gray-50">
                      <td className="p-3">
                        <div className="font-medium text-gray-900">
                          {u.first_name} {u.last_name}
                          {u.is_superuser && <span className="ml-1 text-xs bg-red-100 text-red-600 px-1.5 py-0.5 rounded">Admin</span>}
                        </div>
                        <div className="text-xs text-gray-500">{u.email}</div>
                      </td>
                      <td className="p-3 capitalize">{u.primary_role}</td>
                      <td className="p-3">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          u.status === "active" ? "bg-green-50 text-green-700" :
                          u.status === "suspended" ? "bg-red-50 text-red-700" :
                          "bg-gray-100 text-gray-500"
                        }`}>
                          {u.status}
                        </span>
                      </td>
                      <td className="p-3">{u.avg_rating > 0 ? `${u.avg_rating}★` : "—"}</td>
                      <td className="p-3 text-gray-500">
                        {new Date(u.created_at).toLocaleDateString()}
                      </td>
                      <td className="p-3 text-right">
                        <div className="flex gap-1 justify-end">
                          {u.status === "active" && !u.is_superuser && (
                            <button
                              onClick={() => handleStatusUpdate(u.id, "suspended")}
                              className="px-2 py-1 text-xs bg-red-50 text-red-600 rounded hover:bg-red-100"
                            >
                              Suspend
                            </button>
                          )}
                          {u.status === "suspended" && (
                            <button
                              onClick={() => handleStatusUpdate(u.id, "active")}
                              className="px-2 py-1 text-xs bg-green-50 text-green-600 rounded hover:bg-green-100"
                            >
                              Activate
                            </button>
                          )}
                          {!u.is_superuser && (
                            <button
                              onClick={() => handleToggleAdmin(u.id)}
                              className="px-2 py-1 text-xs bg-blue-50 text-blue-600 rounded hover:bg-blue-100"
                            >
                              Make Admin
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {users.length === 0 && (
                <div className="p-8 text-center text-gray-400">No users found</div>
              )}
            </div>
            <p className="text-sm text-gray-500">{userTotal} total users</p>
          </div>
        )}

        {/* Jobs Tab */}
        {tab === "jobs" && (
          <div className="space-y-4">
            <div className="flex gap-3">
              <input
                type="text"
                value={jobSearch}
                onChange={(e) => setJobSearch(e.target.value)}
                placeholder="Search jobs..."
                className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm"
              />
              <select
                value={jobStatusFilter}
                onChange={(e) => setJobStatusFilter(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
              >
                <option value="">All statuses</option>
                <option value="open">Open</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
                <option value="closed">Closed</option>
                <option value="cancelled">Cancelled</option>
              </select>
              <button
                onClick={fetchJobs}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
              >
                Search
              </button>
            </div>

            <div className="bg-white rounded-lg border overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="text-left p-3 font-medium text-gray-600">Title</th>
                    <th className="text-left p-3 font-medium text-gray-600">Type</th>
                    <th className="text-left p-3 font-medium text-gray-600">Budget</th>
                    <th className="text-left p-3 font-medium text-gray-600">Status</th>
                    <th className="text-left p-3 font-medium text-gray-600">Proposals</th>
                    <th className="text-left p-3 font-medium text-gray-600">Posted</th>
                    <th className="text-right p-3 font-medium text-gray-600">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {jobs.map((j) => (
                    <tr key={j.id} className="hover:bg-gray-50">
                      <td className="p-3 font-medium text-gray-900 max-w-xs truncate">{j.title}</td>
                      <td className="p-3 capitalize text-gray-600">{j.job_type.toLowerCase()}</td>
                      <td className="p-3 text-gray-600 text-xs">
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
                          {j.status}
                        </span>
                      </td>
                      <td className="p-3 text-gray-600">{j.proposal_count}</td>
                      <td className="p-3 text-gray-500">{new Date(j.created_at).toLocaleDateString()}</td>
                      <td className="p-3 text-right">
                        <div className="flex gap-1 justify-end">
                          {j.status === "open" && (
                            <button
                              onClick={async () => {
                                try {
                                  await adminApi.updateJobStatus(j.id, { status: "closed" });
                                  toast.success("Job closed");
                                  fetchJobs();
                                } catch {
                                  toast.error("Failed to close job");
                                }
                              }}
                              className="px-2 py-1 text-xs bg-red-50 text-red-600 rounded hover:bg-red-100"
                            >
                              Close
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {jobs.length === 0 && !loading && (
                <div className="p-8 text-center text-gray-400">No jobs found</div>
              )}
            </div>
            <p className="text-sm text-gray-500">{jobTotal} total jobs</p>
          </div>
        )}

        {/* Transactions Tab */}
        {tab === "transactions" && (
          <div className="space-y-4">
            <div className="flex gap-3">
              <select
                value={txTypeFilter}
                onChange={(e) => setTxTypeFilter(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
              >
                <option value="">All types</option>
                <option value="escrow_fund">Escrow Fund</option>
                <option value="escrow_release">Escrow Release</option>
                <option value="escrow_refund">Escrow Refund</option>
                <option value="platform_fee">Platform Fee</option>
                <option value="payout">Payout</option>
              </select>
              <select
                value={txStatusFilter}
                onChange={(e) => setTxStatusFilter(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
              >
                <option value="">All statuses</option>
                <option value="pending">Pending</option>
                <option value="processing">Processing</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
                <option value="refunded">Refunded</option>
              </select>
              <button
                onClick={fetchTransactions}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
              >
                Filter
              </button>
            </div>

            <div className="bg-white rounded-lg border overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="text-left p-3 font-medium text-gray-600">Type</th>
                    <th className="text-left p-3 font-medium text-gray-600">Amount</th>
                    <th className="text-left p-3 font-medium text-gray-600">Fee</th>
                    <th className="text-left p-3 font-medium text-gray-600">Net</th>
                    <th className="text-left p-3 font-medium text-gray-600">Status</th>
                    <th className="text-left p-3 font-medium text-gray-600">Description</th>
                    <th className="text-left p-3 font-medium text-gray-600">Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {transactions.map((tx) => (
                    <tr key={tx.id} className="hover:bg-gray-50">
                      <td className="p-3 capitalize text-gray-900">
                        {tx.transaction_type.replace(/_/g, " ")}
                      </td>
                      <td className="p-3 font-medium">
                        {tx.amount.toLocaleString()} {tx.currency}
                      </td>
                      <td className="p-3 text-gray-500">{tx.platform_fee.toLocaleString()}</td>
                      <td className="p-3 text-green-700 font-medium">{tx.net_amount.toLocaleString()}</td>
                      <td className="p-3">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          tx.status === "completed" ? "bg-green-50 text-green-700" :
                          tx.status === "pending" ? "bg-yellow-50 text-yellow-700" :
                          tx.status === "failed" ? "bg-red-50 text-red-700" :
                          "bg-gray-100 text-gray-500"
                        }`}>
                          {tx.status}
                        </span>
                      </td>
                      <td className="p-3 text-gray-500 max-w-xs truncate">{tx.description || "—"}</td>
                      <td className="p-3 text-gray-500">{new Date(tx.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {transactions.length === 0 && !loading && (
                <div className="p-8 text-center text-gray-400">No transactions found</div>
              )}
            </div>
            <p className="text-sm text-gray-500">{txTotal} total transactions</p>
          </div>
        )}

        {loading && !stats && (
          <div className="flex items-center justify-center py-12">
            <div className="text-gray-400">Loading...</div>
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
      <div className="flex items-center justify-between">
        <span className="text-2xl">{icon}</span>
      </div>
      <div className={`mt-2 ${isText ? "text-lg" : "text-2xl"} font-bold text-gray-900`}>
        {value}
      </div>
      <div className="text-sm text-gray-500">{label}</div>
    </div>
  );
}
