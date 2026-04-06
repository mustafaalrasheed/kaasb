"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuthStore } from "@/lib/auth-store";
import { getApiError } from "@/lib/utils";
import { SocialLoginButtons } from "@/components/auth/social-login-buttons";
import { PhoneLoginTab } from "@/components/auth/phone-login-tab";
import { useLocale } from "@/providers/locale-provider";

type LoginTab = "email" | "phone";

export default function LoginClient() {
  const router = useRouter();
  const { login } = useAuthStore();
  const { locale } = useLocale();

  const [tab, setTab] = useState<LoginTab>("email");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const ar = locale === "ar";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(getApiError(err, ar
        ? "البريد الإلكتروني أو كلمة المرور غير صحيحة."
        : "Incorrect email or password."));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="card p-8">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-gray-900">
              {ar ? "أهلاً بعودتك" : "Welcome back"}
            </h1>
            <p className="mt-2 text-gray-600">
              {ar ? "سجّل دخولك إلى حساب كاسب" : "Sign in to your Kaasb account"}
            </p>
          </div>

          {/* Tab switcher */}
          <div className="flex rounded-lg bg-gray-100 p-1 mb-6">
            <button
              type="button"
              onClick={() => { setTab("email"); setError(""); }}
              className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${
                tab === "email" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {ar ? "البريد الإلكتروني" : "Email"}
            </button>
            <button
              type="button"
              onClick={() => { setTab("phone"); setError(""); }}
              className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${
                tab === "phone" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {ar ? "رقم الهاتف (OTP)" : "Phone (OTP)"}
            </button>
          </div>

          {tab === "email" ? (
            <>
              {error && (
                <div className="mb-6 p-3 bg-danger-50 text-danger-700 rounded-lg text-sm">
                  {error}
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1.5">
                    {ar ? "البريد الإلكتروني" : "Email address"}
                  </label>
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="input-field"
                    placeholder="you@example.com"
                    dir="ltr"
                    required
                  />
                </div>

                <div>
                  <div className={`flex items-center justify-between mb-1.5 ${ar ? "flex-row-reverse" : ""}`}>
                    <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                      {ar ? "كلمة المرور" : "Password"}
                    </label>
                    <Link href="/auth/forgot-password" className="text-xs text-brand-500 hover:text-brand-600">
                      {ar ? "نسيت كلمة المرور؟" : "Forgot password?"}
                    </Link>
                  </div>
                  <input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="input-field"
                    placeholder={ar ? "أدخل كلمة المرور" : "Enter your password"}
                    required
                  />
                </div>

                <button type="submit" disabled={isLoading} className="btn-primary w-full py-3">
                  {isLoading
                    ? (ar ? "جاري تسجيل الدخول..." : "Signing in...")
                    : (ar ? "تسجيل الدخول" : "Sign in")}
                </button>
              </form>

              <div className="mt-6">
                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-gray-200" />
                  </div>
                  <div className="relative flex justify-center text-sm">
                    <span className="bg-white px-3 text-gray-400">
                      {ar ? "أو تابع باستخدام" : "Or continue with"}
                    </span>
                  </div>
                </div>
                <div className="mt-4">
                  <SocialLoginButtons onSuccess={() => router.push("/dashboard")} />
                </div>
              </div>
            </>
          ) : (
            <PhoneLoginTab onSuccess={() => router.push("/dashboard")} />
          )}

          <p className="mt-6 text-center text-sm text-gray-600">
            {ar ? "ليس لديك حساب؟" : "Don't have an account?"}{" "}
            <Link href="/auth/register" className="text-brand-500 hover:text-brand-600 font-medium">
              {ar ? "إنشاء حساب" : "Sign up"}
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
