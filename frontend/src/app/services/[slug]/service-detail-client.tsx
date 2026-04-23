"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { servicesApi } from "@/lib/api";
import { useLocale } from "@/providers/locale-provider";
import { backendUrl } from "@/lib/utils";
import { toast } from "sonner";

// ---- Types ----

interface ServicePackage {
  id: string;
  tier: "basic" | "standard" | "premium";
  name: string;
  description: string;
  price: number;
  delivery_days: number;
  revisions?: number;
  features?: string[];
}

interface ServiceFreelancer {
  id: string;
  username: string;
  first_name: string;
  last_name: string;
  display_name?: string;
  avatar_url?: string;
  avg_rating?: number;
  total_reviews?: number;
  bio?: string;
}

interface ServiceDetail {
  id: string;
  slug: string;
  title: string;
  description: string;
  tags?: string[];
  images?: string[];
  thumbnail_url?: string;
  packages: ServicePackage[];
  freelancer: ServiceFreelancer;
  avg_rating?: number;
  total_orders?: number;
  review_count?: number;
  status: string;
}

// ---- Strings ----

const t = {
  ar: {
    loading: "جارٍ التحميل...",
    error: "تعذّر تحميل الخدمة. يرجى المحاولة مرة أخرى.",
    timeout: "انتهت مهلة التحميل. تحقّق من اتصالك بالإنترنت ثم أعد المحاولة.",
    retry: "إعادة المحاولة",
    notFound: "الخدمة غير موجودة",
    backToServices: "العودة إلى الخدمات",
    description: "وصف الخدمة",
    tags: "الكلمات المفتاحية",
    orderNow: "اطلب الآن",
    contactFreelancer: "تواصل مع المستقل",
    about: "عن المستقل",
    rating: "التقييم",
    orders: "طلب مكتمل",
    basic: "أساسي",
    standard: "قياسي",
    premium: "مميز",
    deliveryDays: (n: number) => `${n} ${n === 1 ? "يوم" : "أيام"} تسليم`,
    revisions: (n: number) => `${n} تعديل`,
    unlimitedRevisions: "تعديلات غير محدودة",
    currency: "د.ع",
    startingAt: "يبدأ من",
    requirements: "متطلبات المشروع",
    requirementsPlaceholder: "اشرح متطلباتك بالتفصيل...",
    submitOrder: "تأكيد الطلب",
    cancel: "إلغاء",
    orderSuccess: "تم إرسال طلبك! جاري التوجيه للدفع...",
    orderError: "حدث خطأ أثناء إرسال الطلب",
    imagePrev: "الصورة السابقة",
    imageNext: "الصورة التالية",
    noRating: "لا يوجد تقييم بعد",
  },
  en: {
    loading: "Loading...",
    error: "Failed to load this service. Please try again.",
    timeout: "Loading timed out. Check your connection and try again.",
    retry: "Try again",
    notFound: "Service not found",
    backToServices: "Back to Services",
    description: "About This Service",
    tags: "Tags",
    orderNow: "Order Now",
    contactFreelancer: "Contact Freelancer",
    about: "About the Freelancer",
    rating: "Rating",
    orders: "completed orders",
    basic: "Basic",
    standard: "Standard",
    premium: "Premium",
    deliveryDays: (n: number) => `${n} day${n !== 1 ? "s" : ""} delivery`,
    revisions: (n: number) => `${n} revision${n !== 1 ? "s" : ""}`,
    unlimitedRevisions: "Unlimited revisions",
    currency: "IQD",
    startingAt: "Starting at",
    requirements: "Project Requirements",
    requirementsPlaceholder: "Describe your requirements in detail...",
    submitOrder: "Confirm Order",
    cancel: "Cancel",
    orderSuccess: "Order placed! Redirecting to payment...",
    orderError: "Failed to place order",
    imagePrev: "Previous image",
    imageNext: "Next image",
    noRating: "No reviews yet",
  },
};

const TIER_KEYS = ["basic", "standard", "premium"] as const;

// ---- Skeleton (shown during initial load + retries) ----

function ServiceDetailSkeleton() {
  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-pulse">
      <div className="h-4 w-32 bg-gray-200 rounded mb-6" />
      <div className="flex flex-col lg:flex-row gap-8">
        <div className="flex-1 min-w-0 space-y-6">
          <div className="h-8 w-3/4 bg-gray-200 rounded" />
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gray-200" />
            <div className="space-y-2">
              <div className="h-3 w-32 bg-gray-200 rounded" />
              <div className="h-3 w-20 bg-gray-200 rounded" />
            </div>
          </div>
          <div className="aspect-video rounded-xl bg-gray-200" />
          <div className="card p-6 space-y-3">
            <div className="h-4 w-40 bg-gray-200 rounded" />
            <div className="h-3 w-full bg-gray-200 rounded" />
            <div className="h-3 w-5/6 bg-gray-200 rounded" />
            <div className="h-3 w-4/6 bg-gray-200 rounded" />
          </div>
        </div>
        <div className="w-full lg:w-[340px] shrink-0">
          <div className="card p-5 space-y-4">
            <div className="h-5 w-2/3 bg-gray-200 rounded" />
            <div className="h-3 w-full bg-gray-200 rounded" />
            <div className="h-3 w-3/4 bg-gray-200 rounded" />
            <div className="h-10 w-full bg-gray-200 rounded" />
          </div>
        </div>
      </div>
    </div>
  );
}

// ---- Image Carousel ----

function ImageCarousel({ images, title, locale }: { images: string[]; title: string; locale: "ar" | "en" }) {
  const [current, setCurrent] = useState(0);
  const str = t[locale];

  if (images.length === 0) {
    return (
      <div className="aspect-video rounded-xl bg-gray-100 flex items-center justify-center">
        <svg className="w-16 h-16 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      </div>
    );
  }

  return (
    <div className="relative">
      <div className="aspect-video rounded-xl overflow-hidden bg-gray-100">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={backendUrl(images[current])}
          alt={`${title} - ${current + 1}`}
          className="w-full h-full object-cover"
        />
      </div>

      {images.length > 1 && (
        <>
          <button
            onClick={() => setCurrent((c) => (c - 1 + images.length) % images.length)}
            aria-label={str.imagePrev}
            className="absolute left-3 top-1/2 -translate-y-1/2 w-9 h-9 rounded-full bg-white/80 shadow flex items-center justify-center hover:bg-white transition-colors"
          >
            <svg className="w-5 h-5 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <button
            onClick={() => setCurrent((c) => (c + 1) % images.length)}
            aria-label={str.imageNext}
            className="absolute right-3 top-1/2 -translate-y-1/2 w-9 h-9 rounded-full bg-white/80 shadow flex items-center justify-center hover:bg-white transition-colors"
          >
            <svg className="w-5 h-5 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>

          {/* Dots */}
          <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-1.5">
            {images.map((_, i) => (
              <button
                key={i}
                onClick={() => setCurrent(i)}
                className={`w-2 h-2 rounded-full transition-colors ${i === current ? "bg-white" : "bg-white/50"}`}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ---- Order Modal ----

function OrderModal({
  service,
  packageId,
  onClose,
  locale,
}: {
  service: ServiceDetail;
  packageId: string;
  onClose: () => void;
  locale: "ar" | "en";
}) {
  const [requirements, setRequirements] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const str = t[locale];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const res = await servicesApi.placeOrder({
        service_id: service.id,
        package_id: packageId,
        requirements: requirements.trim() || undefined,
      });
      toast.success(str.orderSuccess);
      onClose();
      // Redirect to Qi Card payment page (or mock URL in dev)
      const paymentUrl = (res.data as { payment_url?: string }).payment_url;
      if (paymentUrl) {
        window.location.href = paymentUrl;
      }
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      toast.error(axiosErr?.response?.data?.detail || str.orderError);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
        <div className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">{str.requirements}</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <textarea
              value={requirements}
              onChange={(e) => setRequirements(e.target.value)}
              className="input-field min-h-[140px] resize-y"
              placeholder={str.requirementsPlaceholder}
              rows={5}
            />
            <div className="flex gap-3">
              <button
                type="submit"
                disabled={isSubmitting}
                className="btn-primary flex-1 py-2.5"
              >
                {isSubmitting ? "..." : str.submitOrder}
              </button>
              <button
                type="button"
                onClick={onClose}
                className="btn-secondary py-2.5 px-5"
              >
                {str.cancel}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

// ---- Main Client Component ----

export default function ServiceDetailClient() {
  const params = useParams();
  const slug = params.slug as string;
  const { locale } = useLocale();
  const str = t[locale];

  const [service, setService] = useState<ServiceDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadTick, setReloadTick] = useState(0);
  const [activePackageTier, setActivePackageTier] = useState<"basic" | "standard" | "premium">("basic");
  const [showOrderModal, setShowOrderModal] = useState(false);

  useEffect(() => {
    let cancelled = false;

    // Retry with exponential backoff. Hard cap at 8s total so the spinner
    // never runs indefinitely — matches the "clear error feedback" best
    // practice the user requested.
    async function loadWithRetry() {
      const controller = new AbortController();
      const hardTimeout = setTimeout(() => controller.abort(), 8000);
      const attempts = [0, 500, 1500]; // 3 tries: immediate, +0.5s, +1.5s

      let lastErr: unknown = null;
      for (let i = 0; i < attempts.length; i++) {
        if (cancelled) return;
        if (attempts[i] > 0) {
          await new Promise((r) => setTimeout(r, attempts[i]));
          if (cancelled || controller.signal.aborted) break;
        }
        try {
          const res = await servicesApi.getBySlug(slug);
          clearTimeout(hardTimeout);
          if (cancelled) return;
          const data = res.data?.data || res.data;
          setService(data);
          if (data?.packages?.length > 0) {
            setActivePackageTier(data.packages[0].tier);
          }
          setError("");
          setIsLoading(false);
          return;
        } catch (err: unknown) {
          lastErr = err;
          const status = (err as { response?: { status?: number } })?.response?.status;
          // Don't retry on definitive 4xx — the service genuinely isn't available.
          if (status === 404 || status === 403 || status === 401) break;
          if (controller.signal.aborted) break;
        }
      }

      clearTimeout(hardTimeout);
      if (cancelled) return;
      const status = (lastErr as { response?: { status?: number } })?.response?.status;
      if (status === 404) setError(str.notFound);
      else if (controller.signal.aborted) setError(str.timeout);
      else setError(str.error);
      setIsLoading(false);
    }

    if (slug) {
      setIsLoading(true);
      setError("");
      loadWithRetry();
    }
    return () => {
      cancelled = true;
    };
  }, [slug, locale, reloadTick]); // eslint-disable-line react-hooks/exhaustive-deps

  if (isLoading) {
    return <ServiceDetailSkeleton />;
  }

  if (error || !service) {
    const isNotFound = error === str.notFound;
    return (
      <div className="min-h-[60vh] flex items-center justify-center text-center px-4">
        <div className="max-w-md">
          <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-4">
            <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d={isNotFound
                  ? "M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  : "M12 9v2m0 4h.01M4.93 19h14.14a2 2 0 001.74-3l-7.07-12.25a2 2 0 00-3.48 0L3.19 16a2 2 0 001.74 3z"} />
            </svg>
          </div>
          <p className="text-lg font-semibold text-gray-900">{error || str.notFound}</p>
          <div className="mt-4 flex items-center justify-center gap-3">
            {!isNotFound && (
              <button
                onClick={() => setReloadTick((n) => n + 1)}
                className="btn-primary py-2 px-5 text-sm"
              >
                {str.retry}
              </button>
            )}
            <Link href="/services" className="text-brand-500 hover:text-brand-600 text-sm">
              {str.backToServices}
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const freelancerName = service.freelancer.display_name ||
    `${service.freelancer.first_name} ${service.freelancer.last_name}`;

  // Packages indexed by tier
  const packagesByTier = Object.fromEntries(
    service.packages.map((p) => [p.tier, p])
  ) as Record<string, ServicePackage>;

  const availableTiers = TIER_KEYS.filter((tier) => packagesByTier[tier]);
  const activePackage = packagesByTier[activePackageTier] || service.packages[0];

  const tierLabel = (tier: string) => {
    if (tier === "basic") return str.basic;
    if (tier === "standard") return str.standard;
    return str.premium;
  };

  const images = service.images?.length
    ? service.images
    : service.thumbnail_url
    ? [service.thumbnail_url]
    : [];

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Back link */}
      <Link href="/services" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-brand-600 mb-6 transition-colors">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        {str.backToServices}
      </Link>

      <div className="flex flex-col lg:flex-row gap-8">
        {/* Left — Main content */}
        <div className="flex-1 min-w-0 space-y-6">
          <h1 className="text-2xl font-bold text-gray-900">{service.title}</h1>

          {/* Freelancer summary */}
          <div className="flex items-center gap-3">
            <Link href={`/profile/${service.freelancer.username}`}>
              <div className="w-10 h-10 rounded-full overflow-hidden bg-brand-100 flex items-center justify-center shrink-0">
                {service.freelancer.avatar_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={backendUrl(service.freelancer.avatar_url)} alt={freelancerName} className="w-full h-full object-cover" />
                ) : (
                  <span className="text-sm font-bold text-brand-500">
                    {service.freelancer.first_name[0]}{service.freelancer.last_name[0]}
                  </span>
                )}
              </div>
            </Link>
            <div>
              <Link href={`/profile/${service.freelancer.username}`} className="font-medium text-gray-900 hover:text-brand-600 transition-colors">
                {freelancerName}
              </Link>
              {service.avg_rating && service.avg_rating > 0 ? (
                <p className="text-sm text-gray-500 flex items-center gap-1">
                  <span className="text-yellow-400">★</span>
                  <span>{service.avg_rating.toFixed(1)}</span>
                  {service.review_count ? <span>({service.review_count})</span> : null}
                  {service.total_orders ? <span>· {service.total_orders} {str.orders}</span> : null}
                </p>
              ) : (
                <p className="text-sm text-gray-400">{str.noRating}</p>
              )}
            </div>
          </div>

          {/* Carousel */}
          <ImageCarousel images={images} title={service.title} locale={locale} />

          {/* Description */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-3">{str.description}</h2>
            <div className="text-gray-700 whitespace-pre-line leading-relaxed">
              {service.description}
            </div>
          </div>

          {/* Tags */}
          {service.tags && service.tags.length > 0 && (
            <div className="card p-5">
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">{str.tags}</h2>
              <div className="flex flex-wrap gap-2">
                {service.tags.map((tag) => (
                  <span key={tag} className="px-3 py-1 rounded-full text-sm bg-gray-100 text-gray-700 border border-gray-200">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right — Sticky sidebar */}
        <div className="w-full lg:w-[340px] shrink-0">
          <div className="sticky top-24 space-y-4">
            {/* Package selector */}
            <div className="card overflow-hidden">
              {/* Tier tabs */}
              {availableTiers.length > 1 && (
                <div className="flex border-b border-gray-100">
                  {availableTiers.map((tier) => (
                    <button
                      key={tier}
                      onClick={() => setActivePackageTier(tier)}
                      className={`flex-1 py-3 text-sm font-medium transition-colors ${
                        activePackageTier === tier
                          ? "text-brand-600 border-b-2 border-brand-500 bg-brand-50"
                          : "text-gray-500 hover:text-gray-700"
                      }`}
                    >
                      {tierLabel(tier)}
                    </button>
                  ))}
                </div>
              )}

              <div className="p-5 space-y-4">
                {activePackage && (
                  <>
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold text-gray-900">{activePackage.name}</h3>
                      <span className="text-xl font-bold text-gray-900">
                        {activePackage.price.toLocaleString(locale === "ar" ? "ar" : "en")} {str.currency}
                      </span>
                    </div>

                    <p className="text-sm text-gray-600">{activePackage.description}</p>

                    <div className="flex flex-wrap gap-3 text-sm text-gray-600">
                      <span className="flex items-center gap-1">
                        <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        {str.deliveryDays(activePackage.delivery_days)}
                      </span>
                      {activePackage.revisions !== undefined && (
                        <span className="flex items-center gap-1">
                          <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                          </svg>
                          {activePackage.revisions === -1
                            ? str.unlimitedRevisions
                            : str.revisions(activePackage.revisions)}
                        </span>
                      )}
                    </div>

                    {/* Features */}
                    {activePackage.features && activePackage.features.length > 0 && (
                      <ul className="space-y-1.5">
                        {activePackage.features.map((feat) => (
                          <li key={feat} className="flex items-center gap-2 text-sm text-gray-700">
                            <svg className="w-4 h-4 text-green-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                            {feat}
                          </li>
                        ))}
                      </ul>
                    )}

                    <button
                      onClick={() => setShowOrderModal(true)}
                      className="btn-primary w-full py-3 text-base"
                    >
                      {str.orderNow}
                    </button>
                  </>
                )}
              </div>
            </div>

            {/* Freelancer card */}
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">{str.about}</h3>
              <Link href={`/profile/${service.freelancer.username}`} className="flex items-center gap-3 group mb-4">
                <div className="w-12 h-12 rounded-full overflow-hidden bg-brand-100 flex items-center justify-center shrink-0">
                  {service.freelancer.avatar_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={backendUrl(service.freelancer.avatar_url)} alt={freelancerName} className="w-full h-full object-cover" />
                  ) : (
                    <span className="text-lg font-bold text-brand-500">
                      {service.freelancer.first_name[0]}{service.freelancer.last_name[0]}
                    </span>
                  )}
                </div>
                <div>
                  <p className="font-medium text-gray-900 group-hover:text-brand-600 transition-colors">{freelancerName}</p>
                  {service.freelancer.avg_rating && service.freelancer.avg_rating > 0 ? (
                    <p className="text-sm text-gray-500">
                      ★ {service.freelancer.avg_rating.toFixed(1)}
                      {service.freelancer.total_reviews ? ` (${service.freelancer.total_reviews})` : ""}
                    </p>
                  ) : null}
                </div>
              </Link>

              {service.freelancer.bio && (
                <p className="text-sm text-gray-600 line-clamp-3 mb-4">{service.freelancer.bio}</p>
              )}

              <Link href={`/dashboard/messages?with=${service.freelancer.id}`} className="btn-secondary w-full py-2.5 text-sm text-center block">
                {str.contactFreelancer}
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Order Modal */}
      {showOrderModal && activePackage && (
        <OrderModal
          service={service}
          packageId={activePackage.id}
          onClose={() => setShowOrderModal(false)}
          locale={locale}
        />
      )}
    </div>
  );
}
