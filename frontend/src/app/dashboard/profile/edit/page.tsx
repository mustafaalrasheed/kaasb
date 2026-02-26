"use client";

import { useState, useRef, useEffect } from "react";
import { useAuthStore } from "@/lib/auth-store";
import { usersApi } from "@/lib/api";
import { toast } from "sonner";

const EXPERIENCE_LEVELS = [
  { value: "entry", label: "Entry Level" },
  { value: "intermediate", label: "Intermediate" },
  { value: "expert", label: "Expert" },
];

const COUNTRIES = [
  "Iraq", "United States", "United Kingdom", "Canada", "Germany",
  "France", "India", "Pakistan", "Egypt", "Saudi Arabia",
  "UAE", "Jordan", "Turkey", "Australia", "Netherlands",
  "Sweden", "Brazil", "Japan", "South Korea", "Other",
];

export default function EditProfilePage() {
  const { user, fetchUser } = useAuthStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isUploadingAvatar, setIsUploadingAvatar] = useState(false);
  const [newSkill, setNewSkill] = useState("");

  const [form, setForm] = useState({
    display_name: "",
    bio: "",
    country: "",
    city: "",
    timezone: "",
    phone: "",
    title: "",
    hourly_rate: "",
    experience_level: "",
    portfolio_url: "",
    skills: [] as string[],
  });

  // Load current user data into form
  useEffect(() => {
    if (user) {
      setForm({
        display_name: user.display_name || "",
        bio: user.bio || "",
        country: user.country || "",
        city: user.city || "",
        timezone: user.timezone || "",
        phone: user.phone || "",
        title: user.title || "",
        hourly_rate: user.hourly_rate?.toString() || "",
        experience_level: user.experience_level || "",
        portfolio_url: user.portfolio_url || "",
        skills: user.skills || [],
      });
    }
  }, [user]);

  const isFreelancer = user?.primary_role === "freelancer";

  // === Handlers ===

  const handleChange = (
    e: React.ChangeEvent<
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >
  ) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleAddSkill = () => {
    const skill = newSkill.trim();
    if (skill && !form.skills.includes(skill) && form.skills.length < 20) {
      setForm({ ...form, skills: [...form.skills, skill] });
      setNewSkill("");
    }
  };

  const handleRemoveSkill = (skillToRemove: string) => {
    setForm({
      ...form,
      skills: form.skills.filter((s) => s !== skillToRemove),
    });
  };

  const handleSkillKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddSkill();
    }
  };

  const handleAvatarClick = () => {
    fileInputRef.current?.click();
  };

  const handleAvatarChange = async (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Client-side validation
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      toast.error("Image must be smaller than 10MB");
      return;
    }
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      toast.error("Only JPEG, PNG, and WebP images are allowed");
      return;
    }

    setIsUploadingAvatar(true);
    try {
      await usersApi.uploadAvatar(file);
      await fetchUser();
      toast.success("Avatar updated!");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to upload avatar");
    } finally {
      setIsUploadingAvatar(false);
      // Reset file input
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleRemoveAvatar = async () => {
    try {
      await usersApi.removeAvatar();
      await fetchUser();
      toast.success("Avatar removed");
    } catch {
      toast.error("Failed to remove avatar");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      // Build update payload with only changed/non-empty fields
      const payload: Record<string, unknown> = {};

      if (form.display_name) payload.display_name = form.display_name;
      if (form.bio) payload.bio = form.bio;
      if (form.country) payload.country = form.country;
      if (form.city) payload.city = form.city;
      if (form.timezone) payload.timezone = form.timezone;
      if (form.phone) payload.phone = form.phone;

      if (isFreelancer) {
        if (form.title) payload.title = form.title;
        if (form.hourly_rate) payload.hourly_rate = parseFloat(form.hourly_rate);
        if (form.experience_level) payload.experience_level = form.experience_level;
        if (form.portfolio_url) payload.portfolio_url = form.portfolio_url;
        if (form.skills.length > 0) payload.skills = form.skills;
      }

      if (Object.keys(payload).length === 0) {
        toast.error("No changes to save");
        setIsSubmitting(false);
        return;
      }

      await usersApi.updateProfile(payload);
      await fetchUser();
      toast.success("Profile updated successfully!");
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Failed to update profile");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!user) return null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Edit Profile</h1>
        <p className="mt-1 text-gray-600">
          Update your profile information visible to others on Kaasb.
        </p>
      </div>

      {/* Avatar Section */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Profile Photo
        </h2>
        <div className="flex items-center gap-6">
          <button
            onClick={handleAvatarClick}
            disabled={isUploadingAvatar}
            className="relative w-24 h-24 rounded-full overflow-hidden bg-brand-100 flex items-center justify-center cursor-pointer hover:opacity-80 transition-opacity group"
          >
            {user.avatar_url ? (
              <img
                src={`http://localhost:8000${user.avatar_url}`}
                alt="Avatar"
                className="w-full h-full object-cover"
              />
            ) : (
              <span className="text-3xl font-bold text-brand-500">
                {user.first_name[0]}
                {user.last_name[0]}
              </span>
            )}
            <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
              <span className="text-white text-xs font-medium">
                {isUploadingAvatar ? "Uploading..." : "Change"}
              </span>
            </div>
          </button>

          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={handleAvatarChange}
            className="hidden"
          />

          <div>
            <button
              onClick={handleAvatarClick}
              disabled={isUploadingAvatar}
              className="btn-secondary py-2 px-4 text-sm"
            >
              {isUploadingAvatar ? "Uploading..." : "Upload Photo"}
            </button>
            {user.avatar_url && (
              <button
                onClick={handleRemoveAvatar}
                className="ml-3 text-sm text-danger-500 hover:text-danger-700"
              >
                Remove
              </button>
            )}
            <p className="mt-2 text-xs text-gray-500">
              JPEG, PNG, or WebP. Max 10MB.
            </p>
          </div>
        </div>
      </div>

      {/* Profile Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Info */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Basic Information
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Display Name
              </label>
              <input
                name="display_name"
                value={form.display_name}
                onChange={handleChange}
                className="input-field"
                placeholder={`${user.first_name} ${user.last_name}`}
                maxLength={100}
              />
              <p className="mt-1 text-xs text-gray-500">
                How your name appears to others (leave blank to use your full name)
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Phone Number
              </label>
              <input
                name="phone"
                value={form.phone}
                onChange={handleChange}
                className="input-field"
                placeholder="+964 XXX XXX XXXX"
                maxLength={20}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Country
              </label>
              <select
                name="country"
                value={form.country}
                onChange={handleChange}
                className="input-field"
              >
                <option value="">Select country</option>
                {COUNTRIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                City
              </label>
              <input
                name="city"
                value={form.city}
                onChange={handleChange}
                className="input-field"
                placeholder="Your city"
                maxLength={100}
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Bio
              </label>
              <textarea
                name="bio"
                value={form.bio}
                onChange={handleChange}
                className="input-field min-h-[120px] resize-y"
                placeholder="Tell clients about yourself, your experience, and what you're passionate about..."
                maxLength={2000}
                rows={5}
              />
              <p className="mt-1 text-xs text-gray-500 text-right">
                {form.bio.length}/2000
              </p>
            </div>
          </div>
        </div>

        {/* Freelancer-specific section */}
        {isFreelancer && (
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Professional Details
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Professional Title
                </label>
                <input
                  name="title"
                  value={form.title}
                  onChange={handleChange}
                  className="input-field"
                  placeholder="e.g., Senior Python Developer"
                  maxLength={200}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Hourly Rate (USD)
                </label>
                <input
                  name="hourly_rate"
                  type="number"
                  value={form.hourly_rate}
                  onChange={handleChange}
                  className="input-field"
                  placeholder="25"
                  min={5}
                  max={500}
                  step={0.5}
                />
              </div>

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
                  <option value="">Select level</option>
                  {EXPERIENCE_LEVELS.map((level) => (
                    <option key={level.value} value={level.value}>
                      {level.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Portfolio URL
                </label>
                <input
                  name="portfolio_url"
                  value={form.portfolio_url}
                  onChange={handleChange}
                  className="input-field"
                  placeholder="https://your-portfolio.com"
                  maxLength={500}
                />
              </div>

              {/* Skills Editor */}
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Skills
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
                    disabled={!newSkill.trim() || form.skills.length >= 20}
                    className="btn-secondary py-2 px-4 text-sm whitespace-nowrap"
                  >
                    Add
                  </button>
                </div>

                {/* Skills tags */}
                {form.skills.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {form.skills.map((skill) => (
                      <span
                        key={skill}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium bg-brand-50 text-brand-700 border border-brand-200"
                      >
                        {skill}
                        <button
                          type="button"
                          onClick={() => handleRemoveSkill(skill)}
                          className="text-brand-400 hover:text-brand-600 ml-0.5"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                )}
                <p className="mt-2 text-xs text-gray-500">
                  {form.skills.length}/20 skills added
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Submit */}
        <div className="flex justify-end gap-3">
          <button
            type="submit"
            disabled={isSubmitting}
            className="btn-primary py-2.5 px-8"
          >
            {isSubmitting ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </form>
    </div>
  );
}
