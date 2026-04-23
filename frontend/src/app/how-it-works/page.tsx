/**
 * /how-it-works — bilingual SSR page explaining the Kaasb flow for
 * clients (hiring) and freelancers (getting work). Static content so
 * it can be fully server-rendered; no client interactivity needed.
 *
 * Referenced from navbar footer + /help page.
 */

import type { Metadata } from "next";
import Link from "next/link";
import { SITE_NAME, SITE_URL } from "@/lib/seo";

export const metadata: Metadata = {
  title: `How Kaasb Works | كيف يعمل كاسب`,
  description:
    "Step-by-step: how clients hire freelancers on Kaasb and how freelancers deliver work and get paid. Bilingual (Arabic + English).",
  alternates: { canonical: "/how-it-works" },
  openGraph: {
    title: `How Kaasb Works | ${SITE_NAME}`,
    description:
      "The complete flow for clients and freelancers on Kaasb — Iraq's leading freelancing marketplace.",
    url: `${SITE_URL}/how-it-works`,
    type: "article",
  },
};

type Step = { en: string; ar: string; detailEn: string; detailAr: string };

const CLIENT_STEPS: Step[] = [
  {
    en: "Browse services or post a job",
    ar: "تصفّح الخدمات أو انشر مشروعاً",
    detailEn:
      "Look through ready-made services at set prices, or post a custom brief to have freelancers come to you.",
    detailAr:
      "تصفّح الخدمات الجاهزة بأسعار ثابتة، أو انشر مشروعاً مخصصاً ليتقدّم لك المستقلون بعروضهم.",
  },
  {
    en: "Choose a package and place your order",
    ar: "اختر الباقة المناسبة وأرسل طلبك",
    detailEn:
      "Pick Basic, Standard, or Premium. Pay via Qi Card — funds go into secure escrow, not to the freelancer directly.",
    detailAr:
      "اختر الأساسي أو القياسي أو المميز. ادفع عبر كي كارد — تُحفظ الأموال في ضمان آمن ولا تذهب للمستقل مباشرة.",
  },
  {
    en: "Answer the requirement questions",
    ar: "أجب على أسئلة المتطلبات",
    detailEn:
      "Every service asks a few questions so the freelancer has what they need to start. Delivery clock begins only after you submit answers.",
    detailAr:
      "تسأل كل خدمة بعض الأسئلة ليبدأ المستقل العمل على الفور. يبدأ عدّاد التسليم فقط بعد إرسال إجاباتك.",
  },
  {
    en: "Review the delivery",
    ar: "راجع التسليم",
    detailEn:
      "Accept the delivery, request a revision if it's off-scope, or open a dispute if something is seriously wrong. We escrow your payment until you're satisfied.",
    detailAr:
      "وافق على التسليم، أو اطلب تعديلاً إذا كان خارج النطاق، أو افتح نزاعاً إذا كان هناك خطأ جسيم. ندفع فقط عندما تكون راضياً.",
  },
  {
    en: "Rate the freelancer",
    ar: "قيّم المستقل",
    detailEn:
      "Leave a 1–5 star review — reviews build freelancer reputation and help the next client choose well.",
    detailAr:
      "اترك تقييماً من ١ إلى ٥ نجوم — التقييمات تبني سمعة المستقلين وتساعد العملاء القادمين.",
  },
];

const FREELANCER_STEPS: Step[] = [
  {
    en: "Create a seller profile",
    ar: "أنشئ ملف المستقل الخاص بك",
    detailEn:
      "Register, fill out your bio, skills, and a professional photo. Public profile URL becomes your portfolio.",
    detailAr:
      "سجّل واملأ نبذتك ومهاراتك وصورة احترافية. رابط ملفك العام يصبح معرض أعمالك.",
  },
  {
    en: "Publish a service or bid on buyer requests",
    ar: "أنشر خدمة أو قدّم عرضاً على طلبات المشترين",
    detailEn:
      "Create up to three packages (Basic / Standard / Premium) for every service. Or bid on open buyer requests with a custom offer.",
    detailAr:
      "أنشئ ثلاث باقات لكل خدمة (أساسي / قياسي / مميز). أو قدّم عروضاً مخصصة على طلبات المشترين المفتوحة.",
  },
  {
    en: "Get orders from clients",
    ar: "استقبل الطلبات من العملاء",
    detailEn:
      "Clients answer your requirement questions, payment goes into escrow, and your delivery clock starts.",
    detailAr:
      "يجيب العميل على أسئلة المتطلبات، تدخل الأموال إلى الضمان، ويبدأ عدّاد التسليم.",
  },
  {
    en: "Deliver the work on time",
    ar: "سلّم العمل في الوقت المحدد",
    detailEn:
      "Upload files or a written delivery through the order page. The client has 3 days to accept or request revisions.",
    detailAr:
      "ارفع الملفات أو تسليماً مكتوباً من صفحة الطلب. أمام العميل ٣ أيام للقبول أو طلب التعديلات.",
  },
  {
    en: "Get paid via Qi Card",
    ar: "استلم أموالك عبر كي كارد",
    detailEn:
      "Once the client accepts (or auto-complete fires 3 days later), Kaasb admins transfer your IQD to your Qi Card. Platform fee is 10%; you keep 90%.",
    detailAr:
      "بمجرد قبول العميل (أو بعد الإكمال التلقائي خلال ٣ أيام)، يحوّل مشرفو كاسب أموالك بالدينار إلى كي كارد. رسوم المنصة ١٠٪، تحتفظ أنت بـ ٩٠٪.",
  },
];

function StepList({ steps, startNumber }: { steps: Step[]; startNumber: number }) {
  return (
    <ol className="space-y-6">
      {steps.map((step, i) => (
        <li key={i} className="flex gap-4">
          <span
            className="shrink-0 w-10 h-10 rounded-full bg-brand-500 text-white font-bold flex items-center justify-center text-lg"
            aria-hidden
          >
            {startNumber + i}
          </span>
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-gray-900" dir="rtl">
              {step.ar}
            </h3>
            <p className="text-sm text-gray-600 mt-1 leading-relaxed" dir="rtl">
              {step.detailAr}
            </p>
            <div className="mt-3 pt-3 border-t border-gray-100">
              <h3 className="font-semibold text-gray-900" dir="ltr">
                {step.en}
              </h3>
              <p className="text-sm text-gray-600 mt-1 leading-relaxed" dir="ltr">
                {step.detailEn}
              </p>
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}

export default function HowItWorksPage() {
  return (
    <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <header className="text-center mb-10">
        <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-2" dir="rtl">
          كيف يعمل كاسب
        </h1>
        <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-3" dir="ltr">
          How Kaasb Works
        </h2>
        <p className="text-gray-600 max-w-2xl mx-auto" dir="rtl">
          منصة مخصصة للسوق العراقي — الدفع بالدينار عبر كي كارد، مدعومة بالعربية والإنجليزية.
        </p>
        <p className="text-gray-600 max-w-2xl mx-auto mt-2" dir="ltr">
          Built for the Iraqi market — IQD payments via Qi Card, bilingual Arabic and English.
        </p>
      </header>

      <section id="clients" className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-6 text-center">
          <span dir="rtl">للعملاء (شراء الخدمات)</span>
          <span className="block text-lg text-gray-500 font-normal mt-1" dir="ltr">
            For Clients (Hiring)
          </span>
        </h2>
        <StepList steps={CLIENT_STEPS} startNumber={1} />
        <div className="text-center mt-8">
          <Link href="/services" className="btn-primary px-6 py-3">
            <span dir="rtl">ابدأ بتصفح الخدمات</span>
            <span className="mx-2">·</span>
            <span dir="ltr">Browse Services</span>
          </Link>
        </div>
      </section>

      <div className="border-t border-gray-200 my-10" />

      <section id="freelancers" className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-6 text-center">
          <span dir="rtl">للمستقلين (تقديم الخدمات)</span>
          <span className="block text-lg text-gray-500 font-normal mt-1" dir="ltr">
            For Freelancers (Selling)
          </span>
        </h2>
        <StepList steps={FREELANCER_STEPS} startNumber={1} />
        <div className="text-center mt-8">
          <Link href="/auth/register" className="btn-primary px-6 py-3">
            <span dir="rtl">أنشئ حساب مستقل</span>
            <span className="mx-2">·</span>
            <span dir="ltr">Create Freelancer Account</span>
          </Link>
        </div>
      </section>

      <div className="border-t border-gray-200 my-10" />

      <section className="text-center">
        <p className="text-gray-600 mb-4">
          <span dir="rtl">هل لديك سؤال لم تجد إجابته هنا؟</span>
          <span className="mx-2">·</span>
          <span dir="ltr">Didn&apos;t find your answer?</span>
        </p>
        <div className="flex gap-3 justify-center flex-wrap">
          <Link href="/faq" className="btn-secondary px-5 py-2">
            FAQ
          </Link>
          <Link href="/help" className="btn-secondary px-5 py-2">
            <span dir="rtl">مركز المساعدة</span>
            <span className="mx-2">·</span>
            <span dir="ltr">Help Center</span>
          </Link>
        </div>
      </section>
    </main>
  );
}
