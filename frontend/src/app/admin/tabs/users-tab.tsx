"use client";

interface AdminUser {
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  primary_role: string;
  status: string;
  is_superuser: boolean;
  is_support?: boolean;
  avg_rating: number;
  total_reviews: number;
  total_earnings: number;
  jobs_completed: number;
  created_at: string;
  chat_violations?: number;
  chat_suspended_until?: string | null;
}

interface UsersTabProps {
  users: AdminUser[];
  total: number;
  loading: boolean;
  search: string;
  roleFilter: string;
  currentUserId: string | undefined;
  ar: boolean;
  dateLocale: string;
  onSearchChange: (v: string) => void;
  onRoleFilterChange: (v: string) => void;
  onSearch: () => void;
  onStatusUpdate: (userId: string, status: string) => void;
  onToggleAdmin: (userId: string, isCurrentlyAdmin: boolean) => void;
  onToggleSupport: (userId: string, isCurrentlySupport: boolean) => void;
  onUnsuspendChat: (userId: string) => void;
}

export function UsersTab({
  users, total, loading, search, roleFilter, currentUserId,
  ar, dateLocale,
  onSearchChange, onRoleFilterChange, onSearch,
  onStatusUpdate, onToggleAdmin, onToggleSupport, onUnsuspendChat,
}: UsersTabProps) {
  const now = Date.now();
  const isChatSuspended = (u: AdminUser) =>
    !!u.chat_suspended_until && new Date(u.chat_suspended_until).getTime() > now;
  const roleLabels: Record<string, string> = ar
    ? { client: "عميل", freelancer: "مستقل", admin: "مدير" }
    : { client: "Client", freelancer: "Freelancer", admin: "Admin" };

  const statusLabels: Record<string, string> = ar
    ? { active: "نشط", suspended: "موقوف", deactivated: "مُلغى", pending_verification: "قيد التحقق" }
    : { active: "Active", suspended: "Suspended", deactivated: "Deactivated", pending_verification: "Pending Verification" };

  return (
    <div className="space-y-4">
      <div className="flex gap-3 flex-wrap">
        <input
          type="text" value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder={ar ? "بحث عن مستخدم..." : "Search users..."}
          className="flex-1 min-w-[200px] border border-gray-300 rounded-lg px-4 py-2 text-sm"
          onKeyDown={(e) => e.key === "Enter" && onSearch()}
        />
        <select
          value={roleFilter} onChange={(e) => onRoleFilterChange(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
        >
          <option value="">{ar ? "كل الأدوار" : "All Roles"}</option>
          <option value="client">{ar ? "عميل" : "Client"}</option>
          <option value="freelancer">{ar ? "مستقل" : "Freelancer"}</option>
          <option value="admin">{ar ? "مدير" : "Admin"}</option>
        </select>
        <button onClick={onSearch} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">
          {ar ? "بحث" : "Search"}
        </button>
      </div>

      <div className="bg-white rounded-lg border overflow-x-auto">
        <table className="min-w-[650px] w-full text-sm">
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
                    {!u.is_superuser && u.is_support && (
                      <span className="ms-1 text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded">
                        {ar ? "دعم" : "Support"}
                      </span>
                    )}
                    {isChatSuspended(u) && (
                      <span
                        className="ms-1 text-xs bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded"
                        title={ar ? "الدردشة موقوفة مؤقتاً" : "Chat temporarily suspended"}
                      >
                        {ar ? "دردشة موقوفة" : "Chat Suspended"}
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-gray-500">{u.email}</div>
                </td>
                <td className="p-3 text-gray-600">{roleLabels[u.primary_role] ?? u.primary_role}</td>
                <td className="p-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    u.status === "active" ? "bg-green-50 text-green-700" :
                    u.status === "suspended" ? "bg-red-50 text-red-700" :
                    "bg-gray-100 text-gray-500"
                  }`}>
                    {statusLabels[u.status] ?? u.status}
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
                      <button
                        onClick={() => onStatusUpdate(u.id, "suspended")}
                        className="px-2 py-1 text-xs bg-red-50 text-red-600 rounded hover:bg-red-100"
                      >
                        {ar ? "إيقاف" : "Suspend"}
                      </button>
                    )}
                    {(u.status === "suspended" || u.status === "deactivated") && (
                      <button
                        onClick={() => onStatusUpdate(u.id, "active")}
                        className="px-2 py-1 text-xs bg-green-50 text-green-600 rounded hover:bg-green-100"
                      >
                        {ar ? "تفعيل" : "Activate"}
                      </button>
                    )}
                    {u.id !== currentUserId && !u.is_superuser && (
                      <button
                        onClick={() => onToggleAdmin(u.id, false)}
                        className="px-2 py-1 text-xs bg-blue-50 text-blue-600 rounded hover:bg-blue-100"
                      >
                        {ar ? "ترقية لمدير" : "Make Admin"}
                      </button>
                    )}
                    {u.id !== currentUserId && u.is_superuser && (
                      <button
                        onClick={() => onToggleAdmin(u.id, true)}
                        className="px-2 py-1 text-xs bg-orange-50 text-orange-600 rounded hover:bg-orange-100"
                      >
                        {ar ? "إلغاء صلاحية المدير" : "Revoke Admin"}
                      </button>
                    )}
                    {u.id !== currentUserId && !u.is_superuser && !u.is_support && (
                      <button
                        onClick={() => onToggleSupport(u.id, false)}
                        className="px-2 py-1 text-xs bg-purple-50 text-purple-700 rounded hover:bg-purple-100"
                      >
                        {ar ? "تعيين دعم" : "Make Support"}
                      </button>
                    )}
                    {u.id !== currentUserId && !u.is_superuser && u.is_support && (
                      <button
                        onClick={() => onToggleSupport(u.id, true)}
                        className="px-2 py-1 text-xs bg-orange-50 text-orange-600 rounded hover:bg-orange-100"
                      >
                        {ar ? "إلغاء صلاحية الدعم" : "Revoke Support"}
                      </button>
                    )}
                    {isChatSuspended(u) && (
                      <button
                        onClick={() => onUnsuspendChat(u.id)}
                        className="px-2 py-1 text-xs bg-amber-50 text-amber-700 rounded hover:bg-amber-100"
                        title={ar ? "رفع إيقاف الدردشة" : "Lift chat suspension"}
                      >
                        {ar ? "رفع إيقاف الدردشة" : "Unsuspend Chat"}
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
        {ar ? `${total} مستخدم إجمالاً` : `${total} user(s) total`}
      </p>
    </div>
  );
}
