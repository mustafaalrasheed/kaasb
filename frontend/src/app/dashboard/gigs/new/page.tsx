"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { gigsApi } from "@/lib/api";
import { useLocale } from "@/providers/locale-provider";
import { toast } from "sonner";

// ---- Types ----

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

// ---- Strings ----

const t = {
  ar: {
    title: "إنشاء خدمة جديدة",
    stepOverview: "المعلومات الأساسية",
    stepPricing: "التسعير",
    stepReview: "المراجعة",
    step: "الخطوة",
    of: "من",
    next: "التالي",
    back: "رجوع",
    submit: "إرسال للمراجعة",
    submitting: "جارٍ الإرسال...",
    submitSuccess: "تم إرسال خدمتك للمراجعة!",
    submitError: "حدث خطأ أثناء الإرسال",

    // Step 1
    titleLabel: "عنوان الخدمة",
    titlePlaceholder: "مثال: سأصمم لك شعاراً احترافياً",
    categoryLabel: "الفئة",
    selectCategory: "اختر فئة",
    subcategoryLabel: "الفئة الفرعية",
    selectSubcategory: "اختر فئة فرعية (اختياري)",
    descriptionLabel: "وصف الخدمة",
    descriptionPlaceholder: "اشرح ما تقدمه بالتفصيل...",
    tagsLabel: "الكلمات المفتاحية",
    tagsPlaceholder: "مثال: تصميم، شعار، هوية بصرية (افصل بفواصل)",
    tagsHint: "أضف كلمات مفتاحية تساعد العملاء في العثور على خدمتك",

    // Step 2
    pricingTitle: "الباقات",
    pricingHint: "أضف باقة واحدة على الأقل. باقة الأساسي إلزامية.",
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

    // Step 3
    reviewTitle: "مراجعة الخدمة",
    reviewHint: "تأكد من المعلومات قبل الإرسال.",
    reviewGigTitle: "العنوان",
    reviewCategory: "الفئة",
    reviewDescription: "الوصف",
    reviewTags: "الكلمات المفتاحية",
    reviewPackages: "الباقات",
    reviewPrice: "السعر",
    reviewDays: "أيام التسليم",
    currency: "د.ع",
    days: "أيام",
    noSubcategory: "—",
    noTags: "—",
  },
  en: {
    title: "Create a New Gig",
    stepOverview: "Overview",
    stepPricing: "Pricing",
    stepReview: "Review",
    step: "Step",
    of: "of",
    next: "Next",
    back: "Back",
    submit: "Submit for Review",
    submitting: "Submitting...",
    submitSuccess: "Your gig has been submitted for review!",
    submitError: "Failed to submit gig",

    // Step 1
    titleLabel: "Gig Title",
    titlePlaceholder: "e.g., I will design a professional logo for your brand",
    categoryLabel: "Category",
    selectCategory: "Select a category",
    subcategoryLabel: "Subcategory",
    selectSubcategory: "Select subcategory (optional)",
    descriptionLabel: "Description",
    descriptionPlaceholder: "Describe what you'll deliver in detail...",
    tagsLabel: "Tags",
    tagsPlaceholder: "e.g., design, logo, branding (comma separated)",
    tagsHint: "Tags help buyers find your gig in search",

    // Step 2
    pricingTitle: "Packages",
    pricingHint: "Add at least one package. Basic is required.",
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

    // Step 3
    reviewTitle: "Review Your Gig",
    reviewHint: "Check everything before submitting.",
    reviewGigTitle: "Title",
    reviewCategory: "Category",
    reviewDescription: "Description",
    reviewTags: "Tags",
    reviewPackages: "Packages",
    reviewPrice: "Price",
    reviewDays: "Delivery days",
    currency: "IQD",
    days: "days",
    noSubcategory: "—",
    noTags: "—",
  },
};

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

// ---- Step indicator ----

function StepIndicator({
  step,
  steps,
  locale,
}: {
  step: number;
  steps: string[];
  locale: "ar" | "en";
}) {
  return (
    <div className="flex items-center justify-center gap-0 mb-8">
      {steps.map((label, i) => {
        const idx = i + 1;
        const isCompleted = idx < step;
        const isActive = idx === step;
        return (
          <div key={idx} className="flex items-center">
            <div className="flex flex-col items-center">
              <div
                className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-semibold border-2 transition-colors ${
                  isCompleted
                    ? "bg-brand-500 border-brand-500 text-white"
                    : isActive
                    ? "bg-white border-brand-500 text-brand-600"
                    : "bg-white border-gray-200 text-gray-400"
                }`}
              >
                {isCompleted ? (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  idx
                )}
              </div>
              <span
                className={`mt-1.5 text-xs font-medium ${
                  isActive ? "text-brand-600" : isCompleted ? "text-gray-700" : "text-gray-400"
                }`}
              >
                {label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div
                className={`w-16 sm:w-24 h-0.5 mx-1 mb-5 transition-colors ${
                  isCompleted ? "bg-brand-500" : "bg-gray-200"
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ---- Package Card ----

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

// ---- Main Page ----

export default function NewGigPage() {
  const { locale } = useLocale();
  const router = useRouter();
  const str = t[locale];

  const [step, setStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [categories, setCategories] = useState<Category[]>([]);

  // Step 1
  const [title, setTitle] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [subcategoryId, setSubcategoryId] = useState("");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState("");

  // Step 2 — packages
  const [packages, setPackages] = useState<Record<Tier, PackageForm>>({
    basic: { ...DEFAULT_PACKAGE(), enabled: true },
    standard: DEFAULT_PACKAGE(),
    premium: DEFAULT_PACKAGE(),
  });

  useEffect(() => {
    gigsApi.getCategories().then((res) => {
      setCategories(res.data?.data || res.data || []);
    }).catch(() => {});
  }, []);

  const selectedCategory = categories.find((c) => c.id === categoryId);
  const subcategories = selectedCategory?.subcategories || [];

  const updatePackage = (tier: Tier, field: keyof PackageForm, value: string) => {
    setPackages((prev) => ({
      ...prev,
      [tier]: { ...prev[tier], [field]: value },
    }));
  };

  const togglePackage = (tier: Tier) => {
    setPackages((prev) => ({
      ...prev,
      [tier]: { ...prev[tier], enabled: !prev[tier].enabled },
    }));
  };

  const validateStep1 = () => {
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
    return true;
  };

  const validateStep2 = () => {
    const validatePkg = (pkg: PackageForm, tierLabel: string): boolean => {
      if (!pkg.name.trim()) {
        toast.error(locale === "ar" ? `يرجى إدخال اسم باقة ${tierLabel}` : `Please enter a name for the ${tierLabel} package`);
        return false;
      }
      if (pkg.name.trim().length < 3) {
        toast.error(locale === "ar" ? `اسم باقة ${tierLabel} يجب أن يكون 3 أحرف على الأقل` : `${tierLabel} package name must be at least 3 characters`);
        return false;
      }
      if (!pkg.description.trim()) {
        toast.error(locale === "ar" ? `يرجى إدخال وصف باقة ${tierLabel}` : `Please enter a description for the ${tierLabel} package`);
        return false;
      }
      if (pkg.description.trim().length < 10) {
        toast.error(locale === "ar" ? `وصف باقة ${tierLabel} يجب أن يكون 10 أحرف على الأقل` : `${tierLabel} package description must be at least 10 characters`);
        return false;
      }
      if (!pkg.price) {
        toast.error(locale === "ar" ? `يرجى إدخال سعر باقة ${tierLabel}` : `Please enter a price for the ${tierLabel} package`);
        return false;
      }
      if (!pkg.delivery_days) {
        toast.error(locale === "ar" ? `يرجى إدخال مدة التسليم لباقة ${tierLabel}` : `Please enter delivery days for the ${tierLabel} package`);
        return false;
      }
      return true;
    };

    const str = t[locale];
    if (!validatePkg(packages.basic, str.basic)) return false;
    for (const tier of ["standard", "premium"] as Tier[]) {
      if (packages[tier].enabled && !validatePkg(packages[tier], tier === "standard" ? str.standard : str.premium)) return false;
    }
    return true;
  };

  const handleNext = () => {
    if (step === 1 && !validateStep1()) return;
    if (step === 2 && !validateStep2()) return;
    setStep((s) => s + 1);
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      const enabledPackages = TIERS.filter(
        (tier) => tier === "basic" || packages[tier].enabled
      ).map((tier) => {
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

      const tagList = tags.split(",").map((t) => t.trim()).filter(Boolean);

      await gigsApi.create({
        title: title.trim(),
        description: description.trim(),
        category_id: categoryId,
        subcategory_id: subcategoryId || undefined,
        tags: tagList.length > 0 ? tagList : undefined,
        packages: enabledPackages,
      });

      toast.success(str.submitSuccess);
      router.push("/dashboard/gigs");
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: unknown } } };
      const detail = axiosErr?.response?.data?.detail;
      if (Array.isArray(detail)) {
        // Translate common Pydantic v2 validation messages to the active locale
        const translated = detail.map((d: { msg?: string; loc?: string[]; ctx?: { min_length?: number; max_length?: number } }) => {
          const msg = d.msg || "";
          const field = d.loc?.slice(-1)[0] ?? "";
          if (locale === "ar") {
            if (msg.includes("at least") && d.ctx?.min_length) {
              return `الحقل "${field}" يجب أن يكون ${d.ctx.min_length} أحرف على الأقل`;
            }
            if (msg.includes("at most") && d.ctx?.max_length) {
              return `الحقل "${field}" يجب ألا يتجاوز ${d.ctx.max_length} حرفاً`;
            }
            if (msg.includes("required") || msg.includes("missing")) {
              return `الحقل "${field}" مطلوب`;
            }
            return msg;
          }
          return msg;
        });
        toast.error(translated.join(" | "));
      } else {
        toast.error((detail as string) || str.submitError);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const stepLabels = [str.stepOverview, str.stepPricing, str.stepReview];

  const categoryName = selectedCategory
    ? (locale === "ar" ? selectedCategory.name_ar : selectedCategory.name_en)
    : str.noSubcategory;

  const selectedSub = subcategories.find((s) => s.id === subcategoryId);
  const subcategoryName = selectedSub
    ? (locale === "ar" ? selectedSub.name_ar : selectedSub.name_en)
    : str.noSubcategory;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{str.title}</h1>
        <p className="mt-1 text-sm text-gray-500">{str.step} {step} {str.of} 3</p>
      </div>

      <StepIndicator step={step} steps={stepLabels} locale={locale} />

      {/* ---- Step 1: Overview ---- */}
      {step === 1 && (
        <div className="card p-6 space-y-5">
          <h2 className="text-lg font-semibold text-gray-900">{str.stepOverview}</h2>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{str.titleLabel} *</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="input-field"
              placeholder={str.titlePlaceholder}
              minLength={10}
              maxLength={200}
              required
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
                required
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
              required
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
            <p className="mt-1 text-xs text-gray-400">{str.tagsHint}</p>
          </div>
        </div>
      )}

      {/* ---- Step 2: Pricing ---- */}
      {step === 2 && (
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
      )}

      {/* ---- Step 3: Review ---- */}
      {step === 3 && (
        <div className="space-y-4">
          <div className="card p-5">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">{str.reviewTitle}</h2>
            <p className="text-sm text-gray-500 mb-5">{str.reviewHint}</p>

            <dl className="divide-y divide-gray-100">
              <div className="py-3 grid grid-cols-3 gap-4 text-sm">
                <dt className="font-medium text-gray-500">{str.reviewGigTitle}</dt>
                <dd className="col-span-2 text-gray-900">{title}</dd>
              </div>
              <div className="py-3 grid grid-cols-3 gap-4 text-sm">
                <dt className="font-medium text-gray-500">{str.reviewCategory}</dt>
                <dd className="col-span-2 text-gray-900">
                  {categoryName}
                  {selectedSub && <span className="text-gray-400"> / {subcategoryName}</span>}
                </dd>
              </div>
              <div className="py-3 grid grid-cols-3 gap-4 text-sm">
                <dt className="font-medium text-gray-500">{str.reviewDescription}</dt>
                <dd className="col-span-2 text-gray-700 whitespace-pre-line line-clamp-5">{description}</dd>
              </div>
              <div className="py-3 grid grid-cols-3 gap-4 text-sm">
                <dt className="font-medium text-gray-500">{str.reviewTags}</dt>
                <dd className="col-span-2 text-gray-700">
                  {tags.trim() ? (
                    <div className="flex flex-wrap gap-1.5">
                      {tags.split(",").map((tag) => tag.trim()).filter(Boolean).map((tag) => (
                        <span key={tag} className="px-2 py-0.5 rounded-full text-xs bg-gray-100 text-gray-700 border border-gray-200">
                          {tag}
                        </span>
                      ))}
                    </div>
                  ) : (
                    str.noTags
                  )}
                </dd>
              </div>
            </dl>
          </div>

          {/* Packages summary */}
          <div className="card p-5">
            <h3 className="font-semibold text-gray-900 mb-4">{str.reviewPackages}</h3>
            <div className="space-y-3">
              {TIERS.filter((tier) => tier === "basic" || packages[tier].enabled).map((tier) => {
                const pkg = packages[tier];
                const tierLabel = tier === "basic" ? str.basic : tier === "standard" ? str.standard : str.premium;
                return (
                  <div key={tier} className="flex items-center justify-between py-3 border-b border-gray-100 last:border-0">
                    <div>
                      <p className="font-medium text-gray-900">{tierLabel} — {pkg.name}</p>
                      <p className="text-sm text-gray-500 mt-0.5 line-clamp-1">{pkg.description}</p>
                    </div>
                    <div className="text-end shrink-0 ms-4">
                      <p className="font-semibold text-gray-900">{parseFloat(pkg.price || "0").toLocaleString(locale === "ar" ? "ar" : "en")} {str.currency}</p>
                      <p className="text-xs text-gray-400">{pkg.delivery_days} {str.days}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Navigation */}
      <div className="flex gap-3 justify-between">
        <button
          type="button"
          onClick={() => step === 1 ? router.push("/dashboard/gigs") : setStep((s) => s - 1)}
          className="btn-secondary py-2.5 px-6"
        >
          {str.back}
        </button>

        {step < 3 ? (
          <button
            type="button"
            onClick={handleNext}
            className="btn-primary py-2.5 px-8"
          >
            {str.next}
          </button>
        ) : (
          <button
            type="button"
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="btn-primary py-2.5 px-8"
          >
            {isSubmitting ? str.submitting : str.submit}
          </button>
        )}
      </div>
    </div>
  );
}
