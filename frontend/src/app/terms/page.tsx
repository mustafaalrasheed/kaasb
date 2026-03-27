import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Terms of Service",
  description:
    "Read the Terms of Service for the Kaasb freelancing platform. " +
    "These terms govern your use of Kaasb as a client or freelancer.",
  robots: { index: true, follow: true },
};

const LAST_UPDATED = "27 March 2026";
const CONTACT_EMAIL = "legal@kaasb.com";
const COMPANY_NAME = "Kaasb Technology LLC";

export default function TermsOfServicePage() {
  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <div className="bg-brand-50 border-b border-brand-100 py-12">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-gray-900">Terms of Service</h1>
          <p className="mt-2 text-gray-500">Last updated: {LAST_UPDATED}</p>
          <h2 className="mt-6 text-2xl font-bold text-gray-900 text-right" dir="rtl">
            شروط الخدمة
          </h2>
          <p className="mt-1 text-gray-500 text-right" dir="rtl">
            آخر تحديث: ٢٧ مارس ٢٠٢٦
          </p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-12">

        {/* ── Acceptance ── */}
        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">1. Acceptance of Terms</h2>
          <p className="text-gray-700 leading-relaxed">
            By creating an account or using the Kaasb Platform operated by {COMPANY_NAME},
            you agree to be bound by these Terms of Service (&quot;Terms&quot;). If you do not agree,
            you must not use the Platform.
          </p>
          <p className="mt-3 text-gray-700 leading-relaxed">
            We may update these Terms at any time. Continued use of the Platform after
            changes are published constitutes acceptance of the revised Terms. Significant
            changes will be communicated by email or in-platform notification.
          </p>
          <div className="mt-6 p-4 bg-gray-50 rounded-lg" dir="rtl">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">١. قبول الشروط</h3>
            <p className="text-gray-700 leading-relaxed">
              بإنشاء حساب أو استخدام منصة كاسب، فإنك توافق على الالتزام بهذه الشروط.
              إن لم توافق، يجب ألا تستخدم المنصة. قد نحدّث هذه الشروط في أي وقت؛
              واستمرار استخدامك للمنصة يُعدّ موافقةً على الشروط المُحدَّثة.
            </p>
          </div>
        </section>

        {/* ── Eligibility ── */}
        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">2. Eligibility</h2>
          <ul className="list-disc list-inside space-y-2 text-gray-700">
            <li>You must be at least 18 years old to use the Platform.</li>
            <li>You must have the legal capacity to enter into a binding contract.</li>
            <li>You must not have been previously banned from the Platform.</li>
            <li>
              Use of the Platform is subject to applicable laws in your jurisdiction,
              including Iraqi telecommunications and financial regulations.
            </li>
          </ul>
          <div className="mt-6 p-4 bg-gray-50 rounded-lg" dir="rtl">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">٢. الأهلية</h3>
            <p className="text-gray-700 leading-relaxed">
              يجب أن يكون عمرك ١٨ عامًا على الأقل، وأن تتمتع بالأهلية القانونية لإبرام
              عقود ملزمة، وألا تكون محظورًا مسبقًا من المنصة. يخضع استخدام المنصة
              للقوانين المعمول بها في دولتك، بما فيها اللوائح العراقية المعنية.
            </p>
          </div>
        </section>

        {/* ── User Accounts ── */}
        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">3. User Accounts</h2>
          <p className="text-gray-700 leading-relaxed">
            You are responsible for maintaining the confidentiality of your account
            credentials and for all activity under your account. You must:
          </p>
          <ul className="list-disc list-inside space-y-2 mt-3 text-gray-700">
            <li>Provide accurate and complete registration information.</li>
            <li>Keep your password secure and not share it with others.</li>
            <li>Notify us immediately of any unauthorised access at{" "}
              <a href={`mailto:${CONTACT_EMAIL}`} className="text-brand-500 hover:underline">
                {CONTACT_EMAIL}
              </a>.
            </li>
            <li>Not create multiple accounts to circumvent suspensions or restrictions.</li>
          </ul>
        </section>

        {/* ── Platform Services ── */}
        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">4. Platform Services</h2>
          <p className="text-gray-700 leading-relaxed">
            Kaasb provides a marketplace connecting clients who post jobs with freelancers
            who submit proposals. Kaasb is not a party to any contract formed between
            clients and freelancers — we facilitate the connection and payment escrow.
          </p>
          <div className="mt-4 space-y-3">
            <div>
              <h3 className="font-medium text-gray-900">For Clients</h3>
              <p className="text-gray-700 mt-1 leading-relaxed">
                Clients may post job listings, review proposals, accept freelancers, fund
                milestone escrow, approve work, and leave reviews. Clients are responsible
                for clearly defining project requirements and funding escrow before work begins.
              </p>
            </div>
            <div>
              <h3 className="font-medium text-gray-900">For Freelancers</h3>
              <p className="text-gray-700 mt-1 leading-relaxed">
                Freelancers may submit proposals on open jobs, deliver work according to
                agreed milestones, and request payouts upon client approval. Freelancers
                are responsible for the quality and timely delivery of their work.
              </p>
            </div>
          </div>
          <div className="mt-6 p-4 bg-gray-50 rounded-lg" dir="rtl">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">٤. خدمات المنصة</h3>
            <p className="text-gray-700 leading-relaxed">
              تُوفّر كاسب منصةً تربط أصحاب العمل بالمستقلين. لا تُعدّ كاسب طرفًا في
              أي عقد بين أصحاب العمل والمستقلين، بل تُيسّر التواصل وضمان الدفع.
              يتحمل أصحاب العمل مسؤولية تحديد المتطلبات وتمويل الضمان، فيما يتحمل
              المستقلون مسؤولية جودة العمل والتسليم في الوقت المحدد.
            </p>
          </div>
        </section>

        {/* ── Payments & Fees ── */}
        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">5. Payments &amp; Fees</h2>
          <ul className="list-disc list-inside space-y-2 text-gray-700">
            <li>
              Payment processing is provided through Stripe (USD), Qi Card (IQD), and
              Wise (international payouts).
            </li>
            <li>
              Platform fees are displayed at the time of transaction and may be updated
              with 30 days&apos; notice.
            </li>
            <li>
              Escrow funds are held by Kaasb and released to the freelancer only upon
              client approval of a milestone.
            </li>
            <li>
              Disputes regarding payment must be raised within 14 days of the relevant
              milestone completion.
            </li>
            <li>
              Kaasb does not guarantee payment from clients. Clients must fund escrow
              before freelancers begin milestone work.
            </li>
          </ul>
        </section>

        {/* ── Prohibited Conduct ── */}
        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">6. Prohibited Conduct</h2>
          <p className="text-gray-700 leading-relaxed mb-3">You must not:</p>
          <ul className="list-disc list-inside space-y-2 text-gray-700">
            <li>Post false, misleading, or fraudulent job listings or proposals.</li>
            <li>Harass, threaten, or abuse other users.</li>
            <li>Circumvent the Platform&apos;s payment system by transacting outside Kaasb.</li>
            <li>Upload malicious code, viruses, or interfere with Platform infrastructure.</li>
            <li>Impersonate another person or entity.</li>
            <li>Violate any applicable law, including Iraqi law and international sanctions.</li>
            <li>Use automated bots or scrapers to extract Platform data.</li>
            <li>Post content that infringes intellectual property rights.</li>
          </ul>
          <p className="mt-4 text-gray-700">
            Violation of these rules may result in immediate account suspension or
            permanent ban without refund.
          </p>
          <div className="mt-6 p-4 bg-gray-50 rounded-lg" dir="rtl">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">٦. السلوك المحظور</h3>
            <p className="text-gray-700 leading-relaxed">
              يُحظر عليك نشر قوائم وهمية أو مضللة، ومضايقة المستخدمين أو تهديدهم،
              والتحايل على نظام الدفع، ورفع رموز ضارة، وانتحال شخصية الآخرين،
              وانتهاك القوانين المعمول بها. قد تؤدي المخالفات إلى تعليق الحساب فورًا.
            </p>
          </div>
        </section>

        {/* ── Content Moderation ── */}
        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">7. Content Moderation</h2>
          <p className="text-gray-700 leading-relaxed">
            Kaasb reserves the right to review, remove, or restrict any content that
            violates these Terms. Users may report content they believe violates our
            policies using the &quot;Report&quot; feature available on jobs, profiles, and messages.
          </p>
          <p className="mt-3 text-gray-700 leading-relaxed">
            We aim to review content reports within 5 business days. Decisions may be
            appealed by contacting{" "}
            <a href={`mailto:${CONTACT_EMAIL}`} className="text-brand-500 hover:underline">
              {CONTACT_EMAIL}
            </a>
            .
          </p>
        </section>

        {/* ── Intellectual Property ── */}
        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">8. Intellectual Property</h2>
          <p className="text-gray-700 leading-relaxed">
            All content on the Kaasb Platform (software, design, trademarks) is the property
            of {COMPANY_NAME} or its licensors. You may not reproduce, distribute, or create
            derivative works without written permission.
          </p>
          <p className="mt-3 text-gray-700 leading-relaxed">
            Work product delivered by a freelancer to a client becomes the client&apos;s intellectual
            property upon full payment, unless otherwise agreed in the project contract.
          </p>
        </section>

        {/* ── Limitation of Liability ── */}
        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">9. Limitation of Liability</h2>
          <p className="text-gray-700 leading-relaxed">
            To the maximum extent permitted by law, Kaasb shall not be liable for:
          </p>
          <ul className="list-disc list-inside space-y-2 mt-3 text-gray-700">
            <li>Indirect, incidental, or consequential damages arising from use of the Platform.</li>
            <li>Disputes between clients and freelancers.</li>
            <li>Losses resulting from third-party payment processor failures.</li>
            <li>Temporary Platform unavailability due to maintenance or technical issues.</li>
          </ul>
          <p className="mt-4 text-gray-700">
            Our total liability to you shall not exceed the fees paid by you to Kaasb in
            the 12 months preceding the claim.
          </p>
        </section>

        {/* ── Governing Law ── */}
        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">10. Governing Law</h2>
          <p className="text-gray-700 leading-relaxed">
            These Terms are governed by the laws of the Republic of Iraq. Disputes that
            cannot be resolved amicably shall be submitted to the competent courts in Baghdad,
            Iraq.
          </p>
          <div className="mt-6 p-4 bg-gray-50 rounded-lg" dir="rtl">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">١٠. القانون الحاكم</h3>
            <p className="text-gray-700 leading-relaxed">
              تخضع هذه الشروط لقوانين جمهورية العراق. تُحسم النزاعات التي لا يمكن
              تسويتها وديًا أمام المحاكم المختصة في بغداد، العراق.
            </p>
          </div>
        </section>

        {/* ── Account Termination ── */}
        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">11. Account Termination</h2>
          <p className="text-gray-700 leading-relaxed">
            You may deactivate your account at any time from{" "}
            <Link href="/dashboard/settings" className="text-brand-500 hover:underline">
              Account Settings
            </Link>
            . For a permanent hard deletion of your data, use the
            &quot;Delete My Account&quot; option in settings.
          </p>
          <p className="mt-3 text-gray-700 leading-relaxed">
            Kaasb may suspend or terminate your account if you violate these Terms,
            engage in fraudulent activity, or pose a risk to the Platform or other users.
          </p>
        </section>

        {/* ── Contact ── */}
        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">12. Contact</h2>
          <address className="not-italic text-gray-700 space-y-1">
            <div><strong>{COMPANY_NAME}</strong></div>
            <div>Baghdad, Iraq</div>
            <div>
              Legal enquiries:{" "}
              <a href={`mailto:${CONTACT_EMAIL}`} className="text-brand-500 hover:underline">
                {CONTACT_EMAIL}
              </a>
            </div>
          </address>
          <div className="mt-6 p-4 bg-gray-50 rounded-lg" dir="rtl">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">١٢. التواصل</h3>
            <address className="not-italic text-gray-700 space-y-1">
              <div><strong>شركة كاسب تكنولوجي</strong></div>
              <div>بغداد، العراق</div>
              <div>
                الاستفسارات القانونية:{" "}
                <a href={`mailto:${CONTACT_EMAIL}`} className="text-brand-500 hover:underline">
                  {CONTACT_EMAIL}
                </a>
              </div>
            </address>
          </div>
        </section>

        {/* Footer nav */}
        <div className="border-t border-gray-200 pt-6 flex flex-wrap gap-4 text-sm text-gray-500">
          <Link href="/terms" className="hover:text-gray-700 hover:underline font-medium text-gray-700">
            Terms of Service
          </Link>
          <Link href="/privacy" className="hover:text-gray-700 hover:underline">
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
