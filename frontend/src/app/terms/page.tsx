import type { Metadata } from "next";
import Link from "next/link";
import { LegalViewToggle } from "@/components/legal/legal-view-toggle";

export const metadata: Metadata = {
  title: "Terms of Service | شروط الخدمة",
  description:
    "Terms of Service governing use of the Kaasb freelancing marketplace in Iraq. Bilingual (Arabic / English).",
  robots: { index: true, follow: true },
};

// NOTE for future maintainers — replace placeholders before public reliance:
// <!-- __REG_NO__ = Iraqi commercial registration number -->
// <!-- __ADDRESS__ = registered physical address -->
// <!-- __COMPANY_TYPE__ = registration type (e.g. LLC) -->

const VERSION = "1.0";
const EFFECTIVE_DATE_EN = "20 April 2026";
const EFFECTIVE_DATE_AR = "٢٠ نيسان ٢٠٢٦";
const COMPANY_EN = "Kaasb Technology LLC";
const COMPANY_AR = "شركة كاسب تكنولوجي";
const EMAIL_LEGAL = "legal@kaasb.com";
const EMAIL_SUPPORT = "support@kaasb.com";
const PLATFORM_FEE_PERCENT = 10;
const AUTO_COMPLETE_DAYS = 3;

type Toc = { id: string; en: string; ar: string };

const TOC: Toc[] = [
  { id: "1",  en: "Acceptance & Electronic Contract", ar: "القبول والتعاقد الإلكتروني" },
  { id: "2",  en: "Definitions",                       ar: "التعريفات" },
  { id: "3",  en: "Eligibility & Account",             ar: "الأهلية والحساب" },
  { id: "4",  en: "Role of the Platform",              ar: "دور المنصة" },
  { id: "5",  en: "Buyer Obligations",                 ar: "التزامات المشتري" },
  { id: "6",  en: "Seller Obligations",                ar: "التزامات البائع" },
  { id: "7",  en: "Gigs & Orders",                     ar: "الخدمات والطلبات" },
  { id: "8",  en: "Jobs & Proposals",                  ar: "الوظائف والعروض" },
  { id: "9",  en: "Payments & Fees",                   ar: "المدفوعات والرسوم" },
  { id: "10", en: "Refunds",                           ar: "المبالغ المستردة" },
  { id: "11", en: "Disputes",                          ar: "النزاعات" },
  { id: "12", en: "Prohibited Conduct",                ar: "السلوك المحظور" },
  { id: "13", en: "Seller Levels",                     ar: "مستويات البائعين" },
  { id: "14", en: "Intellectual Property",             ar: "الملكية الفكرية" },
  { id: "15", en: "User Content Licence",              ar: "ترخيص محتوى المستخدم" },
  { id: "16", en: "Reviews",                           ar: "التقييمات" },
  { id: "17", en: "Content Moderation",                ar: "مراقبة المحتوى" },
  { id: "18", en: "Suspension & Termination",          ar: "التعليق والإنهاء" },
  { id: "19", en: "Disclaimers",                       ar: "إخلاء المسؤولية" },
  { id: "20", en: "Limitation of Liability",           ar: "حدود المسؤولية" },
  { id: "21", en: "Indemnification",                   ar: "التعويض" },
  { id: "22", en: "Governing Law & Venue",             ar: "القانون الحاكم والاختصاص" },
  { id: "23", en: "Force Majeure",                     ar: "القوة القاهرة" },
  { id: "24", en: "General Provisions",                ar: "أحكام عامة" },
  { id: "25", en: "Changes to Terms",                  ar: "تعديل الشروط" },
  { id: "26", en: "Contact & Legal Notices",           ar: "التواصل والإخطارات القانونية" },
  { id: "27", en: "Language Precedence",               ar: "الأسبقية اللغوية" },
];

export default function TermsOfServicePage() {
  return (
    <div className="min-h-screen bg-white">
      <div className="bg-brand-50 border-b border-brand-100 py-12">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-gray-900">Terms of Service</h1>
          <p className="mt-1 text-sm text-gray-500">
            Version {VERSION} · Effective {EFFECTIVE_DATE_EN}
          </p>
          <h2 className="mt-6 text-2xl font-bold text-gray-900 text-right" dir="rtl">
            شروط الخدمة
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

          <aside className="hidden lg:block">
            <nav aria-label="Table of contents" className="lg:sticky lg:top-6">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                Contents · المحتوى
              </h3>
              <ol className="space-y-1.5 text-sm">
                {TOC.map((s) => (
                  <li key={s.id}>
                    <a href={`#${s.id}`} className="text-gray-600 hover:text-brand-600 hover:underline block leading-snug">
                      <span className="font-mono text-xs text-gray-400 me-1">{s.id}.</span>
                      {s.en} <span className="text-gray-400" dir="rtl">· {s.ar}</span>
                    </a>
                  </li>
                ))}
              </ol>
            </nav>
          </aside>

          <details className="lg:hidden mb-8 border border-gray-200 rounded-lg p-4">
            <summary className="text-sm font-semibold text-gray-700 cursor-pointer">
              Contents · المحتوى ({TOC.length})
            </summary>
            <ol className="mt-3 space-y-1.5 text-sm">
              {TOC.map((s) => (
                <li key={s.id}>
                  <a href={`#${s.id}`} className="text-gray-600 hover:text-brand-600 hover:underline">
                    <span className="font-mono text-xs text-gray-400 me-1">{s.id}.</span>
                    {s.en} <span className="text-gray-400" dir="rtl">· {s.ar}</span>
                  </a>
                </li>
              ))}
            </ol>
          </details>

          <article className="space-y-14 min-w-0">

            <div className="flex justify-center sm:justify-end -mt-4">
              <LegalViewToggle />
            </div>

            {/* 1. Acceptance */}
            <section id="1" className="scroll-mt-24">
              <SectionHeader num="1" en="Acceptance & Electronic Contract" ar="القبول والتعاقد الإلكتروني" />
              <Bilingual
                en={
                  <>
                    <p>
                      These Terms of Service (the &quot;Terms&quot;) constitute a binding legal agreement between you
                      and {COMPANY_EN} (&quot;Kaasb&quot;, &quot;we&quot;, &quot;our&quot;, &quot;us&quot;) governing your use of the Kaasb
                      Platform located at{" "}
                      <Link href="https://kaasb.com" className="text-brand-500 hover:underline">kaasb.com</Link> and
                      all associated services, applications, and application-programming interfaces (together,
                      the &quot;Platform&quot;).
                    </p>
                    <p className="mt-3">
                      By creating an account, clicking &quot;I agree&quot;, or continuing to use the Platform after the
                      effective date, you expressly accept these Terms in electronic form. You acknowledge
                      that an electronic acceptance has the same legal effect as a handwritten signature under
                      the Iraqi Electronic Signature and Electronic Transactions Law No. 78 of 2012.
                    </p>
                    <p className="mt-3">
                      If you do not agree with any part of these Terms, you must not create an account or
                      otherwise use the Platform.
                    </p>
                  </>
                }
                ar={
                  <>
                    <p>
                      تُشكِّل شروط الخدمة هذه («الشروط») اتفاقاً قانونياً ملزماً بينك وبين {COMPANY_AR}
                      («كاسب» أو «نحن»)، وتحكم استخدامك لمنصة كاسب الكائنة على{" "}
                      <Link href="https://kaasb.com" className="text-brand-500 hover:underline" dir="ltr">kaasb.com</Link>{" "}
                      وكافة الخدمات والتطبيقات وواجهات البرمجة المرتبطة بها (يُشار إليها مجتمعةً بـ«المنصة»).
                    </p>
                    <p className="mt-3">
                      بإنشاء حساب أو النقر على زر «أوافق» أو الاستمرار في استخدام المنصة بعد تاريخ النفاذ،
                      فإنك تقبل هذه الشروط قبولاً صريحاً بالشكل الإلكتروني، وتُقرّ بأن القبول الإلكتروني
                      يُرتِّب الأثر القانوني ذاته للتوقيع اليدوي وفق قانون التوقيع الإلكتروني والمعاملات
                      الإلكترونية العراقي رقم ٧٨ لسنة ٢٠١٢.
                    </p>
                    <p className="mt-3">
                      وفي حال عدم موافقتك على أيٍّ من بنود هذه الشروط، يتعيّن عليك الامتناع عن إنشاء حساب
                      أو استخدام المنصة.
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
                    <li><strong>Buyer (Client)</strong> — a registered User who posts a Job, places an Order on a Gig, or otherwise engages a Seller.</li>
                    <li><strong>Seller (Freelancer)</strong> — a registered User who offers services, publishes Gigs, or submits Proposals.</li>
                    <li><strong>Gig</strong> — a packaged service offered by a Seller at a stated price, in one or more Packages.</li>
                    <li><strong>Job</strong> — a project posted by a Buyer inviting Proposals from Sellers.</li>
                    <li><strong>Order</strong> — a purchase of a Gig by a Buyer.</li>
                    <li><strong>Proposal</strong> — a Seller&apos;s offer to perform a Job.</li>
                    <li><strong>Contract</strong> — the engagement formed after a Proposal is accepted, which may include Milestones.</li>
                    <li><strong>Escrow</strong> — funds paid by a Buyer and held on the Platform until released according to these Terms.</li>
                    <li><strong>Platform Fee</strong> — the commission Kaasb charges, as defined in Section 9.</li>
                  </ul>
                }
                ar={
                  <ul className="list-disc me-6 space-y-2">
                    <li><strong>المشتري (العميل)</strong> — مستخدم مسجَّل يُنشئ وظيفة، أو يُقدم طلباً على خدمة، أو يتعاقد مع بائع.</li>
                    <li><strong>البائع (المستقل)</strong> — مستخدم مسجَّل يعرض خدمات أو ينشر خدماته («الـ Gigs») أو يُقدم عروضاً.</li>
                    <li><strong>الخدمة (Gig)</strong> — خدمة معروضة من بائع بسعر محدد، عبر باقة أو أكثر.</li>
                    <li><strong>الوظيفة</strong> — مشروع ينشره المشتري لاستقطاب عروض من البائعين.</li>
                    <li><strong>الطلب</strong> — شراء المشتري لخدمة (Gig).</li>
                    <li><strong>العرض</strong> — اقتراح بائع لتنفيذ وظيفة.</li>
                    <li><strong>العقد</strong> — الارتباط القائم بعد قبول العرض، وقد يتضمن معالم (Milestones).</li>
                    <li><strong>الضمان (الإسكرو)</strong> — مبلغ يدفعه المشتري ويُحتَفَظ به على المنصة حتى إفراجه وفق هذه الشروط.</li>
                    <li><strong>رسوم المنصة</strong> — العمولة التي تستوفيها كاسب وفقاً للبند ٩.</li>
                  </ul>
                }
              />
            </section>

            {/* 3. Eligibility */}
            <section id="3" className="scroll-mt-24">
              <SectionHeader num="3" en="Eligibility & Account" ar="الأهلية والحساب" />
              <Bilingual
                en={
                  <>
                    <Sub num="3.1" title="Age and capacity">
                      You must be at least eighteen (18) years of age and possess full legal capacity to
                      contract under the laws of your place of residence. If you act on behalf of a
                      corporate entity, you warrant that you are duly authorised to bind that entity.
                    </Sub>
                    <Sub num="3.2" title="Accurate information">
                      You must provide accurate, current, and complete information during registration, and
                      keep that information up to date. Fraudulent or materially misleading information is
                      grounds for suspension or termination.
                    </Sub>
                    <Sub num="3.3" title="Account security">
                      You are solely responsible for the confidentiality of your credentials and for all
                      activity under your account. You must notify us without undue delay at{" "}
                      <a href={`mailto:${EMAIL_LEGAL}`} className="text-brand-500 hover:underline">{EMAIL_LEGAL}</a>{" "}
                      of any suspected unauthorised use.
                    </Sub>
                    <Sub num="3.4" title="One account rule">
                      You may hold only one active account. Creating multiple accounts to circumvent a
                      suspension, evade rating history, manipulate search rankings, or otherwise abuse the
                      Platform is strictly prohibited.
                    </Sub>
                    <Sub num="3.5" title="Prohibited jurisdictions">
                      You must not use the Platform from a jurisdiction that is subject to comprehensive
                      international sanctions inconsistent with applicable law.
                    </Sub>
                  </>
                }
                ar={
                  <>
                    <Sub num="٣.١" title="السن والأهلية" rtl>
                      يجب ألا يقل عمرك عن ثمانية عشر (١٨) عاماً، وأن تتمتع بالأهلية القانونية الكاملة
                      للتعاقد وفق قانون محل إقامتك. وإن كنت تتصرف نيابةً عن شخصٍ اعتباري، فإنك تضمن
                      تفويضك الصحيح بإلزام ذلك الشخص.
                    </Sub>
                    <Sub num="٣.٢" title="صحة المعلومات" rtl>
                      يجب تقديم معلومات صحيحة وكاملة ومُحدَّثة عند التسجيل والحفاظ على تحديثها. ويُعدّ
                      تقديم معلومات احتيالية أو مضلِّلة جوهرياً سبباً للتعليق أو الإنهاء.
                    </Sub>
                    <Sub num="٣.٣" title="أمن الحساب" rtl>
                      أنت وحدك المسؤول عن سرية بيانات الدخول وعن كل نشاطٍ يجري على حسابك، ويجب إخطارنا
                      دون تأخير غير مبرَّر على{" "}
                      <a href={`mailto:${EMAIL_LEGAL}`} className="text-brand-500 hover:underline">{EMAIL_LEGAL}</a>{" "}
                      عند الاشتباه بأي استخدام غير مصرَّح به.
                    </Sub>
                    <Sub num="٣.٤" title="قاعدة الحساب الواحد" rtl>
                      لا يجوز الاحتفاظ بأكثر من حساب واحد فعّال. ويُحظَر إنشاء حسابات متعددة لغرض التحايل
                      على تعليقٍ سابق، أو التهرُّب من سجل التقييم، أو التلاعب بنتائج البحث، أو أي إساءة
                      أخرى للمنصة.
                    </Sub>
                    <Sub num="٣.٥" title="الولايات القضائية المحظورة" rtl>
                      يُحظر استخدام المنصة من ولاية قضائية خاضعة لعقوبات دولية شاملة تتعارض مع القانون
                      الساري.
                    </Sub>
                  </>
                }
              />
            </section>

            {/* 4. Role */}
            <section id="4" className="scroll-mt-24">
              <SectionHeader num="4" en="Role of the Platform" ar="دور المنصة" />
              <Bilingual
                en={
                  <>
                    <p>
                      Kaasb operates a digital marketplace that connects Buyers and Sellers and provides
                      facilitation services including escrow, messaging, dispute mediation, and identity
                      verification. Kaasb is <strong>not</strong> a party to the service contract formed between a
                      Buyer and a Seller, is not the employer of any Seller, and is not responsible for the
                      performance, quality, legality, or delivery of any service.
                    </p>
                    <p className="mt-3">
                      Where Kaasb acts as a mediator or decides a dispute under Section 11, it does so in a
                      neutral administrative capacity and not as an arbitrator or court.
                    </p>
                  </>
                }
                ar={
                  <>
                    <p>
                      تُشغِّل كاسب سوقاً رقمياً يصل بين المشترين والبائعين ويُقدِّم خدمات تيسير تشمل الضمان
                      (الإسكرو) والمراسلة والتحكيم الإداري (الوساطة) والتحقق من الهوية. ولا تُعدّ كاسب
                      <strong> طرفاً </strong> في عقد الخدمة المُبرَم بين المشتري والبائع، ولا صاحب عملٍ
                      لأيٍّ من البائعين، ولا مسؤولةً عن تنفيذ أي خدمة أو جودتها أو قانونيتها أو تسليمها.
                    </p>
                    <p className="mt-3">
                      حين تتولى كاسب دور الوسيط أو تبتّ في نزاع بموجب البند ١١، فإنها تتصرف بوصفها جهةً
                      إداريةً محايدة، لا كمُحكِّم أو محكمة.
                    </p>
                  </>
                }
              />
            </section>

            {/* 5. Buyer obligations */}
            <section id="5" className="scroll-mt-24">
              <SectionHeader num="5" en="Buyer Obligations" ar="التزامات المشتري" />
              <Bilingual
                en={
                  <ul className="list-disc ms-6 space-y-1.5">
                    <li>Describe your requirements accurately, completely, and in good faith.</li>
                    <li>Fund Escrow in full before work begins and respond promptly to requirement questions.</li>
                    <li>Communicate respectfully and exclusively through the Platform; do not solicit off-Platform contact or payment.</li>
                    <li>Review deliveries and respond within the revision or acceptance window.</li>
                    <li>Leave honest, non-coerced reviews.</li>
                    <li>Comply with all applicable Iraqi laws, including tax and intellectual-property laws, in connection with work you commission.</li>
                  </ul>
                }
                ar={
                  <ul className="list-disc me-6 space-y-1.5">
                    <li>وصف متطلباتك بدقة واكتمال وبحسن نيّة.</li>
                    <li>تمويل الضمان (الإسكرو) بالكامل قبل بدء العمل والإجابة عن أسئلة المتطلبات فوراً.</li>
                    <li>التواصل باحترام وبشكل حصري عبر المنصة، وعدم السعي للتواصل أو الدفع خارجها.</li>
                    <li>مراجعة التسليمات والاستجابة خلال مدة التعديل أو القبول.</li>
                    <li>تقديم تقييمات صادقة وغير مُكرَهة.</li>
                    <li>الامتثال للقوانين العراقية السارية، بما فيها قوانين الضرائب والملكية الفكرية، فيما يخص الأعمال التي تطلبها.</li>
                  </ul>
                }
              />
            </section>

            {/* 6. Seller obligations */}
            <section id="6" className="scroll-mt-24">
              <SectionHeader num="6" en="Seller Obligations" ar="التزامات البائع" />
              <Bilingual
                en={
                  <ul className="list-disc ms-6 space-y-1.5">
                    <li>Offer only services you are qualified and legally permitted to perform.</li>
                    <li>Describe Gigs, pricing, timelines, and revision policies accurately.</li>
                    <li>Deliver work that conforms to the agreed scope and within the agreed time.</li>
                    <li>Respond to Buyers within the response-time expectations associated with your Seller Level.</li>
                    <li>Not engage in plagiarism, infringement, or substitution of low-quality work.</li>
                    <li>Comply with tax-declaration obligations under Iraqi law for income received through the Platform.</li>
                  </ul>
                }
                ar={
                  <ul className="list-disc me-6 space-y-1.5">
                    <li>عدم عرض سوى الخدمات التي تملك أهلية وصلاحية قانونية لأدائها.</li>
                    <li>وصف الخدمات والتسعير والمواعيد وسياسات التعديل بدقة.</li>
                    <li>تسليم العمل مطابقاً للنطاق المتفق عليه ضمن المدة المحددة.</li>
                    <li>الردّ على المشترين ضمن توقعات زمن الاستجابة المرتبطة بمستوى البائع الخاص بك.</li>
                    <li>عدم الانتحال أو التعدي على حقوق الغير أو استبدال العمل بعمل أدنى جودة.</li>
                    <li>الامتثال لالتزامات الإقرار الضريبي وفق القانون العراقي عن الدخل المُحَصَّل عبر المنصة.</li>
                  </ul>
                }
              />
            </section>

            {/* 7. Gigs & Orders */}
            <section id="7" className="scroll-mt-24">
              <SectionHeader num="7" en="Gigs & Orders" ar="الخدمات والطلبات" />
              <Bilingual
                en={
                  <>
                    <Sub num="7.1" title="Listing and review">
                      New Gigs are submitted for administrative review. Kaasb may approve, reject, or request
                      revisions. Listings that breach these Terms, infringe third-party rights, or misrepresent
                      the service will be rejected.
                    </Sub>
                    <Sub num="7.2" title="Order lifecycle">
                      Orders move through the following states: <em>pending payment → pending requirements →
                      in progress → delivered → completed</em>. Orders may also enter <em>revision</em>,{" "}
                      <em>cancelled</em>, or <em>disputed</em> states.
                    </Sub>
                    <Sub num="7.3" title="Requirements and delivery">
                      After payment, the Buyer must submit the requirements requested by the Seller. The
                      delivery timer begins when requirements are submitted. Sellers must deliver using the
                      structured delivery form, attaching the deliverable files and a message.
                    </Sub>
                    <Sub num="7.4" title="Revisions">
                      The Seller defines the number of revisions included in each Gig Package. Revision
                      requests must be specific and related to the original agreed scope. Out-of-scope
                      requests require a new Order or Package upgrade.
                    </Sub>
                    <Sub num="7.5" title={`Auto-completion after ${AUTO_COMPLETE_DAYS} days`}>
                      If the Buyer neither accepts the delivery nor requests a revision within{" "}
                      {AUTO_COMPLETE_DAYS} calendar days of delivery, the Order is automatically marked as
                      completed and Escrow becomes eligible for release. This period may be extended while a
                      dispute is pending.
                    </Sub>
                    <Sub num="7.6" title="Cancellation">
                      Before work begins, either party may cancel for any reason. After work begins,
                      cancellation requires mutual consent unless a dispute is resolved in the requesting
                      party&apos;s favour under Section 11.
                    </Sub>
                  </>
                }
                ar={
                  <>
                    <Sub num="٧.١" title="النشر والمراجعة" rtl>
                      تُقدَّم الخدمات الجديدة للمراجعة الإدارية، ويحق لكاسب قبولها أو رفضها أو طلب
                      تعديلات عليها. وتُرفض القوائم المخالفة لهذه الشروط أو المتعدية على حقوق الغير أو
                      المُضلِّلة في وصف الخدمة.
                    </Sub>
                    <Sub num="٧.٢" title="دورة حياة الطلب" rtl>
                      تنتقل الطلبات عبر الحالات الآتية: <em>بانتظار الدفع → بانتظار المتطلبات → قيد
                      التنفيذ → مُسلَّم → مكتمل</em>. وقد تمرّ كذلك بحالات <em>تعديل</em> أو{" "}
                      <em>إلغاء</em> أو <em>نزاع</em>.
                    </Sub>
                    <Sub num="٧.٣" title="المتطلبات والتسليم" rtl>
                      بعد الدفع، يجب على المشتري تقديم المتطلبات التي يطلبها البائع، ويبدأ مُهِل التسليم
                      من لحظة تقديمها. ويُسلِّم البائع عبر نموذج التسليم المُنَظَّم مُرفِقاً ملفات التسليم
                      ورسالةً مرافقة.
                    </Sub>
                    <Sub num="٧.٤" title="التعديلات" rtl>
                      يُحدِّد البائع عدد التعديلات المُضمَّنة في كل باقة. ويجب أن تكون طلبات التعديل
                      محدَّدة ومرتبطة بالنطاق الأصلي المتفق عليه. أما ما يتجاوز النطاق فيستوجب طلباً
                      جديداً أو ترقية الباقة.
                    </Sub>
                    <Sub num="٧.٥" title={`الإكمال التلقائي بعد ${AUTO_COMPLETE_DAYS} أيام`} rtl>
                      إن لم يقبل المشتري التسليم ولم يطلب تعديلاً خلال {AUTO_COMPLETE_DAYS} أيام تقويمية
                      من التسليم، يُعتبر الطلب مكتملاً تلقائياً ويصبح الضمان قابلاً للإفراج. وقد تُمدَّد
                      هذه المدة ما دام النزاع قائماً.
                    </Sub>
                    <Sub num="٧.٦" title="الإلغاء" rtl>
                      قبل بدء العمل، يجوز لأي طرف الإلغاء لأي سببٍ كان. وبعد البدء، يستوجب الإلغاء
                      موافقة الطرفين ما لم يُحسم نزاع لصالح الطرف الطالب وفق البند ١١.
                    </Sub>
                  </>
                }
              />
            </section>

            {/* 8. Jobs & Proposals */}
            <section id="8" className="scroll-mt-24">
              <SectionHeader num="8" en="Jobs & Proposals" ar="الوظائف والعروض" />
              <Bilingual
                en={
                  <>
                    <p>
                      In addition to Gigs, Buyers may post Jobs inviting Proposals. A Contract is formed when
                      the Buyer accepts a Proposal. Contracts may include Milestones; each Milestone must be
                      funded to Escrow and is released upon Buyer approval. The Seller may request payment
                      only for Milestones that are fully funded.
                    </p>
                    <p className="mt-3">
                      Buyers may additionally post short Buyer Requests to which Sellers submit offers.
                      Accepted offers create an Order under Section 7.
                    </p>
                  </>
                }
                ar={
                  <>
                    <p>
                      إضافةً إلى الخدمات (Gigs)، يجوز للمشترين نشر «وظائف» لاستقطاب عروض. ويُبرَم العقد
                      بقبول المشتري للعرض. وقد يتضمن العقد معالم (Milestones) يتعيَّن تمويل كلٍّ منها في
                      الإسكرو، ويُفرَج عنها بموافقة المشتري. ولا يحق للبائع المطالبة بالدفع إلا عن
                      المعالم المُمَوَّلة بالكامل.
                    </p>
                    <p className="mt-3">
                      ويجوز للمشترين نشر طلبات قصيرة («طلبات المشتري») يقدّم عليها البائعون عروضهم،
                      فيُنشئ قبول العرض طلباً خاضعاً للبند ٧.
                    </p>
                  </>
                }
              />
            </section>

            {/* 9. Payments & Fees */}
            <section id="9" className="scroll-mt-24">
              <SectionHeader num="9" en="Payments & Fees" ar="المدفوعات والرسوم" />
              <Bilingual
                en={
                  <>
                    <Sub num="9.1" title="Currency">
                      All payments, Escrow balances, and payouts are denominated in Iraqi Dinars (IQD). Any
                      USD figures displayed on the Platform are informational only and may be based on a
                      reference rate that does not reflect Qi Card&apos;s applied rate at the moment of a
                      transaction.
                    </Sub>
                    <Sub num="9.2" title="Payment processor">
                      All payments are processed exclusively through Qi Card. Kaasb does not accept cash,
                      bank transfers outside Qi Card, or any alternative processor.
                    </Sub>
                    <Sub num="9.3" title="Escrow">
                      Funds paid by the Buyer are held in Escrow. Escrow passes through the states{" "}
                      <em>pending → funded → released → refunded</em>, or <em>disputed</em>. Escrow is
                      released to the Seller upon Buyer acceptance, auto-completion after{" "}
                      {AUTO_COMPLETE_DAYS} days, or dispute resolution in the Seller&apos;s favour.
                    </Sub>
                    <Sub num="9.4" title={`Platform Fee (${PLATFORM_FEE_PERCENT}%)`}>
                      Kaasb deducts a Platform Fee equal to <strong>{PLATFORM_FEE_PERCENT}%</strong> of the
                      Order value from the Seller&apos;s payout. Buyers are not charged a service fee today. If
                      Buyer-side fees are introduced, Buyers will be notified at least thirty (30) days in
                      advance and fees will be displayed at checkout before any charge.
                    </Sub>
                    <Sub num="9.5" title="Taxes">
                      Prices displayed on the Platform are stated inclusive of any taxes that Kaasb is
                      required to collect. Each User is solely responsible for declaring and paying any
                      income tax, sales tax, or other levies applicable to them under Iraqi law.
                    </Sub>
                    <Sub num="9.6" title="Payouts">
                      Payouts are initiated manually by Kaasb administrators through the Qi Card merchant
                      portal, as Qi Card does not currently expose a payout API. Routine payouts are
                      processed within five (5) business days of Escrow release. Payouts exceeding the
                      dual-control threshold require approval by two separate administrators.
                    </Sub>
                    <Sub num="9.7" title="Payment holds">
                      Kaasb may place a temporary hold on a payout where required by law, where dispute is
                      pending, where fraud is suspected, or where verification of the payee&apos;s identity is
                      incomplete.
                    </Sub>
                  </>
                }
                ar={
                  <>
                    <Sub num="٩.١" title="العملة" rtl>
                      جميع المدفوعات وأرصدة الضمان والمبالغ المصروفة بالدينار العراقي. وأي أرقام
                      بالدولار الأمريكي تظهر على المنصة فهي للاسترشاد فقط، وقد تستند إلى سعر مرجعي لا
                      يعكس السعر الذي تطبّقه كي كارد لحظة تنفيذ المعاملة.
                    </Sub>
                    <Sub num="٩.٢" title="معالج الدفع" rtl>
                      تُعالَج جميع المدفوعات حصراً عبر كي كارد. ولا تقبل كاسب النقد ولا الحوالات المصرفية
                      خارج كي كارد ولا أي معالج بديل.
                    </Sub>
                    <Sub num="٩.٣" title="الضمان (الإسكرو)" rtl>
                      تُحفَظ المبالغ المدفوعة من المشتري في الضمان، وتمرّ بالحالات{" "}
                      <em>قيد الانتظار → مُموَّل → مُفرَج عنه → مُستَرَد</em>، أو <em>متنازع عليه</em>.
                      ويُفرَج عن الضمان لصالح البائع عند قبول المشتري، أو الإكمال التلقائي بعد{" "}
                      {AUTO_COMPLETE_DAYS} أيام، أو حسم النزاع لصالح البائع.
                    </Sub>
                    <Sub num="٩.٤" title={`رسوم المنصة (${PLATFORM_FEE_PERCENT}٪)`} rtl>
                      تستوفي كاسب رسوم منصة قدرها <strong>{PLATFORM_FEE_PERCENT}٪</strong> من قيمة الطلب
                      تُحسم من مستحقات البائع. ولا تُفرض اليوم رسوم على المشترين. وفي حال استحداث رسوم
                      على المشترين، يُخطَرون قبل سريانها بثلاثين (٣٠) يوماً على الأقل، وتُعرض الرسوم في
                      مرحلة الدفع قبل تحصيلها.
                    </Sub>
                    <Sub num="٩.٥" title="الضرائب" rtl>
                      الأسعار المعروضة على المنصة شاملةٌ لأي ضرائب تلتزم كاسب بتحصيلها. ويتحمل كل
                      مستخدم وحده إقرار ودفع أي ضريبة دخل أو مبيعات أو أي رسوم سارية عليه وفق القانون
                      العراقي.
                    </Sub>
                    <Sub num="٩.٦" title="صرف المستحقات" rtl>
                      يجري صرف مستحقات البائعين يدوياً من قِبل إداريي كاسب عبر بوابة التاجر لدى كي كارد،
                      إذ لا تُتيح كي كارد حالياً واجهة برمجية للصرف. وتُعالج المستحقات الاعتيادية خلال
                      خمسة (٥) أيام عمل من إفراج الإسكرو. وتستوجب المستحقات التي تتجاوز حدّ الرقابة
                      المزدوجة موافقة إداريَّين اثنين.
                    </Sub>
                    <Sub num="٩.٧" title="إيقاف الصرف مؤقتاً" rtl>
                      يحق لكاسب إيقاف الصرف مؤقتاً متى أوجب القانون ذلك، أو كان ثمة نزاع قائم، أو اشتباه
                      باحتيال، أو عدم اكتمال التحقق من هوية المستفيد.
                    </Sub>
                  </>
                }
              />
            </section>

            {/* 10. Refunds */}
            <section id="10" className="scroll-mt-24">
              <SectionHeader num="10" en="Refunds" ar="المبالغ المستردة" />
              <Bilingual
                en={
                  <p>
                    Refund eligibility, timelines, procedure, and allocation of transaction fees are
                    governed by the separate <Link href="/refunds" className="text-brand-500 hover:underline">Refund Policy</Link>,
                    which forms an integral part of these Terms. Because Qi Card does not currently expose a
                    refund API, approved refunds are processed manually through the Qi Card merchant portal.
                  </p>
                }
                ar={
                  <p>
                    تخضع أحقية الاسترداد ومُدده وإجراءاته وتوزيع رسوم المعاملة لـ
                    <Link href="/refunds" className="text-brand-500 hover:underline">سياسة الاسترداد</Link>
                    المنفصلة التي تُشكِّل جزءاً لا يتجزأ من هذه الشروط. ولأن كي كارد لا تُتيح حالياً
                    واجهة برمجية للاسترداد، فإن المبالغ المُعتمَدة تُنفَّذ يدوياً عبر بوابة التاجر.
                  </p>
                }
              />
            </section>

            {/* 11. Disputes */}
            <section id="11" className="scroll-mt-24">
              <SectionHeader num="11" en="Disputes" ar="النزاعات" />
              <Bilingual
                en={
                  <>
                    <p>
                      Either party may raise a dispute regarding an Order at any time while Escrow is in the
                      <em> funded</em> or <em>delivered</em> state, and in any event before the Order is
                      completed or auto-completed. When a dispute is raised, Escrow is frozen until the
                      dispute is resolved.
                    </p>
                    <p className="mt-3">The procedure is:</p>
                    <ol className="list-decimal ms-6 mt-2 space-y-1.5">
                      <li>Direct negotiation between the parties, in good faith, through the Platform&apos;s order conversation.</li>
                      <li>If unresolved within a reasonable period, a Kaasb administrator reviews the order, deliverables, messages, and evidence.</li>
                      <li>The administrator decides whether Escrow is released, refunded, or split between the parties.</li>
                      <li>If either party is dissatisfied with the administrative decision, the party may pursue remedies before the competent Iraqi court under Section 22.</li>
                    </ol>
                    <p className="mt-3">
                      Administrative decisions are made in a neutral, good-faith capacity on the basis of the
                      information available, and are not arbitration awards.
                    </p>
                  </>
                }
                ar={
                  <>
                    <p>
                      يحق لأي من الطرفين إثارة نزاع بشأن طلبٍ ما في أي وقتٍ يكون فيه الضمان في حالة
                      <em> مُموَّل</em> أو <em>مُسلَّم</em>، وعلى أي حالٍ قبل اكتمال الطلب أو إكماله
                      تلقائياً. ويُجَمَّد الضمان عند إثارة النزاع حتى البت فيه.
                    </p>
                    <p className="mt-3">ويجري الإجراء على النحو الآتي:</p>
                    <ol className="list-decimal me-6 mt-2 space-y-1.5">
                      <li>تفاوض مباشر بين الطرفين بحسن نيّة عبر محادثة الطلب داخل المنصة.</li>
                      <li>إن لم يُسوَّ النزاع خلال مدة معقولة، يُراجع إداري كاسب الطلب والتسليمات والمراسلات والأدلة.</li>
                      <li>يقرر الإداري الإفراج عن الضمان أو استرداده أو تقسيمه بين الطرفين.</li>
                      <li>إن لم يقتنع أي طرف بالقرار الإداري، جاز له اللجوء إلى المحكمة العراقية المختصة وفق البند ٢٢.</li>
                    </ol>
                    <p className="mt-3">
                      تُتَّخذ القرارات الإدارية بصفة محايدة وبحسن نيّة استناداً إلى المعلومات المتاحة،
                      ولا تُعدّ أحكام تحكيم.
                    </p>
                  </>
                }
              />
            </section>

            {/* 12. Prohibited conduct */}
            <section id="12" className="scroll-mt-24">
              <SectionHeader num="12" en="Prohibited Conduct" ar="السلوك المحظور" />
              <Bilingual
                en={
                  <>
                    <p>You must not, and must not attempt to:</p>
                    <ul className="list-disc ms-6 mt-3 space-y-1.5">
                      <li><strong>Off-Platform solicitation.</strong> Solicit, request, offer, or share contact information (phone numbers, email addresses, social-media handles, external messaging-app identifiers, payment details) in order to move the transaction off the Platform.</li>
                      <li><strong>Fee circumvention.</strong> Agree to, suggest, or facilitate any arrangement designed to avoid the Platform Fee.</li>
                      <li><strong>Fraud & misrepresentation.</strong> Post false, misleading, plagiarised, or AI-generated content passed off as original human work in breach of Gig description.</li>
                      <li><strong>Harassment.</strong> Harass, threaten, defame, or sexually solicit any User or Kaasb employee.</li>
                      <li><strong>Unlawful content.</strong> Offer or request services or content that are unlawful in Iraq, infringe intellectual property, or violate third-party rights.</li>
                      <li><strong>Account abuse.</strong> Create multiple accounts, buy or sell accounts, manipulate reviews or rankings, or share an account with others.</li>
                      <li><strong>Interference.</strong> Upload malicious code, probe infrastructure, scrape Platform data, or bypass technical access controls.</li>
                      <li><strong>Impersonation.</strong> Misrepresent your identity, role, qualifications, or affiliation with any person or entity.</li>
                      <li><strong>Sanctions evasion / AML.</strong> Use the Platform to evade international sanctions, launder proceeds of crime, or finance terrorism.</li>
                    </ul>
                    <p className="mt-3">
                      Automated detection of off-Platform solicitation or fee-circumvention attempts in
                      messages follows a <strong>three-stage escalation</strong>:
                    </p>
                    <ol className="list-decimal ms-6 mt-2 space-y-1.5">
                      <li>First detected instance — the message is blocked and the User receives a written warning.</li>
                      <li>Second instance — the message is blocked and the User&apos;s messaging is temporarily suspended for twenty-four (24) hours.</li>
                      <li>Third instance — the matter is escalated for potential account suspension and forfeiture of pending payouts.</li>
                    </ol>
                    <p className="mt-3">
                      The full anti-off-Platform rules, reporting channels, and appeal procedure are set out
                      in the <Link href="/acceptable-use" className="text-brand-500 hover:underline">Acceptable Use Policy</Link>.
                    </p>
                  </>
                }
                ar={
                  <>
                    <p>يُحظَر عليك الآتي، ومحاولة الآتي:</p>
                    <ul className="list-disc me-6 mt-3 space-y-1.5">
                      <li><strong>السعي للتعامل خارج المنصة.</strong> طلب أو عرض أو تبادل وسائل الاتصال (أرقام هاتف، بريد إلكتروني، حسابات تواصل اجتماعي، معرفات تطبيقات مراسلة خارجية، تفاصيل دفع) بقصد نقل المعاملة خارج المنصة.</li>
                      <li><strong>التحايل على الرسوم.</strong> الاتفاق على أي ترتيبٍ يهدف إلى تجاوز رسوم المنصة أو تسهيله أو اقتراحه.</li>
                      <li><strong>الاحتيال والتضليل.</strong> نشر محتوى كاذب أو مضلِّل أو منتحَل أو مُولَّد بالذكاء الاصطناعي يُقدَّم بوصفه عملاً أصلياً بما يخالف وصف الخدمة.</li>
                      <li><strong>المضايقة.</strong> مضايقة أي مستخدم أو موظف كاسب أو تهديده أو التشهير به أو مراودته جنسياً.</li>
                      <li><strong>المحتوى غير المشروع.</strong> عرض أو طلب خدمات أو محتوى تخالف القانون العراقي أو تتعدى على حقوق الملكية الفكرية أو حقوق الغير.</li>
                      <li><strong>إساءة استخدام الحساب.</strong> إنشاء حسابات متعددة، أو بيع/شراء حسابات، أو التلاعب بالتقييمات أو التصنيف، أو مشاركة الحساب.</li>
                      <li><strong>التدخل التقني.</strong> رفع رموز ضارة أو استكشاف البنية التحتية أو كشط بيانات المنصة أو تجاوز الضوابط التقنية.</li>
                      <li><strong>انتحال الهوية.</strong> إيهامٌ غير صحيح بشأن هويتك أو دورك أو مؤهلاتك أو ارتباطك بأي شخص أو جهة.</li>
                      <li><strong>التهرب من العقوبات وغسل الأموال.</strong> استخدام المنصة للتهرب من عقوبات دولية أو غسل متحصلات جريمة أو تمويل إرهاب.</li>
                    </ul>
                    <p className="mt-3">
                      ويتدرج الكشف الآلي لمحاولات الخروج من المنصة أو التحايل على الرسوم في المراسلات عبر
                      <strong> ثلاث مراحل</strong>:
                    </p>
                    <ol className="list-decimal me-6 mt-2 space-y-1.5">
                      <li>المرة الأولى — تُحجب الرسالة ويتلقى المستخدم تنبيهاً كتابياً.</li>
                      <li>المرة الثانية — تُحجب الرسالة وتُعلَّق المراسلة مدة أربعٍ وعشرين (٢٤) ساعة.</li>
                      <li>المرة الثالثة — يُحال الأمر للنظر في تعليق الحساب ومصادرة الصرف المُعلَّق.</li>
                    </ol>
                    <p className="mt-3">
                      تُبيَّن القواعد الكاملة للحظر خارج المنصة وقنوات الإبلاغ وإجراء التظلم في{" "}
                      <Link href="/acceptable-use" className="text-brand-500 hover:underline">سياسة الاستخدام المقبول</Link>.
                    </p>
                  </>
                }
              />
            </section>

            {/* 13. Seller levels */}
            <section id="13" className="scroll-mt-24">
              <SectionHeader num="13" en="Seller Levels" ar="مستويات البائعين" />
              <Bilingual
                en={
                  <>
                    <p>
                      Kaasb operates a Seller Level programme (New Seller, Level 1, Level 2, Top Rated)
                      intended to signal quality to Buyers and to unlock additional features for Sellers.
                      Levels are recalculated periodically based on objective criteria including completed
                      orders, average rating, on-time delivery rate, response rate, and rule violations.
                    </p>
                    <p className="mt-3">
                      Levels may be downgraded or revoked if the qualifying criteria are no longer met, if a
                      rule violation is recorded, or if fraud is detected. A Seller may appeal a level
                      decision by writing to{" "}
                      <a href={`mailto:${EMAIL_SUPPORT}`} className="text-brand-500 hover:underline">{EMAIL_SUPPORT}</a>{" "}
                      within fourteen (14) days of the level change. Level status does not create any vested
                      right or guarantee of continued benefits.
                    </p>
                  </>
                }
                ar={
                  <>
                    <p>
                      تُشَغِّل كاسب برنامج «مستويات البائعين» (بائع جديد، المستوى الأول، المستوى الثاني،
                      الأعلى تقييماً) للدلالة على الجودة للمشترين ولإتاحة خصائص إضافية للبائعين.
                      وتُحتسب المستويات دورياً استناداً إلى معايير موضوعية تشمل الطلبات المكتملة، ومتوسط
                      التقييم، ومعدل التسليم في الوقت، ومعدل الاستجابة، ومخالفات القواعد.
                    </p>
                    <p className="mt-3">
                      يجوز تخفيض المستوى أو سحبه عند عدم استيفاء المعايير أو تسجيل مخالفة أو اكتشاف
                      احتيال. ويحق للبائع التظلم بالكتابة إلى{" "}
                      <a href={`mailto:${EMAIL_SUPPORT}`} className="text-brand-500 hover:underline">{EMAIL_SUPPORT}</a>{" "}
                      خلال أربعة عشر (١٤) يوماً من تغيير المستوى. ولا يُنشئ المستوى حقاً مكتسباً ولا ضماناً
                      باستمرار المزايا.
                    </p>
                  </>
                }
              />
            </section>

            {/* 14. IP */}
            <section id="14" className="scroll-mt-24">
              <SectionHeader num="14" en="Intellectual Property" ar="الملكية الفكرية" />
              <Bilingual
                en={
                  <>
                    <Sub num="14.1" title="Platform IP">
                      All software, design, trademarks, logos, text, and compilations comprising the Platform
                      are the property of Kaasb or its licensors, protected by Iraqi Law No. 65 of 1976 on
                      Trademarks and by international copyright treaties.
                    </Sub>
                    <Sub num="14.2" title="Deliverables">
                      Upon full payment (i.e. release of Escrow for the relevant Order or Milestone), and
                      unless the parties agree otherwise in writing, all rights in the deliverables,
                      including copyright, transfer from the Seller to the Buyer. Stock assets, pre-existing
                      libraries, and tools used to create the deliverable remain the property of their
                      original owners and are licensed to the Buyer only to the extent necessary to exploit
                      the deliverable as agreed.
                    </Sub>
                    <Sub num="14.3" title="IP takedown notices">
                      If you believe content on the Platform infringes your intellectual-property rights,
                      send a written notice to{" "}
                      <a href={`mailto:${EMAIL_LEGAL}`} className="text-brand-500 hover:underline">{EMAIL_LEGAL}</a>{" "}
                      identifying the infringing content (URL), the right asserted, proof of ownership, your
                      contact details, and a good-faith statement. Kaasb will review and, where appropriate,
                      remove or disable the content and notify the uploader, who may file a counter-notice.
                      Repeat infringers will have their accounts terminated.
                    </Sub>
                  </>
                }
                ar={
                  <>
                    <Sub num="١٤.١" title="ملكية المنصة" rtl>
                      تخصّ كاسبَ أو مرخِّصيها جميعُ البرمجيات والتصميمات والعلامات التجارية والشعارات
                      والنصوص والتجميعات المُكوِّنة للمنصة، وهي محميةٌ بالقانون العراقي رقم ٦٥ لسنة ١٩٧٦
                      بشأن العلامات التجارية، وبالاتفاقيات الدولية لحقوق المؤلف.
                    </Sub>
                    <Sub num="١٤.٢" title="التسليمات" rtl>
                      عند إتمام الدفع كاملاً (أي إفراج الضمان للطلب أو المعلم المعني)، وما لم يتفق الطرفان
                      كتابةً على خلاف ذلك، تنتقل جميع الحقوق في التسليمات، بما فيها حق المؤلف، من البائع
                      إلى المشتري. وتبقى الأصول الجاهزة والمكتبات السابقة والأدوات المُستخدَمة ملكاً
                      لأصحابها، ويُرخَّص للمشتري بها بالقدر اللازم لاستغلال التسليم وفق المتفق عليه.
                    </Sub>
                    <Sub num="١٤.٣" title="إخطارات إزالة الانتهاك" rtl>
                      إن رأيت أن محتوى على المنصة ينتهك حقوق ملكيتك الفكرية، أرسل إخطاراً كتابياً إلى{" "}
                      <a href={`mailto:${EMAIL_LEGAL}`} className="text-brand-500 hover:underline">{EMAIL_LEGAL}</a>{" "}
                      يتضمن تحديد المحتوى المُدَّعى بانتهاكه (الرابط)، والحق المحتج به، وما يُثبت الملكية،
                      وبيانات التواصل، وتصريحاً بحسن النيّة. وستراجع كاسب الإخطار وتزيل المحتوى أو تُعَطِّله
                      عند الاقتضاء، وتُخطر الطرف المُحَمِّل الذي يحق له تقديم إخطار مضاد. ويُنهى حساب
                      المخالف المتكرر.
                    </Sub>
                  </>
                }
              />
            </section>

            {/* 15. User content licence */}
            <section id="15" className="scroll-mt-24">
              <SectionHeader num="15" en="User Content Licence" ar="ترخيص محتوى المستخدم" />
              <Bilingual
                en={
                  <p>
                    You retain ownership of the content you upload or publish on the Platform (profile copy,
                    Gig descriptions, portfolio samples, messages, reviews, and delivery files, together
                    &quot;User Content&quot;). You grant Kaasb a non-exclusive, royalty-free, worldwide licence to
                    host, reproduce, display, and adapt your User Content solely to the extent necessary to
                    operate, promote, and improve the Platform. This licence terminates when you delete the
                    relevant content, except where retention is required by these Terms, by law, or to
                    preserve evidence in an open dispute.
                  </p>
                }
                ar={
                  <p>
                    تحتفظ بملكية المحتوى الذي ترفعه أو تنشره على المنصة (نبذة الملف، وصف الخدمات، أعمال
                    سابقة، رسائل، تقييمات، ملفات تسليم — يُشار إليه مجتمعاً بـ«محتوى المستخدم»). وتمنح
                    كاسبَ ترخيصاً غير حصري ومجاني وعالمياً لاستضافة محتوى المستخدم ونَسخِه وعرضِه
                    وتكييفِه بالقدر اللازم لتشغيل المنصة والترويج لها وتحسينها. ويُنهى هذا الترخيص بحذفك
                    للمحتوى المعني، باستثناء حالات الاحتفاظ الإلزامي بموجب هذه الشروط أو القانون أو حفظ
                    الأدلة في نزاعٍ قائم.
                  </p>
                }
              />
            </section>

            {/* 16. Reviews */}
            <section id="16" className="scroll-mt-24">
              <SectionHeader num="16" en="Reviews" ar="التقييمات" />
              <Bilingual
                en={
                  <>
                    <p>
                      Reviews must be honest, based on genuine experience, and posted by the party to the
                      transaction. The following practices are prohibited and will lead to review removal
                      and, where repeated, account action:
                    </p>
                    <ul className="list-disc ms-6 mt-3 space-y-1.5">
                      <li>Self-reviewing via any account you control or influence.</li>
                      <li>Reciprocal-review arrangements (&quot;I&apos;ll give you 5 stars if you give me 5 stars&quot;).</li>
                      <li>Offering or demanding a reward (refund, discount, bonus) in exchange for a specific rating.</li>
                      <li>Publishing defamatory, threatening, sexually explicit, or discriminatory content.</li>
                      <li>Disclosing confidential project details contrary to a written agreement.</li>
                    </ul>
                    <p className="mt-3">
                      Kaasb may remove reviews that breach these rules. Kaasb does not edit the substantive
                      content of reviews that comply with these rules, even if a party disagrees with them.
                    </p>
                  </>
                }
                ar={
                  <>
                    <p>
                      يجب أن تكون التقييمات صادقةً ومبنيةً على تجربة فعلية ومُدَوَّنة من طرفٍ في المعاملة.
                      وتُحظَر الممارسات الآتية ويؤدي ذلك إلى إزالة التقييم، ومع التكرار، لإجراءٍ على
                      الحساب:
                    </p>
                    <ul className="list-disc me-6 mt-3 space-y-1.5">
                      <li>التقييم الذاتي عبر أي حساب تملكه أو تؤثر فيه.</li>
                      <li>ترتيبات التقييم المتبادل («أعطني خمس نجوم وأعطيك خمس نجوم»).</li>
                      <li>عرض أو طلب مقابلٍ (استرداد، خصم، مكافأة) في مقابل تقييمٍ بعينه.</li>
                      <li>نشر محتوى تشهيري أو تهديدي أو صريح جنسياً أو تمييزي.</li>
                      <li>الإفصاح عن تفاصيل سرية للمشروع بما يخالف اتفاقاً كتابياً.</li>
                    </ul>
                    <p className="mt-3">
                      يجوز لكاسب إزالة التقييمات المخالفة. ولا تُعدِّل كاسب المحتوى الموضوعي للتقييمات
                      المستوفية لهذه القواعد حتى وإن اعترض عليها أحد الطرفين.
                    </p>
                  </>
                }
              />
            </section>

            {/* 17. Moderation */}
            <section id="17" className="scroll-mt-24">
              <SectionHeader num="17" en="Content Moderation" ar="مراقبة المحتوى" />
              <Bilingual
                en={
                  <p>
                    Kaasb may review, refuse, edit, or remove any content that it reasonably believes
                    violates these Terms or applicable law, or that is harmful to Users or to Kaasb. Users
                    may report content via the &quot;Report&quot; action on Gigs, Jobs, profiles, and messages.
                    Reports are reviewed within a reasonable period. A decision may be appealed by writing to{" "}
                    <a href={`mailto:${EMAIL_SUPPORT}`} className="text-brand-500 hover:underline">{EMAIL_SUPPORT}</a>.
                  </p>
                }
                ar={
                  <p>
                    يجوز لكاسب مراجعة أي محتوى أو رفضه أو تعديله أو إزالته متى رأت بشكل معقول أنه يخالف
                    هذه الشروط أو القانون الساري أو يُلحق ضرراً بالمستخدمين أو بكاسب. ويمكن للمستخدمين
                    الإبلاغ عبر زر «إبلاغ» في الخدمات والوظائف والملفات الشخصية والرسائل. وتُراجَع
                    البلاغات خلال مدة معقولة، ويجوز التظلم من القرار بالكتابة إلى{" "}
                    <a href={`mailto:${EMAIL_SUPPORT}`} className="text-brand-500 hover:underline">{EMAIL_SUPPORT}</a>.
                  </p>
                }
              />
            </section>

            {/* 18. Suspension */}
            <section id="18" className="scroll-mt-24">
              <SectionHeader num="18" en="Suspension & Termination" ar="التعليق والإنهاء" />
              <Bilingual
                en={
                  <>
                    <Sub num="18.1" title="Termination by User">
                      You may deactivate or delete your account at any time from{" "}
                      <Link href="/dashboard/settings" className="text-brand-500 hover:underline">Account Settings</Link>.
                      Deletion does not release you from obligations in respect of open Orders, unpaid fees,
                      or ongoing disputes, and does not affect retention obligations in Section 9 of the{" "}
                      <Link href="/privacy" className="text-brand-500 hover:underline">Privacy Policy</Link>.
                    </Sub>
                    <Sub num="18.2" title="Termination by Kaasb">
                      Kaasb may suspend or terminate your account, remove content, withhold payouts, and
                      refuse service — with or without prior notice — where you have breached these Terms,
                      engaged in fraud, created a risk to the Platform or other Users, or where required by
                      law.
                    </Sub>
                    <Sub num="18.3" title="Effect on Escrow and pending payouts">
                      On termination:
                      <ul className="list-disc ms-6 mt-2 space-y-1">
                        <li>Funded Escrow on an open Order will either be completed under the normal order workflow, refunded to the Buyer, or resolved by dispute administration as the facts require.</li>
                        <li>Unreleased payouts may be withheld pending investigation and resolution of any claims.</li>
                        <li>Termination for serious breach (fraud, fee circumvention, sanctions evasion) may result in forfeiture of pending Platform Fee balances due to the terminated party, subject to applicable law.</li>
                      </ul>
                    </Sub>
                    <Sub num="18.4" title="Survival">
                      Sections 9 (to the extent of outstanding balances), 10, 14, 15 (to the extent of
                      licence granted prior to deletion), 19, 20, 21, 22, and 27 survive termination.
                    </Sub>
                  </>
                }
                ar={
                  <>
                    <Sub num="١٨.١" title="الإنهاء من المستخدم" rtl>
                      يمكنك تعطيل الحساب أو حذفه في أي وقت من{" "}
                      <Link href="/dashboard/settings" className="text-brand-500 hover:underline">إعدادات الحساب</Link>.
                      ولا يُعفيك الحذف من التزاماتك المتعلقة بالطلبات القائمة أو الرسوم المستحقة أو
                      النزاعات الجارية، ولا يمسّ التزامات الاحتفاظ الواردة في البند ٩ من{" "}
                      <Link href="/privacy" className="text-brand-500 hover:underline">سياسة الخصوصية</Link>.
                    </Sub>
                    <Sub num="١٨.٢" title="الإنهاء من كاسب" rtl>
                      يجوز لكاسب تعليق حسابك أو إنهاؤه، وإزالة المحتوى، وحجز المستحقات، ورفض الخدمة —
                      بإشعارٍ مسبق أو بدونه — في حال إخلالك بهذه الشروط أو ارتكاب احتيال أو تشكيل خطر على
                      المنصة أو المستخدمين، أو حين يستوجب القانون ذلك.
                    </Sub>
                    <Sub num="١٨.٣" title="الأثر على الضمان والمستحقات" rtl>
                      عند الإنهاء:
                      <ul className="list-disc me-6 mt-2 space-y-1">
                        <li>يُعالَج الضمان المُموَّل لطلب قائم إما بإتمام الدورة الطبيعية للطلب، أو ردّه للمشتري، أو البت فيه عبر إدارة النزاعات وفق الوقائع.</li>
                        <li>يجوز حجز المستحقات غير المُفرج عنها ريثما يُحقَّق في أي مطالبات وتُحسم.</li>
                        <li>قد يؤدي الإنهاء بسبب إخلالٍ جسيم (احتيال، تحايل على الرسوم، تهرب من عقوبات) إلى مصادرة أرصدة رسوم المنصة المستحقة للطرف المُنهى، وفقاً للقانون الساري.</li>
                      </ul>
                    </Sub>
                    <Sub num="١٨.٤" title="بقاء الأحكام نافذة" rtl>
                      تبقى البنود ٩ (بقدر الأرصدة القائمة) و١٠ و١٤ و١٥ (بقدر الترخيص الممنوح قبل الحذف)
                      و١٩ و٢٠ و٢١ و٢٢ و٢٧ نافذةً بعد الإنهاء.
                    </Sub>
                  </>
                }
              />
            </section>

            {/* 19. Disclaimers */}
            <section id="19" className="scroll-mt-24">
              <SectionHeader num="19" en="Disclaimers" ar="إخلاء المسؤولية" />
              <Bilingual
                en={
                  <p>
                    To the maximum extent permitted by applicable law, the Platform is provided on an{" "}
                    &quot;as is&quot; and &quot;as available&quot; basis. Kaasb makes no warranty, express or implied, as to
                    the fitness of the Platform for a particular purpose, uninterrupted availability, the
                    accuracy or completeness of Gig listings or Proposals, or the outcome of any Contract
                    between Users. Kaasb does not verify the skills, qualifications, or credentials asserted
                    by Users beyond the identity and payment checks described on the Platform.
                  </p>
                }
                ar={
                  <p>
                    إلى أقصى حدٍّ يُجيزه القانون الساري، تُقدَّم المنصة «كما هي» و«حسب التوافر». ولا تُقدِّم
                    كاسب أي ضمانٍ صريح أو ضمني بشأن ملاءمة المنصة لغرضٍ بعينه، أو استمرار إتاحتها، أو
                    دقة واكتمال قوائم الخدمات والعروض، أو نتائج أي عقدٍ بين المستخدمين. ولا تتحقق كاسب
                    من المهارات والمؤهلات والاعتمادات التي يدّعيها المستخدمون بما يتجاوز فحوصات الهوية
                    والدفع المُبيَّنة على المنصة.
                  </p>
                }
              />
            </section>

            {/* 20. Limitation */}
            <section id="20" className="scroll-mt-24">
              <SectionHeader num="20" en="Limitation of Liability" ar="حدود المسؤولية" />
              <Bilingual
                en={
                  <>
                    <p>
                      To the maximum extent permitted by applicable law, Kaasb and its officers, employees,
                      and contractors shall not be liable for:
                    </p>
                    <ul className="list-disc ms-6 mt-3 space-y-1.5">
                      <li>Indirect, incidental, special, consequential, or punitive damages, including lost profit, lost data, or reputational harm.</li>
                      <li>The acts or omissions of Buyers or Sellers, or the performance or non-performance of any Contract between Users.</li>
                      <li>Losses arising from third-party payment-processor failures, communications outages, or force-majeure events under Section 23.</li>
                      <li>Temporary Platform unavailability due to maintenance, deployment, or technical incidents.</li>
                    </ul>
                    <p className="mt-3">
                      Kaasb&apos;s aggregate liability to you arising from or in connection with the Platform
                      shall not exceed the greater of (a) the Platform Fees actually received by Kaasb from
                      you in the twelve (12) months preceding the event giving rise to liability, or (b) one
                      hundred thousand Iraqi Dinars (100,000 IQD).
                    </p>
                    <p className="mt-3">
                      Nothing in this Section limits or excludes liability that cannot be limited or
                      excluded under mandatory Iraqi law, including liability for fraud or for harm caused
                      intentionally or by gross negligence.
                    </p>
                  </>
                }
                ar={
                  <>
                    <p>
                      إلى أقصى حدٍّ يُجيزه القانون الساري، لا تُسأل كاسب ومسؤولوها وموظفوها والمتعاقدون
                      معها عن:
                    </p>
                    <ul className="list-disc me-6 mt-3 space-y-1.5">
                      <li>الأضرار غير المباشرة أو العَرَضية أو الخاصة أو التبعية أو العقابية، بما فيها فوات الربح وفقدان البيانات والضرر بالسُّمعة.</li>
                      <li>أفعال أو امتناع المشترين أو البائعين، أو تنفيذ أي عقد بين المستخدمين أو عدم تنفيذه.</li>
                      <li>الخسائر الناشئة عن إخفاقات أطراف الدفع الخارجية، أو انقطاعات الاتصالات، أو أحداث القوة القاهرة وفق البند ٢٣.</li>
                      <li>عدم إتاحة المنصة مؤقتاً بسبب الصيانة أو النشر أو حوادث تقنية.</li>
                    </ul>
                    <p className="mt-3">
                      لا تتجاوز مسؤولية كاسب الإجمالية تجاهك الناشئة عن المنصة أو المرتبطة بها أكبر
                      القيمتين التاليتين: (أ) رسوم المنصة التي استلمتها كاسب فعلاً منك في الاثني عشر (١٢)
                      شهراً السابقة على الحدث المنشئ للمسؤولية، أو (ب) مئة ألف دينار عراقي (١٠٠٫٠٠٠ د.ع.).
                    </p>
                    <p className="mt-3">
                      لا يحدّ هذا البند من المسؤوليات التي لا يجوز حدُّها أو استبعادها بمقتضى القانون
                      العراقي الآمر، بما فيها المسؤولية عن الغش أو الضرر المتعمَّد أو الخطأ الجسيم.
                    </p>
                  </>
                }
              />
            </section>

            {/* 21. Indemnification */}
            <section id="21" className="scroll-mt-24">
              <SectionHeader num="21" en="Indemnification" ar="التعويض" />
              <Bilingual
                en={
                  <p>
                    You agree to indemnify and hold harmless Kaasb and its officers, employees, and
                    contractors against any third-party claim, liability, loss, or cost (including
                    reasonable legal fees) arising from (a) your breach of these Terms; (b) content you
                    upload, post, or transmit through the Platform; (c) your violation of applicable law;
                    or (d) the services you deliver or commission through the Platform. Kaasb will notify
                    you promptly of any such claim and may, at its option, participate in the defence.
                  </p>
                }
                ar={
                  <p>
                    تلتزم بتعويض كاسب ومسؤوليها وموظفيها والمتعاقدين معها وإبقائهم في مأمنٍ عن أي
                    مطالبةٍ أو مسؤوليةٍ أو خسارةٍ أو تكلفةٍ (بما فيها الأتعاب القانونية المعقولة) تنشأ عن
                    (أ) إخلالك بهذه الشروط، أو (ب) المحتوى الذي ترفعه أو تنشره أو تُرسله عبر المنصة، أو
                    (ج) مخالفتك للقانون الساري، أو (د) الخدمات التي تُقدِّمها أو تطلبها عبر المنصة. وستُخطرك
                    كاسب بأي مطالبة فور ورودها، ولها أن تشارك في الدفاع بخيارها.
                  </p>
                }
              />
            </section>

            {/* 22. Governing law */}
            <section id="22" className="scroll-mt-24">
              <SectionHeader num="22" en="Governing Law & Venue" ar="القانون الحاكم والاختصاص" />
              <Bilingual
                en={
                  <p>
                    These Terms are governed by the laws of the Republic of Iraq, without regard to
                    conflict-of-laws principles. Any dispute arising from or in connection with these Terms
                    that is not resolved through the procedure in Section 11 shall be submitted exclusively
                    to the competent First Instance Court of Baghdad / Karkh. The language of proceedings
                    shall be Arabic.
                  </p>
                }
                ar={
                  <p>
                    تخضع هذه الشروط لقوانين جمهورية العراق، دون اعتبارٍ لقواعد تنازع القوانين. ويُعرض أي
                    نزاع ينشأ عن هذه الشروط أو يتصل بها ولم يُحسم وفق إجراء البند ١١ حصراً أمام محكمة
                    البداءة المختصة في بغداد/الكرخ. وتكون لغة الإجراءات هي العربية.
                  </p>
                }
              />
            </section>

            {/* 23. Force majeure */}
            <section id="23" className="scroll-mt-24">
              <SectionHeader num="23" en="Force Majeure" ar="القوة القاهرة" />
              <Bilingual
                en={
                  <p>
                    Neither party shall be liable for failure or delay in performance caused by events
                    beyond its reasonable control, including acts of war or armed conflict, civil unrest,
                    government action, epidemic or pandemic, natural disaster, power or internet outage,
                    failure of the Qi Card network, or cybersecurity attacks not attributable to its own
                    negligence. The affected party shall use reasonable efforts to mitigate and shall notify
                    the other party as soon as reasonably practicable.
                  </p>
                }
                ar={
                  <p>
                    لا يُسأل أي طرف عن عدم التنفيذ أو تأخره بسبب أحداث خارجة عن إرادته المعقولة، كالحرب
                    أو النزاع المسلح، أو الاضطرابات الأهلية، أو الإجراءات الحكومية، أو الأوبئة، أو الكوارث
                    الطبيعية، أو انقطاع الكهرباء أو الإنترنت، أو تعطل شبكة كي كارد، أو الهجمات السيبرانية
                    غير العائدة لإهمالٍ منه. ويبذل الطرف المتأثر جهداً معقولاً للحدّ من الأثر، ويُخطر
                    الطرف الآخر في أقرب وقتٍ معقولٍ عملياً.
                  </p>
                }
              />
            </section>

            {/* 24. General provisions */}
            <section id="24" className="scroll-mt-24">
              <SectionHeader num="24" en="General Provisions" ar="أحكام عامة" />
              <Bilingual
                en={
                  <ul className="list-disc ms-6 space-y-1.5">
                    <li><strong>Entire agreement.</strong> These Terms, together with the Privacy Policy, Cookie Policy, Refund Policy, and Acceptable Use Policy, constitute the entire agreement between you and Kaasb in respect of the Platform.</li>
                    <li><strong>Severability.</strong> If a provision is held invalid or unenforceable, the remaining provisions continue in full force and the invalid provision shall be interpreted to achieve its intended commercial purpose to the extent permitted by law.</li>
                    <li><strong>No waiver.</strong> A failure or delay by Kaasb to enforce a provision is not a waiver of its right to do so later.</li>
                    <li><strong>Assignment.</strong> You may not assign these Terms without our prior written consent. Kaasb may assign these Terms in connection with a merger, acquisition, reorganisation, or sale of assets, on notice to you.</li>
                    <li><strong>Relationship.</strong> No partnership, joint venture, agency, or employment relationship is created by these Terms.</li>
                    <li><strong>Electronic notices.</strong> You consent to receiving communications from Kaasb in electronic form.</li>
                  </ul>
                }
                ar={
                  <ul className="list-disc me-6 space-y-1.5">
                    <li><strong>الاتفاق الكامل.</strong> تُكوِّن هذه الشروط مع سياسة الخصوصية وسياسة ملفات الارتباط وسياسة الاسترداد وسياسة الاستخدام المقبول الاتفاق الكامل بينك وبين كاسب بشأن المنصة.</li>
                    <li><strong>قابلية الفصل.</strong> إذا بطل بندٌ أو تعذر تنفيذه، تظل بقية البنود نافذة، ويُؤَوَّل البند الباطل بحيث يحقق غرضه التجاري إلى أقصى مدى يجيزه القانون.</li>
                    <li><strong>عدم التنازل.</strong> لا يُعدّ تأخر كاسب في إنفاذ بندٍ أو إحجامها عنه تنازلاً عن حقها في إنفاذه لاحقاً.</li>
                    <li><strong>التنازل والإحالة.</strong> لا يجوز لك التنازل عن هذه الشروط دون موافقتنا الكتابية المسبقة. ويحق لكاسب التنازل عنها بمناسبة اندماج أو استحواذ أو إعادة تنظيم أو بيع أصول، مع إخطارك.</li>
                    <li><strong>طبيعة العلاقة.</strong> لا تُنشئ هذه الشروط شراكةً أو مشروعاً مشتركاً أو وكالةً أو علاقة استخدام.</li>
                    <li><strong>الإخطارات الإلكترونية.</strong> توافق على تلقي المراسلات من كاسب بالشكل الإلكتروني.</li>
                  </ul>
                }
              />
            </section>

            {/* 25. Changes */}
            <section id="25" className="scroll-mt-24">
              <SectionHeader num="25" en="Changes to Terms" ar="تعديل الشروط" />
              <Bilingual
                en={
                  <p>
                    We may amend these Terms from time to time. Non-material changes (clarifications, typo
                    corrections, reformatting) are effective upon publication. Material changes — affecting
                    fees, dispute procedures, liability, or User rights — will be notified at least thirty
                    (30) days in advance through email and in-Platform notification. Continued use of the
                    Platform after the effective date of a change constitutes acceptance.
                  </p>
                }
                ar={
                  <p>
                    يحق لنا تعديل هذه الشروط من حينٍ لآخر. وتسري التعديلات غير الجوهرية (توضيحات، تصحيحات
                    إملائية، إعادة تنسيق) فور نشرها. أما التعديلات الجوهرية — التي تمسّ الرسوم أو
                    إجراءات النزاع أو المسؤولية أو حقوق المستخدم — فيُخطَر بها قبل سريانها بثلاثين (٣٠)
                    يوماً على الأقل عبر البريد الإلكتروني وإشعار داخل المنصة. ويُعدّ استمرارك في استخدام
                    المنصة بعد تاريخ نفاذ التعديل قبولاً له.
                  </p>
                }
              />
            </section>

            {/* 26. Contact */}
            <section id="26" className="scroll-mt-24">
              <SectionHeader num="26" en="Contact & Legal Notices" ar="التواصل والإخطارات القانونية" />
              <Bilingual
                en={
                  <>
                    <p>
                      Legal notices to Kaasb must be sent in writing to{" "}
                      <a href={`mailto:${EMAIL_LEGAL}`} className="text-brand-500 hover:underline">{EMAIL_LEGAL}</a>.
                      Notices by telephone are accepted only to follow up on a prior written notice.
                    </p>
                    <address className="not-italic mt-3 space-y-1">
                      <div><strong>{COMPANY_EN}</strong></div>
                      <div>Republic of Iraq</div>
                      <div>Legal: <a href={`mailto:${EMAIL_LEGAL}`} className="text-brand-500 hover:underline">{EMAIL_LEGAL}</a></div>
                      <div>Support: <a href={`mailto:${EMAIL_SUPPORT}`} className="text-brand-500 hover:underline">{EMAIL_SUPPORT}</a></div>
                    </address>
                  </>
                }
                ar={
                  <>
                    <p>
                      تُرسَل الإخطارات القانونية إلى كاسب كتابةً على{" "}
                      <a href={`mailto:${EMAIL_LEGAL}`} className="text-brand-500 hover:underline">{EMAIL_LEGAL}</a>.
                      ولا تُقبل الإخطارات الهاتفية إلا لمتابعة إخطار كتابي سابق.
                    </p>
                    <address className="not-italic mt-3 space-y-1">
                      <div><strong>{COMPANY_AR}</strong></div>
                      <div>جمهورية العراق</div>
                      <div>الشؤون القانونية: <a href={`mailto:${EMAIL_LEGAL}`} className="text-brand-500 hover:underline">{EMAIL_LEGAL}</a></div>
                      <div>الدعم: <a href={`mailto:${EMAIL_SUPPORT}`} className="text-brand-500 hover:underline">{EMAIL_SUPPORT}</a></div>
                    </address>
                  </>
                }
              />
            </section>

            {/* 27. Precedence */}
            <section id="27" className="scroll-mt-24">
              <SectionHeader num="27" en="Language Precedence" ar="الأسبقية اللغوية" />
              <Bilingual
                en={
                  <p>
                    These Terms are published in Arabic and English. In the event of any conflict,
                    discrepancy, or ambiguity between the two versions, the <strong>Arabic version</strong> shall
                    prevail, consistent with Article 14 of the Iraqi Civil Code and the customary rule of
                    Iraqi courts.
                  </p>
                }
                ar={
                  <p>
                    صدرت هذه الشروط باللغتين العربية والإنجليزية. وفي حال وجود أي تعارض أو اختلاف أو
                    غموض بين النُسختين، تُعتمد <strong>النسخة العربية</strong>، وفقاً لأحكام المادة ١٤ من
                    القانون المدني العراقي والعُرف القضائي العراقي.
                  </p>
                }
              />
            </section>

            <div className="border-t border-gray-200 pt-6 flex flex-wrap gap-4 text-sm text-gray-500">
              <Link href="/privacy" className="hover:text-gray-700 hover:underline">Privacy Policy</Link>
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

// Shared helpers kept in-file to avoid a new module.
function SectionHeader({ num, en, ar }: { num: string; en: string; ar: string }) {
  return (
    <header className="mb-5 pb-3 border-b border-gray-200">
      <h2 data-legal-lang="en" dir="ltr" className="text-xl font-semibold text-gray-900 text-left">
        <span className="font-mono text-sm text-gray-400 me-2">{num}.</span>{en}
      </h2>
      <h3 data-legal-lang="ar" className="mt-1 text-lg font-semibold text-gray-700 text-right" dir="rtl">
        <span className="font-mono text-sm text-gray-400 ms-2">{toArabicNumerals(num)}.</span>{ar}
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
function Sub({ num, title, rtl, children }: { num: string; title: string; rtl?: boolean; children: React.ReactNode }) {
  return (
    <div>
      <h4 className={`font-semibold text-gray-900 ${rtl ? "text-right" : ""}`} dir={rtl ? "rtl" : "ltr"}>
        <span className="font-mono text-xs text-gray-400 me-1">{num}</span>{title}
      </h4>
      <div className="mt-1 text-gray-700 leading-relaxed" dir={rtl ? "rtl" : "ltr"}>{children}</div>
    </div>
  );
}
function toArabicNumerals(s: string): string {
  const map: Record<string, string> = { "0": "٠", "1": "١", "2": "٢", "3": "٣", "4": "٤", "5": "٥", "6": "٦", "7": "٧", "8": "٨", "9": "٩" };
  return s.replace(/[0-9]/g, (d) => map[d]);
}
