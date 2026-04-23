/**
 * /help — landing page for the help center. SSR, no interactivity.
 * Cards link out to /how-it-works, /faq, and support@kaasb.com.
 * Publishes our support SLA (Phase 8 deliverable) right on this page.
 */

import type { Metadata } from "next";
import Link from "next/link";
import { SITE_NAME, SITE_URL } from "@/lib/seo";

export const metadata: Metadata = {
  title: "Help Center | مركز المساعدة",
  description:
    "Get help with Kaasb — learn how the platform works, browse FAQs, or contact support. We reply within 8 business hours.",
  alternates: { canonical: "/help" },
  openGraph: {
    title: `Help Center | ${SITE_NAME}`,
    description:
      "How Kaasb works, FAQs, and direct support. Bilingual Arabic and English.",
    url: `${SITE_URL}/help`,
    type: "website",
  },
};

function HelpCard({
  href,
  icon,
  titleEn,
  titleAr,
  descEn,
  descAr,
}: {
  href: string;
  icon: React.ReactNode;
  titleEn: string;
  titleAr: string;
  descEn: string;
  descAr: string;
}) {
  return (
    <Link
      href={href}
      className="card p-6 hover:shadow-lg hover:border-brand-300 transition-all group"
    >
      <div className="w-12 h-12 rounded-xl bg-brand-50 flex items-center justify-center mb-4 group-hover:bg-brand-100 transition-colors">
        {icon}
      </div>
      <h3 className="font-bold text-gray-900 text-lg mb-1" dir="rtl">
        {titleAr}
      </h3>
      <h3 className="font-bold text-gray-900 text-lg mb-3" dir="ltr">
        {titleEn}
      </h3>
      <p className="text-sm text-gray-600 leading-relaxed mb-1" dir="rtl">
        {descAr}
      </p>
      <p className="text-sm text-gray-600 leading-relaxed" dir="ltr">
        {descEn}
      </p>
    </Link>
  );
}

const ICON_CLASS = "w-6 h-6 text-brand-600";

export default function HelpPage() {
  return (
    <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <header className="text-center mb-10">
        <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-2" dir="rtl">
          مركز المساعدة
        </h1>
        <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4" dir="ltr">
          Help Center
        </h2>
        <p className="text-gray-600 max-w-xl mx-auto" dir="rtl">
          ابحث عن الإجابات أو تواصل مع فريق الدعم.
        </p>
        <p className="text-gray-600 max-w-xl mx-auto mt-1" dir="ltr">
          Find answers or reach our support team.
        </p>
      </header>

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 mb-12">
        <HelpCard
          href="/how-it-works"
          titleEn="How Kaasb Works"
          titleAr="كيف يعمل كاسب"
          descEn="Step-by-step: hiring freelancers and selling services on Kaasb."
          descAr="خطوة بخطوة: توظيف المستقلين وبيع الخدمات على كاسب."
          icon={
            <svg className={ICON_CLASS} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
          }
        />
        <HelpCard
          href="/faq"
          titleEn="FAQ"
          titleAr="الأسئلة الشائعة"
          descEn="20 common questions on payments, orders, disputes, and your account."
          descAr="٢٠ سؤالاً شائعاً حول الدفع والطلبات والنزاعات وحسابك."
          icon={
            <svg className={ICON_CLASS} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093M12 17h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          }
        />
        <HelpCard
          href="mailto:support@kaasb.com"
          titleEn="Email Support"
          titleAr="راسل الدعم"
          descEn="Write to support@kaasb.com. We reply within 8 business hours."
          descAr="راسلنا على support@kaasb.com. نرد خلال ٨ ساعات عمل."
          icon={
            <svg className={ICON_CLASS} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
              />
            </svg>
          }
        />
      </div>

      {/* SLA — published commitment */}
      <section className="card p-6 bg-gradient-to-br from-brand-50 to-white border-brand-200 mb-12">
        <h2 className="text-xl font-bold text-gray-900 mb-4">
          <span dir="rtl">التزامنا في الدعم</span>
          <span className="mx-2 text-gray-400">·</span>
          <span dir="ltr">Our Support Commitment</span>
        </h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <div className="text-3xl font-bold text-brand-600 mb-1">8h</div>
            <p className="text-sm font-semibold text-gray-900">
              <span dir="rtl">أول رد</span>
              <span className="mx-1">·</span>
              <span dir="ltr">First response</span>
            </p>
            <p className="text-sm text-gray-600 mt-1" dir="rtl">
              خلال ٨ ساعات عمل (٠٨:٠٠–٢٠:٠٠ بتوقيت بغداد، ٧ أيام في الأسبوع).
            </p>
            <p className="text-sm text-gray-600 mt-1" dir="ltr">
              Within 8 business hours (08:00–20:00 Baghdad time, 7 days a week).
            </p>
          </div>
          <div>
            <div className="text-3xl font-bold text-brand-600 mb-1">48h</div>
            <p className="text-sm font-semibold text-gray-900">
              <span dir="rtl">الحل</span>
              <span className="mx-1">·</span>
              <span dir="ltr">Resolution</span>
            </p>
            <p className="text-sm text-gray-600 mt-1" dir="rtl">
              معظم القضايا تُحلّ خلال ٤٨ ساعة. النزاعات المعقدة قد تستغرق وقتاً أطول.
            </p>
            <p className="text-sm text-gray-600 mt-1" dir="ltr">
              Most issues resolved within 48 hours. Complex disputes may take longer.
            </p>
          </div>
        </div>
      </section>

      {/* In-app support callout */}
      <section className="text-center">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          <span dir="rtl">هل تملك حساباً بالفعل؟</span>
          <span className="mx-2">·</span>
          <span dir="ltr">Already have an account?</span>
        </h3>
        <p className="text-gray-600 mb-4" dir="rtl">
          استخدم نموذج &laquo;تواصل مع الدعم&raquo; من لوحة التحكم للحصول على ردود أسرع
          — يأتي مرفقاً ببيانات حسابك ولا يحتاج منك التعريف.
        </p>
        <p className="text-gray-600 mb-4" dir="ltr">
          Use the &quot;Contact Support&quot; form inside your dashboard for faster
          replies — your account info is automatically attached.
        </p>
        <Link href="/dashboard/messages" className="btn-primary px-6 py-3">
          <span dir="rtl">فتح الدعم في التطبيق</span>
          <span className="mx-2">·</span>
          <span dir="ltr">Open In-App Support</span>
        </Link>
      </section>
    </main>
  );
}
