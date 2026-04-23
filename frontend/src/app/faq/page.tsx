/**
 * /faq — bilingual SSR FAQ page with FAQPage JSON-LD for Google rich results.
 *
 * 20 questions organized by topic. Server-rendered for SEO; no client
 * interactivity (anchor links for navigation). Every answer is bilingual
 * AR+EN so the same page ranks in both languages.
 */

import type { Metadata } from "next";
import Link from "next/link";
import { SITE_NAME, SITE_URL } from "@/lib/seo";

export const metadata: Metadata = {
  title: "FAQ — Frequently Asked Questions | الأسئلة الشائعة",
  description:
    "Answers to common questions about Kaasb — payments, fees, disputes, payouts, account verification, and more. Bilingual Arabic and English.",
  alternates: { canonical: "/faq" },
  openGraph: {
    title: `FAQ | ${SITE_NAME}`,
    description:
      "Answers to 20 common questions about hiring freelancers and selling services on Kaasb.",
    url: `${SITE_URL}/faq`,
    type: "article",
  },
};

type Faq = { id: string; q_en: string; q_ar: string; a_en: string; a_ar: string };

const SECTIONS: { key: string; en: string; ar: string; faqs: Faq[] }[] = [
  {
    key: "getting-started",
    en: "Getting Started",
    ar: "البدء",
    faqs: [
      {
        id: "what-is-kaasb",
        q_en: "What is Kaasb?",
        q_ar: "ما هو كاسب؟",
        a_en: "Kaasb is Iraq's leading freelancing platform, connecting clients with skilled freelancers across the Middle East. Secure payments through Qi Card, bilingual Arabic and English, designed for the Iraqi market.",
        a_ar: "كاسب هو منصة العمل الحر الرائدة في العراق، يربط العملاء بالمستقلين الموهوبين في الشرق الأوسط. دفعات آمنة عبر كي كارد، ودعم ثنائي اللغة بالعربية والإنجليزية، مصمم خصيصاً للسوق العراقي.",
      },
      {
        id: "is-free-to-join",
        q_en: "Is Kaasb free to join?",
        q_ar: "هل التسجيل في كاسب مجاني؟",
        a_en: "Yes — creating an account, browsing services, and posting jobs is 100% free. Kaasb only takes a 10% service fee on completed orders.",
        a_ar: "نعم — إنشاء الحساب وتصفح الخدمات ونشر المشاريع مجاني تماماً. يأخذ كاسب فقط رسوم خدمة ١٠٪ على الطلبات المكتملة.",
      },
      {
        id: "buyer-or-seller",
        q_en: "Can one account be both a buyer and a seller?",
        q_ar: "هل يمكن للحساب الواحد أن يكون مشترياً وبائعاً في نفس الوقت؟",
        a_en: "Yes. A single Kaasb account can both hire freelancers and sell services. Switch modes anytime from your dashboard.",
        a_ar: "نعم. يمكن للحساب الواحد في كاسب أن يوظّف المستقلين ويقدّم خدمات في الوقت نفسه. يمكنك التبديل بين الوضعين في أي وقت من لوحة التحكم.",
      },
    ],
  },
  {
    key: "payments",
    en: "Payments",
    ar: "الدفع",
    faqs: [
      {
        id: "accepted-payment",
        q_en: "What payment methods are accepted?",
        q_ar: "ما هي طرق الدفع المقبولة؟",
        a_en: "Kaasb accepts Qi Card for all payments and payouts. This is the primary payment method for Iraqi clients and freelancers.",
        a_ar: "يقبل كاسب بطاقة كي كارد لجميع المدفوعات والتحويلات. هذه هي وسيلة الدفع الأساسية للعملاء والمستقلين العراقيين.",
      },
      {
        id: "currency",
        q_en: "What currency are prices shown in?",
        q_ar: "ما هي العملة المعتمدة للأسعار؟",
        a_en: "All prices on Kaasb are in Iraqi Dinar (IQD). We do not convert to USD or any other currency.",
        a_ar: "جميع الأسعار على كاسب بالدينار العراقي. لا نقوم بالتحويل إلى الدولار أو أي عملة أخرى.",
      },
      {
        id: "escrow-explained",
        q_en: "How does the escrow work?",
        q_ar: "كيف يعمل نظام الضمان؟",
        a_en: "When a client pays for an order, the funds are held by Kaasb (not the freelancer) until the work is approved. This protects both sides — clients get what they paid for, freelancers get paid for approved work.",
        a_ar: "عندما يدفع العميل ثمن الطلب، تُحفظ الأموال لدى كاسب (وليس لدى المستقل) حتى تتم الموافقة على العمل. هذا يحمي الطرفين — يحصل العميل على ما دفع مقابله، ويحصل المستقل على دفعته مقابل العمل المقبول.",
      },
      {
        id: "platform-fee",
        q_en: "What is the platform fee?",
        q_ar: "كم تبلغ رسوم المنصة؟",
        a_en: "Kaasb takes 10% of the order value. The freelancer keeps the remaining 90%. The fee is only taken on completed orders — no fee on cancelled or refunded orders.",
        a_ar: "يأخذ كاسب ١٠٪ من قيمة الطلب. يحتفظ المستقل بالـ ٩٠٪ المتبقية. تُستقطع الرسوم فقط من الطلبات المكتملة — لا توجد رسوم على الطلبات الملغاة أو المستردة.",
      },
      {
        id: "refund-timeline",
        q_en: "How long do refunds take?",
        q_ar: "كم تستغرق عملية الاسترداد؟",
        a_en: "Refunds are processed manually through Qi Card by Kaasb admins within 48 business hours of approval. Funds appear back on your Qi Card according to Qi Card's own settlement timing.",
        a_ar: "تُعالج عمليات الاسترداد يدوياً عبر كي كارد من قبل مشرفي كاسب خلال ٤٨ ساعة عمل من الموافقة. تظهر الأموال مرة أخرى على بطاقتك وفقاً لجدول تسويات كي كارد.",
      },
      {
        id: "payout-timing",
        q_en: "When do freelancers get paid?",
        q_ar: "متى يحصل المستقلون على أموالهم؟",
        a_en: "After the client accepts a delivery (or after the 3-day auto-complete window), the escrow is marked ready for payout. Admins transfer IQD to the freelancer's Qi Card every Tuesday and Friday.",
        a_ar: "بعد قبول العميل للتسليم (أو بعد فترة الإكمال التلقائي لمدة ٣ أيام)، يُحرّر الضمان للصرف. ينقل المشرفون المبلغ بالدينار إلى بطاقة المستقل كل ثلاثاء وجمعة.",
      },
    ],
  },
  {
    key: "orders",
    en: "Orders & Delivery",
    ar: "الطلبات والتسليم",
    faqs: [
      {
        id: "requirements",
        q_en: "Why do I need to answer questions after I pay?",
        q_ar: "لماذا أحتاج إلى الإجابة على أسئلة بعد الدفع؟",
        a_en: "Services may include required questions so the freelancer knows exactly what you need before starting. The delivery clock begins only AFTER you submit answers, so take your time.",
        a_ar: "قد تتضمن الخدمات أسئلة مطلوبة ليعرف المستقل بالضبط ما تحتاجه قبل البدء. يبدأ عدّاد التسليم فقط بعد إرسال إجاباتك، لذا يمكنك أخذ وقتك.",
      },
      {
        id: "auto-complete",
        q_en: "What happens if I don't respond to a delivery?",
        q_ar: "ماذا يحدث إذا لم أرد على التسليم؟",
        a_en: "If the client doesn't accept or request revisions within 3 days of delivery, the order is auto-completed and the escrow is released to the freelancer. This protects freelancers from unresponsive clients.",
        a_ar: "إذا لم يقبل العميل أو يطلب تعديلات خلال ٣ أيام من التسليم، يُكتمل الطلب تلقائياً ويُحرّر الضمان للمستقل. يحمي هذا المستقلين من العملاء غير المستجيبين.",
      },
      {
        id: "revisions",
        q_en: "How do revisions work?",
        q_ar: "كيف تعمل التعديلات؟",
        a_en: "Each package includes a number of revisions — 1, 2, or unlimited. If the delivery is off-scope or missing what was promised, request a revision. The freelancer has the original delivery time (minimum 3 days) to re-deliver.",
        a_ar: "تتضمن كل باقة عدداً من التعديلات — ١ أو ٢ أو غير محدودة. إذا كان التسليم خارج النطاق أو ناقصاً، اطلب تعديلاً. يملك المستقل وقت التسليم الأصلي (٣ أيام كحد أدنى) لإعادة التسليم.",
      },
    ],
  },
  {
    key: "disputes",
    en: "Disputes",
    ar: "النزاعات",
    faqs: [
      {
        id: "when-dispute",
        q_en: "When should I open a dispute?",
        q_ar: "متى يجب أن أفتح نزاعاً؟",
        a_en: "Open a dispute only after attempting to resolve directly with the freelancer through revisions. Disputes are for cases like non-delivery, delivered work not matching the service description, or a freelancer who has gone silent.",
        a_ar: "افتح نزاعاً فقط بعد محاولة حلّ المشكلة مباشرةً مع المستقل عبر التعديلات. النزاعات مخصصة لحالات مثل عدم التسليم، أو تسليم عمل لا يطابق وصف الخدمة، أو اختفاء المستقل.",
      },
      {
        id: "dispute-outcome",
        q_en: "How are disputes resolved?",
        q_ar: "كيف تُحلّ النزاعات؟",
        a_en: "A Kaasb admin reviews the order chat, delivery files, and both sides' statements. They decide to either release the escrow to the freelancer (work was acceptable) or refund the client (work was off-scope or missing). Resolutions typically happen within 48 hours.",
        a_ar: "يراجع مشرف كاسب محادثات الطلب وملفات التسليم وبيانات الطرفين. يقرّر إما تحرير الضمان للمستقل (إذا كان العمل مقبولاً) أو استرداد المبلغ للعميل (إذا كان العمل خارج النطاق أو ناقصاً). تُحلّ النزاعات عادةً خلال ٤٨ ساعة.",
      },
      {
        id: "dispute-appeals",
        q_en: "Can I appeal a dispute decision?",
        q_ar: "هل يمكنني الاعتراض على قرار النزاع؟",
        a_en: "Contact support@kaasb.com within 7 days of the resolution with new evidence. A second admin will review. In most cases, the initial decision stands.",
        a_ar: "تواصل مع support@kaasb.com خلال ٧ أيام من القرار مع أدلة جديدة. سيراجع مشرف آخر. في أغلب الحالات، يبقى القرار الأول قائماً.",
      },
    ],
  },
  {
    key: "account",
    en: "Account & Security",
    ar: "الحساب والأمان",
    faqs: [
      {
        id: "otp-not-received",
        q_en: "I didn't receive my verification code. What should I do?",
        q_ar: "لم أستلم رمز التحقق. ماذا أفعل؟",
        a_en: "Codes are sent first via WhatsApp, then SMS, then email. If you're outside Iraq, the SMS may not deliver — check your spam folder for the email fallback, or wait 60 seconds and request a new code.",
        a_ar: "تُرسل الرموز أولاً عبر واتساب، ثم الرسائل النصية، ثم البريد الإلكتروني. إذا كنت خارج العراق، قد لا تصل الرسائل النصية — تحقّق من مجلد الرسائل غير المرغوبة في بريدك، أو انتظر ٦٠ ثانية واطلب رمزاً جديداً.",
      },
      {
        id: "forgot-password",
        q_en: "I forgot my password. How do I reset it?",
        q_ar: "نسيت كلمة المرور. كيف أعيد تعيينها؟",
        a_en: "Use the 'Forgot Password' link on the login page. We'll email you a reset link valid for 1 hour. Resetting your password signs you out of all devices.",
        a_ar: "استخدم رابط 'نسيت كلمة المرور' في صفحة تسجيل الدخول. سنرسل لك رابط إعادة التعيين عبر البريد الإلكتروني، صالحاً لمدة ساعة. إعادة تعيين كلمة المرور تسجّل خروجك من جميع الأجهزة.",
      },
      {
        id: "account-security",
        q_en: "How do you protect my account?",
        q_ar: "كيف تحمون حسابي؟",
        a_en: "Passwords are hashed with bcrypt, sessions are JWT-based with 30-minute expiry, all traffic is HTTPS, sensitive fields are encrypted at rest, and you can review and revoke active sessions from your dashboard settings.",
        a_ar: "يتم تشفير كلمات المرور بـ bcrypt، والجلسات مبنية على JWT مع انتهاء صلاحية خلال ٣٠ دقيقة، وجميع حركة المرور مشفّرة بـ HTTPS، والحقول الحساسة مشفّرة في التخزين، ويمكنك مراجعة وإلغاء الجلسات النشطة من إعدادات لوحة التحكم.",
      },
      {
        id: "delete-account",
        q_en: "How do I delete my account?",
        q_ar: "كيف أحذف حسابي؟",
        a_en: "Go to Dashboard → Settings → Danger Zone → Delete Account. We keep financial records required by Iraqi law for 7 years but anonymize your personal data. See our Privacy Policy for full details.",
        a_ar: "انتقل إلى لوحة التحكم ← الإعدادات ← منطقة الخطر ← حذف الحساب. نحتفظ بالسجلات المالية التي يتطلبها القانون العراقي لمدة ٧ سنوات ولكننا نُخفي بياناتك الشخصية. راجع سياسة الخصوصية للتفاصيل الكاملة.",
      },
    ],
  },
  {
    key: "off-platform",
    en: "Platform Rules",
    ar: "قواعد المنصة",
    faqs: [
      {
        id: "off-platform-contact",
        q_en: "Can I exchange contact info with a freelancer to work off-platform?",
        q_ar: "هل يمكنني تبادل معلومات الاتصال مع مستقل للعمل خارج المنصة؟",
        a_en: "No. Attempting to move work off-platform violates our terms of service. Off-platform work has no escrow protection, no dispute resolution, and puts both sides at risk of fraud. We automatically mask phone numbers, emails, and external app names in chat to help prevent accidental sharing.",
        a_ar: "لا. محاولة نقل العمل خارج المنصة تنتهك شروط الخدمة. العمل خارج المنصة لا يوفر حماية الضمان ولا حلّ النزاعات ويعرّض الطرفين لخطر الاحتيال. نقوم تلقائياً بإخفاء أرقام الهواتف والبريد الإلكتروني وأسماء التطبيقات الخارجية في المحادثات لمنع المشاركة غير المقصودة.",
      },
      {
        id: "prohibited-services",
        q_en: "What services are prohibited?",
        q_ar: "ما هي الخدمات المحظورة؟",
        a_en: "Services that violate Iraqi law, infringe intellectual property, involve adult content, or require access to financial accounts are not allowed. Full list in our Terms of Service.",
        a_ar: "الخدمات التي تنتهك القانون العراقي، أو تنتهك حقوق الملكية الفكرية، أو تتضمن محتوى للبالغين، أو تتطلب الوصول إلى حسابات مالية غير مسموح بها. القائمة الكاملة في شروط الخدمة.",
      },
    ],
  },
];

/**
 * FAQPage JSON-LD schema — each Q&A becomes a structured object so
 * Google can surface answers directly in search results.
 * https://developers.google.com/search/docs/appearance/structured-data/faqpage
 */
function FaqJsonLd() {
  const allFaqs = SECTIONS.flatMap((s) => s.faqs);
  const schema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: allFaqs.map((f) => ({
      "@type": "Question",
      name: f.q_en,
      acceptedAnswer: {
        "@type": "Answer",
        text: f.a_en,
      },
    })),
  };
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}

export default function FaqPage() {
  return (
    <>
      <FaqJsonLd />
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <header className="text-center mb-10">
          <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-2" dir="rtl">
            الأسئلة الشائعة
          </h1>
          <h2 className="text-3xl sm:text-4xl font-bold text-gray-900" dir="ltr">
            Frequently Asked Questions
          </h2>
        </header>

        {/* TOC */}
        <nav className="mb-10 flex flex-wrap justify-center gap-3" aria-label="Sections">
          {SECTIONS.map((s) => (
            <a
              key={s.key}
              href={`#${s.key}`}
              className="text-sm text-brand-600 hover:text-brand-700 underline-offset-2 hover:underline"
            >
              <span dir="rtl">{s.ar}</span>
              <span className="mx-1 text-gray-400">·</span>
              <span dir="ltr">{s.en}</span>
            </a>
          ))}
        </nav>

        {SECTIONS.map((section) => (
          <section key={section.key} id={section.key} className="mb-10 scroll-mt-20">
            <h2 className="text-2xl font-bold text-gray-900 mb-5 border-b pb-2">
              <span dir="rtl">{section.ar}</span>
              <span className="mx-2 text-gray-400">·</span>
              <span dir="ltr">{section.en}</span>
            </h2>
            <div className="space-y-6">
              {section.faqs.map((faq) => (
                <details key={faq.id} id={faq.id} className="card p-5 group scroll-mt-20" open>
                  <summary className="cursor-pointer list-none flex justify-between gap-4">
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-900" dir="rtl">
                        {faq.q_ar}
                      </h3>
                      <h3 className="font-semibold text-gray-900 mt-1" dir="ltr">
                        {faq.q_en}
                      </h3>
                    </div>
                    <svg
                      className="w-5 h-5 text-gray-400 group-open:rotate-180 transition-transform shrink-0 mt-1"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      aria-hidden
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 9l-7 7-7-7"
                      />
                    </svg>
                  </summary>
                  <div className="mt-4 space-y-3 border-t border-gray-100 pt-3">
                    <p className="text-gray-700 leading-relaxed" dir="rtl">
                      {faq.a_ar}
                    </p>
                    <p className="text-gray-700 leading-relaxed" dir="ltr">
                      {faq.a_en}
                    </p>
                  </div>
                </details>
              ))}
            </div>
          </section>
        ))}

        <section className="text-center pt-6 border-t border-gray-200">
          <p className="text-gray-600 mb-4">
            <span dir="rtl">لم تجد إجابتك؟</span>
            <span className="mx-2">·</span>
            <span dir="ltr">Still have questions?</span>
          </p>
          <div className="flex gap-3 justify-center flex-wrap">
            <Link href="/help" className="btn-secondary px-5 py-2">
              <span dir="rtl">مركز المساعدة</span>
              <span className="mx-2">·</span>
              <span dir="ltr">Help Center</span>
            </Link>
            <a
              href="mailto:support@kaasb.com"
              className="btn-secondary px-5 py-2"
            >
              support@kaasb.com
            </a>
          </div>
        </section>
      </main>
    </>
  );
}
