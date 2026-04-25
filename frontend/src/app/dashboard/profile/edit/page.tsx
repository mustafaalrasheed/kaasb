"use client";

import { useState, useRef, useEffect } from "react";
import { useAuthStore } from "@/lib/auth-store";
import { useEffectiveRole } from "@/lib/use-active-mode";
import { usersApi } from "@/lib/api";
import { backendUrl, getApiError } from "@/lib/utils";
import { useLocale } from "@/providers/locale-provider";
import { toast } from "sonner";

const EXPERIENCE_LEVELS = [
  { value: "entry",        labelAr: "مبتدئ",      labelEn: "Entry Level" },
  { value: "intermediate", labelAr: "متوسط",      labelEn: "Intermediate" },
  { value: "expert",       labelAr: "خبير",        labelEn: "Expert" },
];

const COUNTRIES = [
  { value: "Iraq",                 labelAr: "العراق",                   labelEn: "Iraq" },
  { value: "United States",        labelAr: "الولايات المتحدة",          labelEn: "United States" },
  { value: "United Kingdom",       labelAr: "المملكة المتحدة",           labelEn: "United Kingdom" },
  { value: "Canada",               labelAr: "كندا",                      labelEn: "Canada" },
  { value: "Germany",              labelAr: "ألمانيا",                   labelEn: "Germany" },
  { value: "France",               labelAr: "فرنسا",                     labelEn: "France" },
  { value: "India",                labelAr: "الهند",                     labelEn: "India" },
  { value: "Pakistan",             labelAr: "باكستان",                   labelEn: "Pakistan" },
  { value: "Egypt",                labelAr: "مصر",                       labelEn: "Egypt" },
  { value: "Saudi Arabia",         labelAr: "المملكة العربية السعودية",  labelEn: "Saudi Arabia" },
  { value: "UAE",                  labelAr: "الإمارات",                  labelEn: "UAE" },
  { value: "Jordan",               labelAr: "الأردن",                    labelEn: "Jordan" },
  { value: "Turkey",               labelAr: "تركيا",                     labelEn: "Turkey" },
  { value: "Australia",            labelAr: "أستراليا",                  labelEn: "Australia" },
  { value: "Netherlands",          labelAr: "هولندا",                    labelEn: "Netherlands" },
  { value: "Sweden",               labelAr: "السويد",                    labelEn: "Sweden" },
  { value: "Brazil",               labelAr: "البرازيل",                  labelEn: "Brazil" },
  { value: "Japan",                labelAr: "اليابان",                   labelEn: "Japan" },
  { value: "South Korea",          labelAr: "كوريا الجنوبية",            labelEn: "South Korea" },
  { value: "Other",                labelAr: "أخرى",                      labelEn: "Other" },
];

export default function EditProfilePage() {
  const { user, isAuthenticated, fetchUser } = useAuthStore();
  const effectiveRole = useEffectiveRole(user, isAuthenticated);
  const { locale } = useLocale();
  const ar = locale === "ar";
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
    experience_level: "",
    portfolio_url: "",
    skills: [] as string[],
  });

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
        experience_level: user.experience_level || "",
        portfolio_url: user.portfolio_url || "",
        skills: user.skills || [],
      });
    }
  }, [user]);

  // Profile editor surfaces freelancer-only fields (skills, experience,
  // portfolio) when the user is acting as a seller. Following the active
  // mode here lets a client who flipped to selling start filling those
  // out without first having to change their primary_role.
  const isFreelancer = effectiveRole === "freelancer";

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
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
    setForm({ ...form, skills: form.skills.filter((s) => s !== skillToRemove) });
  };

  const handleSkillKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddSkill();
    }
  };

  const handleAvatarClick = () => fileInputRef.current?.click();

  const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      toast.error(ar ? "يجب أن تكون الصورة أصغر من 10 ميجابايت" : "Image must be smaller than 10 MB");
      return;
    }
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      toast.error(ar ? "يُسمح فقط بصور JPEG و PNG و WebP" : "Only JPEG, PNG and WebP images are allowed");
      return;
    }
    setIsUploadingAvatar(true);
    try {
      await usersApi.uploadAvatar(file);
      await fetchUser();
      toast.success(ar ? "تم تحديث الصورة الشخصية" : "Profile photo updated");
    } catch (err: unknown) {
      toast.error(getApiError(err, ar ? "تعذّر رفع الصورة" : "Failed to upload image"));
    } finally {
      setIsUploadingAvatar(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleRemoveAvatar = async () => {
    try {
      await usersApi.removeAvatar();
      await fetchUser();
      toast.success(ar ? "تم حذف الصورة الشخصية" : "Profile photo removed");
    } catch {
      toast.error(ar ? "تعذّر حذف الصورة" : "Failed to remove photo");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const payload: Record<string, unknown> = {};
      if (form.display_name) payload.display_name = form.display_name;
      if (form.bio) payload.bio = form.bio;
      if (form.country) payload.country = form.country;
      if (form.city) payload.city = form.city;
      if (form.timezone) payload.timezone = form.timezone;
      if (form.phone) payload.phone = form.phone;

      if (isFreelancer) {
        if (form.title) payload.title = form.title;
        if (form.experience_level) payload.experience_level = form.experience_level;
        if (form.portfolio_url) payload.portfolio_url = form.portfolio_url;
        if (form.skills.length > 0) payload.skills = form.skills;
      }

      if (Object.keys(payload).length === 0) {
        toast.error(ar ? "لا توجد تغييرات للحفظ" : "No changes to save");
        setIsSubmitting(false);
        return;
      }

      await usersApi.updateProfile(payload);
      await fetchUser();
      toast.success(ar ? "تم تحديث الملف الشخصي بنجاح" : "Profile updated successfully");
    } catch (err: unknown) {
      toast.error(getApiError(err, ar ? "تعذّر تحديث الملف الشخصي" : "Failed to update profile"));
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!user) return null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          {ar ? "تعديل الملف الشخصي" : "Edit Profile"}
        </h1>
        <p className="mt-1 text-gray-600">
          {ar ? "تحديث معلوماتك الظاهرة للآخرين على كاسب." : "Update your information visible to others on Kaasb."}
        </p>
      </div>

      {/* Avatar Section */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          {ar ? "الصورة الشخصية" : "Profile Photo"}
        </h2>
        <div className="flex items-center gap-6">
          <button
            onClick={handleAvatarClick}
            disabled={isUploadingAvatar}
            className="relative w-24 h-24 rounded-full overflow-hidden bg-brand-100 flex items-center justify-center cursor-pointer hover:opacity-80 transition-opacity group"
          >
            {user.avatar_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={`${backendUrl(user.avatar_url)}?v=${new Date(user.updated_at).getTime()}`} alt={ar ? "صورة شخصية" : "Profile photo"} className="w-full h-full object-cover" />
            ) : (
              <span className="text-3xl font-bold text-brand-500">
                {user.first_name[0]}{user.last_name[0]}
              </span>
            )}
            <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
              <span className="text-white text-xs font-medium">
                {isUploadingAvatar ? (ar ? "جاري الرفع..." : "Uploading...") : (ar ? "تغيير" : "Change")}
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
              {isUploadingAvatar ? (ar ? "جاري الرفع..." : "Uploading...") : (ar ? "رفع صورة" : "Upload Photo")}
            </button>
            {user.avatar_url && (
              <button
                onClick={handleRemoveAvatar}
                className="ms-3 text-sm text-danger-500 hover:text-danger-700"
              >
                {ar ? "حذف" : "Remove"}
              </button>
            )}
            <p className="mt-2 text-xs text-gray-500">
              {ar ? "JPEG أو PNG أو WebP. الحد الأقصى 10 ميجابايت." : "JPEG, PNG or WebP. Max 10 MB."}
            </p>
          </div>
        </div>
      </div>

      {/* Profile Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Info */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            {ar ? "المعلومات الأساسية" : "Basic Information"}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {ar ? "الاسم المعروض" : "Display Name"}
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
                {ar
                  ? "كيف يظهر اسمك للآخرين (اتركه فارغاً لاستخدام اسمك الكامل)"
                  : "How your name appears to others (leave blank to use your full name)"}
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {ar ? "رقم الهاتف" : "Phone Number"}
              </label>
              <input
                name="phone"
                value={form.phone}
                onChange={handleChange}
                className="input-field"
                placeholder="+964 7XX XXX XXXX"
                maxLength={20}
                dir="ltr"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {ar ? "الدولة" : "Country"}
              </label>
              <select name="country" value={form.country} onChange={handleChange} className="input-field">
                <option value="">{ar ? "اختر الدولة" : "Select country"}</option>
                {COUNTRIES.map((c) => (
                  <option key={c.value} value={c.value}>
                    {ar ? c.labelAr : c.labelEn}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {ar ? "المدينة" : "City"}
              </label>
              <input
                name="city"
                value={form.city}
                onChange={handleChange}
                className="input-field"
                placeholder={ar ? "مدينتك" : "Your city"}
                maxLength={100}
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {ar ? "نبذة شخصية" : "Bio"}
              </label>
              <textarea
                name="bio"
                value={form.bio}
                onChange={handleChange}
                className="input-field min-h-[120px] resize-y"
                placeholder={ar
                  ? "اكتب نبذة عنك، عن خبرتك، وما تتقنه..."
                  : "Write about yourself, your experience, and what you excel at..."}
                maxLength={2000}
                rows={5}
              />
              <p className="mt-1 text-xs text-gray-500 text-end">{form.bio.length}/2000</p>
            </div>
          </div>
        </div>

        {/* Freelancer-specific section */}
        {isFreelancer && (
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              {ar ? "التفاصيل المهنية" : "Professional Details"}
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {ar ? "اللقب المهني" : "Professional Title"}
                </label>
                <input
                  name="title"
                  value={form.title}
                  onChange={handleChange}
                  className="input-field"
                  placeholder={ar ? "مثال: مطور Python متقدم" : "e.g. Senior Python Developer"}
                  maxLength={200}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {ar ? "مستوى الخبرة" : "Experience Level"}
                </label>
                <select name="experience_level" value={form.experience_level} onChange={handleChange} className="input-field">
                  <option value="">{ar ? "اختر المستوى" : "Select level"}</option>
                  {EXPERIENCE_LEVELS.map((level) => (
                    <option key={level.value} value={level.value}>
                      {ar ? level.labelAr : level.labelEn}
                    </option>
                  ))}
                </select>
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {ar ? "رابط معرض الأعمال" : "Portfolio URL"}
                </label>
                <input
                  name="portfolio_url"
                  value={form.portfolio_url}
                  onChange={handleChange}
                  className="input-field"
                  placeholder="https://portfolio-url.com"
                  maxLength={500}
                  dir="ltr"
                />
              </div>

              {/* Skills Editor */}
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {ar ? "المهارات" : "Skills"}
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
                    disabled={!newSkill.trim() || form.skills.length >= 20}
                    className="btn-secondary py-2 px-4 text-sm whitespace-nowrap"
                  >
                    {ar ? "إضافة" : "Add"}
                  </button>
                </div>

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
                          className="text-brand-400 hover:text-brand-600"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                )}
                <p className="mt-2 text-xs text-gray-500">
                  {form.skills.length}/20 {ar ? "مهارة" : "skills"}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Submit */}
        <div className="flex gap-3">
          <button type="submit" disabled={isSubmitting} className="btn-primary py-2.5 px-8">
            {isSubmitting ? (ar ? "جاري الحفظ..." : "Saving...") : (ar ? "حفظ التغييرات" : "Save Changes")}
          </button>
        </div>
      </form>
    </div>
  );
}
