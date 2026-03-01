"use client";

import { useState } from "react";
import { usersApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { toast } from "sonner";

export default function SettingsPage() {
  const { logout } = useAuthStore();

  // Password change state
  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [isChangingPassword, setIsChangingPassword] = useState(false);

  // Deactivation state
  const [showDeactivate, setShowDeactivate] = useState(false);
  const [confirmText, setConfirmText] = useState("");

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();

    if (passwordForm.new_password !== passwordForm.confirm_password) {
      toast.error("New passwords do not match");
      return;
    }

    setIsChangingPassword(true);
    try {
      await usersApi.changePassword({
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password,
      });
      toast.success("Password changed successfully!");
      setPasswordForm({
        current_password: "",
        new_password: "",
        confirm_password: "",
      });
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        toast.error(detail.map((d: any) => d.msg).join(", "));
      } else {
        toast.error(detail || "Failed to change password");
      }
    } finally {
      setIsChangingPassword(false);
    }
  };

  const handleDeactivate = async () => {
    if (confirmText !== "DEACTIVATE") return;

    try {
      await usersApi.deactivateAccount();
      toast.success("Account deactivated");
      logout();
    } catch {
      toast.error("Failed to deactivate account");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="mt-1 text-gray-600">
          Manage your account settings and security.
        </p>
      </div>

      {/* Change Password */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Change Password
        </h2>
        <form onSubmit={handlePasswordChange} className="space-y-4 max-w-md">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Current Password
            </label>
            <input
              type="password"
              value={passwordForm.current_password}
              onChange={(e) =>
                setPasswordForm({
                  ...passwordForm,
                  current_password: e.target.value,
                })
              }
              className="input-field"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              New Password
            </label>
            <input
              type="password"
              value={passwordForm.new_password}
              onChange={(e) =>
                setPasswordForm({
                  ...passwordForm,
                  new_password: e.target.value,
                })
              }
              className="input-field"
              minLength={8}
              required
            />
            <p className="mt-1 text-xs text-gray-500">
              Min 8 characters with uppercase, digit, and special character
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Confirm New Password
            </label>
            <input
              type="password"
              value={passwordForm.confirm_password}
              onChange={(e) =>
                setPasswordForm({
                  ...passwordForm,
                  confirm_password: e.target.value,
                })
              }
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
            {isChangingPassword ? "Changing..." : "Change Password"}
          </button>
        </form>
      </div>

      {/* Danger Zone */}
      <div className="card p-6 border border-danger-500/20">
        <h2 className="text-lg font-semibold text-danger-700 mb-2">
          Danger Zone
        </h2>
        <p className="text-sm text-gray-600 mb-4">
          Deactivating your account will hide your profile and cancel any active
          contracts. This action can be reversed by contacting support.
        </p>

        {!showDeactivate ? (
          <button
            onClick={() => setShowDeactivate(true)}
            className="btn-danger py-2 px-5 text-sm"
          >
            Deactivate Account
          </button>
        ) : (
          <div className="p-4 bg-danger-50 rounded-lg space-y-3">
            <p className="text-sm font-medium text-danger-700">
              Type <strong>DEACTIVATE</strong> to confirm:
            </p>
            <input
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              className="input-field max-w-xs"
              placeholder="Type DEACTIVATE"
            />
            <div className="flex gap-3">
              <button
                onClick={handleDeactivate}
                disabled={confirmText !== "DEACTIVATE"}
                className="btn-danger py-2 px-5 text-sm"
              >
                Confirm Deactivation
              </button>
              <button
                onClick={() => {
                  setShowDeactivate(false);
                  setConfirmText("");
                }}
                className="btn-secondary py-2 px-5 text-sm"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
