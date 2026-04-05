"use client";

import { useState } from "react";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { getApiError } from "@/lib/utils";
import { toast } from "sonner";

/**
 * Phone OTP login flow (two-step):
 * 1. User enters Iraqi phone number → OTP sent to their registered email (beta)
 * 2. User enters 6-digit OTP → receives JWT tokens and is logged in
 */
export function PhoneLoginTab({ onSuccess }: { onSuccess: () => void }) {
  const { initialize } = useAuthStore();

  const [step, setStep] = useState<"phone" | "otp">("phone");
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  // Prepend +964 if the user typed a local Iraqi number (starts with 07x)
  function normalizePhone(raw: string): string {
    const digits = raw.replace(/\s+/g, "");
    if (digits.startsWith("07")) return "+964" + digits.slice(1);
    if (digits.startsWith("7") && digits.length === 10) return "+964" + digits;
    return digits;
  }

  async function handleSendOtp(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    const normalized = normalizePhone(phone);
    try {
      await authApi.sendPhoneOtp(normalized);
      setPhone(normalized);
      setStep("otp");
      toast.success("رمز التحقق أُرسل إلى بريدك الإلكتروني المسجّل");
    } catch (err: unknown) {
      setError(getApiError(err, "حدث خطأ. يرجى المحاولة مجدداً."));
    } finally {
      setIsLoading(false);
    }
  }

  async function handleVerifyOtp(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      await authApi.verifyPhoneOtp(phone, otp);
      // Reload auth state from /auth/me
      await initialize();
      onSuccess();
    } catch (err: unknown) {
      setError(getApiError(err, "الرمز غير صحيح أو منتهي الصلاحية."));
    } finally {
      setIsLoading(false);
    }
  }

  if (step === "otp") {
    return (
      <form onSubmit={handleVerifyOtp} className="space-y-5" dir="rtl">
        <div className="text-center text-sm text-gray-600 bg-brand-50 rounded-lg p-3">
          <p>أُرسل رمز التحقق إلى بريدك الإلكتروني المرتبط بـ</p>
          <p className="font-medium text-gray-800 mt-1 font-mono">{phone}</p>
        </div>

        {error && (
          <div className="p-3 bg-danger-50 text-danger-700 rounded-lg text-sm text-right">
            {error}
          </div>
        )}

        <div>
          <label htmlFor="otp" className="block text-sm font-medium text-gray-700 mb-1.5">
            رمز التحقق (6 أرقام)
          </label>
          <input
            id="otp"
            type="text"
            inputMode="numeric"
            pattern="[0-9]{6}"
            maxLength={6}
            value={otp}
            onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
            className="input-field text-center text-2xl tracking-widest font-mono"
            placeholder="000000"
            autoFocus
            required
          />
        </div>

        <button
          type="submit"
          disabled={isLoading || otp.length !== 6}
          className="btn-primary w-full py-3"
        >
          {isLoading ? "جارٍ التحقق..." : "تحقق ودخول"}
        </button>

        <button
          type="button"
          onClick={() => { setStep("phone"); setOtp(""); setError(""); }}
          className="w-full text-sm text-gray-500 hover:text-gray-700 text-center"
        >
          تغيير رقم الهاتف
        </button>
      </form>
    );
  }

  return (
    <form onSubmit={handleSendOtp} className="space-y-5" dir="rtl">
      {error && (
        <div className="p-3 bg-danger-50 text-danger-700 rounded-lg text-sm text-right">
          {error}
        </div>
      )}

      <div>
        <label htmlFor="phone" className="block text-sm font-medium text-gray-700 mb-1.5">
          رقم الهاتف
        </label>
        <div className="flex gap-2">
          <span className="flex items-center px-3 rounded-lg border border-gray-300 bg-gray-50 text-gray-600 text-sm font-medium whitespace-nowrap">
            🇮🇶 +964
          </span>
          <input
            id="phone"
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className="input-field flex-1"
            placeholder="07X XXXX XXXX"
            required
          />
        </div>
        <p className="mt-1 text-xs text-gray-400">
          سيتم إرسال الرمز إلى بريدك الإلكتروني المسجّل مؤقتاً
        </p>
      </div>

      <button
        type="submit"
        disabled={isLoading || !phone.trim()}
        className="btn-primary w-full py-3"
      >
        {isLoading ? "جارٍ الإرسال..." : "إرسال رمز التحقق"}
      </button>
    </form>
  );
}
