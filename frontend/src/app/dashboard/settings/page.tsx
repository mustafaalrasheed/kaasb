"use client";

import { useState } from "react";
import { usersApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { toast } from "sonner";
import { getApiError } from "@/lib/utils";

export default function SettingsPage() {
  const { logout } = useAuthStore();

  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [showDeactivate, setShowDeactivate] = useState(false);
  const [confirmText, setConfirmText] = useState("");

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();

    if (passwordForm.new_password !== passwordForm.confirm_password) {
      toast.error("كلمتا المرور غير متطابقتين");
      return;
    }

    setIsChangingPassword(true);
    try {
      await usersApi.changePassword({
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password,
      });
      toast.success("تم تغيير كلمة المرور بنجاح");
      setPasswordForm({ current_password: "", new_password: "", confirm_password: "" });
    } catch (err: unknown) {
      toast.error(getApiError(err, "تعذّر تغيير كلمة المرور"));
    } finally {
      setIsChangingPassword(false);
    }
  };

  const handleDeactivate = async () => {
    if (confirmText !== "DEACTIVATE") return;
    try {
      await usersApi.deactivateAccount();
      toast.success("تم إلغاء تفعيل الحساب");
      logout();
    } catch {
      toast.error("تعذّر إلغاء تفعيل الحساب");
    }
  };

  return (
    <div className="space-y-6" dir="rtl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">الإعدادات</h1>
        <p className="mt-1 text-gray-600">إدارة إعدادات حسابك والأمان.</p>
      </div>

      {/* Change Password */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">تغيير كلمة المرور</h2>
        <form onSubmit={handlePasswordChange} className="space-y-4 max-w-md">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              كلمة المرور الحالية
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
              كلمة المرور الجديدة
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
              8 أحرف على الأقل مع حرف كبير ورقم وحرف خاص
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              تأكيد كلمة المرور الجديدة
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
          <button
            type="submit"
            disabled={isChangingPassword}
            className="btn-primary py-2 px-6 text-sm"
          >
            {isChangingPassword ? "جاري التغيير..." : "تغيير كلمة المرور"}
          </button>
        </form>
      </div>

      {/* Danger Zone */}
      <div className="card p-6 border border-danger-500/20">
        <h2 className="text-lg font-semibold text-danger-700 mb-2">منطقة الخطر</h2>
        <p className="text-sm text-gray-600 mb-4">
          سيؤدي إلغاء تفعيل حسابك إلى إخفاء ملفك الشخصي وإلغاء أي عقود نشطة.
          يمكن التراجع عن هذا الإجراء بالتواصل مع الدعم.
        </p>

        {!showDeactivate ? (
          <button
            onClick={() => setShowDeactivate(true)}
            className="btn-danger py-2 px-5 text-sm"
          >
            إلغاء تفعيل الحساب
          </button>
        ) : (
          <div className="p-4 bg-danger-50 rounded-lg space-y-3">
            <p className="text-sm font-medium text-danger-700">
              اكتب <strong>DEACTIVATE</strong> للتأكيد:
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
                تأكيد الإلغاء
              </button>
              <button
                onClick={() => { setShowDeactivate(false); setConfirmText(""); }}
                className="btn-secondary py-2 px-5 text-sm"
              >
                إلغاء
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
