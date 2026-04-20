import type { Metadata } from "next";
import Link from "next/link";
import { LegalViewToggle } from "@/components/legal/legal-view-toggle";

export const metadata: Metadata = {
  title: "Refund Policy | سياسة الاسترداد",
  description:
    "When refunds are available on Kaasb, how to request one, processing timelines, and allocation of Qi Card transaction fees.",
  robots: { index: true, follow: true },
};

const VERSION = "1.0";
const EFFECTIVE_DATE_EN = "20 April 2026";
const EFFECTIVE_DATE_AR = "٢٠ نيسان ٢٠٢٦";
const EMAIL_SUPPORT = "support@kaasb.com";
const PROCESSING_DAYS = 14;
const AUTO_COMPLETE_DAYS = 3;

export default function RefundPolicyPage() {
  return (
    <div className="min-h-screen bg-white">
      <div className="bg-brand-50 border-b border-brand-100 py-12">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-gray-900">Refund Policy</h1>
          <p className="mt-1 text-sm text-gray-500">Version {VERSION} · Effective {EFFECTIVE_DATE_EN}</p>
          <h2 className="mt-6 text-2xl font-bold text-gray-900 text-right" dir="rtl">سياسة الاسترداد</h2>
          <p className="mt-1 text-sm text-gray-500 text-right" dir="rtl">
            الإصدار {VERSION} · نافذ اعتباراً من {EFFECTIVE_DATE_AR}
          </p>
          <p className="mt-4 text-xs text-gray-500 italic max-w-2xl">
            This Refund Policy forms an integral part of the{" "}
            <Link href="/terms" className="underline">Terms of Service</Link>.
            — تُشكِّل هذه السياسة جزءاً لا يتجزأ من{" "}
            <Link href="/terms" className="underline">شروط الخدمة</Link>.
          </p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-10">

        <div className="flex justify-center sm:justify-end">
          <LegalViewToggle />
        </div>

        <section>
          <Header num="1" en="Scope" ar="النطاق" />
          <Bilingual
            en={
              <p>
                This Policy applies to payments made by Buyers on the Kaasb Platform for Gigs, Orders,
                Milestones, or Job Contracts, all of which pass through Escrow before release to the Seller.
                Refunds are processed exclusively through Qi Card, in Iraqi Dinars (IQD).
              </p>
            }
            ar={
              <p>
                تسري هذه السياسة على مدفوعات المشترين عبر منصة كاسب للخدمات والطلبات والمعالم وعقود
                الوظائف، وكلّها تمرّ بالضمان (الإسكرو) قبل الإفراج للبائع. وتُنفَّذ المبالغ المستردة حصراً
                عبر كي كارد وبالدينار العراقي.
              </p>
            }
          />
        </section>

        <section>
          <Header num="2" en="When a refund is available" ar="متى يُستَحَق الاسترداد" />
          <Bilingual
            en={
              <>
                <p>A refund of the funded Escrow amount is available in the following situations:</p>
                <ul className="list-disc ms-6 mt-3 space-y-1.5">
                  <li><strong>Pre-delivery cancellation.</strong> The Order is cancelled by mutual consent, or by the Buyer alone before the Seller has begun work and before requirements are accepted.</li>
                  <li><strong>Seller non-delivery.</strong> The Seller fails to deliver by the agreed deadline and no extension has been granted.</li>
                  <li><strong>Dispute decided for the Buyer.</strong> A Kaasb administrator resolves a dispute under Section 11 of the Terms in the Buyer&apos;s favour, in whole or in part.</li>
                  <li><strong>Confirmed fraud or policy breach by the Seller.</strong> Including plagiarism, material misrepresentation, or service not rendered.</li>
                  <li><strong>Payment error.</strong> A double-charge or a verified incorrect charge caused by the Platform.</li>
                </ul>
                <p className="mt-3">A refund is <strong>not</strong> available when:</p>
                <ul className="list-disc ms-6 mt-2 space-y-1.5">
                  <li>The delivery has been accepted by the Buyer.</li>
                  <li>The Order has been auto-completed after the {AUTO_COMPLETE_DAYS}-day window without a revision request or dispute.</li>
                  <li>The Buyer is dissatisfied with the result of work that conforms to the agreed scope and requirements (subjective taste).</li>
                  <li>The request is made after final acceptance of all milestones.</li>
                </ul>
              </>
            }
            ar={
              <>
                <p>يُستَحَق ردّ مبلغ الضمان المُموَّل في الحالات الآتية:</p>
                <ul className="list-disc me-6 mt-3 space-y-1.5">
                  <li><strong>الإلغاء قبل التسليم.</strong> إلغاء الطلب باتفاق الطرفين، أو من المشتري وحده قبل بدء البائع العمل وقبل قبول المتطلبات.</li>
                  <li><strong>عدم تسليم البائع.</strong> إخفاق البائع في التسليم بحلول الموعد المتفق عليه دون منح تمديد.</li>
                  <li><strong>حسم النزاع لصالح المشتري.</strong> قرار إداري من كاسب وفق البند ١١ من الشروط لصالح المشتري، كلّياً أو جزئياً.</li>
                  <li><strong>احتيال أو مخالفة سياسة من البائع.</strong> كالانتحال، أو التضليل الجوهري، أو عدم تأدية الخدمة.</li>
                  <li><strong>خطأ في الدفع.</strong> خصم مزدوج أو خصم خاطئ مُتحقَّق منه ناتج عن المنصة.</li>
                </ul>
                <p className="mt-3">ولا يُستَحَق الاسترداد في الحالات الآتية:</p>
                <ul className="list-disc me-6 mt-2 space-y-1.5">
                  <li>قبول المشتري للتسليم.</li>
                  <li>اكتمال الطلب تلقائياً بعد مرور مدة الـ{AUTO_COMPLETE_DAYS} أيام دون طلب تعديل أو نزاع.</li>
                  <li>عدم رضا المشتري عن عملٍ مطابق للنطاق والمتطلبات المتفق عليها (ذوق شخصي).</li>
                  <li>تقديم الطلب بعد القبول النهائي لجميع المعالم.</li>
                </ul>
              </>
            }
          />
        </section>

        <section>
          <Header num="3" en="Time window for a request" ar="مدة تقديم الطلب" />
          <Bilingual
            en={
              <ul className="list-disc ms-6 space-y-1.5">
                <li><strong>If the Seller has not yet delivered</strong> — at any time until delivery or until the Order is cancelled.</li>
                <li><strong>After delivery</strong> — within the {AUTO_COMPLETE_DAYS}-day review window, either by requesting a revision or by raising a dispute. After the window expires without action, the Order auto-completes and becomes ineligible for refund.</li>
                <li><strong>For a payment error</strong> — within thirty (30) days of the charge.</li>
              </ul>
            }
            ar={
              <ul className="list-disc me-6 space-y-1.5">
                <li><strong>قبل التسليم</strong> — في أي وقت حتى التسليم أو إلغاء الطلب.</li>
                <li><strong>بعد التسليم</strong> — خلال مدة المراجعة البالغة {AUTO_COMPLETE_DAYS} أيام، إما بطلب تعديل أو بإثارة نزاع. وبانقضاء المدة دون إجراء، يُكتمل الطلب تلقائياً ويخرج من نطاق الاسترداد.</li>
                <li><strong>عند خطأ الدفع</strong> — خلال ثلاثين (٣٠) يوماً من الخصم.</li>
              </ul>
            }
          />
        </section>

        <section>
          <Header num="4" en="How to request a refund" ar="كيفية تقديم طلب الاسترداد" />
          <Bilingual
            en={
              <ol className="list-decimal ms-6 space-y-1.5">
                <li>Open the relevant Order page in your dashboard.</li>
                <li>Select &quot;Request cancellation&quot; (before delivery) or &quot;Raise a dispute&quot; (after delivery).</li>
                <li>Provide a clear description of the reason and attach supporting evidence (messages, files, screenshots).</li>
                <li>For payment-error cases, write to{" "}
                  <a href={`mailto:${EMAIL_SUPPORT}`} className="text-brand-500 hover:underline">{EMAIL_SUPPORT}</a>{" "}
                  with the transaction reference.
                </li>
              </ol>
            }
            ar={
              <ol className="list-decimal me-6 space-y-1.5">
                <li>افتح صفحة الطلب في لوحة حسابك.</li>
                <li>اختر «طلب إلغاء» (قبل التسليم) أو «إثارة نزاع» (بعد التسليم).</li>
                <li>قدّم وصفاً واضحاً للسبب وأرفق الأدلة (رسائل، ملفات، لقطات شاشة).</li>
                <li>في حالات خطأ الدفع، راسل{" "}
                  <a href={`mailto:${EMAIL_SUPPORT}`} className="text-brand-500 hover:underline">{EMAIL_SUPPORT}</a>{" "}
                  مع رقم المعاملة المرجعي.
                </li>
              </ol>
            }
          />
        </section>

        <section>
          <Header num="5" en="Processing time" ar="مدة المعالجة" />
          <Bilingual
            en={
              <p>
                Approved refunds are processed within <strong>{PROCESSING_DAYS} business days</strong> of the
                approval decision and returned to the original Qi Card that was charged. The time for funds
                to appear in your Qi Card account depends on Qi Card&apos;s own settlement cycle and on your
                issuing bank, and is outside Kaasb&apos;s control. Partial refunds are supported where an Order
                is partially fulfilled or a dispute is split.
              </p>
            }
            ar={
              <p>
                تُعالَج المبالغ المعتمَدة خلال <strong>{PROCESSING_DAYS} يوم عمل</strong> من قرار
                الموافقة، وتُعاد إلى بطاقة كي كارد التي جرى الخصم منها أصلاً. وتعتمد مدة ظهور المبلغ
                في حسابك لدى كي كارد على دورة التسوية الخاصة بها وبالبنك المُصدِر، وهي خارج سيطرة
                كاسب. ويُدعَم الاسترداد الجزئي عند التنفيذ الجزئي للطلب أو التقسيم الإداري للنزاع.
              </p>
            }
          />
        </section>

        <section>
          <Header num="6" en="Allocation of transaction fees" ar="توزيع رسوم المعاملة" />
          <Bilingual
            en={
              <ul className="list-disc ms-6 space-y-1.5">
                <li><strong>When fault is the Seller&apos;s or the Platform&apos;s</strong> (non-delivery, fraud, payment error), Kaasb absorbs any Qi Card transaction fee; the Buyer receives a full refund.</li>
                <li><strong>When cancellation is initiated by the Buyer after the Seller has started work</strong>, and the Seller has partially performed in good faith, the Qi Card transaction fee may be deducted from the refunded amount. Any such deduction will be displayed before the Buyer confirms the cancellation.</li>
                <li><strong>Dispute-split outcomes</strong> — fees are allocated in proportion to the split, unless the administrator&apos;s decision states otherwise.</li>
              </ul>
            }
            ar={
              <ul className="list-disc me-6 space-y-1.5">
                <li><strong>عند نشوء الخطأ من البائع أو من المنصة</strong> (عدم تسليم، احتيال، خطأ دفع)، تتحمل كاسب أي رسوم للمعاملة لدى كي كارد، ويُعاد للمشتري المبلغ كاملاً.</li>
                <li><strong>عند إلغاء المشتري بعد بدء البائع العمل</strong> وأداءٍ جزئي بحسن نيّة من البائع، يجوز خصم رسوم معاملة كي كارد من المبلغ المُعاد. وتُعرض قيمة الخصم قبل تأكيد الإلغاء.</li>
                <li><strong>الحسم الجزئي في النزاع</strong> — توزع الرسوم بحسب نسبة التقسيم، ما لم يذكر القرار الإداري خلاف ذلك.</li>
              </ul>
            }
          />
        </section>

        <section>
          <Header num="7" en="Chargebacks" ar="الاعتراضات المصرفية" />
          <Bilingual
            en={
              <p>
                Initiating a chargeback with Qi Card or an issuing bank instead of following this Policy may
                result in immediate suspension of your account and forfeiture of pending balances. Please
                attempt resolution through the Platform first.
              </p>
            }
            ar={
              <p>
                اللجوء إلى اعتراضٍ مصرفي لدى كي كارد أو البنك المُصدِر بدلاً من اتباع هذه السياسة قد
                يؤدي إلى تعليق حسابك فوراً ومصادرة الأرصدة المُعلَّقة. يرجى السعي أولاً إلى الحل عبر
                المنصة.
              </p>
            }
          />
        </section>

        <section>
          <Header num="8" en="Contact" ar="التواصل" />
          <Bilingual
            en={
              <p>
                For refund enquiries or escalations:{" "}
                <a href={`mailto:${EMAIL_SUPPORT}`} className="text-brand-500 hover:underline">{EMAIL_SUPPORT}</a>.
              </p>
            }
            ar={
              <p>
                للاستفسارات أو التصعيد:{" "}
                <a href={`mailto:${EMAIL_SUPPORT}`} className="text-brand-500 hover:underline">{EMAIL_SUPPORT}</a>.
              </p>
            }
          />
        </section>

        <section>
          <Header num="9" en="Language precedence" ar="الأسبقية اللغوية" />
          <Bilingual
            en={<p>In the event of conflict, the <strong>Arabic version</strong> of this Policy prevails.</p>}
            ar={<p>عند التعارض، تُعتمد <strong>النسخة العربية</strong> من هذه السياسة.</p>}
          />
        </section>

        <div className="border-t border-gray-200 pt-6 flex flex-wrap gap-4 text-sm text-gray-500">
          <Link href="/privacy" className="hover:text-gray-700 hover:underline">Privacy Policy</Link>
          <Link href="/terms" className="hover:text-gray-700 hover:underline">Terms of Service</Link>
          <Link href="/cookies" className="hover:text-gray-700 hover:underline">Cookie Policy</Link>
          <Link href="/acceptable-use" className="hover:text-gray-700 hover:underline">Acceptable Use</Link>
        </div>
      </div>
    </div>
  );
}

function Header({ num, en, ar }: { num: string; en: string; ar: string }) {
  const arNum = num.replace(/[0-9]/g, (d) => "٠١٢٣٤٥٦٧٨٩"[+d]);
  return (
    <header className="mb-4 pb-2 border-b border-gray-200">
      <h2 data-legal-lang="en" dir="ltr" className="text-xl font-semibold text-gray-900 text-left">
        <span className="font-mono text-sm text-gray-400 me-2">{num}.</span>{en}
      </h2>
      <h3 data-legal-lang="ar" className="mt-1 text-lg font-semibold text-gray-700 text-right" dir="rtl">
        <span className="font-mono text-sm text-gray-400 ms-2">{arNum}.</span>{ar}
      </h3>
    </header>
  );
}
function Bilingual({ en, ar }: { en: React.ReactNode; ar: React.ReactNode }) {
  return (
    <div className="bilingual-grid grid md:grid-cols-2 md:gap-8 gap-4">
      <div data-legal-lang="en" dir="ltr" className="text-gray-700 leading-relaxed space-y-3 text-left">{en}</div>
      <div data-legal-lang="ar" dir="rtl" className="text-gray-700 leading-relaxed space-y-3 text-right">{ar}</div>
    </div>
  );
}
