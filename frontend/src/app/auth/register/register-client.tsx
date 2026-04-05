"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuthStore } from "@/lib/auth-store";
import { getApiError } from "@/lib/utils";
import { SocialLoginButtons } from "@/components/auth/social-login-buttons";

export default function RegisterClient() {
  const router = useRouter();
  const { register } = useAuthStore();
  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    username: "",
    email: "",
    password: "",
    primary_role: "freelancer" as "client" | "freelancer",
  });
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    const updated = { ...formData, [name]: value };

    // Auto-suggest username from first + last name (no spaces, lowercase)
    if (name === "first_name" || name === "last_name") {
      const first = name === "first_name" ? value : formData.first_name;
      const last = name === "last_name" ? value : formData.last_name;
      if (!formData.username || formData.username === autoUsername(formData.first_name, formData.last_name)) {
        updated.username = autoUsername(first, last);
      }
    }

    // Strip spaces from username as user types
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
    setError("");
    setIsLoading(true);

    try {
      await register(formData);
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(getApiError(err, "فشل إنشاء الحساب. تحقق من بياناتك وحاول مجدداً."));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4 py-12" dir="rtl">
      <div className="w-full max-w-md">
        <div className="card p-8">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-gray-900">أنشئ حسابك</h1>
            <p className="mt-2 text-gray-600">انضم إلى كاسب وابدأ رحلتك المهنية</p>
          </div>

          {error && (
            <div className="mb-6 p-3 bg-danger-50 text-danger-700 rounded-lg text-sm whitespace-pre-line">
              {error}
            </div>
          )}

          {/* Social login */}
          <div className="mb-6">
            <SocialLoginButtons
              role={formData.primary_role}
              onSuccess={() => router.push("/dashboard")}
            />
            <div className="relative mt-5 mb-1">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-200" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="bg-white px-3 text-gray-400">أو سجّل بالبريد الإلكتروني</span>
              </div>
            </div>
          </div>

          {/* Role Selection */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-3">
              أريد:
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
                <div className="font-medium text-sm">العمل كمستقل</div>
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
                <div className="font-medium text-sm">توظيف مستقلين</div>
              </button>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="first_name" className="block text-sm font-medium text-gray-700 mb-1">
                  الاسم الأول
                </label>
                <input
                  id="first_name"
                  name="first_name"
                  type="text"
                  value={formData.first_name}
                  onChange={handleChange}
                  className="input-field"
                  required
                />
              </div>
              <div>
                <label htmlFor="last_name" className="block text-sm font-medium text-gray-700 mb-1">
                  اسم العائلة
                </label>
                <input
                  id="last_name"
                  name="last_name"
                  type="text"
                  value={formData.last_name}
                  onChange={handleChange}
                  className="input-field"
                  required
                />
              </div>
            </div>

            <div>
              <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
                اسم المستخدم
              </label>
              <input
                id="username"
                name="username"
                type="text"
                value={formData.username}
                onChange={handleChange}
                className="input-field"
                placeholder="مثال: ali_hassan"
                pattern="^[a-zA-Z0-9_-]+$"
                minLength={3}
                dir="ltr"
                required
              />
              <p className="mt-1 text-xs text-gray-500">
                أحرف لاتينية وأرقام وشرطات فقط، بدون مسافات
              </p>
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                البريد الإلكتروني
              </label>
              <input
                id="email"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleChange}
                className="input-field"
                placeholder="you@example.com"
                dir="ltr"
                required
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                كلمة المرور
              </label>
              <input
                id="password"
                name="password"
                type="password"
                value={formData.password}
                onChange={handleChange}
                className="input-field"
                placeholder="8 أحرف كحد أدنى"
                minLength={8}
                required
              />
              <p className="mt-1 text-xs text-gray-500">
                يجب أن تحتوي على حرف كبير ورقم وحرف خاص
              </p>
            </div>

            <button type="submit" disabled={isLoading} className="btn-primary w-full py-3 mt-2">
              {isLoading ? "جاري إنشاء الحساب..." : "إنشاء الحساب"}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-gray-600">
            لديك حساب بالفعل؟{" "}
            <Link href="/auth/login" className="text-brand-500 hover:text-brand-600 font-medium">
              تسجيل الدخول
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
