"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { jobsApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { useLocale } from "@/providers/locale-provider";
import { toast } from "sonner";
import { getApiError } from "@/lib/utils";
import { JOB_CATEGORIES } from "@/types/job";

const DURATIONS_AR = [
  { value: "less_than_1_week",   label: "أقل من أسبوع" },
  { value: "1_to_4_weeks",       label: "من 1 إلى 4 أسابيع" },
  { value: "1_to_3_months",      label: "من 1 إلى 3 أشهر" },
  { value: "3_to_6_months",      label: "من 3 إلى 6 أشهر" },
  { value: "more_than_6_months", label: "أكثر من 6 أشهر" },
];

const DURATIONS_EN = [
  { value: "less_than_1_week",   label: "Less than 1 week" },
  { value: "1_to_4_weeks",       label: "1 to 4 weeks" },
  { value: "1_to_3_months",      label: "1 to 3 months" },
  { value: "3_to_6_months",      label: "3 to 6 months" },
  { value: "more_than_6_months", label: "More than 6 months" },
];

export default function PostJobPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading } = useAuthStore();
  const { locale } = useLocale();
  const ar = locale === "ar";

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

  const durations = ar ? DURATIONS_AR : DURATIONS_EN;

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/auth/login");
    }
    if (!authLoading && user && user.primary_role !== "client") {
      toast.error(ar ? "فقط العملاء يمكنهم نشر الوظائف" : "Only clients can post jobs");
      router.push("/dashboard");
    }
  }, [authLoading, isAuthenticated, user, router]); // eslint-disable-line react-hooks/exhaustive-deps

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
      toast.success(ar ? "تم نشر الوظيفة بنجاح!" : "Job posted successfully!");
      router.push(`/jobs/${response.data.id}`);
    } catch (err: unknown) {
      toast.error(getApiError(err, ar ? "تعذّر نشر الوظيفة" : "Failed to post job"));
    } finally {
      setIsSubmitting(false);
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <p className="text-gray-500">{ar ? "جاري التحميل..." : "Loading..."}</p>
      </div>
    );
  }

  if (!user || user.primary_role !== "client") return null;

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          {ar ? "نشر وظيفة جديدة" : "Post a New Job"}
        </h1>
        <p className="mt-1 text-gray-600">
          {ar ? "صف مشروعك وابحث عن المستقل المثالي." : "Describe your project and find the perfect freelancer."}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Title & Category */}
        <div className="card p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">
            {ar ? "تفاصيل الوظيفة" : "Job Details"}
          </h2>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {ar ? "عنوان الوظيفة *" : "Job Title *"}
            </label>
            <input
              name="title"
              value={form.title}
              onChange={handleChange}
              className="input-field"
              placeholder={ar ? "مثال: بناء موقع تجارة إلكترونية متجاوب" : "e.g. Build a responsive e-commerce website"}
              minLength={10}
              maxLength={200}
              required
            />
            <p className="mt-1 text-xs text-gray-500">
              {ar
                ? "كن محدداً — عناوين من قبيل \"بناء لوحة تحكم بـ React\" تجلب عروضاً أكثر."
                : "Be specific — titles like \"Build a React dashboard\" attract more proposals."}
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {ar ? "التصنيف *" : "Category *"}
            </label>
            <select
              name="category"
              value={form.category}
              onChange={handleChange}
              className="input-field"
              required
            >
              <option value="">{ar ? "اختر التصنيف" : "Select category"}</option>
              {JOB_CATEGORIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {ar ? "الوصف *" : "Description *"}
            </label>
            <textarea
              name="description"
              value={form.description}
              onChange={handleChange}
              className="input-field min-h-[200px] resize-y"
              placeholder={ar
                ? "صف نطاق المشروع والمخرجات والمتطلبات الخاصة..."
                : "Describe the project scope, deliverables, and specific requirements..."}
              minLength={50}
              maxLength={10000}
              rows={8}
              required
            />
            <p className="mt-1 text-xs text-gray-500 text-end">
              {form.description.length}/10,000
            </p>
          </div>
        </div>

        {/* Budget */}
        <div className="card p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">
            {ar ? "الميزانية" : "Budget"}
          </h2>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {ar ? "نوع التسعير *" : "Pricing Type *"}
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
                <div className="font-medium">{ar ? "سعر ثابت" : "Fixed Price"}</div>
                <div className="text-xs text-gray-500 mt-1">
                  {ar ? "ادفع مبلغاً محدداً للمشروع كاملاً" : "Pay a set amount for the whole project"}
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
                <div className="font-medium">{ar ? "بالساعة" : "Hourly"}</div>
                <div className="text-xs text-gray-500 mt-1">
                  {ar ? "ادفع بالساعة مع تقدم العمل" : "Pay per hour as work progresses"}
                </div>
              </button>
            </div>
          </div>

          {form.job_type === "fixed" ? (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {ar ? "السعر الثابت (USD) *" : "Fixed Price (USD) *"}
              </label>
              <input
                name="fixed_price"
                type="number"
                value={form.fixed_price}
                onChange={handleChange}
                className="input-field"
                placeholder="500"
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
                  {ar ? "الحد الأدنى (USD/س) *" : "Min Rate (USD/hr) *"}
                </label>
                <input
                  name="budget_min"
                  type="number"
                  value={form.budget_min}
                  onChange={handleChange}
                  className="input-field"
                  placeholder="15"
                  min={5}
                  step={0.5}
                  dir="ltr"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {ar ? "الحد الأقصى (USD/س)" : "Max Rate (USD/hr)"}
                </label>
                <input
                  name="budget_max"
                  type="number"
                  value={form.budget_max}
                  onChange={handleChange}
                  className="input-field"
                  placeholder="50"
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
          <h2 className="text-lg font-semibold text-gray-900">
            {ar ? "المتطلبات" : "Requirements"}
          </h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {ar ? "مستوى الخبرة" : "Experience Level"}
              </label>
              <select
                name="experience_level"
                value={form.experience_level}
                onChange={handleChange}
                className="input-field"
              >
                <option value="">{ar ? "أي مستوى" : "Any level"}</option>
                <option value="entry">{ar ? "مبتدئ" : "Entry Level"}</option>
                <option value="intermediate">{ar ? "متوسط" : "Intermediate"}</option>
                <option value="expert">{ar ? "خبير" : "Expert"}</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {ar ? "المدة المتوقعة" : "Estimated Duration"}
              </label>
              <select
                name="duration"
                value={form.duration}
                onChange={handleChange}
                className="input-field"
              >
                <option value="">{ar ? "غير محددة" : "Not specified"}</option>
                {durations.map((d) => (
                  <option key={d.value} value={d.value}>{d.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Skills */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {ar ? "المهارات المطلوبة" : "Required Skills"}
            </label>
            <div className="flex gap-2 mb-3">
              <input
                value={newSkill}
                onChange={(e) => setNewSkill(e.target.value)}
                onKeyDown={handleSkillKeyDown}
                className="input-field flex-1"
                placeholder={ar ? "اكتب مهارة ثم اضغط Enter" : "Type a skill and press Enter"}
                maxLength={50}
              />
              <button
                type="button"
                onClick={handleAddSkill}
                disabled={!newSkill.trim() || form.skills_required.length >= 15}
                className="btn-secondary py-2 px-4 text-sm whitespace-nowrap"
              >
                {ar ? "إضافة" : "Add"}
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
              {form.skills_required.length}/15 {ar ? "مهارة" : "skills"}
            </p>
          </div>
        </div>

        {/* Submit */}
        <div className="flex gap-3">
          <button type="submit" disabled={isSubmitting} className="btn-primary py-2.5 px-8">
            {isSubmitting ? (ar ? "جاري النشر..." : "Posting...") : (ar ? "نشر الوظيفة" : "Post Job")}
          </button>
          <button
            type="button"
            onClick={() => router.back()}
            className="btn-secondary py-2.5 px-6"
          >
            {ar ? "إلغاء" : "Cancel"}
          </button>
        </div>
      </form>
    </div>
  );
}
