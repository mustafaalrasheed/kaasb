"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { jobsApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { toast } from "sonner";
import { getApiError } from "@/lib/utils";
import { JOB_CATEGORIES } from "@/types/job";

const DURATIONS = [
  { value: "less_than_1_week", label: "أقل من أسبوع" },
  { value: "1_to_4_weeks", label: "من 1 إلى 4 أسابيع" },
  { value: "1_to_3_months", label: "من 1 إلى 3 أشهر" },
  { value: "3_to_6_months", label: "من 3 إلى 6 أشهر" },
  { value: "more_than_6_months", label: "أكثر من 6 أشهر" },
];

export default function PostJobPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading } = useAuthStore();

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [newSkill, setNewSkill] = useState("");

  const [form, setForm] = useState({
    title: "",
    description: "",
    category: "",
    job_type: "fixed" as "fixed" | "hourly",
    fixed_price: "",
    budget_min: "",
    budget_max: "",
    experience_level: "",
    duration: "",
    skills_required: [] as string[],
  });

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/auth/login");
    }
    if (!authLoading && user && user.primary_role !== "client") {
      toast.error("فقط العملاء يمكنهم نشر الوظائف");
      router.push("/dashboard");
    }
  }, [authLoading, isAuthenticated, user, router]);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleAddSkill = () => {
    const skill = newSkill.trim();
    if (skill && !form.skills_required.includes(skill) && form.skills_required.length < 15) {
      setForm({ ...form, skills_required: [...form.skills_required, skill] });
      setNewSkill("");
    }
  };

  const handleRemoveSkill = (skill: string) => {
    setForm({ ...form, skills_required: form.skills_required.filter((s) => s !== skill) });
  };

  const handleSkillKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddSkill();
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      const payload: Parameters<typeof jobsApi.create>[0] = {
        title: form.title,
        description: form.description,
        category: form.category,
        job_type: form.job_type,
        ...(form.job_type === "fixed"
          ? { fixed_price: parseFloat(form.fixed_price) }
          : {
              budget_min: parseFloat(form.budget_min),
              ...(form.budget_max ? { budget_max: parseFloat(form.budget_max) } : {}),
            }),
        ...(form.experience_level ? { experience_level: form.experience_level } : {}),
        ...(form.duration ? { duration: form.duration } : {}),
        ...(form.skills_required.length > 0 ? { skills_required: form.skills_required } : {}),
      };

      const response = await jobsApi.create(payload);
      toast.success("تم نشر الوظيفة بنجاح!");
      router.push(`/jobs/${response.data.id}`);
    } catch (err: unknown) {
      toast.error(getApiError(err, "تعذّر نشر الوظيفة"));
    } finally {
      setIsSubmitting(false);
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <p className="text-gray-500">جاري التحميل...</p>
      </div>
    );
  }

  if (!user || user.primary_role !== "client") return null;

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8" dir="rtl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">نشر وظيفة جديدة</h1>
        <p className="mt-1 text-gray-600">
          صف مشروعك وابحث عن المستقل المثالي.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Title & Category */}
        <div className="card p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">تفاصيل الوظيفة</h2>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              عنوان الوظيفة *
            </label>
            <input
              name="title"
              value={form.title}
              onChange={handleChange}
              className="input-field"
              placeholder="مثال: بناء موقع تجارة إلكترونية متجاوب"
              minLength={10}
              maxLength={200}
              required
            />
            <p className="mt-1 text-xs text-gray-500">
              كن محدداً — عناوين من قبيل "بناء لوحة تحكم بـ React" تجلب عروضاً أكثر.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              التصنيف *
            </label>
            <select
              name="category"
              value={form.category}
              onChange={handleChange}
              className="input-field"
              required
            >
              <option value="">اختر التصنيف</option>
              {JOB_CATEGORIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              الوصف *
            </label>
            <textarea
              name="description"
              value={form.description}
              onChange={handleChange}
              className="input-field min-h-[200px] resize-y"
              placeholder="صف نطاق المشروع والمخرجات والمتطلبات الخاصة..."
              minLength={50}
              maxLength={10000}
              rows={8}
              required
            />
            <p className="mt-1 text-xs text-gray-500 text-left">
              {form.description.length}/10,000
            </p>
          </div>
        </div>

        {/* Budget */}
        <div className="card p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">الميزانية</h2>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              نوع التسعير *
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setForm({ ...form, job_type: "fixed" })}
                className={`p-4 rounded-lg border-2 text-center transition-all ${
                  form.job_type === "fixed"
                    ? "border-brand-500 bg-brand-50 text-brand-700"
                    : "border-gray-200 hover:border-gray-300"
                }`}
              >
                <div className="font-medium">سعر ثابت</div>
                <div className="text-xs text-gray-500 mt-1">
                  ادفع مبلغاً محدداً للمشروع كاملاً
                </div>
              </button>
              <button
                type="button"
                onClick={() => setForm({ ...form, job_type: "hourly" })}
                className={`p-4 rounded-lg border-2 text-center transition-all ${
                  form.job_type === "hourly"
                    ? "border-brand-500 bg-brand-50 text-brand-700"
                    : "border-gray-200 hover:border-gray-300"
                }`}
              >
                <div className="font-medium">بالساعة</div>
                <div className="text-xs text-gray-500 mt-1">
                  ادفع بالساعة مع تقدم العمل
                </div>
              </button>
            </div>
          </div>

          {form.job_type === "fixed" ? (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                السعر الثابت (USD) *
              </label>
              <input
                name="fixed_price"
                type="number"
                value={form.fixed_price}
                onChange={handleChange}
                className="input-field"
                placeholder="مثال: 500"
                min={5}
                step={1}
                dir="ltr"
                required
              />
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  الحد الأدنى (USD/س) *
                </label>
                <input
                  name="budget_min"
                  type="number"
                  value={form.budget_min}
                  onChange={handleChange}
                  className="input-field"
                  placeholder="مثال: 15"
                  min={5}
                  step={0.5}
                  dir="ltr"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  الحد الأقصى (USD/س)
                </label>
                <input
                  name="budget_max"
                  type="number"
                  value={form.budget_max}
                  onChange={handleChange}
                  className="input-field"
                  placeholder="مثال: 50"
                  min={5}
                  step={0.5}
                  dir="ltr"
                />
              </div>
            </div>
          )}
        </div>

        {/* Requirements */}
        <div className="card p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">المتطلبات</h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                مستوى الخبرة
              </label>
              <select
                name="experience_level"
                value={form.experience_level}
                onChange={handleChange}
                className="input-field"
              >
                <option value="">أي مستوى</option>
                <option value="entry">مبتدئ</option>
                <option value="intermediate">متوسط</option>
                <option value="expert">خبير</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                المدة المتوقعة
              </label>
              <select
                name="duration"
                value={form.duration}
                onChange={handleChange}
                className="input-field"
              >
                <option value="">غير محددة</option>
                {DURATIONS.map((d) => (
                  <option key={d.value} value={d.value}>{d.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Skills */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              المهارات المطلوبة
            </label>
            <div className="flex gap-2 mb-3">
              <input
                value={newSkill}
                onChange={(e) => setNewSkill(e.target.value)}
                onKeyDown={handleSkillKeyDown}
                className="input-field flex-1"
                placeholder="اكتب مهارة ثم اضغط Enter"
                maxLength={50}
              />
              <button
                type="button"
                onClick={handleAddSkill}
                disabled={!newSkill.trim() || form.skills_required.length >= 15}
                className="btn-secondary py-2 px-4 text-sm whitespace-nowrap"
              >
                إضافة
              </button>
            </div>

            {form.skills_required.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {form.skills_required.map((skill) => (
                  <span
                    key={skill}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium bg-brand-50 text-brand-700 border border-brand-200"
                  >
                    {skill}
                    <button
                      type="button"
                      onClick={() => handleRemoveSkill(skill)}
                      className="text-brand-400 hover:text-brand-600"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}
            <p className="mt-2 text-xs text-gray-500">
              {form.skills_required.length}/15 مهارة
            </p>
          </div>
        </div>

        {/* Submit */}
        <div className="flex justify-start gap-3">
          <button type="submit" disabled={isSubmitting} className="btn-primary py-2.5 px-8">
            {isSubmitting ? "جاري النشر..." : "نشر الوظيفة"}
          </button>
          <button
            type="button"
            onClick={() => router.back()}
            className="btn-secondary py-2.5 px-6"
          >
            إلغاء
          </button>
        </div>
      </form>
    </div>
  );
}
