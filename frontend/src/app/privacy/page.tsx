import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Privacy Policy | سياسة الخصوصية",
  description:
    "How Kaasb collects, uses, stores and protects personal data of users of the Kaasb freelancing marketplace in Iraq. Bilingual (Arabic / English).",
  robots: { index: true, follow: true },
};

// NOTE for future maintainers: before first public reliance, replace these
// placeholders in the rendered prose below — do NOT leave them blank.
// <!-- __REG_NO__ = Iraqi commercial registration number -->
// <!-- __ADDRESS__ = registered physical address -->
// <!-- __COMPANY_TYPE__ = registration type (e.g. LLC) -->

const VERSION = "1.0";
const EFFECTIVE_DATE_EN = "20 April 2026";
const EFFECTIVE_DATE_AR = "٢٠ نيسان ٢٠٢٦";
const COMPANY_EN = "Kaasb Technology LLC";
const COMPANY_AR = "شركة كاسب تكنولوجي";
const EMAIL_PRIVACY = "privacy@kaasb.com";
const EMAIL_LEGAL = "legal@kaasb.com";
const EMAIL_SECURITY = "security@kaasb.com";
const EMAIL_SUPPORT = "support@kaasb.com";

type Toc = { id: string; en: string; ar: string };

const TOC: Toc[] = [
  { id: "1",  en: "Introduction",            ar: "تمهيد" },
  { id: "2",  en: "Definitions",             ar: "التعريفات" },
  { id: "3",  en: "Data Controller",         ar: "المتحكم بالبيانات" },
  { id: "4",  en: "Data We Collect",         ar: "البيانات التي نجمعها" },
  { id: "5",  en: "Purposes & Legal Bases",  ar: "الأغراض والأسس القانونية" },
  { id: "6",  en: "Qi Card Payment Flow",    ar: "تدفق الدفع عبر كي كارد" },
  { id: "7",  en: "Sub-processors",          ar: "المعالجون الفرعيون" },
  { id: "8",  en: "International Transfers", ar: "النقل الدولي للبيانات" },
  { id: "9",  en: "Retention Periods",       ar: "مُدد الاحتفاظ" },
  { id: "10", en: "Security",                ar: "الإجراءات الأمنية" },
  { id: "11", en: "Your Rights",             ar: "حقوق المستخدم" },
  { id: "12", en: "Cookies",                 ar: "ملفات الارتباط" },
  { id: "13", en: "Children",                ar: "القاصرون" },
  { id: "14", en: "Breach Notification",     ar: "الإخطار بخرق البيانات" },
  { id: "15", en: "Changes to This Policy",  ar: "تعديل هذه السياسة" },
  { id: "16", en: "Contact",                 ar: "التواصل" },
  { id: "17", en: "Language Precedence",     ar: "الأسبقية اللغوية" },
];

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <div className="bg-brand-50 border-b border-brand-100 py-12">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-gray-900">Privacy Policy</h1>
          <p className="mt-1 text-sm text-gray-500">
            Version {VERSION} · Effective {EFFECTIVE_DATE_EN}
          </p>
          <h2 className="mt-6 text-2xl font-bold text-gray-900 text-right" dir="rtl">
            سياسة الخصوصية
          </h2>
          <p className="mt-1 text-sm text-gray-500 text-right" dir="rtl">
            الإصدار {VERSION} · نافذ اعتباراً من {EFFECTIVE_DATE_AR}
          </p>
          <p className="mt-4 text-xs text-gray-500 italic max-w-2xl">
            Pending formal review by licensed Iraqi counsel before public reliance.
            — قيد المراجعة القانونية من قبل محامٍ عراقي مرخّص قبل الاعتماد العام.
          </p>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="lg:grid lg:grid-cols-[240px_1fr] lg:gap-12">

          {/* Sticky TOC — desktop */}
          <aside className="hidden lg:block">
            <nav aria-label="Table of contents" className="lg:sticky lg:top-6">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                Contents · المحتوى
              </h3>
              <ol className="space-y-1.5 text-sm">
                {TOC.map((s) => (
                  <li key={s.id}>
                    <a href={`#${s.id}`} className="text-gray-600 hover:text-brand-600 hover:underline block leading-snug">
                      <span className="font-mono text-xs text-gray-400 mr-1">{s.id}.</span>
                      {s.en} <span className="text-gray-400" dir="rtl">· {s.ar}</span>
                    </a>
                  </li>
                ))}
              </ol>
            </nav>
          </aside>

          {/* Mobile TOC — collapsible */}
          <details className="lg:hidden mb-8 border border-gray-200 rounded-lg p-4">
            <summary className="text-sm font-semibold text-gray-700 cursor-pointer">
              Contents · المحتوى ({TOC.length})
            </summary>
            <ol className="mt-3 space-y-1.5 text-sm">
              {TOC.map((s) => (
                <li key={s.id}>
                  <a href={`#${s.id}`} className="text-gray-600 hover:text-brand-600 hover:underline">
                    <span className="font-mono text-xs text-gray-400 mr-1">{s.id}.</span>
                    {s.en} <span className="text-gray-400" dir="rtl">· {s.ar}</span>
                  </a>
                </li>
              ))}
            </ol>
          </details>

          <article className="space-y-14 min-w-0">

            {/* 1. Introduction */}
            <section id="1" className="scroll-mt-24">
              <SectionHeader num="1" en="Introduction" ar="تمهيد" />
              <Bilingual
                en={
                  <>
                    <p>
                      {COMPANY_EN} (&quot;Kaasb&quot;, &quot;we&quot;, &quot;our&quot;, &quot;us&quot;) operates the online freelancing
                      marketplace available at{" "}
                      <Link href="https://kaasb.com" className="text-brand-500 hover:underline">kaasb.com</Link>{" "}
                      (the &quot;Platform&quot;). This Privacy Policy (the &quot;Policy&quot;) describes the categories of
                      personal data we collect, the purposes and legal bases for processing, the parties with
                      whom we share data, the security measures we apply, and the rights available to you.
                    </p>
                    <p className="mt-3">
                      This Policy applies to visitors, registered buyers (clients), registered sellers
                      (freelancers), and administrators. By registering, logging in, or continuing to use the
                      Platform after the effective date of this Policy, you acknowledge that you have read and
                      understood it.
                    </p>
                  </>
                }
                ar={
                  <>
                    <p>
                      تُشغِّل {COMPANY_AR} («كاسب» أو «نحن») منصة العمل الحر المتاحة على{" "}
                      <Link href="https://kaasb.com" className="text-brand-500 hover:underline" dir="ltr">kaasb.com</Link>{" "}
                      («المنصة»). توضح هذه السياسة («السياسة») فئات البيانات الشخصية التي نجمعها، وأغراض
                      المعالجة وأسسها القانونية، والأطراف التي نُشارك معها البيانات، والتدابير الأمنية
                      المُتَّبعة، والحقوق الممنوحة لك.
                    </p>
                    <p className="mt-3">
                      تسري هذه السياسة على الزوار والمشترين المسجلين (العملاء) والبائعين المسجلين (المستقلين)
                      والإداريين. وبتسجيلك أو دخولك أو استمرار استخدامك للمنصة بعد تاريخ نفاذ هذه السياسة،
                      فإنك تُقرّ بقراءتها واستيعابها.
                    </p>
                  </>
                }
              />
            </section>

            {/* 2. Definitions */}
            <section id="2" className="scroll-mt-24">
              <SectionHeader num="2" en="Definitions" ar="التعريفات" />
              <Bilingual
                en={
                  <ul className="list-disc ms-6 space-y-2">
                    <li><strong>Personal Data</strong> — any information relating to an identified or identifiable natural person.</li>
                    <li><strong>Processing</strong> — any operation performed on Personal Data, including collection, storage, use, disclosure or erasure.</li>
                    <li><strong>Data Controller</strong> — the party that determines the purposes and means of Processing. For this Platform, that party is Kaasb.</li>
                    <li><strong>Sub-processor</strong> — a third party that processes Personal Data on behalf of Kaasb under contract.</li>
                    <li><strong>User</strong> — any natural person who creates an account on the Platform, whether as a Buyer or Seller.</li>
                  </ul>
                }
                ar={
                  <ul className="list-disc me-6 space-y-2">
                    <li><strong>البيانات الشخصية</strong> — أي معلومة تتعلق بشخص طبيعي محدَّد أو قابل للتحديد.</li>
                    <li><strong>المعالجة</strong> — أي عملية تُجرى على البيانات الشخصية، بما فيها الجمع والتخزين والاستخدام والإفصاح والمحو.</li>
                    <li><strong>المتحكم بالبيانات</strong> — الطرف الذي يُحدِّد أغراض المعالجة ووسائلها، وهو في هذه المنصة: كاسب.</li>
                    <li><strong>المعالج الفرعي</strong> — طرف خارجي يُعالج البيانات الشخصية نيابةً عن كاسب بموجب عقد.</li>
                    <li><strong>المستخدم</strong> — أي شخص طبيعي يُنشئ حساباً على المنصة، سواء كان مشترياً أو بائعاً.</li>
                  </ul>
                }
              />
            </section>

            {/* 3. Data Controller */}
            <section id="3" className="scroll-mt-24">
              <SectionHeader num="3" en="Data Controller" ar="المتحكم بالبيانات" />
              <Bilingual
                en={
                  <>
                    <p>The Data Controller responsible for your Personal Data is:</p>
                    <address className="not-italic mt-3 space-y-1">
                      <div><strong>{COMPANY_EN}</strong></div>
                      <div>Republic of Iraq</div>
                      <div>Privacy: <a href={`mailto:${EMAIL_PRIVACY}`} className="text-brand-500 hover:underline">{EMAIL_PRIVACY}</a></div>
                      <div>Legal: <a href={`mailto:${EMAIL_LEGAL}`} className="text-brand-500 hover:underline">{EMAIL_LEGAL}</a></div>
                    </address>
                    <p className="mt-3 text-sm text-gray-600">
                      We have not appointed a Data Protection Officer, as none is required under the laws
                      currently applicable to us. All data-protection enquiries should be addressed to the
                      privacy email above.
                    </p>
                  </>
                }
                ar={
                  <>
                    <p>المتحكم بالبيانات المسؤول عن معالجة بياناتك الشخصية هو:</p>
                    <address className="not-italic mt-3 space-y-1">
                      <div><strong>{COMPANY_AR}</strong></div>
                      <div>جمهورية العراق</div>
                      <div>الخصوصية: <a href={`mailto:${EMAIL_PRIVACY}`} className="text-brand-500 hover:underline">{EMAIL_PRIVACY}</a></div>
                      <div>الشؤون القانونية: <a href={`mailto:${EMAIL_LEGAL}`} className="text-brand-500 hover:underline">{EMAIL_LEGAL}</a></div>
                    </address>
                    <p className="mt-3 text-sm text-gray-600">
                      لم نُعيِّن مسؤولاً لحماية البيانات لعدم وجود إلزام بذلك بموجب التشريعات السارية
                      حالياً. تُوجَّه جميع الاستفسارات المتعلقة بحماية البيانات إلى البريد الإلكتروني أعلاه.
                    </p>
                  </>
                }
              />
            </section>

            {/* 4. Data We Collect */}
            <section id="4" className="scroll-mt-24">
              <SectionHeader num="4" en="Data We Collect" ar="البيانات التي نجمعها" />
              <Bilingual
                en={
                  <div className="space-y-4">
                    <Sub num="4.1" title="Account data">
                      First and last name, username, email address, hashed password (bcrypt — we never store
                      your password in plain text), primary role (Buyer or Seller), and preferred language.
                    </Sub>
                    <Sub num="4.2" title="Profile data">
                      Display name, profile photo (optional), biography, skills, professional title, country
                      and city (optional), portfolio links, Seller Level, completion rate, response rate, and
                      public ratings. Profile data displayed to other Users is listed clearly on your profile
                      settings page.
                    </Sub>
                    <Sub num="4.3" title="Payment data">
                      Qi Card payment identifier returned by the Qi Card gateway after a successful
                      transaction, transaction amount in Iraqi Dinars (IQD), transaction reference numbers,
                      escrow state, and payout history. We do <strong>not</strong> collect, store, or have access
                      to your full card number, CVV, or PIN; those are handled directly by Qi Card.
                    </Sub>
                    <Sub num="4.4" title="Communications data">
                      Messages exchanged between Users on the Platform, attachments, system messages
                      generated by the order workflow, and records of any moderation action. We scan messages
                      for prohibited content (off-platform solicitation, sharing of contact details intended
                      to circumvent the Platform) using an automated filter and retain the filter log.
                    </Sub>
                    <Sub num="4.5" title="Device & usage data">
                      IP address, user-agent string, device/browser type, operating system, language header,
                      pages visited, request timestamps, referrer URL, and session identifiers. Used for
                      security, abuse prevention, and service reliability.
                    </Sub>
                    <Sub num="4.6" title="Cookies & storage">
                      Authentication cookies (<code className="text-xs">access_token</code>,{" "}
                      <code className="text-xs">refresh_token</code>), CSRF-protection cookie, locale cookie,
                      and a single <code className="text-xs">localStorage</code> key recording your cookie
                      consent choice. See our <Link href="/cookies" className="text-brand-500 hover:underline">Cookie Policy</Link>.
                    </Sub>
                    <Sub num="4.7" title="Uploaded files">
                      Gig images, order delivery files, and profile avatars you upload. File type and size are
                      validated server-side; we scan for magic-byte consistency. We do not extract or index
                      content from uploaded files beyond what is necessary to display them on the Platform.
                    </Sub>
                    <Sub num="4.8" title="Social-login identifiers">
                      If you sign in with Google or Facebook, we receive your verified email address, display
                      name, profile photo URL, and the provider&apos;s stable account ID. We do not receive your
                      contacts, friends list, or social graph.
                    </Sub>
                    <Sub num="4.9" title="Phone OTP">
                      If you verify a phone number, we store the phone number, a SHA-256 hash of the
                      one-time code (never the code itself), expiry timestamp, attempt counter, and delivery
                      channel (SMS, WhatsApp, or email fallback).
                    </Sub>
                    <Sub num="4.10" title="Admin audit records">
                      If you are an administrator, actions you take on the Platform (user status changes,
                      payout approvals, escrow releases, dispute resolutions) are recorded in an audit log
                      with your user identifier, a timestamp, the affected record, and the decision taken.
                    </Sub>
                  </div>
                }
                ar={
                  <div className="space-y-4">
                    <Sub num="٤.١" title="بيانات الحساب" rtl>
                      الاسم الأول واسم العائلة، اسم المستخدم، البريد الإلكتروني، كلمة المرور بعد تشفيرها
                      بخوارزمية bcrypt (لا نُخزِّن كلمة المرور نصّاً صريحاً إطلاقاً)، الدور الأساسي (مشترٍ
                      أو بائع)، واللغة المفضَّلة.
                    </Sub>
                    <Sub num="٤.٢" title="بيانات الملف الشخصي" rtl>
                      الاسم المعروض، الصورة الشخصية (اختيارية)، النبذة التعريفية، المهارات، المسمى الوظيفي،
                      البلد والمدينة (اختيارية)، روابط أعمال سابقة، مستوى البائع، معدل الإنجاز، معدل
                      الاستجابة، والتقييمات العامة. تُعرض البيانات المنشورة لسائر المستخدمين بوضوح في صفحة
                      إعدادات ملفك الشخصي.
                    </Sub>
                    <Sub num="٤.٣" title="بيانات الدفع" rtl>
                      المُعرِّف الذي تُرجعه بوابة كي كارد عند إتمام المعاملة، ومبلغ المعاملة بالدينار
                      العراقي، والأرقام المرجعية، وحالة الضمان (الإسكرو)، وسجل الصرف. لا نجمع رقم بطاقتك
                      الكامل ولا رمز التحقق (CVV) ولا الرقم السري (PIN) ولا نتمكن من الاطلاع عليها؛ إذ
                      تُعالَج مباشرةً لدى كي كارد.
                    </Sub>
                    <Sub num="٤.٤" title="بيانات المراسلات" rtl>
                      الرسائل المُتبادَلة بين المستخدمين على المنصة، والمرفقات، والرسائل النظامية الصادرة
                      عن دورة العمل، وسجلات إجراءات المراقبة. نُجري فحصاً آلياً للرسائل بحثاً عن محتوى
                      محظور (المحاولات لصرف التعامل خارج المنصة أو تبادل بيانات الاتصال بقصد التحايل)،
                      ونحتفظ بسجل نتائج الفلترة.
                    </Sub>
                    <Sub num="٤.٥" title="بيانات الجهاز والاستخدام" rtl>
                      عنوان IP، وبيانات المتصفح والجهاز ونظام التشغيل، ولغة الطلب، والصفحات المزارة،
                      والطوابع الزمنية، ورابط المصدر، ومُعرِّفات الجلسات. تُستخدم لأغراض الأمن ومكافحة
                      الإساءة وضمان موثوقية الخدمة.
                    </Sub>
                    <Sub num="٤.٦" title="ملفات الارتباط والتخزين" rtl>
                      ملفات ارتباط المصادقة (<code className="text-xs" dir="ltr">access_token</code> و{" "}
                      <code className="text-xs" dir="ltr">refresh_token</code>)، وملف حماية CSRF، وملف
                      اللغة، ومفتاح واحد في{" "}
                      <code className="text-xs" dir="ltr">localStorage</code> لحفظ اختيارك لإعدادات
                      الارتباط. راجع{" "}
                      <Link href="/cookies" className="text-brand-500 hover:underline">سياسة ملفات الارتباط</Link>.
                    </Sub>
                    <Sub num="٤.٧" title="الملفات المرفوعة" rtl>
                      صور الخدمات، وملفات تسليم الطلبات، والصور الشخصية التي ترفعها. يُتحقَّق من النوع
                      والحجم على الخادم، ويُجرى فحص توافق التوقيع الأول للملف. لا نستخرج محتوى الملفات
                      المرفوعة ولا نفهرسه خارج ما يلزم لعرضها على المنصة.
                    </Sub>
                    <Sub num="٤.٨" title="مُعرِّفات تسجيل الدخول الاجتماعي" rtl>
                      إذا سجّلت الدخول عبر جوجل أو فيسبوك، نتلقى بريدك الإلكتروني المُتحقَّق منه، والاسم
                      المعروض، ورابط الصورة، ومُعرِّف الحساب الثابت لدى المزوِّد. لا نستلم جهات اتصالك
                      ولا قوائم أصدقائك ولا شبكتك الاجتماعية.
                    </Sub>
                    <Sub num="٤.٩" title="التحقق عبر الهاتف" rtl>
                      عند التحقق من رقم الهاتف، نُخزِّن الرقم، وبصمة SHA-256 لرمز التحقق (ولا نُخزِّن
                      الرمز نفسه)، وتاريخ الانتهاء، وعدّاد المحاولات، وقناة التسليم (SMS أو واتساب أو
                      بريد إلكتروني بديل).
                    </Sub>
                    <Sub num="٤.١٠" title="سجلات تدقيق الإداريين" rtl>
                      إن كنت إدارياً، تُسجَّل الإجراءات التي تتخذها على المنصة (تغيير حالة المستخدمين،
                      الموافقة على الصرف، إفراج الإسكرو، تسوية النزاعات) في سجل تدقيق يتضمن مُعرِّفك
                      والطابع الزمني والسجل المتأثر والقرار المتخذ.
                    </Sub>
                  </div>
                }
              />
            </section>

            {/* 5. Purposes & Legal Bases */}
            <section id="5" className="scroll-mt-24">
              <SectionHeader num="5" en="Purposes & Legal Bases" ar="الأغراض والأسس القانونية" />
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left border-collapse">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="p-3 font-semibold text-gray-700 border border-gray-200">Purpose · الغرض</th>
                      <th className="p-3 font-semibold text-gray-700 border border-gray-200">Data · البيانات</th>
                      <th className="p-3 font-semibold text-gray-700 border border-gray-200">Legal basis · الأساس</th>
                    </tr>
                  </thead>
                  <tbody className="text-gray-700 align-top">
                    {[
                      ["Creating and maintaining your account · إنشاء حسابك وإدارته", "Account, Profile", "Performance of a contract · تنفيذ العقد"],
                      ["Processing orders and payments · معالجة الطلبات والمدفوعات", "Payment, Account", "Performance of a contract · تنفيذ العقد"],
                      ["Detecting fraud and abuse · كشف الاحتيال والإساءة", "Device & usage, Communications", "Legitimate interest · مصلحة مشروعة"],
                      ["Enforcing Terms and moderating content · إنفاذ الشروط ومراقبة المحتوى", "Communications, Profile", "Legitimate interest · مصلحة مشروعة"],
                      ["Sending service notifications · إرسال إشعارات الخدمة", "Account", "Performance of a contract · تنفيذ العقد"],
                      ["Complying with Iraqi commercial, tax and AML law · الامتثال للقانون التجاري والضريبي وقوانين مكافحة غسل الأموال العراقية", "Payment, Account", "Legal obligation · التزام قانوني"],
                      ["Improving service reliability and performance · تحسين الموثوقية والأداء", "Device & usage (aggregated)", "Legitimate interest · مصلحة مشروعة"],
                      ["Non-essential cookies (none today) · ملفات ارتباط غير أساسية (لا يوجد حالياً)", "—", "Consent · الموافقة"],
                    ].map(([purpose, data, basis]) => (
                      <tr key={purpose} className="border-b border-gray-200">
                        <td className="p-3 border border-gray-200">{purpose}</td>
                        <td className="p-3 border border-gray-200">{data}</td>
                        <td className="p-3 border border-gray-200">{basis}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            {/* 6. Qi Card Flow */}
            <section id="6" className="scroll-mt-24">
              <SectionHeader num="6" en="Qi Card Payment Flow" ar="تدفق الدفع عبر كي كارد" />
              <Bilingual
                en={
                  <>
                    <p>
                      All payments on the Platform are processed exclusively through Qi Card in Iraqi Dinars
                      (IQD). The end-to-end flow is:
                    </p>
                    <ol className="list-decimal ms-6 mt-3 space-y-1.5">
                      <li>You initiate a payment on the Platform. Kaasb creates a payment session and signs the redirect URL with HMAC-SHA256 to prevent tampering.</li>
                      <li>You are redirected to Qi Card&apos;s environment where you enter your card or wallet details. Kaasb never sees that data.</li>
                      <li>Qi Card processes the payment and redirects you back with a signed reference.</li>
                      <li>Kaasb verifies the signature, records the reference, and holds the funds logically in escrow until the order is completed, auto-completed, cancelled, or resolved by dispute.</li>
                      <li>Payouts to Sellers are initiated manually by Kaasb administrators through the Qi Card merchant portal, because Qi Card does not currently expose a payout API.</li>
                    </ol>
                    <p className="mt-3 text-sm text-gray-600">
                      Qi Card is an independent payment processor. Its handling of your card data is governed
                      by Qi Card&apos;s own privacy terms, which are outside the scope of this Policy.
                    </p>
                  </>
                }
                ar={
                  <>
                    <p>
                      تُعالَج جميع المدفوعات على المنصة حصرياً عبر «كي كارد» وبالدينار العراقي. ويجري
                      التدفق على النحو الآتي:
                    </p>
                    <ol className="list-decimal me-6 mt-3 space-y-1.5">
                      <li>تبدأ عملية الدفع على المنصة. تُنشئ كاسب جلسة دفع وتوقّع رابط التحويل بخوارزمية HMAC-SHA256 لمنع العبث به.</li>
                      <li>تُحوَّل إلى بيئة كي كارد لإدخال بيانات بطاقتك أو محفظتك، ولا يمكن لكاسب الاطلاع على هذه البيانات.</li>
                      <li>تُعالج كي كارد العملية وتُعيدك إلى المنصة برقم مرجعي مُوقَّع.</li>
                      <li>تتحقق كاسب من التوقيع وتُقيِّد المرجع، وتحتفظ بالأموال منطقياً في حساب الضمان (إسكرو) حتى إتمام الطلب أو إتمامه تلقائياً أو إلغائه أو البتّ فيه بنزاع.</li>
                      <li>يُنفَّذ صرف مستحقات البائعين يدوياً من قِبل إداريي كاسب عبر بوابة التاجر في كي كارد، إذ لا تُتيح كي كارد حالياً واجهة برمجية للصرف.</li>
                    </ol>
                    <p className="mt-3 text-sm text-gray-600">
                      تُعدّ «كي كارد» معالج دفع مستقلاً، وتخضع معالجتها لبيانات بطاقتك لشروط خصوصيتها
                      الخاصة، وهي خارج نطاق هذه السياسة.
                    </p>
                  </>
                }
              />
            </section>

            {/* 7. Sub-processors */}
            <section id="7" className="scroll-mt-24">
              <SectionHeader num="7" en="Sub-processors" ar="المعالجون الفرعيون" />
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left border-collapse">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="p-3 font-semibold text-gray-700 border border-gray-200">Processor</th>
                      <th className="p-3 font-semibold text-gray-700 border border-gray-200">Purpose</th>
                      <th className="p-3 font-semibold text-gray-700 border border-gray-200">Location</th>
                    </tr>
                  </thead>
                  <tbody className="text-gray-700">
                    {[
                      ["Qi Card", "Payment processing · معالجة الدفع", "Iraq · العراق"],
                      ["Hetzner Online GmbH", "Hosting, database, backups · استضافة وقواعد البيانات والنسخ الاحتياطي", "Germany · ألمانيا"],
                      ["Resend", "Transactional email · البريد الإلكتروني", "United States · الولايات المتحدة"],
                      ["Sentry", "Error tracking (PII-stripped) · تتبع الأخطاء (بعد إزالة البيانات الشخصية)", "United States · الولايات المتحدة"],
                      ["Google LLC (OAuth)", "Optional social login · تسجيل دخول اختياري", "United States · الولايات المتحدة"],
                      ["Meta Platforms (Facebook Login)", "Optional social login · تسجيل دخول اختياري", "United States · الولايات المتحدة"],
                      ["Twilio", "Phone OTP delivery (SMS / WhatsApp) · إرسال رموز التحقق", "United States · الولايات المتحدة"],
                    ].map(([p, purpose, loc]) => (
                      <tr key={p} className="border-b border-gray-200">
                        <td className="p-3 border border-gray-200 font-medium">{p}</td>
                        <td className="p-3 border border-gray-200">{purpose}</td>
                        <td className="p-3 border border-gray-200">{loc}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-3 text-sm text-gray-600">
                We do not currently use analytics, advertising, or third-party customer-support tools. If we
                add any, this list will be updated and — where required by applicable law — your consent
                will be requested.
                <br dir="rtl" />
                <span dir="rtl">لا نستخدم حالياً أدوات تحليل أو إعلانات أو دعم عملاء من أطراف خارجية. عند إضافة أيٍّ منها، سيُحدَّث هذا الجدول، وسنطلب موافقتك حيثما اقتضى القانون ذلك.</span>
              </p>
            </section>

            {/* 8. International transfers */}
            <section id="8" className="scroll-mt-24">
              <SectionHeader num="8" en="International Transfers" ar="النقل الدولي للبيانات" />
              <Bilingual
                en={
                  <p>
                    Personal Data is transferred outside the Republic of Iraq to the locations of the
                    Sub-processors listed in Section 7 (primarily Germany and the United States). We take
                    reasonable contractual and technical measures — including standard data-protection
                    clauses, encryption in transit (TLS), and least-privilege access controls — to ensure an
                    adequate level of protection. By using the Platform, you acknowledge that your Personal
                    Data may be processed in those jurisdictions.
                  </p>
                }
                ar={
                  <p>
                    تُنقَل البيانات الشخصية خارج جمهورية العراق إلى مواقع المعالجين الفرعيين المذكورين في
                    البند 7 (بشكل رئيسي ألمانيا والولايات المتحدة). ونتّخذ تدابير تعاقدية وفنية معقولة —
                    تشمل شروط حماية بيانات قياسية، والتشفير أثناء النقل (TLS)، ومبدأ أدنى الصلاحيات —
                    لضمان مستوى حماية كافٍ. وباستخدامك للمنصة، فإنك تُقرّ بجواز معالجة بياناتك الشخصية في
                    تلك الولايات القضائية.
                  </p>
                }
              />
            </section>

            {/* 9. Retention */}
            <section id="9" className="scroll-mt-24">
              <SectionHeader num="9" en="Retention Periods" ar="مُدد الاحتفاظ" />
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left border-collapse">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="p-3 font-semibold text-gray-700 border border-gray-200">Data · البيانات</th>
                      <th className="p-3 font-semibold text-gray-700 border border-gray-200">Retention · المدة</th>
                      <th className="p-3 font-semibold text-gray-700 border border-gray-200">After · بعد المدة</th>
                    </tr>
                  </thead>
                  <tbody className="text-gray-700">
                    {[
                      ["Active account data · بيانات الحساب النشط", "While account is active · طوال فترة نشاط الحساب", "Deleted or anonymised on closure · تُحذف أو تُجعل مجهولة عند الإغلاق"],
                      ["Notifications · الإشعارات", "90 days · ٩٠ يوماً", "Permanently deleted · تُحذف نهائياً"],
                      ["Revoked session tokens · جلسات مُلغاة", "30 days · ٣٠ يوماً", "Permanently deleted · تُحذف نهائياً"],
                      ["Deactivated accounts (PII) · حسابات معطّلة", "24 months · ٢٤ شهراً", "Personal data anonymised · تُجعل البيانات مجهولة"],
                      ["Messages (after either party closes account) · الرسائل بعد إغلاق أحد الطرفين", "90 days · ٩٠ يوماً", "Content purged, metadata retained for records · يُمسح المحتوى وتبقى البيانات الوصفية"],
                      ["Uploaded files (after order closure or account deletion) · الملفات المرفوعة", "90 days · ٩٠ يوماً", "Permanently deleted · تُحذف نهائياً"],
                      ["Financial & transaction records · السجلات المالية والمعاملات", "10 years · ١٠ سنوات", "Retained (Iraqi Commercial Code Art. 12) · احتفاظ إلزامي وفق المادة ١٢ من قانون التجارة"],
                      ["Admin audit log · سجل تدقيق الإداريين", "10 years · ١٠ سنوات", "Retained · احتفاظ دائم"],
                      ["Pending moderation reports · بلاغات قيد المراجعة", "6 months · ٦ أشهر", "Auto-dismissed · تُصرف تلقائياً"],
                      ["Database backups · النسخ الاحتياطية", "Up to 35 days · ٣٥ يوماً كحد أقصى", "Rotated out of backup set · تُزال من مجموعة النسخ"],
                    ].map(([d, r, a]) => (
                      <tr key={d} className="border-b border-gray-200">
                        <td className="p-3 border border-gray-200">{d}</td>
                        <td className="p-3 border border-gray-200">{r}</td>
                        <td className="p-3 border border-gray-200">{a}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-3 text-sm text-gray-600">
                The 10-year retention for financial and audit records reflects record-keeping obligations
                imposed on Iraqi commercial entities. Where a longer retention is required by law, court
                order, or ongoing regulatory investigation, data may be retained for that longer period.
                <br dir="rtl" />
                <span dir="rtl">تعكس مدة العشر سنوات للسجلات المالية وسجلات التدقيق الالتزامات المفروضة على الكيانات التجارية العراقية. وعند وجود التزام قانوني أو قرار قضائي أو تحقيق رقابي مستمر يستلزم مدة أطول، تُحفظ البيانات لتلك المدة.</span>
              </p>
            </section>

            {/* 10. Security */}
            <section id="10" className="scroll-mt-24">
              <SectionHeader num="10" en="Security" ar="الإجراءات الأمنية" />
              <Bilingual
                en={
                  <>
                    <p>We apply a defence-in-depth approach, including:</p>
                    <ul className="list-disc ms-6 mt-3 space-y-1.5">
                      <li>TLS encryption for all traffic between your device and our servers.</li>
                      <li>Bcrypt password hashing with per-user salt; passwords are never stored or logged in plain text.</li>
                      <li>Short-lived JWT access tokens (30 minutes) and rotating refresh tokens (7 days) stored as HTTP-only cookies.</li>
                      <li>Automatic revocation of all active sessions and token-version bump on password change or reset.</li>
                      <li>HMAC-SHA256 signing of Qi Card redirect URLs to prevent payment tampering.</li>
                      <li>Redis-backed single-use controls on password-reset tokens.</li>
                      <li>Rate limiting, CSRF protection, and security-relevant HTTP headers.</li>
                      <li>Automated scanning of user-to-user messages for prohibited content.</li>
                      <li>Dual-control approval required for administrative payouts above the threshold configured under Iraqi law.</li>
                      <li>Immutable admin audit log for sensitive operations.</li>
                      <li>Centralised error tracking with PII stripped before submission.</li>
                    </ul>
                    <p className="mt-3 text-sm text-gray-600">
                      No security measure is absolute. If you discover a vulnerability, please report it
                      responsibly to{" "}
                      <a href={`mailto:${EMAIL_SECURITY}`} className="text-brand-500 hover:underline">{EMAIL_SECURITY}</a>.
                    </p>
                  </>
                }
                ar={
                  <>
                    <p>نعتمد نهج «الدفاع متعدد الطبقات»، يشمل:</p>
                    <ul className="list-disc me-6 mt-3 space-y-1.5">
                      <li>تشفير جميع الاتصالات بين جهازك وخوادمنا بواسطة TLS.</li>
                      <li>تجزئة كلمات المرور بخوارزمية bcrypt مع ملح فريد لكل مستخدم، دون تخزينها أو تسجيلها نصّاً صريحاً إطلاقاً.</li>
                      <li>رموز وصول JWT قصيرة العمر (٣٠ دقيقة) ورموز تجديد متناوبة (٧ أيام) تُحفظ في ملفات ارتباط HTTP-only.</li>
                      <li>إبطال فوري لجميع الجلسات ورفع إصدار الرمز عند تغيير كلمة المرور أو إعادة ضبطها.</li>
                      <li>توقيع روابط التحويل إلى كي كارد بخوارزمية HMAC-SHA256 لمنع التلاعب.</li>
                      <li>منع إعادة استعمال رموز إعادة التعيين باستخدام قائمة إبطال في Redis.</li>
                      <li>ضوابط الحد من المعدل، وحماية CSRF، وترويسات HTTP ذات الصلة بالأمن.</li>
                      <li>فحص آلي لرسائل المستخدمين بحثاً عن المحتوى المحظور.</li>
                      <li>موافقة مزدوجة على عمليات الصرف الإدارية التي تتجاوز الحدّ المُقرَّر وفق القانون العراقي.</li>
                      <li>سجل تدقيق إداري غير قابل للتعديل للعمليات الحساسة.</li>
                      <li>تتبع الأخطاء مركزياً بعد إزالة البيانات الشخصية قبل الإرسال.</li>
                    </ul>
                    <p className="mt-3 text-sm text-gray-600">
                      لا يوجد نظام آمن مئة بالمئة. للإبلاغ عن ثغرة أمنية بشكل مسؤول:{" "}
                      <a href={`mailto:${EMAIL_SECURITY}`} className="text-brand-500 hover:underline">{EMAIL_SECURITY}</a>.
                    </p>
                  </>
                }
              />
            </section>

            {/* 11. Your Rights */}
            <section id="11" className="scroll-mt-24">
              <SectionHeader num="11" en="Your Rights" ar="حقوق المستخدم" />
              <Bilingual
                en={
                  <>
                    <p>Subject to applicable law, you have the right to:</p>
                    <ul className="list-disc ms-6 mt-3 space-y-1.5">
                      <li><strong>Access</strong> the Personal Data we hold about you and receive a copy in a structured JSON format.</li>
                      <li><strong>Rectify</strong> inaccurate or incomplete data through your profile settings, or by contacting us.</li>
                      <li><strong>Delete</strong> your account and Personal Data, subject to the retention obligations in Section 9.</li>
                      <li><strong>Restrict or object</strong> to certain processing, including direct marketing (if introduced in the future).</li>
                      <li><strong>Withdraw consent</strong> where Processing is based on consent, at any time. Withdrawal does not affect lawfulness of Processing carried out before withdrawal.</li>
                      <li><strong>Lodge a complaint</strong> with the competent authority in the Republic of Iraq or with Kaasb directly.</li>
                    </ul>
                    <p className="mt-3">
                      You may exercise most of these rights from{" "}
                      <Link href="/dashboard/settings" className="text-brand-500 hover:underline">Account Settings</Link>{" "}
                      (including data export and account deletion). Other requests should be sent to{" "}
                      <a href={`mailto:${EMAIL_PRIVACY}`} className="text-brand-500 hover:underline">{EMAIL_PRIVACY}</a>.
                      We respond within thirty (30) days. We may request proof of identity before acting on a
                      request.
                    </p>
                  </>
                }
                ar={
                  <>
                    <p>مع مراعاة القانون الساري، لك الحق في:</p>
                    <ul className="list-disc me-6 mt-3 space-y-1.5">
                      <li><strong>الاطلاع</strong> على بياناتك الشخصية واستلام نسخة منها بتنسيق JSON منظَّم.</li>
                      <li><strong>تصحيح</strong> البيانات غير الدقيقة أو الناقصة عبر الإعدادات أو بمراسلتنا.</li>
                      <li><strong>حذف</strong> حسابك وبياناتك الشخصية مع مراعاة التزامات الاحتفاظ الواردة في البند ٩.</li>
                      <li><strong>تقييد المعالجة أو الاعتراض</strong> عليها في حالات معينة، بما فيها التسويق المباشر حال استحداثه.</li>
                      <li><strong>سحب الموافقة</strong> في أي وقت عندما تكون المعالجة قائمة على الموافقة. ولا يمسّ السحب مشروعية المعالجة السابقة له.</li>
                      <li><strong>تقديم شكوى</strong> إلى الجهة المختصة في جمهورية العراق أو إلى كاسب مباشرةً.</li>
                    </ul>
                    <p className="mt-3">
                      يمكنك ممارسة معظم هذه الحقوق من{" "}
                      <Link href="/dashboard/settings" className="text-brand-500 hover:underline">إعدادات الحساب</Link>{" "}
                      (تصدير البيانات وحذف الحساب). وتُرسل الطلبات الأخرى إلى{" "}
                      <a href={`mailto:${EMAIL_PRIVACY}`} className="text-brand-500 hover:underline">{EMAIL_PRIVACY}</a>.
                      نُجيب خلال ثلاثين (٣٠) يوماً، ولنا أن نطلب إثبات الهوية قبل تنفيذ الطلب.
                    </p>
                  </>
                }
              />
            </section>

            {/* 12. Cookies */}
            <section id="12" className="scroll-mt-24">
              <SectionHeader num="12" en="Cookies" ar="ملفات الارتباط" />
              <Bilingual
                en={
                  <p>
                    We use strictly necessary cookies to keep you signed in and to secure your session, and
                    a single preference key to remember your cookie-consent choice. We do not currently use
                    analytics or advertising cookies. A detailed list is available in our{" "}
                    <Link href="/cookies" className="text-brand-500 hover:underline">Cookie Policy</Link>.
                  </p>
                }
                ar={
                  <p>
                    نستخدم ملفات ارتباط ضرورية فقط لإبقائك مسجلاً وحماية جلستك، ومفتاحاً واحداً لتذكّر
                    اختيارك في شريط الموافقة. ولا نستخدم حالياً ملفات ارتباط تحليلية أو إعلانية. تتوفر
                    القائمة التفصيلية في{" "}
                    <Link href="/cookies" className="text-brand-500 hover:underline">سياسة ملفات الارتباط</Link>.
                  </p>
                }
              />
            </section>

            {/* 13. Children */}
            <section id="13" className="scroll-mt-24">
              <SectionHeader num="13" en="Children" ar="القاصرون" />
              <Bilingual
                en={
                  <p>
                    The Platform is not directed to persons under eighteen (18) years of age, consistent with
                    the legal-capacity threshold under the Iraqi Civil Code. We do not knowingly collect
                    Personal Data from children. If we become aware that Personal Data of a child has been
                    collected, we will delete it and terminate the associated account.
                  </p>
                }
                ar={
                  <p>
                    لا تُوجَّه المنصة إلى من هم دون الثامنة عشرة (١٨) عاماً، انسجاماً مع سن الأهلية في
                    القانون المدني العراقي. ولا نجمع بياناتٍ شخصيةً من القاصرين عن علم، فإن تبيّن لنا خلاف
                    ذلك، حذفنا البيانات وأنهينا الحساب المرتبط بها.
                  </p>
                }
              />
            </section>

            {/* 14. Breach */}
            <section id="14" className="scroll-mt-24">
              <SectionHeader num="14" en="Breach Notification" ar="الإخطار بخرق البيانات" />
              <Bilingual
                en={
                  <p>
                    In the event of a confirmed Personal Data breach that is likely to result in a risk to
                    your rights or interests, we will notify affected Users within seventy-two (72) hours of
                    confirmation, by email and by in-Platform notification. The notice will describe the
                    nature of the breach, the data categories affected, the measures taken to mitigate it,
                    and the steps you can take to protect yourself.
                  </p>
                }
                ar={
                  <p>
                    في حال تأكّد خرق للبيانات الشخصية يُرجَّح أن يُشكِّل خطراً على حقوقك أو مصالحك، نُخطر
                    المستخدمين المتأثرين خلال اثنتين وسبعين (٧٢) ساعةً من التأكد، عبر البريد الإلكتروني
                    وإشعار داخل المنصة. ويتضمن الإخطار طبيعة الخرق وفئات البيانات المتأثرة والتدابير
                    المتخذة للحدّ منه والخطوات التي يمكنك اتخاذها للحماية.
                  </p>
                }
              />
            </section>

            {/* 15. Changes */}
            <section id="15" className="scroll-mt-24">
              <SectionHeader num="15" en="Changes to This Policy" ar="تعديل هذه السياسة" />
              <Bilingual
                en={
                  <p>
                    We may update this Policy to reflect changes in our practices or in applicable law. Any
                    material change will be notified at least thirty (30) days in advance through email
                    and/or in-Platform notification. The version number and effective date at the top of the
                    page identify the currently effective revision. Continued use of the Platform after the
                    effective date constitutes acceptance of the revised Policy.
                  </p>
                }
                ar={
                  <p>
                    قد نُحدِّث هذه السياسة لتعكس تغيّراتٍ في ممارساتنا أو في القانون الساري. ويُخطر
                    بالتعديلات الجوهرية قبل سريانها بثلاثين (٣٠) يوماً على الأقل عبر البريد الإلكتروني أو
                    إشعار داخل المنصة. ويُبيِّن رقم الإصدار وتاريخ النفاذ المعروضان أعلى الصفحة النسخةَ
                    النافذة حالياً. ويُعدّ استمرارك في استخدام المنصة بعد تاريخ النفاذ قبولاً للسياسة
                    المُعدَّلة.
                  </p>
                }
              />
            </section>

            {/* 16. Contact */}
            <section id="16" className="scroll-mt-24">
              <SectionHeader num="16" en="Contact" ar="التواصل" />
              <Bilingual
                en={
                  <address className="not-italic space-y-1">
                    <div><strong>{COMPANY_EN}</strong></div>
                    <div>Republic of Iraq</div>
                    <div>Privacy: <a href={`mailto:${EMAIL_PRIVACY}`} className="text-brand-500 hover:underline">{EMAIL_PRIVACY}</a></div>
                    <div>Legal: <a href={`mailto:${EMAIL_LEGAL}`} className="text-brand-500 hover:underline">{EMAIL_LEGAL}</a></div>
                    <div>Security: <a href={`mailto:${EMAIL_SECURITY}`} className="text-brand-500 hover:underline">{EMAIL_SECURITY}</a></div>
                    <div>Support: <a href={`mailto:${EMAIL_SUPPORT}`} className="text-brand-500 hover:underline">{EMAIL_SUPPORT}</a></div>
                  </address>
                }
                ar={
                  <address className="not-italic space-y-1">
                    <div><strong>{COMPANY_AR}</strong></div>
                    <div>جمهورية العراق</div>
                    <div>الخصوصية: <a href={`mailto:${EMAIL_PRIVACY}`} className="text-brand-500 hover:underline">{EMAIL_PRIVACY}</a></div>
                    <div>الشؤون القانونية: <a href={`mailto:${EMAIL_LEGAL}`} className="text-brand-500 hover:underline">{EMAIL_LEGAL}</a></div>
                    <div>الأمن: <a href={`mailto:${EMAIL_SECURITY}`} className="text-brand-500 hover:underline">{EMAIL_SECURITY}</a></div>
                    <div>الدعم: <a href={`mailto:${EMAIL_SUPPORT}`} className="text-brand-500 hover:underline">{EMAIL_SUPPORT}</a></div>
                  </address>
                }
              />
            </section>

            {/* 17. Precedence */}
            <section id="17" className="scroll-mt-24">
              <SectionHeader num="17" en="Language Precedence" ar="الأسبقية اللغوية" />
              <Bilingual
                en={
                  <p>
                    This Policy is published in Arabic and English. In the event of any conflict,
                    discrepancy, or ambiguity between the two versions, the <strong>Arabic version</strong> shall
                    prevail, consistent with Article 14 of the Iraqi Civil Code and the customary rule of
                    Iraqi courts.
                  </p>
                }
                ar={
                  <p>
                    صدرت هذه السياسة باللغتين العربية والإنجليزية. وفي حال وجود أي تعارض أو اختلاف أو
                    غموض بين النُسختين، تُعتمد <strong>النسخة العربية</strong>، وفقاً لأحكام المادة ١٤ من
                    القانون المدني العراقي والعُرف القضائي العراقي.
                  </p>
                }
              />
            </section>

            {/* Footer nav */}
            <div className="border-t border-gray-200 pt-6 flex flex-wrap gap-4 text-sm text-gray-500">
              <Link href="/terms" className="hover:text-gray-700 hover:underline">Terms of Service</Link>
              <Link href="/cookies" className="hover:text-gray-700 hover:underline">Cookie Policy</Link>
              <Link href="/refunds" className="hover:text-gray-700 hover:underline">Refund Policy</Link>
              <Link href="/acceptable-use" className="hover:text-gray-700 hover:underline">Acceptable Use</Link>
              <Link href="/dashboard/settings" className="hover:text-gray-700 hover:underline">Account Settings</Link>
            </div>

          </article>
        </div>
      </div>
    </div>
  );
}

// ------------------------------------------------------------
// Presentational helpers — kept in-file to avoid a new module.
// ------------------------------------------------------------

function SectionHeader({ num, en, ar }: { num: string; en: string; ar: string }) {
  return (
    <header className="mb-5 pb-3 border-b border-gray-200">
      <h2 className="text-xl font-semibold text-gray-900">
        <span className="font-mono text-sm text-gray-400 mr-2">{num}.</span>
        {en}
      </h2>
      <h3 className="mt-1 text-lg font-semibold text-gray-700 text-right" dir="rtl">
        <span className="font-mono text-sm text-gray-400 ms-2">{toArabicNumerals(num)}.</span>
        {ar}
      </h3>
    </header>
  );
}

function Bilingual({ en, ar }: { en: React.ReactNode; ar: React.ReactNode }) {
  return (
    <div className="grid md:grid-cols-2 md:gap-8 gap-4">
      <div dir="ltr" className="text-gray-700 leading-relaxed">{en}</div>
      <div dir="rtl" className="text-gray-700 leading-relaxed md:border-r md:pr-8 md:border-gray-200">{ar}</div>
    </div>
  );
}

function Sub({
  num,
  title,
  rtl,
  children,
}: {
  num: string;
  title: string;
  rtl?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h4 className={`font-semibold text-gray-900 ${rtl ? "text-right" : ""}`} dir={rtl ? "rtl" : "ltr"}>
        <span className="font-mono text-xs text-gray-400 me-1">{num}</span>
        {title}
      </h4>
      <p className="mt-1 text-gray-700 leading-relaxed" dir={rtl ? "rtl" : "ltr"}>{children}</p>
    </div>
  );
}

function toArabicNumerals(s: string): string {
  const map: Record<string, string> = { "0": "٠", "1": "١", "2": "٢", "3": "٣", "4": "٤", "5": "٥", "6": "٦", "7": "٧", "8": "٨", "9": "٩" };
  return s.replace(/[0-9]/g, (d) => map[d]);
}
