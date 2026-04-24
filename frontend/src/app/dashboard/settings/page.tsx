"use client";

import { useEffect, useState } from "react";
import { usersApi, authApi } from "@/lib/api";
import type { Session } from "@/lib/api/auth";
import { useAuthStore } from "@/lib/auth-store";
import { useLocale } from "@/providers/locale-provider";
import { toast } from "sonner";
import { getApiError } from "@/lib/utils";

export default function SettingsPage() {
  const { logout } = useAuthStore();
  const { locale } = useLocale();
  const ar = locale === "ar";

  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [showDeactivate, setShowDeactivate] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [sessions, setSessions] = useState<Session[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [revokingId, setRevokingId] = useState<string | null>(null);
  // Email-notification preference: null until loaded so we don't flash
  // a default-checked toggle and then flip it after the GET resolves.
  const [emailPref, setEmailPref] = useState<boolean | null>(null);
  const [savingEmailPref, setSavingEmailPref] = useState(false);

  const loadSessions = async () => {
    try {
      const res = await authApi.listSessions();
      const data = (res.data as unknown as { data?: Session[] })?.data ?? (res.data as Session[]);
      setSessions(Array.isArray(data) ? data : []);
    } catch {
      // Silent — sessions section simply stays empty
    } finally {
      setSessionsLoading(false);
    }
  };

  useEffect(() => {
    loadSessions();
    usersApi
      .getEmailPreferences()
      .then((res) => setEmailPref(Boolean(res.data?.email_notifications_enabled)))
      .catch(() => setEmailPref(true)); // fail-open: server default is true
  }, []);

  const handleToggleEmailPref = async (next: boolean) => {
    // Optimistic flip so the toggle is instantly responsive. Revert on
    // API failure and surface a toast.
    setEmailPref(next);
    setSavingEmailPref(true);
    try {
      await usersApi.updateEmailPreferences(next);
    } catch (err) {
      setEmailPref(!next);
      toast.error(getApiError(err, ar ? "تعذّر حفظ التفضيل" : "Failed to save preference"));
    } finally {
      setSavingEmailPref(false);
    }
  };

  const handleRevokeSession = async (id: string) => {
    setRevokingId(id);
    try {
      await authApi.revokeSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      toast.success(ar ? "تم إنهاء الجلسة" : "Session revoked");
    } catch (err: unknown) {
      toast.error(getApiError(err, ar ? "تعذّر إنهاء الجلسة" : "Failed to revoke session"));
    } finally {
      setRevokingId(null);
    }
  };

  const [revokingOthers, setRevokingOthers] = useState(false);
  const handleRevokeOtherSessions = async () => {
    const confirmMsg = ar
      ? "سيتم تسجيل خروجك من جميع الأجهزة الأخرى. الجهاز الحالي سيبقى مسجّلاً. هل أنت متأكد؟"
      : "All other devices will be signed out. This device stays signed in. Continue?";
    if (!window.confirm(confirmMsg)) return;
    setRevokingOthers(true);
    try {
      const res = await authApi.revokeOtherSessions();
      const count = (res.data as { revoked?: number })?.revoked ?? 0;
      setSessions((prev) => prev.filter((s) => s.is_current));
      toast.success(
        ar
          ? `تم إنهاء ${count} جلسة`
          : `${count} session${count === 1 ? "" : "s"} revoked`
      );
    } catch (err: unknown) {
      toast.error(getApiError(err, ar ? "تعذّر إنهاء الجلسات" : "Failed to revoke sessions"));
    } finally {
      setRevokingOthers(false);
    }
  };

  const describeDevice = (ua: string | null) => {
    if (!ua) return ar ? "جهاز غير معروف" : "Unknown device";
    const u = ua.toLowerCase();
    let os = ar ? "جهاز" : "Device";
    if (u.includes("windows")) os = "Windows";
    else if (u.includes("mac os") || u.includes("macintosh")) os = "macOS";
    else if (u.includes("android")) os = "Android";
    else if (u.includes("iphone") || u.includes("ios")) os = "iOS";
    else if (u.includes("linux")) os = "Linux";
    let browser = "";
    if (u.includes("edg/")) browser = "Edge";
    else if (u.includes("chrome")) browser = "Chrome";
    else if (u.includes("firefox")) browser = "Firefox";
    else if (u.includes("safari")) browser = "Safari";
    return browser ? `${browser} · ${os}` : os;
  };

  const formatWhen = (iso: string | null) => {
    if (!iso) return "—";
    try {
      return new Date(iso).toLocaleString(ar ? "ar-IQ" : "en-US", {
        dateStyle: "medium",
        timeStyle: "short",
      });
    } catch {
      return iso;
    }
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      toast.error(ar ? "كلمتا المرور غير متطابقتين" : "Passwords do not match");
      return;
    }
    setIsChangingPassword(true);
    try {
      await usersApi.changePassword({
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password,
      });
      toast.success(ar ? "تم تغيير كلمة المرور بنجاح" : "Password changed successfully");
      setPasswordForm({ current_password: "", new_password: "", confirm_password: "" });
    } catch (err: unknown) {
      toast.error(getApiError(err, ar ? "تعذّر تغيير كلمة المرور" : "Failed to change password"));
    } finally {
      setIsChangingPassword(false);
    }
  };

  const handleDeactivate = async () => {
    if (confirmText !== "DEACTIVATE") return;
    try {
      await usersApi.deactivateAccount();
      toast.success(ar ? "تم إلغاء تفعيل الحساب" : "Account deactivated");
      logout();
    } catch {
      toast.error(ar ? "تعذّر إلغاء تفعيل الحساب" : "Failed to deactivate account");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          {ar ? "الإعدادات" : "Settings"}
        </h1>
        <p className="mt-1 text-gray-600">
          {ar ? "إدارة إعدادات حسابك والأمان." : "Manage your account settings and security."}
        </p>
      </div>

      {/* Email notifications */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">
          {ar ? "إشعارات البريد الإلكتروني" : "Email Notifications"}
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          {ar
            ? "تلقّي بريد إلكتروني للإشعارات المهمة (قبول العروض، تحرير الدفع، إغلاق النزاع، إلخ). إشعارات التطبيق تعمل دائماً."
            : "Receive email for important notifications (offer accepted, payment released, dispute resolved, etc). In-app notifications always stay on."}
        </p>
        <label className="inline-flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            className="h-5 w-5 rounded border-gray-300 text-primary-600 focus:ring-primary-500 disabled:opacity-50"
            checked={emailPref ?? true}
            disabled={emailPref === null || savingEmailPref}
            onChange={(e) => handleToggleEmailPref(e.target.checked)}
          />
          <span className="text-sm font-medium text-gray-900">
            {emailPref === null
              ? (ar ? "جارٍ التحميل..." : "Loading...")
              : (ar ? "تفعيل إشعارات البريد الإلكتروني" : "Enable email notifications")}
          </span>
        </label>
      </div>

      {/* Change Password */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          {ar ? "تغيير كلمة المرور" : "Change Password"}
        </h2>
        <form onSubmit={handlePasswordChange} className="space-y-4 max-w-md">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {ar ? "كلمة المرور الحالية" : "Current Password"}
            </label>
            <input
              type="password"
              value={passwordForm.current_password}
              onChange={(e) => setPasswordForm({ ...passwordForm, current_password: e.target.value })}
              className="input-field"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {ar ? "كلمة المرور الجديدة" : "New Password"}
            </label>
            <input
              type="password"
              value={passwordForm.new_password}
              onChange={(e) => setPasswordForm({ ...passwordForm, new_password: e.target.value })}
              className="input-field"
              minLength={8}
              required
            />
            <p className="mt-1 text-xs text-gray-500">
              {ar
                ? "8 أحرف على الأقل مع حرف كبير ورقم وحرف خاص"
                : "Min 8 characters with an uppercase letter, number and special character"}
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {ar ? "تأكيد كلمة المرور الجديدة" : "Confirm New Password"}
            </label>
            <input
              type="password"
              value={passwordForm.confirm_password}
              onChange={(e) => setPasswordForm({ ...passwordForm, confirm_password: e.target.value })}
              className="input-field"
              minLength={8}
              required
            />
          </div>
          <button type="submit" disabled={isChangingPassword} className="btn-primary py-2 px-6 text-sm">
            {isChangingPassword
              ? (ar ? "جاري التغيير..." : "Changing...")
              : (ar ? "تغيير كلمة المرور" : "Change Password")}
          </button>
        </form>
      </div>

      {/* Active Sessions */}
      <div className="card p-6">
        <div className="flex items-start justify-between mb-4 gap-4">
          <div className="flex-1 min-w-0">
            <h2 className="text-lg font-semibold text-gray-900">
              {ar ? "الجلسات النشطة" : "Active Sessions"}
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              {ar
                ? "الأجهزة التي سجّلت الدخول من حسابك. يمكنك إنهاء أي جلسة لا تعرفها."
                : "Devices currently signed in to your account. Revoke any you don't recognize."}
            </p>
          </div>
          {sessions.length > 1 && (
            <button
              onClick={handleRevokeOtherSessions}
              disabled={revokingOthers}
              className="text-sm font-medium text-danger-600 hover:text-danger-700 whitespace-nowrap"
            >
              {revokingOthers
                ? (ar ? "جاري..." : "Revoking...")
                : (ar ? "إنهاء جميع الجلسات الأخرى" : "Sign out of all other devices")}
            </button>
          )}
        </div>

        {sessionsLoading ? (
          <p className="text-sm text-gray-500">{ar ? "جاري التحميل..." : "Loading..."}</p>
        ) : sessions.length === 0 ? (
          <p className="text-sm text-gray-500">{ar ? "لا توجد جلسات نشطة." : "No active sessions."}</p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {sessions.map((s) => (
              <li key={s.id} className="py-3 flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-gray-900 text-sm">{describeDevice(s.user_agent)}</span>
                    {s.is_current && (
                      <span className="text-[10px] uppercase tracking-wider font-semibold bg-green-50 text-green-700 px-2 py-0.5 rounded">
                        {ar ? "الجلسة الحالية" : "This device"}
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-gray-500 mt-1 truncate">
                    {s.ip_address ? `${s.ip_address} · ` : ""}
                    {ar ? "آخر استخدام" : "Last used"}: {formatWhen(s.last_used_at || s.created_at)}
                  </div>
                </div>
                {!s.is_current && (
                  <button
                    onClick={() => handleRevokeSession(s.id)}
                    disabled={revokingId === s.id}
                    className="text-sm text-danger-600 hover:text-danger-700 font-medium whitespace-nowrap"
                  >
                    {revokingId === s.id
                      ? (ar ? "جاري..." : "Revoking...")
                      : (ar ? "إنهاء الجلسة" : "Sign out")}
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Danger Zone */}
      <div className="card p-6 border border-danger-500/20">
        <h2 className="text-lg font-semibold text-danger-700 mb-2">
          {ar ? "منطقة الخطر" : "Danger Zone"}
        </h2>
        <p className="text-sm text-gray-600 mb-4">
          {ar
            ? "سيؤدي إلغاء تفعيل حسابك إلى إخفاء ملفك الشخصي وإلغاء أي عقود نشطة. يمكن التراجع عن هذا الإجراء بالتواصل مع الدعم."
            : "Deactivating your account will hide your profile and cancel any active contracts. This can be reversed by contacting support."}
        </p>

        {!showDeactivate ? (
          <button onClick={() => setShowDeactivate(true)} className="btn-danger py-2 px-5 text-sm">
            {ar ? "إلغاء تفعيل الحساب" : "Deactivate Account"}
          </button>
        ) : (
          <div className="p-4 bg-danger-50 rounded-lg space-y-3">
            <p className="text-sm font-medium text-danger-700">
              {ar ? (
                <>اكتب <strong>DEACTIVATE</strong> للتأكيد:</>
              ) : (
                <>Type <strong>DEACTIVATE</strong> to confirm:</>
              )}
            </p>
            <input
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              className="input-field max-w-xs"
              placeholder="DEACTIVATE"
              dir="ltr"
            />
            <div className="flex gap-3">
              <button
                onClick={handleDeactivate}
                disabled={confirmText !== "DEACTIVATE"}
                className="btn-danger py-2 px-5 text-sm"
              >
                {ar ? "تأكيد الإلغاء" : "Confirm Deactivation"}
              </button>
              <button
                onClick={() => { setShowDeactivate(false); setConfirmText(""); }}
                className="btn-secondary py-2 px-5 text-sm"
              >
                {ar ? "إلغاء" : "Cancel"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
