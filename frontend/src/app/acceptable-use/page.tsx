import type { Metadata } from "next";
import Link from "next/link";
import { LegalViewToggle } from "@/components/legal/legal-view-toggle";

export const metadata: Metadata = {
  title: "Acceptable Use Policy | سياسة الاستخدام المقبول",
  description:
    "Community standards for the Kaasb marketplace: prohibited conduct, anti off-platform rules, reporting, and appeals.",
  robots: { index: true, follow: true },
};

const VERSION = "1.0";
const EFFECTIVE_DATE_EN = "20 April 2026";
const EFFECTIVE_DATE_AR = "٢٠ نيسان ٢٠٢٦";
const EMAIL_SUPPORT = "support@kaasb.com";

export default function AcceptableUsePage() {
  return (
    <div className="min-h-screen bg-white">
      <div className="bg-brand-50 border-b border-brand-100 py-12">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-gray-900">Acceptable Use Policy</h1>
          <p className="mt-1 text-sm text-gray-500">Version {VERSION} · Effective {EFFECTIVE_DATE_EN}</p>
          <h2 className="mt-6 text-2xl font-bold text-gray-900 text-right" dir="rtl">سياسة الاستخدام المقبول</h2>
          <p className="mt-1 text-sm text-gray-500 text-right" dir="rtl">
            الإصدار {VERSION} · نافذ اعتباراً من {EFFECTIVE_DATE_AR}
          </p>
          <p className="mt-4 text-xs text-gray-500 italic max-w-2xl">
            This Policy forms an integral part of the{" "}
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
          <Header num="1" en="Our commitment" ar="التزامنا" />
          <Bilingual
            en={
              <p>
                Kaasb aims to be a trusted, safe, and productive marketplace for Iraqi businesses and
                independent professionals. This Policy explains the conduct we expect from every User and
                the consequences of breaching these rules.
              </p>
            }
            ar={
              <p>
                تسعى كاسب إلى أن تكون سوقاً موثوقاً وآمناً ومُنتجاً للأعمال العراقية والمحترفين
                المستقلين. وتُبيِّن هذه السياسة السلوك المتوقَّع من كل مستخدم والعواقب المترتبة على
                مخالفته.
              </p>
            }
          />
        </section>

        <section>
          <Header num="2" en="Prohibited content and services" ar="المحتوى والخدمات المحظورة" />
          <Bilingual
            en={
              <ul className="list-disc ms-6 space-y-1.5">
                <li>Services, content, or communications that violate Iraqi law, including the Penal Code and the Anti-Cyber-Crime provisions.</li>
                <li>Adult, sexually explicit, or escort-related services.</li>
                <li>Services promoting violence, terrorism, or incitement to hatred on the basis of religion, ethnicity, gender, or nationality.</li>
                <li>Sale or advertisement of weapons, controlled substances, stolen goods, or counterfeit items.</li>
                <li>Academic cheating services designed to defraud educational institutions.</li>
                <li>Content that infringes copyright, trademark, patent, or other intellectual-property rights.</li>
                <li>Misleading medical, legal, or financial advice presented as professional counsel.</li>
                <li>Malware, spyware, or services designed to facilitate hacking or unauthorised access.</li>
                <li>Sexually suggestive content involving any person under the age of eighteen.</li>
                <li>Personal data of third parties obtained or distributed without lawful basis.</li>
              </ul>
            }
            ar={
              <ul className="list-disc me-6 space-y-1.5">
                <li>الخدمات والمحتوى والمراسلات المخالفة للقانون العراقي، بما فيها قانون العقوبات وأحكام مكافحة الجرائم المعلوماتية.</li>
                <li>خدمات الكبار أو الخدمات ذات الطابع الجنسي الصريح أو المرافقة.</li>
                <li>الخدمات التي تروّج للعنف أو الإرهاب أو التحريض على الكراهية على أساس الدين أو العرق أو الجنس أو الجنسية.</li>
                <li>بيع أو ترويج الأسلحة أو المواد الخاضعة للرقابة أو البضائع المسروقة أو المقلَّدة.</li>
                <li>خدمات الغش الأكاديمي المُصمَّمة لإيهام المؤسسات التعليمية.</li>
                <li>المحتوى المنتهك لحقوق المؤلف أو العلامات التجارية أو براءات الاختراع أو أي حقوق ملكية فكرية.</li>
                <li>النصائح الطبية أو القانونية أو المالية المُضلِّلة المُقدَّمة بوصفها مشورةً مهنية.</li>
                <li>البرمجيات الخبيثة أو برامج التجسس أو الخدمات التي تُسهِّل الاختراق أو الوصول غير المصرَّح به.</li>
                <li>المحتوى الإيحائي جنسياً الذي يشمل أي شخص دون الثامنة عشرة.</li>
                <li>بيانات شخصية لأطراف ثالثة مُحَصَّلة أو مُوزَّعة دون سندٍ قانوني.</li>
              </ul>
            }
          />
        </section>

        <section>
          <Header num="3" en="Off-Platform solicitation and fee circumvention" ar="الخروج بالتعامل خارج المنصة والتحايل على الرسوم" />
          <Bilingual
            en={
              <>
                <p>
                  Conducting transactions off the Platform deprives Kaasb of the resources required to
                  operate Escrow, dispute resolution, identity verification, and Seller protection. It also
                  removes the safety net you rely on. Therefore we prohibit:
                </p>
                <ul className="list-disc ms-6 mt-3 space-y-1.5">
                  <li>Sharing phone numbers, email addresses, social-media handles, external messaging-app identifiers, or bank/payment details in messages, Service descriptions, profile copy, or delivery files with the purpose of moving a transaction off the Platform.</li>
                  <li>Proposing, agreeing to, or facilitating any arrangement designed to avoid the Platform Fee, including partial off-Platform payment.</li>
                  <li>Cancelling a Platform Order to re-execute it directly with the same counter-party.</li>
                  <li>Using the messaging system to advertise services that are listed only off the Platform.</li>
                </ul>
                <p className="mt-3">
                  <strong>Exception.</strong> Contact information may be shared after the Order is completed
                  when reasonably needed to deliver the service (for example, a handover file that
                  includes credentials for a live website). When in doubt, ask support.
                </p>
              </>
            }
            ar={
              <>
                <p>
                  الخروج بالتعامل خارج المنصة يحرم كاسبَ من الموارد اللازمة لتشغيل الضمان، وحلّ
                  النزاعات، والتحقق من الهوية، وحماية البائعين، ويسحب منك شبكة الأمان التي تعتمد عليها.
                  لذلك يُحظَر:
                </p>
                <ul className="list-disc me-6 mt-3 space-y-1.5">
                  <li>تبادل أرقام الهواتف أو البريد الإلكتروني أو حسابات التواصل الاجتماعي أو معرّفات تطبيقات المراسلة أو تفاصيل الحسابات المصرفية في الرسائل أو أوصاف الخدمات أو نبذة الملف الشخصي أو ملفات التسليم، بقصد نقل المعاملة خارج المنصة.</li>
                  <li>اقتراح أو قبول أو تسهيل أي ترتيبٍ لتجاوز رسوم المنصة، بما فيه الدفع الجزئي خارجها.</li>
                  <li>إلغاء طلب على المنصة لإعادة تنفيذه مع الطرف ذاته خارجها.</li>
                  <li>استخدام المراسلة للترويج لخدماتٍ معروضة خارج المنصة فقط.</li>
                </ul>
                <p className="mt-3">
                  <strong>استثناء.</strong> يجوز تبادل بيانات الاتصال بعد اكتمال الطلب حين يتطلب ذلك
                  تسليم الخدمة فعلياً (كملف تسليمٍ يتضمن اعتمادات موقعٍ مُباشر). ويُراجَع الدعم عند
                  الشك.
                </p>
              </>
            }
          />
        </section>

        <section>
          <Header num="4" en="How enforcement works" ar="آلية الإنفاذ" />
          <Bilingual
            en={
              <>
                <p>
                  Messages exchanged on the Platform pass through an automated filter that looks for
                  contact details, off-Platform payment references, and fee-circumvention patterns. When a
                  breach is detected:
                </p>
                <ol className="list-decimal ms-6 mt-3 space-y-1.5">
                  <li><strong>First instance</strong> — the message is blocked from delivery and a warning is recorded against your account.</li>
                  <li><strong>Second instance</strong> — the message is blocked and your messaging is suspended for twenty-four (24) hours.</li>
                  <li><strong>Third instance</strong> — the incident is escalated to Kaasb administrators, who may suspend or terminate your account and forfeit pending Platform Fee balances due to the breaching party.</li>
                </ol>
                <p className="mt-3">
                  Serious breaches (fraud, unlawful content, repeated circumvention) may trigger
                  immediate suspension at any stage, without a prior warning.
                </p>
              </>
            }
            ar={
              <>
                <p>
                  تمرّ الرسائل المُتبادَلة عبر المنصة بمُرشِّح آلي يبحث عن بيانات الاتصال ومراجع الدفع
                  خارج المنصة وأنماط التحايل على الرسوم. وعند رصد مخالفة:
                </p>
                <ol className="list-decimal me-6 mt-3 space-y-1.5">
                  <li><strong>المرة الأولى</strong> — تُحجب الرسالة من التسليم ويُسجَّل تنبيه على حسابك.</li>
                  <li><strong>المرة الثانية</strong> — تُحجب الرسالة وتُعلَّق مراسلتك لمدة أربع وعشرين (٢٤) ساعة.</li>
                  <li><strong>المرة الثالثة</strong> — يُرفَع الأمر إلى إداريي كاسب الذين قد يُعلِّقون حسابك أو يُنهونه ويُصادرون أرصدة رسوم المنصة المستحقة للطرف المخالف.</li>
                </ol>
                <p className="mt-3">
                  وتستوجب المخالفات الجسيمة (احتيال، محتوى غير مشروع، تحايل متكرر) تعليقاً فورياً في
                  أي مرحلة ودون تنبيه مسبق.
                </p>
              </>
            }
          />
        </section>

        <section>
          <Header num="5" en="Community conduct" ar="آداب المجتمع" />
          <Bilingual
            en={
              <ul className="list-disc ms-6 space-y-1.5">
                <li>Treat every User with respect. Harassment, threats, sexual advances, and discrimination are not tolerated.</li>
                <li>Use professional language in all messages, Service titles, and descriptions.</li>
                <li>Do not create multiple accounts, manipulate reviews, or attempt to game search rankings.</li>
                <li>Do not impersonate another person, brand, or organisation.</li>
                <li>Do not collect or redistribute personal data of other Users.</li>
              </ul>
            }
            ar={
              <ul className="list-disc me-6 space-y-1.5">
                <li>عامل كل مستخدم باحترام. لا تُقبل المضايقة أو التهديد أو المراودة الجنسية أو التمييز.</li>
                <li>استخدم لغةً مهنيةً في الرسائل وعناوين الخدمات وأوصافها.</li>
                <li>لا تُنشئ حسابات متعددة ولا تتلاعب بالتقييمات ولا تسعَ للتأثير على نتائج البحث.</li>
                <li>لا تنتحل شخصية أي فردٍ أو علامةٍ تجاريةٍ أو منظمة.</li>
                <li>لا تجمع بياناتٍ شخصيةً للمستخدمين ولا تُعيد نشرها.</li>
              </ul>
            }
          />
        </section>

        <section>
          <Header num="6" en="Reporting a violation" ar="الإبلاغ عن مخالفة" />
          <Bilingual
            en={
              <p>
                Use the &quot;Report&quot; action on a profile, Service, Job, message, or review to flag it for
                administrative review. Severe or time-sensitive cases (impersonation of a Kaasb employee,
                threats, fraud in progress) should be sent to{" "}
                <a href={`mailto:${EMAIL_SUPPORT}`} className="text-brand-500 hover:underline">{EMAIL_SUPPORT}</a>{" "}
                with the subject line &quot;Urgent&quot; and a link to the content in question.
              </p>
            }
            ar={
              <p>
                استخدم زر «إبلاغ» على الملف الشخصي أو الخدمة أو الوظيفة أو الرسالة أو التقييم للإحالة
                إلى الإدارة. وتُرسَل الحالات الجسيمة أو العاجلة (انتحال موظف كاسب، تهديدات، احتيال
                جارٍ) إلى{" "}
                <a href={`mailto:${EMAIL_SUPPORT}`} className="text-brand-500 hover:underline">{EMAIL_SUPPORT}</a>{" "}
                بعنوان «عاجل» مع رابط المحتوى المعني.
              </p>
            }
          />
        </section>

        <section>
          <Header num="7" en="Appeals" ar="التظلم" />
          <Bilingual
            en={
              <p>
                If you believe an enforcement action was taken in error, write to{" "}
                <a href={`mailto:${EMAIL_SUPPORT}`} className="text-brand-500 hover:underline">{EMAIL_SUPPORT}</a>{" "}
                within fourteen (14) days explaining the circumstances. A different administrator from the
                one who took the original action will review the appeal.
              </p>
            }
            ar={
              <p>
                إن رأيت أن إجراءً تنفيذياً اتُّخِذ خطأً، راسل{" "}
                <a href={`mailto:${EMAIL_SUPPORT}`} className="text-brand-500 hover:underline">{EMAIL_SUPPORT}</a>{" "}
                خلال أربعة عشر (١٤) يوماً موضّحاً الملابسات، على أن يراجع التظلم إداريٌّ غير الذي
                اتخذ القرار الأصلي.
              </p>
            }
          />
        </section>

        <section>
          <Header num="8" en="Language precedence" ar="الأسبقية اللغوية" />
          <Bilingual
            en={<p>In the event of conflict, the <strong>Arabic version</strong> of this Policy prevails.</p>}
            ar={<p>عند التعارض، تُعتمد <strong>النسخة العربية</strong> من هذه السياسة.</p>}
          />
        </section>

        <div className="border-t border-gray-200 pt-6 flex flex-wrap gap-4 text-sm text-gray-500">
          <Link href="/privacy" className="hover:text-gray-700 hover:underline">Privacy Policy</Link>
          <Link href="/terms" className="hover:text-gray-700 hover:underline">Terms of Service</Link>
          <Link href="/cookies" className="hover:text-gray-700 hover:underline">Cookie Policy</Link>
          <Link href="/refunds" className="hover:text-gray-700 hover:underline">Refund Policy</Link>
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
