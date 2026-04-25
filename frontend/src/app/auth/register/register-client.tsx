"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuthStore } from "@/lib/auth-store";
import { getApiError } from "@/lib/utils";
import { SocialLoginButtons } from "@/components/auth/social-login-buttons";
import { useLocale } from "@/providers/locale-provider";

export default function RegisterClient() {
  const router = useRouter();
  const { register } = useAuthStore();
  const { locale } = useLocale();
  const ar = locale === "ar";

  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    username: "",
    email: "",
    password: "",
    primary_role: "freelancer" as "client" | "freelancer",
  });
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [legalAccepted, setLegalAccepted] = useState(false);

  const passwordMismatch =
    confirmPassword.length > 0 && confirmPassword !== formData.password;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    const updated = { ...formData, [name]: value };
    if (name === "first_name" || name === "last_name") {
      const first = name === "first_name" ? value : formData.first_name;
      const last  = name === "last_name"  ? value : formData.last_name;
      if (!formData.username || formData.username === autoUsername(formData.first_name, formData.last_name)) {
        updated.username = autoUsername(first, last);
      }
    }
    if (name === "username") {
      updated.username = value.replace(/\s/g, "_").replace(/[^a-zA-Z0-9_-]/g, "");
    }
    setFormData(updated);
  };

  function autoUsername(first: string, last: string): string {
    return `${first}_${last}`.toLowerCase().replace(/\s/g, "_").replace(/[^a-zA-Z0-9_-]/g, "").slice(0, 30);
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (confirmPassword !== formData.password) {
      setError(ar
        ? "كلمتا المرور غير متطابقتين."
        : "Passwords don't match. Please re-type the confirmation.");
      return;
    }
    if (!legalAccepted) {
      setError(ar
        ? "يجب الموافقة على شروط الخدمة وسياسة الخصوصية قبل المتابعة."
        : "You must agree to the Terms of Service and Privacy Policy before continuing.");
      return;
    }
    setError("");
    setIsLoading(true);
    try {
      await register({ ...formData, terms_accepted: true });
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(getApiError(err, ar
        ? "فشل إنشاء الحساب. تحقق من بياناتك وحاول مجدداً."
        : "Registration failed. Please check your details and try again."));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <div className="card p-8">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-gray-900">
              {ar ? "أنشئ حسابك" : "Create your account"}
            </h1>
            <p className="mt-2 text-gray-600">
              {ar ? "انضم إلى كاسب وابدأ رحلتك المهنية" : "Join Kaasb and start your professional journey"}
            </p>
          </div>

          {error && (
            <div className="mb-6 p-3 bg-danger-50 text-danger-700 rounded-lg text-sm whitespace-pre-line">
              {error}
            </div>
          )}

          {/* Social login — disabled until legal checkbox below the form is ticked */}
          <div className="mb-6">
            <SocialLoginButtons
              role={formData.primary_role}
              onSuccess={() => router.push("/dashboard")}
              termsAccepted={legalAccepted}
            />
            {!legalAccepted && (
              <p className="mt-2 text-xs text-gray-500 text-center">
                {ar
                  ? "وافق على الشروط أدناه لتفعيل تسجيل الدخول الاجتماعي."
                  : "Accept the terms below to enable social sign-up."}
              </p>
            )}
            <div className="relative mt-5 mb-1">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-200" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="bg-white px-3 text-gray-400">
                  {ar ? "أو سجّل بالبريد الإلكتروني" : "Or register with email"}
                </span>
              </div>
            </div>
          </div>

          {/* Role Selection */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-3">
              {ar ? "أريد:" : "I want to:"}
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setFormData({ ...formData, primary_role: "freelancer" })}
                className={`p-4 rounded-lg border-2 text-center transition-all ${
                  formData.primary_role === "freelancer"
                    ? "border-brand-500 bg-brand-50 text-brand-700"
                    : "border-gray-200 hover:border-gray-300"
                }`}
              >
                <div className="text-2xl mb-1">💼</div>
                <div className="font-medium text-sm">
                  {ar ? "العمل كمستقل" : "Work as Freelancer"}
                </div>
              </button>
              <button
                type="button"
                onClick={() => setFormData({ ...formData, primary_role: "client" })}
                className={`p-4 rounded-lg border-2 text-center transition-all ${
                  formData.primary_role === "client"
                    ? "border-brand-500 bg-brand-50 text-brand-700"
                    : "border-gray-200 hover:border-gray-300"
                }`}
              >
                <div className="text-2xl mb-1">🏢</div>
                <div className="font-medium text-sm">
                  {ar ? "توظيف مستقلين" : "Hire Freelancers"}
                </div>
              </button>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="first_name" className="block text-sm font-medium text-gray-700 mb-1">
                  {ar ? "الاسم الأول" : "First name"}
                </label>
                <input id="first_name" name="first_name" type="text" value={formData.first_name}
                  onChange={handleChange} className="input-field" required />
              </div>
              <div>
                <label htmlFor="last_name" className="block text-sm font-medium text-gray-700 mb-1">
                  {ar ? "اسم العائلة" : "Last name"}
                </label>
                <input id="last_name" name="last_name" type="text" value={formData.last_name}
                  onChange={handleChange} className="input-field" required />
              </div>
            </div>

            <div>
              <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
                {ar ? "اسم المستخدم" : "Username"}
              </label>
              <input id="username" name="username" type="text" value={formData.username}
                onChange={handleChange} className="input-field"
                placeholder={ar ? "مثال: ali_hassan" : "e.g. ali_hassan"}
                pattern="^[a-zA-Z0-9_-]+$" minLength={3} dir="ltr" required />
              <p className="mt-1 text-xs text-gray-500">
                {ar ? "أحرف لاتينية وأرقام وشرطات فقط، بدون مسافات"
                     : "Latin letters, numbers and hyphens only — no spaces"}
              </p>
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                {ar ? "البريد الإلكتروني" : "Email address"}
              </label>
              <input id="email" name="email" type="email" value={formData.email}
                onChange={handleChange} className="input-field"
                placeholder="you@example.com" dir="ltr" required />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                {ar ? "كلمة المرور" : "Password"}
              </label>
              <input id="password" name="password" type="password" value={formData.password}
                onChange={handleChange} className="input-field"
                placeholder={ar ? "8 أحرف كحد أدنى" : "Min. 8 characters"}
                minLength={8} required />
              <p className="mt-1 text-xs text-gray-500">
                {ar ? "يجب أن تحتوي على حرف كبير ورقم وحرف خاص"
                     : "Must include an uppercase letter, number and special character"}
              </p>
            </div>

            <div>
              <label htmlFor="confirm_password" className="block text-sm font-medium text-gray-700 mb-1">
                {ar ? "تأكيد كلمة المرور" : "Confirm password"}
              </label>
              <input
                id="confirm_password"
                name="confirm_password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className={`input-field ${passwordMismatch ? "border-danger-300 focus:border-danger-500 focus:ring-danger-500" : ""}`}
                placeholder={ar ? "أعد كتابة كلمة المرور" : "Re-type your password"}
                minLength={8}
                required
                aria-invalid={passwordMismatch || undefined}
              />
              {passwordMismatch && (
                <p className="mt-1 text-xs text-danger-600">
                  {ar ? "كلمتا المرور غير متطابقتين." : "Passwords don't match yet."}
                </p>
              )}
            </div>

            <div className="flex items-start gap-2 mt-2">
              <input
                id="legal_accepted"
                type="checkbox"
                checked={legalAccepted}
                onChange={(e) => setLegalAccepted(e.target.checked)}
                className="mt-1 h-4 w-4 rounded border-gray-300 text-brand-500 focus:ring-brand-500"
                required
              />
              <label htmlFor="legal_accepted" className="text-xs text-gray-600 leading-relaxed">
                {ar ? (
                  <>
                    أوافق على{" "}
                    <Link href="/terms" target="_blank" rel="noopener noreferrer" className="text-brand-500 hover:underline">
                      شروط الخدمة
                    </Link>{" "}
                    و{" "}
                    <Link href="/privacy" target="_blank" rel="noopener noreferrer" className="text-brand-500 hover:underline">
                      سياسة الخصوصية
                    </Link>{" "}
                    و{" "}
                    <Link href="/acceptable-use" target="_blank" rel="noopener noreferrer" className="text-brand-500 hover:underline">
                      سياسة الاستخدام المقبول
                    </Link>
                    . أُقرّ بأنني أبلغ من العمر ١٨ سنة فأكثر.
                  </>
                ) : (
                  <>
                    I agree to the{" "}
                    <Link href="/terms" target="_blank" rel="noopener noreferrer" className="text-brand-500 hover:underline">
                      Terms of Service
                    </Link>
                    ,{" "}
                    <Link href="/privacy" target="_blank" rel="noopener noreferrer" className="text-brand-500 hover:underline">
                      Privacy Policy
                    </Link>
                    , and{" "}
                    <Link href="/acceptable-use" target="_blank" rel="noopener noreferrer" className="text-brand-500 hover:underline">
                      Acceptable Use Policy
                    </Link>
                    . I confirm I am at least 18 years old.
                  </>
                )}
              </label>
            </div>

            <button
              type="submit"
              disabled={isLoading || !legalAccepted || passwordMismatch || confirmPassword === ""}
              className="btn-primary w-full py-3 mt-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading
                ? (ar ? "جاري إنشاء الحساب..." : "Creating account...")
                : (ar ? "إنشاء الحساب" : "Create account")}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-gray-600">
            {ar ? "لديك حساب بالفعل؟" : "Already have an account?"}{" "}
            <Link href="/auth/login" className="text-brand-500 hover:text-brand-600 font-medium">
              {ar ? "تسجيل الدخول" : "Sign in"}
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
