import Link from "next/link";
import { cookies } from "next/headers";
import { FaqJsonLd } from "@/components/seo/json-ld";
import { HeroCta } from "./_components/hero-cta";
import {
  SITE_NAME,
  SITE_URL,
  DEFAULT_OG_IMAGE,
  KEYWORDS,
} from "@/lib/seo";

export async function generateMetadata() {
  const cookieStore = await cookies();
  const locale = cookieStore.get("locale")?.value === "en" ? "en" : "ar";
  const ar = locale === "ar";

  const title = ar
    ? `كاسب - منصة المستقلين الرائدة في العراق`
    : `${SITE_NAME} - Iraq's Leading Freelancing Platform`;
  const description = ar
    ? "كاسب يربط الشركات بالمستقلين الموهوبين في العراق والشرق الأوسط. تصفّح الخدمات الجاهزة أو انشر مشروعاً — مع دفعات آمنة عبر كي كارد."
    : "Kaasb connects businesses with talented freelancers across Iraq and the Middle East. Browse ready-made services or post a job — with secure payments via Qi Card.";

  return {
    title,
    description,
    keywords: KEYWORDS.primary,
    alternates: { canonical: "/" },
    openGraph: {
      title,
      description,
      url: SITE_URL,
      images: [{ url: DEFAULT_OG_IMAGE, width: 1200, height: 630 }],
    },
  };
}

const FAQ_ITEMS_AR = [
  {
    question: "ما هو كاسب؟",
    answer:
      "كاسب هو منصة العمل الحر الرائدة في العراق التي تربط الشركات بالمستقلين الموهوبين في الشرق الأوسط. يمكنك نشر مشاريع، توظيف خبراء، وإدارة المشاريع مع دفعات آمنة عبر كي كارد.",
  },
  {
    question: "كيف أوظّف مستقلاً على كاسب؟",
    answer:
      "ببساطة انشر مشروعك مع وصف وميزانية، راجع العروض من المستقلين المؤهلين، واختر الأنسب. المدفوعات مؤمّنة عبر نظام الضمان لدينا.",
  },
  {
    question: "هل استخدام كاسب مجاني؟",
    answer:
      "التسجيل وتصفح المشاريع مجاني تماماً. كاسب يأخذ رسوم خدمة بسيطة فقط عند إتمام المشروع بنجاح.",
  },
  {
    question: "ما هي طرق الدفع المدعومة في كاسب؟",
    answer:
      "كاسب يستخدم كي كارد — أشهر بطاقة دفع في العراق — لجميع المدفوعات والتحويلات.",
  },
  {
    question: "هل يمكنني العمل كمستقل من العراق؟",
    answer:
      "نعم! كاسب مصمم خصيصاً للمستقلين العراقيين وسوق الشرق الأوسط. أنشئ ملفك المجاني، اعرض مهاراتك، وابدأ بتقديم العروض.",
  },
];

const FAQ_ITEMS_EN = [
  {
    question: "What is Kaasb?",
    answer:
      "Kaasb is Iraq's leading freelancing platform that connects businesses with talented freelancers across the Middle East. You can post jobs, hire experts, and manage projects with secure payments via Qi Card.",
  },
  {
    question: "How do I hire a freelancer on Kaasb?",
    answer:
      "Simply post your job with a description and budget, review proposals from qualified freelancers, and hire the best fit. Payments are secured through our escrow system.",
  },
  {
    question: "Is Kaasb free to use?",
    answer:
      "Signing up and browsing jobs is completely free. Kaasb charges a small service fee only when a project is completed successfully.",
  },
  {
    question: "What payment methods does Kaasb support?",
    answer:
      "Kaasb uses Qi Card — Iraq's most popular payment card — for all payments and payouts.",
  },
  {
    question: "Can I work as a freelancer from Iraq?",
    answer:
      "Yes! Kaasb is designed specifically for Iraqi freelancers and the Middle East market. Create a free profile, showcase your skills, and start bidding on projects.",
  },
];

const HOW_IT_WORKS_AR = [
  {
    step: "01",
    title: "اختر طريقتك",
    description: "تصفّح خدمات جاهزة واطلب مباشرة، أو انشر مشروعك وتلقَّ عروضاً من المستقلين.",
    icon: "🎯",
  },
  {
    step: "02",
    title: "تعاون بأمان",
    description: "تواصل مع المستقل عبر المنصة. المدفوعات محجوزة في الضمان حتى تنتهي من العمل.",
    icon: "🔒",
  },
  {
    step: "03",
    title: "استلم وادفع",
    description: "راجع التسليم، اقبله، وتُحرَّر المدفوعات تلقائياً عبر كي كارد.",
    icon: "✅",
  },
];

const HOW_IT_WORKS_EN = [
  {
    step: "01",
    title: "Choose your path",
    description: "Browse ready-made services and order instantly, or post a project and receive proposals.",
    icon: "🎯",
  },
  {
    step: "02",
    title: "Collaborate safely",
    description: "Communicate through the platform. Payments are held in escrow until work is complete.",
    icon: "🔒",
  },
  {
    step: "03",
    title: "Receive & pay",
    description: "Review the delivery, approve it, and funds release automatically via Qi Card.",
    icon: "✅",
  },
];

function decodeJwtRole(token: string): string | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")));
    return typeof payload.role === "string" ? payload.role : null;
  } catch {
    return null;
  }
}

function isJwtExpired(token: string): boolean {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return true;
    const payload = JSON.parse(atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")));
    return typeof payload.exp !== "number" || Date.now() / 1000 > payload.exp - 5;
  } catch {
    return true;
  }
}

export default async function HomePage() {
  const cookieStore = await cookies();
  const locale = cookieStore.get("locale")?.value === "en" ? "en" : "ar";
  const ar = locale === "ar";

  const tokenCookie = cookieStore.get("access_token")?.value;
  const isLoggedIn = !!tokenCookie && !isJwtExpired(tokenCookie);
  const role = tokenCookie ? decodeJwtRole(tokenCookie) : null;
  const dashboardHref = role === "admin" ? "/admin" : "/dashboard";

  const faqItems = ar ? FAQ_ITEMS_AR : FAQ_ITEMS_EN;
  const howItWorks = ar ? HOW_IT_WORKS_AR : HOW_IT_WORKS_EN;

  return (
    <div className="min-h-[calc(100vh-4rem)]">
      {/* FAQ Structured Data */}
      <FaqJsonLd items={faqItems} />

      {/* Hero Section */}
      <section className="bg-gradient-to-br from-brand-500 via-brand-600 to-brand-800 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 lg:py-32">
          <div className="max-w-3xl">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight">
              {ar ? (
                <>
                  سوق العمل الحر
                  <span className="text-brand-200"> الأول في العراق</span>
                </>
              ) : (
                <>
                  Iraq&apos;s freelance
                  <span className="text-brand-200"> marketplace</span>
                </>
              )}
            </h1>
            <p className="mt-6 text-lg sm:text-xl text-blue-100 leading-relaxed">
              {ar
                ? "تصفّح آلاف الخدمات الجاهزة، أو انشر وظيفتك وتلقَّ عروضاً من مستقلين محترفين. الدفع الآمن عبر كي كارد."
                : "Browse thousands of ready-made services, or post a job and receive proposals from skilled freelancers. Secure payments via Qi Card."}
            </p>

            {/* Dual discovery paths */}
            <div className="mt-10 grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-xl">
              {/* Path 1: Browse gigs (Fiverr model) */}
              <Link
                href="/gigs"
                className="flex flex-col gap-1 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 px-5 py-4 transition-colors text-start"
              >
                <span className="text-2xl">🛍️</span>
                <span className="font-semibold text-white">
                  {ar ? "تصفّح الخدمات" : "Browse Services"}
                </span>
                <span className="text-sm text-blue-200">
                  {ar ? "خدمات جاهزة بأسعار ثابتة" : "Ready-made services, fixed price"}
                </span>
              </Link>

              {/* Path 2: Post a job (Upwork model) */}
              <Link
                href={isLoggedIn ? "/jobs/new" : "/jobs"}
                className="flex flex-col gap-1 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 px-5 py-4 transition-colors text-start"
              >
                <span className="text-2xl">📋</span>
                <span className="font-semibold text-white">
                  {ar ? "انشر مشروعك" : "Post a Project"}
                </span>
                <span className="text-sm text-blue-200">
                  {ar ? "تلقَّ عروضاً من مستقلين" : "Receive proposals from freelancers"}
                </span>
              </Link>
            </div>

            <div className="mt-6">
              <HeroCta
                ar={ar}
                ssrLoggedIn={isLoggedIn}
                ssrDashboardHref={dashboardHref}
                variant="hero"
              />
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-center text-gray-900">
            {ar ? "كيف يعمل كاسب" : "How Kaasb Works"}
          </h2>
          <p className="mt-4 text-center text-gray-600 max-w-2xl mx-auto">
            {ar
              ? "البداية بسيطة. سواء كنت توظّف أو تعمل كمستقل، كاسب يسهّل الأمر."
              : "Getting started is simple. Whether you're hiring or freelancing, Kaasb makes it easy."}
          </p>

          <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8">
            {howItWorks.map((item) => (
              <div key={item.step} className="text-center">
                <div className="text-5xl mb-4" role="img" aria-label={item.title}>
                  {item.icon}
                </div>
                <div className="text-sm font-bold text-brand-500 mb-2">
                  {ar ? `الخطوة ${item.step}` : `STEP ${item.step}`}
                </div>
                <h3 className="text-xl font-semibold text-gray-900">
                  {item.title}
                </h3>
                <p className="mt-3 text-gray-600">{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ Section (SEO-visible) */}
      <section className="py-20 bg-white border-t border-gray-100">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
            {ar ? "الأسئلة الشائعة" : "Frequently Asked Questions"}
          </h2>
          <div className="space-y-6">
            {faqItems.map((faq) => (
              <details
                key={faq.question}
                className="group border border-gray-200 rounded-lg"
              >
                <summary className="flex items-center justify-between cursor-pointer p-5 text-lg font-medium text-gray-900 hover:bg-gray-50 rounded-lg">
                  {faq.question}
                  <span className="ms-4 text-gray-400 group-open:rotate-180 transition-transform">
                    &#9662;
                  </span>
                </summary>
                <p className="px-5 pb-5 text-gray-600 leading-relaxed">
                  {faq.answer}
                </p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-4xl mx-auto text-center px-4">
          <h2 className="text-3xl font-bold text-gray-900">
            {ar ? "هل أنت مستعد للبدء؟" : "Ready to get started?"}
          </h2>
          <p className="mt-4 text-lg text-gray-600">
            {ar
              ? "انضم لآلاف المستقلين والشركات على كاسب."
              : "Join thousands of freelancers and businesses on Kaasb."}
          </p>
          <div className="mt-8 flex justify-center gap-4">
            <HeroCta
              ar={ar}
              ssrLoggedIn={isLoggedIn}
              ssrDashboardHref={dashboardHref}
              variant="cta"
            />
          </div>
        </div>
      </section>
    </div>
  );
}
