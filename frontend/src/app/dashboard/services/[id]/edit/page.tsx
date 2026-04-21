"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import { servicesApi } from "@/lib/api";
import { useLocale } from "@/providers/locale-provider";
import { toast } from "sonner";

interface Category {
  id: string;
  name_ar: string;
  name_en: string;
  subcategories?: Subcategory[];
}

interface Subcategory {
  id: string;
  name_ar: string;
  name_en: string;
}

interface PackageForm {
  enabled: boolean;
  name: string;
  description: string;
  price: string;
  delivery_days: string;
  revisions: string;
  features: string;
}

type Tier = "basic" | "standard" | "premium";

const TIERS: Tier[] = ["basic", "standard", "premium"];

const DEFAULT_PACKAGE = (): PackageForm => ({
  enabled: false,
  name: "",
  description: "",
  price: "",
  delivery_days: "3",
  revisions: "1",
  features: "",
});

const t = {
  ar: {
    title: "تعديل الخدمة",
    loading: "جارٍ التحميل...",
    notFound: "الخدمة غير موجودة",
    titleLabel: "عنوان الخدمة",
    titlePlaceholder: "مثال: سأصمم لك شعاراً احترافياً",
    categoryLabel: "الفئة",
    selectCategory: "اختر فئة",
    subcategoryLabel: "الفئة الفرعية",
    selectSubcategory: "اختر فئة فرعية (اختياري)",
    descriptionLabel: "وصف الخدمة",
    descriptionPlaceholder: "اشرح ما تقدمه بالتفصيل...",
    tagsLabel: "الكلمات المفتاحية",
    tagsPlaceholder: "مثال: تصميم، شعار (افصل بفواصل)",
    pricingTitle: "الباقات",
    pricingHint: "عدّل الباقات بالكامل. باقة الأساسي إلزامية.",
    basic: "أساسي",
    standard: "قياسي",
    premium: "مميز",
    addStandard: "+ إضافة باقة قياسية",
    addPremium: "+ إضافة باقة مميزة",
    removePackage: "إزالة",
    packageName: "اسم الباقة",
    packageDesc: "وصف الباقة",
    packagePrice: "السعر (د.ع)",
    packageDays: "مدة التسليم (أيام)",
    packageRevisions: "عدد التعديلات (-1 للامحدودة)",
    packageFeatures: "المميزات (سطر لكل ميزة)",
    packageNamePlaceholder: "مثال: تصميم شعار واحد",
    packageDescPlaceholder: "ماذا يحصل العميل في هذه الباقة؟",
    cancel: "إلغاء",
    save: "حفظ التعديلات",
    saving: "جارٍ الحفظ...",
    saved: "تم حفظ التعديلات",
    saveError: "فشل حفظ التعديلات",
    resubmitNotice: "سيتم إعادة إرسال الخدمة للمراجعة بعد الحفظ.",
    revisionNote: "ملاحظة المراجعة:",
  },
  en: {
    title: "Edit Service",
    loading: "Loading...",
    notFound: "Service not found",
    titleLabel: "Service Title",
    titlePlaceholder: "e.g., I will design a professional logo",
    categoryLabel: "Category",
    selectCategory: "Select a category",
    subcategoryLabel: "Subcategory",
    selectSubcategory: "Select subcategory (optional)",
    descriptionLabel: "Description",
    descriptionPlaceholder: "Describe what you'll deliver in detail...",
    tagsLabel: "Tags",
    tagsPlaceholder: "e.g., design, logo (comma separated)",
    pricingTitle: "Packages",
    pricingHint: "Edit your packages. Basic is required.",
    basic: "Basic",
    standard: "Standard",
    premium: "Premium",
    addStandard: "+ Add Standard Package",
    addPremium: "+ Add Premium Package",
    removePackage: "Remove",
    packageName: "Package Name",
    packageDesc: "Package Description",
    packagePrice: "Price (IQD)",
    packageDays: "Delivery Days",
    packageRevisions: "Revisions (-1 for unlimited)",
    packageFeatures: "Features (one per line)",
    packageNamePlaceholder: "e.g., One logo design",
    packageDescPlaceholder: "What will the buyer receive?",
    cancel: "Cancel",
    save: "Save changes",
    saving: "Saving...",
    saved: "Changes saved",
    saveError: "Failed to save changes",
    resubmitNotice: "Your service will be re-submitted for review after saving.",
    revisionNote: "Reviewer note:",
  },
};

function PackageCard({
  tier,
  pkg,
  onChange,
  onToggle,
  locale,
  required,
}: {
  tier: Tier;
  pkg: PackageForm;
  onChange: (field: keyof PackageForm, value: string) => void;
  onToggle: () => void;
  locale: "ar" | "en";
  required: boolean;
}) {
  const str = t[locale];
  const tierLabel = tier === "basic" ? str.basic : tier === "standard" ? str.standard : str.premium;

  if (!pkg.enabled && !required) {
    return (
      <button
        type="button"
        onClick={onToggle}
        className="w-full py-3 px-4 rounded-xl border-2 border-dashed border-gray-200 text-sm font-medium text-gray-500 hover:border-brand-300 hover:text-brand-600 transition-colors"
      >
        {tier === "standard" ? str.addStandard : str.addPremium}
      </button>
    );
  }

  return (
    <div className="card p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-900">{tierLabel}</h3>
        {!required && (
          <button
            type="button"
            onClick={onToggle}
            className="text-xs text-red-500 hover:text-red-700 transition-colors"
          >
            {str.removePackage}
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="sm:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">{str.packageName} *</label>
          <input
            value={pkg.name}
            onChange={(e) => onChange("name", e.target.value)}
            className="input-field"
            placeholder={str.packageNamePlaceholder}
            required
            maxLength={80}
          />
        </div>

        <div className="sm:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">{str.packageDesc} *</label>
          <textarea
            value={pkg.description}
            onChange={(e) => onChange("description", e.target.value)}
            className="input-field resize-none"
            placeholder={str.packageDescPlaceholder}
            rows={2}
            required
            maxLength={400}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{str.packagePrice} *</label>
          <input
            type="number"
            value={pkg.price}
            onChange={(e) => onChange("price", e.target.value)}
            className="input-field"
            placeholder="5000"
            min={500}
            step={500}
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{str.packageDays} *</label>
          <input
            type="number"
            value={pkg.delivery_days}
            onChange={(e) => onChange("delivery_days", e.target.value)}
            className="input-field"
            placeholder="3"
            min={1}
            max={90}
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{str.packageRevisions}</label>
          <input
            type="number"
            value={pkg.revisions}
            onChange={(e) => onChange("revisions", e.target.value)}
            className="input-field"
            placeholder="1"
            min={-1}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{str.packageFeatures}</label>
          <textarea
            value={pkg.features}
            onChange={(e) => onChange("features", e.target.value)}
            className="input-field resize-none text-sm"
            rows={3}
            placeholder={locale === "ar" ? "مثال:\nتسليم الملفات المصدرية\nثلاثة مفاهيم أولية" : "e.g.:\nSource files\n3 initial concepts"}
          />
        </div>
      </div>
    </div>
  );
}

export default function EditServicePage() {
  const { locale } = useLocale();
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const serviceId = params?.id;
  const str = t[locale];

  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [saving, setSaving] = useState(false);
  const [categories, setCategories] = useState<Category[]>([]);
  const [revisionNote, setRevisionNote] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [subcategoryId, setSubcategoryId] = useState("");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState("");

  const [packages, setPackages] = useState<Record<Tier, PackageForm>>({
    basic: { ...DEFAULT_PACKAGE(), enabled: true },
    standard: DEFAULT_PACKAGE(),
    premium: DEFAULT_PACKAGE(),
  });

  const load = useCallback(async () => {
    if (!serviceId) return;
    try {
      const [catsRes, svcRes] = await Promise.all([
        servicesApi.getCategories(),
        servicesApi.getMine(serviceId),
      ]);
      setCategories(catsRes.data?.data || catsRes.data || []);
      const g = svcRes.data;
      setTitle(g.title || "");
      setDescription(g.description || "");
      setCategoryId(g.category_id || "");
      setSubcategoryId(g.subcategory_id || "");
      setTags((g.tags || []).join(", "));
      setRevisionNote(g.revision_note || null);

      const byTier: Record<Tier, PackageForm> = {
        basic: { ...DEFAULT_PACKAGE(), enabled: true },
        standard: DEFAULT_PACKAGE(),
        premium: DEFAULT_PACKAGE(),
      };
      for (const pkg of g.packages || []) {
        const tier = pkg.tier as Tier;
        if (!TIERS.includes(tier)) continue;
        byTier[tier] = {
          enabled: true,
          name: pkg.name ?? "",
          description: pkg.description ?? "",
          price: String(pkg.price ?? ""),
          delivery_days: String(pkg.delivery_days ?? "3"),
          revisions: String(pkg.revisions ?? "1"),
          features: (pkg.features || []).join("\n"),
        };
      }
      setPackages(byTier);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { status?: number } };
      if (axiosErr?.response?.status === 404 || axiosErr?.response?.status === 403) {
        setNotFound(true);
      } else {
        toast.error(str.saveError);
      }
    } finally {
      setLoading(false);
    }
  }, [serviceId, str.saveError]);

  useEffect(() => {
    load();
  }, [load]);

  const selectedCategory = categories.find((c) => c.id === categoryId);
  const subcategories = selectedCategory?.subcategories || [];

  const updatePackage = (tier: Tier, field: keyof PackageForm, value: string) => {
    setPackages((prev) => ({ ...prev, [tier]: { ...prev[tier], [field]: value } }));
  };

  const togglePackage = (tier: Tier) => {
    setPackages((prev) => ({ ...prev, [tier]: { ...prev[tier], enabled: !prev[tier].enabled } }));
  };

  const validate = () => {
    if (!title.trim() || title.trim().length < 10) {
      toast.error(locale === "ar" ? "العنوان يجب أن يكون 10 أحرف على الأقل" : "Title must be at least 10 characters");
      return false;
    }
    if (!categoryId) {
      toast.error(locale === "ar" ? "يرجى اختيار فئة" : "Please select a category");
      return false;
    }
    if (!description.trim() || description.trim().length < 50) {
      toast.error(locale === "ar" ? "الوصف يجب أن يكون 50 حرفاً على الأقل" : "Description must be at least 50 characters");
      return false;
    }
    const basic = packages.basic;
    if (!basic.name.trim() || basic.name.trim().length < 3) {
      toast.error(locale === "ar" ? "اسم الباقة الأساسية يجب أن يكون 3 أحرف على الأقل" : "Basic package name must be at least 3 characters");
      return false;
    }
    if (!basic.description.trim() || basic.description.trim().length < 10) {
      toast.error(locale === "ar" ? "وصف الباقة الأساسية يجب أن يكون 10 أحرف على الأقل" : "Basic package description must be at least 10 characters");
      return false;
    }
    if (!basic.price || !basic.delivery_days) {
      toast.error(locale === "ar" ? "يرجى إكمال بيانات الباقة الأساسية" : "Please complete the basic package");
      return false;
    }
    return true;
  };

  const handleSave = async () => {
    if (!serviceId || !validate()) return;
    setSaving(true);
    try {
      const enabledPackages = TIERS.filter((tier) => tier === "basic" || packages[tier].enabled).map((tier) => {
        const pkg = packages[tier];
        const features = pkg.features.split("\n").map((f) => f.trim()).filter(Boolean);
        return {
          tier,
          name: pkg.name.trim(),
          description: pkg.description.trim(),
          price: parseFloat(pkg.price),
          delivery_days: parseInt(pkg.delivery_days, 10),
          revisions: pkg.revisions ? parseInt(pkg.revisions, 10) : undefined,
          features: features.length > 0 ? features : undefined,
        };
      });

      const tagList = tags.split(",").map((x) => x.trim()).filter(Boolean);

      await servicesApi.update(serviceId, {
        title: title.trim(),
        description: description.trim(),
        category_id: categoryId,
        subcategory_id: subcategoryId || null,
        tags: tagList,
        packages: enabledPackages,
      });

      toast.success(str.saved);
      router.push("/dashboard/services");
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: unknown } } };
      const detail = axiosErr?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : str.saveError);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="max-w-2xl mx-auto py-10 text-center text-gray-500">{str.loading}</div>;
  }

  if (notFound) {
    return (
      <div className="max-w-2xl mx-auto py-10 text-center">
        <p className="text-gray-700">{str.notFound}</p>
        <button onClick={() => router.push("/dashboard/services")} className="mt-4 btn-secondary py-2 px-4">
          {str.cancel}
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{str.title}</h1>
        <p className="mt-1 text-sm text-gray-500">{str.resubmitNotice}</p>
      </div>

      {revisionNote && (
        <div className="card p-4 border-yellow-200 bg-yellow-50">
          <p className="text-sm font-medium text-yellow-900">{str.revisionNote}</p>
          <p className="text-sm text-yellow-800 mt-1 whitespace-pre-line">{revisionNote}</p>
        </div>
      )}

      <div className="card p-6 space-y-5">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{str.titleLabel} *</label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="input-field"
            placeholder={str.titlePlaceholder}
            minLength={10}
            maxLength={200}
          />
          <p className="mt-1 text-xs text-gray-400 text-end">{title.length}/200</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{str.categoryLabel} *</label>
            <select
              value={categoryId}
              onChange={(e) => { setCategoryId(e.target.value); setSubcategoryId(""); }}
              className="input-field"
            >
              <option value="">{str.selectCategory}</option>
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {locale === "ar" ? cat.name_ar : cat.name_en}
                </option>
              ))}
            </select>
          </div>

          {subcategories.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{str.subcategoryLabel}</label>
              <select
                value={subcategoryId}
                onChange={(e) => setSubcategoryId(e.target.value)}
                className="input-field"
              >
                <option value="">{str.selectSubcategory}</option>
                {subcategories.map((sub) => (
                  <option key={sub.id} value={sub.id}>
                    {locale === "ar" ? sub.name_ar : sub.name_en}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{str.descriptionLabel} *</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="input-field min-h-[160px] resize-y"
            placeholder={str.descriptionPlaceholder}
            minLength={50}
            maxLength={5000}
            rows={6}
          />
          <p className="mt-1 text-xs text-gray-400 text-end">{description.length}/5,000</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{str.tagsLabel}</label>
          <input
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            className="input-field"
            placeholder={str.tagsPlaceholder}
            maxLength={200}
          />
        </div>
      </div>

      <div className="space-y-4">
        <div className="card p-5">
          <h2 className="text-lg font-semibold text-gray-900 mb-1">{str.pricingTitle}</h2>
          <p className="text-sm text-gray-500">{str.pricingHint}</p>
        </div>
        {TIERS.map((tier) => (
          <PackageCard
            key={tier}
            tier={tier}
            pkg={packages[tier]}
            onChange={(field, value) => updatePackage(tier, field, value)}
            onToggle={() => togglePackage(tier)}
            locale={locale}
            required={tier === "basic"}
          />
        ))}
      </div>

      <div className="flex gap-3 justify-between">
        <button
          type="button"
          onClick={() => router.push("/dashboard/services")}
          className="btn-secondary py-2.5 px-6"
        >
          {str.cancel}
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="btn-primary py-2.5 px-8"
        >
          {saving ? str.saving : str.save}
        </button>
      </div>
    </div>
  );
}
