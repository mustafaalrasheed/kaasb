import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Cookie Policy | سياسة ملفات الارتباط",
  description:
    "The cookies and local-storage keys used by the Kaasb marketplace, their purpose, duration, and how to manage consent.",
  robots: { index: true, follow: true },
};

const VERSION = "1.0";
const EFFECTIVE_DATE_EN = "20 April 2026";
const EFFECTIVE_DATE_AR = "٢٠ نيسان ٢٠٢٦";
const EMAIL_PRIVACY = "privacy@kaasb.com";

type CookieRow = {
  name: string;
  category: string;
  purpose_en: string;
  purpose_ar: string;
  duration_en: string;
  duration_ar: string;
};

const COOKIES: CookieRow[] = [
  {
    name: "access_token",
    category: "Strictly necessary",
    purpose_en: "Authenticates your session. Set as HTTP-only cookie after login.",
    purpose_ar: "مصادقة الجلسة، ويُضبط كملف ارتباط HTTP-only بعد تسجيل الدخول.",
    duration_en: "30 minutes",
    duration_ar: "٣٠ دقيقة",
  },
  {
    name: "refresh_token",
    category: "Strictly necessary",
    purpose_en: "Renews expired access tokens without re-logging in. HTTP-only.",
    purpose_ar: "تجديد رموز الوصول المنتهية دون إعادة تسجيل الدخول، وهو HTTP-only.",
    duration_en: "7 days",
    duration_ar: "٧ أيام",
  },
  {
    name: "csrf_token",
    category: "Strictly necessary",
    purpose_en: "Protects against cross-site request forgery on state-changing requests.",
    purpose_ar: "الحماية من تزوير الطلبات عبر المواقع عند الطلبات التي تُغيِّر الحالة.",
    duration_en: "Session",
    duration_ar: "مدة الجلسة",
  },
  {
    name: "locale",
    category: "Strictly necessary",
    purpose_en: "Stores your selected interface language (Arabic or English).",
    purpose_ar: "يحفظ لغة الواجهة التي اخترتها (عربية أو إنجليزية).",
    duration_en: "1 year",
    duration_ar: "سنة واحدة",
  },
  {
    name: "kaasb_cookie_consent",
    category: "Functional (localStorage)",
    purpose_en: "Remembers your cookie-consent choice so the banner is not re-shown.",
    purpose_ar: "يتذكّر اختيارك لإعدادات الارتباط حتى لا يظهر الشريط ثانيةً.",
    duration_en: "Persistent until you clear it",
    duration_ar: "دائم حتى تقوم بمسحه",
  },
];

export default function CookiePolicyPage() {
  return (
    <div className="min-h-screen bg-white">
      <div className="bg-brand-50 border-b border-brand-100 py-12">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-gray-900">Cookie Policy</h1>
          <p className="mt-1 text-sm text-gray-500">Version {VERSION} · Effective {EFFECTIVE_DATE_EN}</p>
          <h2 className="mt-6 text-2xl font-bold text-gray-900 text-right" dir="rtl">سياسة ملفات الارتباط</h2>
          <p className="mt-1 text-sm text-gray-500 text-right" dir="rtl">
            الإصدار {VERSION} · نافذ اعتباراً من {EFFECTIVE_DATE_AR}
          </p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-10">

        <section>
          <Header num="1" en="What cookies are" ar="تعريف ملفات الارتباط" />
          <Bilingual
            en={
              <p>
                Cookies are small text files stored by your browser when you visit a website.{" "}
                <em>localStorage</em> is a similar mechanism that persists data on your device across
                sessions. This policy covers both techniques.
              </p>
            }
            ar={
              <p>
                ملفات الارتباط ملفاتٌ نصية صغيرة يُخزّنها متصفحك عند زيارة الموقع. وتُعدّ تقنية{" "}
                <em>localStorage</em> آليةً مشابهة تحفظ البيانات على جهازك عبر الجلسات. وتغطي هذه
                السياسة كلتا التقنيتين.
              </p>
            }
          />
        </section>

        <section>
          <Header num="2" en="Categories we use" ar="الفئات المُستخدَمة" />
          <Bilingual
            en={
              <>
                <p>We use only two categories today:</p>
                <ul className="list-disc ms-6 mt-3 space-y-1.5">
                  <li><strong>Strictly necessary</strong> — required for authentication, security, and language preference. These cannot be disabled without breaking core functionality, and therefore do not require consent under applicable rules.</li>
                  <li><strong>Functional</strong> — remembers your cookie-consent choice.</li>
                </ul>
                <p className="mt-3">
                  We do <strong>not</strong> use analytics cookies, advertising cookies, third-party trackers,
                  pixel tags, or re-marketing technologies. If we introduce any, the consent banner will be
                  updated and your consent will be requested before any non-essential technology is loaded.
                </p>
              </>
            }
            ar={
              <>
                <p>نستخدم حالياً فئتين فقط:</p>
                <ul className="list-disc me-6 mt-3 space-y-1.5">
                  <li><strong>ضرورية تماماً</strong> — لازمة للمصادقة والأمن وتفضيل اللغة. ولا يمكن تعطيلها دون إخلالٍ بالخصائص الأساسية، ومن ثَمَّ لا تستوجب موافقةً بموجب القواعد السارية.</li>
                  <li><strong>وظيفية</strong> — تحفظ اختيارك في شريط الموافقة على ملفات الارتباط.</li>
                </ul>
                <p className="mt-3">
                  لا نستخدم ملفات ارتباط تحليلية أو إعلانية، ولا أدوات تتبع من أطراف خارجية، ولا
                  وسوم بكسل، ولا تقنيات إعادة التسويق. وإن استحدثنا أيًّا منها، سيُحدَّث شريط الموافقة
                  وستُطلب موافقتك قبل تحميل أي تقنيةٍ غير ضرورية.
                </p>
              </>
            }
          />
        </section>

        <section>
          <Header num="3" en="Detailed list" ar="القائمة التفصيلية" />
          <div className="overflow-x-auto mt-4">
            <table className="w-full text-sm text-left border-collapse">
              <thead>
                <tr className="bg-gray-50">
                  <th className="p-3 font-semibold text-gray-700 border border-gray-200">Name</th>
                  <th className="p-3 font-semibold text-gray-700 border border-gray-200">Category</th>
                  <th className="p-3 font-semibold text-gray-700 border border-gray-200">Purpose · الغرض</th>
                  <th className="p-3 font-semibold text-gray-700 border border-gray-200">Duration · المدة</th>
                </tr>
              </thead>
              <tbody className="text-gray-700 align-top">
                {COOKIES.map((c) => (
                  <tr key={c.name} className="border-b border-gray-200">
                    <td className="p-3 border border-gray-200 font-mono text-xs">{c.name}</td>
                    <td className="p-3 border border-gray-200">{c.category}</td>
                    <td className="p-3 border border-gray-200">
                      <div>{c.purpose_en}</div>
                      <div className="mt-1 text-gray-600" dir="rtl">{c.purpose_ar}</div>
                    </td>
                    <td className="p-3 border border-gray-200">
                      <div>{c.duration_en}</div>
                      <div className="text-gray-600" dir="rtl">{c.duration_ar}</div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <Header num="4" en="Managing cookies" ar="إدارة ملفات الارتباط" />
          <Bilingual
            en={
              <>
                <p>
                  You can manage cookies through your browser settings (clear, block, or be prompted). You
                  may also clear the <code className="text-xs">kaasb_cookie_consent</code> entry from your
                  browser&apos;s local storage to see the consent banner again.
                </p>
                <p className="mt-3">
                  Blocking strictly-necessary cookies will prevent you from logging in or using secure
                  areas of the Platform.
                </p>
              </>
            }
            ar={
              <>
                <p>
                  يمكنك إدارة ملفات الارتباط من إعدادات المتصفح (المسح أو الحجب أو التنبيه)، كما يمكنك
                  مسح مفتاح <code className="text-xs" dir="ltr">kaasb_cookie_consent</code> من مخزن
                  المتصفح لإظهار شريط الموافقة مجدداً.
                </p>
                <p className="mt-3">
                  حجب الملفات الضرورية تماماً سيمنعك من تسجيل الدخول أو استخدام الأجزاء المؤمَّنة من
                  المنصة.
                </p>
              </>
            }
          />
        </section>

        <section>
          <Header num="5" en="Contact" ar="التواصل" />
          <Bilingual
            en={
              <p>
                Questions about this Cookie Policy can be sent to{" "}
                <a href={`mailto:${EMAIL_PRIVACY}`} className="text-brand-500 hover:underline">{EMAIL_PRIVACY}</a>.
              </p>
            }
            ar={
              <p>
                الاستفسارات بشأن هذه السياسة تُرسل إلى{" "}
                <a href={`mailto:${EMAIL_PRIVACY}`} className="text-brand-500 hover:underline">{EMAIL_PRIVACY}</a>.
              </p>
            }
          />
        </section>

        <section>
          <Header num="6" en="Language precedence" ar="الأسبقية اللغوية" />
          <Bilingual
            en={
              <p>
                In the event of conflict between the Arabic and English versions of this Policy, the{" "}
                <strong>Arabic version</strong> prevails, consistent with Article 14 of the Iraqi Civil Code.
              </p>
            }
            ar={
              <p>
                في حال التعارض بين النسختين العربية والإنجليزية، تُعتمد <strong>النسخة العربية</strong>،
                وفقاً للمادة ١٤ من القانون المدني العراقي.
              </p>
            }
          />
        </section>

        <div className="border-t border-gray-200 pt-6 flex flex-wrap gap-4 text-sm text-gray-500">
          <Link href="/privacy" className="hover:text-gray-700 hover:underline">Privacy Policy</Link>
          <Link href="/terms" className="hover:text-gray-700 hover:underline">Terms of Service</Link>
          <Link href="/refunds" className="hover:text-gray-700 hover:underline">Refund Policy</Link>
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
      <h2 className="text-xl font-semibold text-gray-900">
        <span className="font-mono text-sm text-gray-400 mr-2">{num}.</span>{en}
      </h2>
      <h3 className="mt-1 text-lg font-semibold text-gray-700 text-right" dir="rtl">
        <span className="font-mono text-sm text-gray-400 ms-2">{arNum}.</span>{ar}
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
