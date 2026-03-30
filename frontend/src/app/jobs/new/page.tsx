"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { jobsApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { toast } from "sonner";
import { JOB_CATEGORIES } from "@/types/job";

const DURATIONS = [
  { value: "less_than_1_week", label: "Less than 1 week" },
  { value: "1_to_4_weeks", label: "1 to 4 weeks" },
  { value: "1_to_3_months", label: "1 to 3 months" },
  { value: "3_to_6_months", label: "3 to 6 months" },
  { value: "more_than_6_months", label: "More than 6 months" },
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
      toast.error("Only clients can post jobs");
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
    setForm({
      ...form,
      skills_required: form.skills_required.filter((s) => s !== skill),
    });
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
      const payload: Record<string, unknown> = {
        title: form.title,
        description: form.description,
        category: form.category,
        job_type: form.job_type,
      };

      if (form.job_type === "fixed") {
        payload.fixed_price = parseFloat(form.fixed_price);
      } else {
        payload.budget_min = parseFloat(form.budget_min);
        if (form.budget_max) payload.budget_max = parseFloat(form.budget_max);
      }

      if (form.experience_level) payload.experience_level = form.experience_level;
      if (form.duration) payload.duration = form.duration;
      if (form.skills_required.length > 0) payload.skills_required = form.skills_required;

      const response = await jobsApi.create(payload as any);
      toast.success("Job posted successfully!");
      router.push(`/jobs/${response.data.id}`);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        toast.error(detail.map((d: any) => d.msg).join(", "));
      } else {
        toast.error(detail || "Failed to post job");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  if (!user || user.primary_role !== "client") return null;

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Post a New Job</h1>
        <p className="mt-1 text-gray-600">
          Describe your project and find the perfect freelancer.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Title & Category */}
        <div className="card p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">Job Details</h2>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Job Title *
            </label>
            <input
              name="title"
              value={form.title}
              onChange={handleChange}
              className="input-field"
              placeholder="e.g., Build a responsive e-commerce website"
              minLength={10}
              maxLength={200}
              required
            />
            <p className="mt-1 text-xs text-gray-500">
              Be specific — titles like "Build a React dashboard" get more proposals.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Category *
            </label>
            <select
              name="category"
              value={form.category}
              onChange={handleChange}
              className="input-field"
              required
            >
              <option value="">Select a category</option>
              {JOB_CATEGORIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description *
            </label>
            <textarea
              name="description"
              value={form.description}
              onChange={handleChange}
              className="input-field min-h-[200px] resize-y"
              placeholder="Describe the project scope, deliverables, and any specific requirements..."
              minLength={50}
              maxLength={10000}
              rows={8}
              required
            />
            <p className="mt-1 text-xs text-gray-500 text-right">
              {form.description.length}/10,000
            </p>
          </div>
        </div>

        {/* Budget */}
        <div className="card p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">Budget</h2>

          {/* Job type toggle */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Pricing Type *
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
                <div className="font-medium">Fixed Price</div>
                <div className="text-xs text-gray-500 mt-1">
                  Pay a set amount for the whole project
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
                <div className="font-medium">Hourly Rate</div>
                <div className="text-xs text-gray-500 mt-1">
                  Pay by the hour as work progresses
                </div>
              </button>
            </div>
          </div>

          {form.job_type === "fixed" ? (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Fixed Price (USD) *
              </label>
              <input
                name="fixed_price"
                type="number"
                value={form.fixed_price}
                onChange={handleChange}
                className="input-field"
                placeholder="e.g., 500"
                min={5}
                step={1}
                required
              />
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Min Rate (USD/hr) *
                </label>
                <input
                  name="budget_min"
                  type="number"
                  value={form.budget_min}
                  onChange={handleChange}
                  className="input-field"
                  placeholder="e.g., 15"
                  min={5}
                  step={0.5}
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Max Rate (USD/hr)
                </label>
                <input
                  name="budget_max"
                  type="number"
                  value={form.budget_max}
                  onChange={handleChange}
                  className="input-field"
                  placeholder="e.g., 50"
                  min={5}
                  step={0.5}
                />
              </div>
            </div>
          )}
        </div>

        {/* Requirements */}
        <div className="card p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">Requirements</h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Experience Level
              </label>
              <select
                name="experience_level"
                value={form.experience_level}
                onChange={handleChange}
                className="input-field"
              >
                <option value="">Any level</option>
                <option value="entry">Entry Level</option>
                <option value="intermediate">Intermediate</option>
                <option value="expert">Expert</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Estimated Duration
              </label>
              <select
                name="duration"
                value={form.duration}
                onChange={handleChange}
                className="input-field"
              >
                <option value="">Not specified</option>
                {DURATIONS.map((d) => (
                  <option key={d.value} value={d.value}>{d.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Skills */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Required Skills
            </label>
            <div className="flex gap-2 mb-3">
              <input
                value={newSkill}
                onChange={(e) => setNewSkill(e.target.value)}
                onKeyDown={handleSkillKeyDown}
                className="input-field flex-1"
                placeholder="Type a skill and press Enter"
                maxLength={50}
              />
              <button
                type="button"
                onClick={handleAddSkill}
                disabled={!newSkill.trim() || form.skills_required.length >= 15}
                className="btn-secondary py-2 px-4 text-sm whitespace-nowrap"
              >
                Add
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
              {form.skills_required.length}/15 skills
            </p>
          </div>
        </div>

        {/* Submit */}
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={() => router.back()}
            className="btn-secondary py-2.5 px-6"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className="btn-primary py-2.5 px-8"
          >
            {isSubmitting ? "Posting..." : "Post Job"}
          </button>
        </div>
      </form>
    </div>
  );
}
