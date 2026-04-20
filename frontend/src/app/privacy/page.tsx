import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description:
    "Learn how Kaasb collects, uses, and protects your personal information. " +
    "We are committed to protecting the privacy of our users across Iraq and the MENA region.",
  robots: { index: true, follow: true },
};

const LAST_UPDATED = "27 March 2026";
const CONTACT_EMAIL = "privacy@kaasb.com";
const COMPANY_NAME = "Kaasb Technology LLC";

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <div className="bg-brand-50 border-b border-brand-100 py-12">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-gray-900">Privacy Policy</h1>
          <p className="mt-2 text-gray-500">Last updated: {LAST_UPDATED}</p>
          {/* Arabic header */}
          <h2 className="mt-6 text-2xl font-bold text-gray-900 text-right" dir="rtl">
            سياسة الخصوصية
          </h2>
          <p className="mt-1 text-gray-500 text-right" dir="rtl">
            آخر تحديث: ٢٧ مارس ٢٠٢٦
          </p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-12">

        {/* ── Introduction ── */}
        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">1. Introduction</h2>
          <p className="text-gray-700 leading-relaxed">
            {COMPANY_NAME} (&quot;Kaasb&quot;, &quot;we&quot;, &quot;our&quot;, or &quot;us&quot;) operates the online freelancing
            marketplace available at{" "}
            <Link href="https://kaasb.com" className="text-brand-500 hover:underline">
              kaasb.com
            </Link>{" "}
            (the &quot;Platform&quot;). This Privacy Policy explains how we collect, use,
            disclose, and protect information about you when you use our Platform.
          </p>
          <p className="mt-3 text-gray-700 leading-relaxed">
            By registering or using the Platform, you agree to the collection and use of
            information as described in this policy. If you do not agree, please do not
            use the Platform.
          </p>
          {/* Arabic */}
          <div className="mt-6 p-4 bg-gray-50 rounded-lg" dir="rtl">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">١. المقدمة</h3>
            <p className="text-gray-700 leading-relaxed">
              تشغّل شركة كاسب تكنولوجي المنصة الإلكترونية للعمل الحر على kaasb.com. توضّح هذه
              السياسة كيفية جمع معلوماتك واستخدامها والإفصاح عنها وحمايتها. باستخدامك
              للمنصة، فإنك توافق على ما ورد في هذه السياسة.
            </p>
          </div>
        </section>

        {/* ── Information We Collect ── */}
        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">2. Information We Collect</h2>
          <div className="space-y-4">
            <div>
              <h3 className="font-medium text-gray-900">Account Information</h3>
              <p className="text-gray-700 mt-1 leading-relaxed">
                When you register, we collect your name, email address, username, password
                (hashed), primary role (client or freelancer), and optionally your phone number,
                city, country, and profile bio.
              </p>
            </div>
            <div>
              <h3 className="font-medium text-gray-900">Professional Information</h3>
              <p className="text-gray-700 mt-1 leading-relaxed">
                Freelancers may provide a professional title, skills, experience level, and
                portfolio URL. This information is displayed publicly on your profile.
              </p>
            </div>
            <div>
              <h3 className="font-medium text-gray-900">Transaction Data</h3>
              <p className="text-gray-700 mt-1 leading-relaxed">
                We record payment account identifiers (Qi Card token), transaction amounts,
                currencies, and timestamps. We do not store raw card numbers or CVV codes —
                these are handled directly by Qi Card.
              </p>
            </div>
            <div>
              <h3 className="font-medium text-gray-900">Usage Data</h3>
              <p className="text-gray-700 mt-1 leading-relaxed">
                We collect IP addresses, browser type, operating system, pages visited, and
                request timestamps through server logs and Prometheus metrics for
                security and performance monitoring.
              </p>
            </div>
            <div>
              <h3 className="font-medium text-gray-900">Communications</h3>
              <p className="text-gray-700 mt-1 leading-relaxed">
                Messages sent between users through the Platform are stored to enable the
                messaging feature and for content moderation purposes.
              </p>
            </div>
          </div>
          {/* Arabic */}
          <div className="mt-6 p-4 bg-gray-50 rounded-lg" dir="rtl">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">٢. المعلومات التي نجمعها</h3>
            <p className="text-gray-700 leading-relaxed">
              نجمع معلومات الحساب (الاسم، البريد الإلكتروني، كلمة المرور المشفّرة)،
              والمعلومات المهنية (المهارات، السعر بالساعة)، وبيانات المعاملات المالية،
              وبيانات الاستخدام (عناوين IP وسجلات الخادم)، والرسائل المرسلة بين
              المستخدمين على المنصة.
            </p>
          </div>
        </section>

        {/* ── How We Use Your Information ── */}
        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">3. How We Use Your Information</h2>
          <ul className="list-disc list-inside space-y-2 text-gray-700">
            <li>To operate the Platform and provide our services</li>
            <li>To process payments and payouts through Qi Card</li>
            <li>To verify your identity and prevent fraud</li>
            <li>To communicate service notifications (contract updates, payment receipts)</li>
            <li>To enforce our Terms of Service and content moderation policies</li>
            <li>To improve the Platform through aggregate usage analytics</li>
            <li>To comply with legal obligations and respond to lawful requests</li>
          </ul>
          {/* Arabic */}
          <div className="mt-6 p-4 bg-gray-50 rounded-lg" dir="rtl">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">٣. كيف نستخدم معلوماتك</h3>
            <ul className="list-disc list-inside space-y-2 text-gray-700">
              <li>لتشغيل المنصة وتقديم خدماتنا</li>
              <li>لمعالجة المدفوعات والمدفوعات عبر كي كارد</li>
              <li>للتحقق من هويتك ومنع الاحتيال</li>
              <li>لإرسال إشعارات الخدمة</li>
              <li>لإنفاذ شروط الخدمة وسياسات الاعتدال</li>
              <li>لتحسين المنصة من خلال تحليلات الاستخدام المجمّعة</li>
              <li>للامتثال للالتزامات القانونية</li>
            </ul>
          </div>
        </section>

        {/* ── Data Sharing ── */}
        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">4. Data Sharing</h2>
          <p className="text-gray-700 leading-relaxed mb-3">
            We do not sell your personal data. We share data only with:
          </p>
          <ul className="list-disc list-inside space-y-2 text-gray-700">
            <li>
              <strong>Payment processor</strong> (Qi Card) — to process transactions. Qi Card
              has its own privacy policy.
            </li>
            <li>
              <strong>Infrastructure providers</strong> (Hetzner for hosting, Sentry for error
              tracking) — for operating the Platform.
            </li>
            <li>
              <strong>Other users</strong> — your public profile, proposals, and reviews are
              visible to other platform users as required by the service.
            </li>
            <li>
              <strong>Law enforcement</strong> — when required by applicable Iraqi or international
              law, court order, or to protect the rights and safety of users.
            </li>
          </ul>
          {/* Arabic */}
          <div className="mt-6 p-4 bg-gray-50 rounded-lg" dir="rtl">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">٤. مشاركة البيانات</h3>
            <p className="text-gray-700 leading-relaxed">
              لا نبيع بياناتك الشخصية. نشارك البيانات فقط مع معالج الدفع (كي كارد)،
              ومزودي البنية التحتية (هيتزنر وسنتري)، والمستخدمين الآخرين (ملفك العام المرئي)،
              والجهات التنفيذية القانونية عند الحاجة القانونية.
            </p>
          </div>
        </section>

        {/* ── Data Retention ── */}
        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">5. Data Retention</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left border-collapse">
              <thead>
                <tr className="bg-gray-100">
                  <th className="p-3 font-semibold text-gray-700 border">Data Type</th>
                  <th className="p-3 font-semibold text-gray-700 border">Retention Period</th>
                  <th className="p-3 font-semibold text-gray-700 border">Action After TTL</th>
                </tr>
              </thead>
              <tbody className="text-gray-700">
                {[
                  ["Notifications", "90 days", "Permanently deleted"],
                  ["Revoked session tokens", "30 days", "Permanently deleted"],
                  ["Deactivated accounts (PII)", "2 years", "Personal data anonymised"],
                  ["Financial records", "7 years", "Retained (legal/tax obligation)"],
                  ["Audit log", "7 years", "Never deleted"],
                  ["Pending moderation reports", "6 months", "Auto-dismissed"],
                ].map(([type, period, action]) => (
                  <tr key={type} className="border-b">
                    <td className="p-3 border">{type}</td>
                    <td className="p-3 border">{period}</td>
                    <td className="p-3 border">{action}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* ── Your Rights ── */}
        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">6. Your Rights</h2>
          <p className="text-gray-700 leading-relaxed mb-3">
            Depending on your location, you may have the following rights regarding your
            personal data:
          </p>
          <ul className="list-disc list-inside space-y-2 text-gray-700">
            <li>
              <strong>Access (Art. 15 GDPR)</strong> — Request a copy of all personal data we
              hold about you via{" "}
              <Link href="/dashboard/settings" className="text-brand-500 hover:underline">
                Account Settings
              </Link>{" "}
              → Download My Data.
            </li>
            <li>
              <strong>Erasure (Art. 17 GDPR)</strong> — Request permanent deletion of your
              account and personal data (subject to legal retention obligations).
            </li>
            <li>
              <strong>Rectification (Art. 16 GDPR)</strong> — Update incorrect personal data
              through your profile settings.
            </li>
            <li>
              <strong>Objection</strong> — Object to processing for direct marketing at any time.
            </li>
            <li>
              <strong>Portability</strong> — Receive your data in a structured, machine-readable
              JSON format.
            </li>
          </ul>
          <p className="mt-4 text-gray-700">
            To exercise your rights, use the self-service tools in your dashboard or contact us
            at{" "}
            <a href={`mailto:${CONTACT_EMAIL}`} className="text-brand-500 hover:underline">
              {CONTACT_EMAIL}
            </a>
            . We respond within 30 days.
          </p>
          {/* Arabic */}
          <div className="mt-6 p-4 bg-gray-50 rounded-lg" dir="rtl">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">٦. حقوقك</h3>
            <p className="text-gray-700 leading-relaxed">
              لديك الحق في الوصول إلى بياناتك الشخصية وتصحيحها ومحوها ونقلها. يمكنك تنزيل
              بياناتك أو طلب حذف حسابك من خلال إعدادات الحساب، أو عبر مراسلتنا على{" "}
              <a href={`mailto:${CONTACT_EMAIL}`} className="text-brand-500 hover:underline">
                {CONTACT_EMAIL}
              </a>
              . نرد خلال ٣٠ يومًا.
            </p>
          </div>
        </section>

        {/* ── Cookies ── */}
        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">7. Cookies</h2>
          <p className="text-gray-700 leading-relaxed">
            We use essential cookies to maintain your session and security preferences.
            We do not use third-party advertising or analytics cookies. You can manage
            cookie preferences at any time through the cookie consent banner or your
            browser settings.
          </p>
          {/* Arabic */}
          <div className="mt-4 p-4 bg-gray-50 rounded-lg" dir="rtl">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">٧. ملفات تعريف الارتباط</h3>
            <p className="text-gray-700 leading-relaxed">
              نستخدم ملفات تعريف الارتباط الأساسية للحفاظ على جلستك وتفضيلاتك الأمنية فقط.
              لا نستخدم ملفات تعريف ارتباط إعلانية أو تحليلية تابعة لجهات خارجية.
            </p>
          </div>
        </section>

        {/* ── Security ── */}
        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">8. Security</h2>
          <p className="text-gray-700 leading-relaxed">
            We implement industry-standard security measures including bcrypt password hashing,
            JWT authentication with short-lived access tokens (30 minutes), TLS/HTTPS
            encryption in transit, rate limiting to prevent brute-force attacks, and regular
            security monitoring through Sentry and Prometheus.
          </p>
          <p className="mt-3 text-gray-700 leading-relaxed">
            No system is 100% secure. If you discover a security vulnerability, please report
            it responsibly to{" "}
            <a href="mailto:security@kaasb.com" className="text-brand-500 hover:underline">
              security@kaasb.com
            </a>
            .
          </p>
        </section>

        {/* ── Contact ── */}
        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">9. Contact Us</h2>
          <p className="text-gray-700 leading-relaxed">
            For privacy-related questions or to exercise your data rights:
          </p>
          <address className="mt-3 not-italic text-gray-700 space-y-1">
            <div><strong>{COMPANY_NAME}</strong></div>
            <div>Baghdad, Iraq</div>
            <div>
              Email:{" "}
              <a href={`mailto:${CONTACT_EMAIL}`} className="text-brand-500 hover:underline">
                {CONTACT_EMAIL}
              </a>
            </div>
          </address>
          {/* Arabic */}
          <div className="mt-6 p-4 bg-gray-50 rounded-lg" dir="rtl">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">٩. اتصل بنا</h3>
            <p className="text-gray-700 leading-relaxed">
              لأسئلة الخصوصية أو لممارسة حقوقك في البيانات، تواصل معنا:
            </p>
            <address className="mt-2 not-italic text-gray-700 space-y-1">
              <div><strong>شركة كاسب تكنولوجي</strong></div>
              <div>بغداد، العراق</div>
              <div>
                البريد الإلكتروني:{" "}
                <a href={`mailto:${CONTACT_EMAIL}`} className="text-brand-500 hover:underline">
                  {CONTACT_EMAIL}
                </a>
              </div>
            </address>
          </div>
        </section>

        {/* Footer nav */}
        <div className="border-t border-gray-200 pt-6 flex flex-wrap gap-4 text-sm text-gray-500">
          <Link href="/terms" className="hover:text-gray-700 hover:underline">
            Terms of Service
          </Link>
          <Link href="/privacy" className="hover:text-gray-700 hover:underline font-medium text-gray-700">
            Privacy Policy
          </Link>
          <Link href="/dashboard/settings" className="hover:text-gray-700 hover:underline">
            Account Settings
          </Link>
        </div>
      </div>
    </div>
  );
}
