# Support Response Macros

Eight canonical bilingual (AR + EN) templates admins use to answer common support tickets. These are **starting points** — customize with the user's name, order ID, or transaction reference before sending. Don't copy-paste verbatim; every user deserves a reply that feels written for them.

Last updated: 2026-04-24. Maintainer: Mustafa Alrasheed. Companion to [support-runbook.md](./support-runbook.md).

---

## How to use these

- **Always open with the user's name.** Hello {name} / مرحباً {name}.
- **Match the user's language.** If they wrote in Arabic, reply in Arabic. If mixed, pick the dominant language.
- **Cite specifics.** Replace `{placeholders}` with the real values — order ID, transaction ref, timestamp, etc.
- **Promise only what's already done or inside our SLA.** Never invent a timeline.
- **Sign off** as the admin (use first name, not "Support Team" — feels personal).

---

## Macro 1 — Account verification not working (OTP not received)

**English:**
> Hi {name},
>
> I'm sorry the verification code didn't reach you. Kaasb sends OTP codes in this order: WhatsApp → SMS → email. Please check:
>
> 1. **WhatsApp** — look for a message from Kaasb on the phone number tied to your account ({phone}).
> 2. **SMS inbox** on that same phone.
> 3. **Email inbox** + spam folder for an email from `noreply@kaasb.com`.
>
> If you're outside Iraq, SMS may not deliver — the email fallback will. Codes expire after 10 minutes; if none of the above worked, wait 60 seconds and request a new code from the login page.
>
> Let me know if you still can't get in after that and I'll manually verify your phone.
>
> — {admin_name}

**Arabic:**
> مرحباً {name},
>
> آسف لعدم وصول رمز التحقق. يرسل كاسب الرموز بالترتيب التالي: واتساب ← رسالة نصية ← بريد إلكتروني. يُرجى التحقق من:
>
> 1. **واتساب** — ابحث عن رسالة من كاسب على الرقم المرتبط بحسابك ({phone}).
> 2. **صندوق الرسائل النصية** على نفس الهاتف.
> 3. **صندوق البريد الإلكتروني** + مجلد الرسائل غير المرغوبة للبحث عن بريد من `noreply@kaasb.com`.
>
> إذا كنت خارج العراق، قد لا تصل الرسائل النصية — سيصل البريد كبديل. تنتهي صلاحية الرموز بعد ١٠ دقائق؛ إذا لم ينجح شيء، انتظر ٦٠ ثانية واطلب رمزاً جديداً من صفحة تسجيل الدخول.
>
> أخبرني إذا بقيت المشكلة وسأقوم بالتحقق من رقمك يدوياً.
>
> — {admin_name}

---

## Macro 2 — Password reset

**English:**
> Hi {name},
>
> I've sent a password reset link to your registered email address. It's valid for 1 hour. Check your spam folder if it doesn't arrive within 5 minutes.
>
> Important: resetting your password will sign you out of all active sessions. You'll need to log in fresh on each device afterwards.
>
> If you don't receive the email within 15 minutes, let me know and I'll investigate.
>
> — {admin_name}

**Arabic:**
> مرحباً {name},
>
> أرسلت رابط إعادة تعيين كلمة المرور إلى بريدك الإلكتروني المسجل. الرابط صالح لمدة ساعة واحدة. تحقّق من مجلد الرسائل غير المرغوبة إذا لم يصل خلال ٥ دقائق.
>
> مهم: إعادة تعيين كلمة المرور ستسجّل خروجك من جميع الجلسات النشطة. ستحتاج إلى تسجيل الدخول من جديد على كل جهاز.
>
> إذا لم يصل البريد خلال ١٥ دقيقة، أخبرني وسأبحث في المشكلة.
>
> — {admin_name}

---

## Macro 3 — Payment didn't go through / duplicate charge

**English:**
> Hi {name},
>
> I see you had a payment issue on order {order_id}. Looking at your transactions, I can confirm:
>
> - Attempt 1: {status_1} at {time_1}
> - Attempt 2: {status_2} at {time_2}
>
> {if_duplicate_charge}
> You were charged twice for the same order. I'm processing a refund of {amount} IQD for the extra charge — it will appear back on your Qi Card within {qi_card_timing}. The order itself is proceeding normally with the first payment.
> {/if_duplicate_charge}
>
> {if_payment_failed}
> The payment didn't complete successfully (Qi Card returned {error}). No funds were captured. You can retry the payment from the order page, or contact Qi Card support at {qi_card_support} if the issue persists.
> {/if_payment_failed}
>
> I'll personally follow up if anything changes on our end.
>
> — {admin_name}

**Arabic:**
> مرحباً {name},
>
> أرى أنك واجهت مشكلة في الدفع على الطلب {order_id}. بعد مراجعة معاملاتك، يمكنني التأكيد:
>
> - المحاولة الأولى: {status_1} في {time_1}
> - المحاولة الثانية: {status_2} في {time_2}
>
> {if_duplicate_charge}
> تم خصم المبلغ مرتين من نفس الطلب. أقوم الآن بمعالجة استرداد بقيمة {amount} د.ع للشحن الزائد — سيظهر على بطاقة كي كارد خلال {qi_card_timing}. يستمر الطلب الأصلي طبيعياً بالدفعة الأولى.
> {/if_duplicate_charge}
>
> {if_payment_failed}
> لم يكتمل الدفع بنجاح (أعادت كي كارد الخطأ {error}). لم يتم خصم أي مبلغ. يمكنك إعادة المحاولة من صفحة الطلب، أو التواصل مع دعم كي كارد على {qi_card_support} إذا استمرت المشكلة.
> {/if_payment_failed}
>
> سأتابع شخصياً إذا تغير شيء من جانبنا.
>
> — {admin_name}

---

## Macro 4 — Refund timing question

**English:**
> Hi {name},
>
> A refund has been approved for order {order_id} in the amount of {amount} IQD. Here's what to expect:
>
> - Kaasb has marked the refund as approved internally.
> - The actual Qi Card transfer happens manually (Qi Card's v0 API doesn't currently support automated refunds — we're working on this).
> - Once transferred, Qi Card typically settles the refund back to your original card within 3–7 business days, depending on their internal processing.
>
> I'll send you the Qi Card transaction reference as soon as the transfer completes. Expect that within {admin_action_timing} from now.
>
> — {admin_name}

**Arabic:**
> مرحباً {name},
>
> تمت الموافقة على استرداد الطلب {order_id} بمبلغ {amount} د.ع. إليك ما يمكن توقعه:
>
> - وضع كاسب الاسترداد كمعتمَد داخلياً.
> - يتم تحويل كي كارد الفعلي يدوياً (لا تدعم واجهة كي كارد v0 الاسترداد التلقائي حالياً — نعمل على تحسين ذلك).
> - بمجرد التحويل، تقوم كي كارد عادةً بتسوية الاسترداد إلى بطاقتك الأصلية خلال ٣–٧ أيام عمل، حسب معالجتها الداخلية.
>
> سأرسل لك رقم معاملة كي كارد بمجرد اكتمال التحويل. توقع ذلك خلال {admin_action_timing} من الآن.
>
> — {admin_name}

---

## Macro 5 — Payout timing / "When will I get paid?"

**English:**
> Hi {name},
>
> I see you're waiting on payout for completed order(s) {order_ids}. Here's where we are:
>
> - Escrow status: {status} ({amount} IQD)
> - Qi Card details on file: {qi_card_phone} / {qi_card_holder_name}
>
> Kaasb admins manually transfer IQD via the Qi Card merchant portal on **Tuesdays and Fridays** (Baghdad time). Your payout is queued for the next batch on {next_payout_date}. Once transferred, you'll receive an in-app notification with the Qi Card transaction reference and an updated payment history.
>
> {if_missing_fields}
> Before we can release funds, please complete your payout account setup at https://kaasb.com/dashboard/payments — we need both your Qi Card phone AND cardholder name on file. The "Release" button stays disabled until both are filled.
> {/if_missing_fields}
>
> — {admin_name}

**Arabic:**
> مرحباً {name},
>
> أرى أنك تنتظر التحويل للطلبات المكتملة {order_ids}. إليك الحالة:
>
> - حالة الضمان: {status} ({amount} د.ع)
> - بيانات كي كارد المسجلة: {qi_card_phone} / {qi_card_holder_name}
>
> يحوّل مشرفو كاسب الأموال يدوياً عبر بوابة كي كارد التجارية **يومي الثلاثاء والجمعة** (بتوقيت بغداد). طلبك في قائمة الانتظار للدفعة التالية في {next_payout_date}. بمجرد التحويل، ستصلك إشعار داخل التطبيق مع رقم معاملة كي كارد وسجل الدفع المحدّث.
>
> {if_missing_fields}
> قبل أن نتمكن من تحرير الأموال، يُرجى إكمال إعداد حساب الصرف على https://kaasb.com/dashboard/payments — نحتاج إلى رقم هاتف كي كارد واسم حامل البطاقة. يبقى زر "التحرير" معطلاً حتى يُملأ كلاهما.
> {/if_missing_fields}
>
> — {admin_name}

---

## Macro 6 — Dispute process explainer

**English:**
> Hi {name},
>
> I understand you're frustrated with order {order_id}. Before we open a formal dispute, let's make sure revisions can't solve it — that's usually the faster route and most orders resolve at this step.
>
> If the delivery genuinely doesn't match the service description or the freelancer has gone silent for more than 72 hours, here's how to open a dispute:
>
> 1. Go to your order page: https://kaasb.com/dashboard/services/orders
> 2. Click the "Open Dispute" button on the order
> 3. Select a reason + describe the issue + upload evidence (screenshots, delivered files, chat screenshots)
>
> A Kaasb admin will review within 48 hours and decide: refund you, release to the freelancer, or ask for more information. The escrow is frozen during review so no one can move funds until a decision is made.
>
> Want me to open the dispute on your behalf? Just confirm and I will.
>
> — {admin_name}

**Arabic:**
> مرحباً {name},
>
> أفهم إحباطك بخصوص الطلب {order_id}. قبل أن نفتح نزاعاً رسمياً، لنتأكد من أن التعديلات لا تحل المشكلة — غالباً هذا الطريق الأسرع وأغلب الطلبات تُحلّ هنا.
>
> إذا كان التسليم فعلاً لا يطابق وصف الخدمة أو اختفى المستقل لأكثر من ٧٢ ساعة، إليك طريقة فتح النزاع:
>
> 1. انتقل إلى صفحة طلبك: https://kaasb.com/dashboard/services/orders
> 2. اضغط زر "فتح نزاع" على الطلب
> 3. اختر سبباً + صف المشكلة + ارفع أدلة (صور، ملفات مسلّمة، لقطات شاشة للمحادثة)
>
> سيراجع مشرف كاسب خلال ٤٨ ساعة ويقرر: استرداد لك، أو تحرير للمستقل، أو طلب مزيد من المعلومات. الضمان مجمّد أثناء المراجعة فلا أحد يستطيع تحريك الأموال حتى يُتّخذ القرار.
>
> هل تريدني فتح النزاع نيابة عنك؟ أكّد فقط وسأقوم به.
>
> — {admin_name}

---

## Macro 7 — Account verification (phone) — manual override

**English:**
> Hi {name},
>
> I've manually verified the phone number on your account as a one-time courtesy — you can now receive payments and post services. Please note this doesn't replace the normal OTP flow; future security events (password reset, device change) will still require a working OTP delivery channel, so it's worth fixing whatever blocked the original verification.
>
> If the OTP delivery issue was on our end (email routing, Twilio outage), I've flagged it for our infrastructure review and it should be fixed by {fix_eta}.
>
> Welcome to Kaasb. Let me know if you hit anything else.
>
> — {admin_name}

**Arabic:**
> مرحباً {name},
>
> قمت بالتحقق يدوياً من رقم هاتفك كإجراء استثنائي — يمكنك الآن استلام المدفوعات ونشر الخدمات. يُرجى ملاحظة أن هذا لا يحل محل تدفق OTP العادي؛ الأحداث الأمنية المستقبلية (إعادة تعيين كلمة المرور، تغيير الجهاز) ستتطلب قناة OTP تعمل، لذا من المفيد إصلاح ما منع التحقق الأصلي.
>
> إذا كانت مشكلة توصيل OTP من جانبنا (توجيه البريد، انقطاع تويليو)، فقد أشرت إليها للمراجعة الفنية وسيتم إصلاحها بحلول {fix_eta}.
>
> أهلاً بك في كاسب. أخبرني إذا واجهت أي شيء آخر.
>
> — {admin_name}

---

## Macro 8 — Language switch / locale confusion

**English:**
> Hi {name},
>
> Kaasb is available in both Arabic and English — you can switch anytime from the language toggle at the top-right of any page (the 🌐 icon, or the flag).
>
> Your preferred language is saved in a cookie, so once you pick one, every page shows in that language until you switch again. If you're seeing a mix of languages on one page, that usually means a cookie is stuck — clear cookies for kaasb.com and reload.
>
> — {admin_name}

**Arabic:**
> مرحباً {name},
>
> كاسب متوفر بالعربية والإنجليزية — يمكنك التبديل في أي وقت من زر تبديل اللغة في أعلى يسار أي صفحة (أيقونة 🌐، أو العلم).
>
> تُحفظ لغتك المفضلة في ملف تعريف ارتباط، فبمجرد اختيارها، تظهر كل صفحة بتلك اللغة حتى تبدّلها مجدداً. إذا رأيت خلطاً بين اللغات في صفحة واحدة، هذا يعني أن ملف الارتباط عالق — امسح ملفات الارتباط لـ kaasb.com وأعد التحميل.
>
> — {admin_name}

---

## Signature + tone guidelines

- **Length**: 4–8 lines for simple questions; 10–15 max for complex. If you're writing more, send the key info and offer a call.
- **Tone**: warm professional. Not stiff, not casual. Imagine explaining to a small business owner who runs their account themselves.
- **Emojis**: avoid in payment, dispute, or legal contexts. A single 👋 or ✅ is fine for welcome / confirmation messages.
- **Closing**: always use your first name. "— Mustafa" / "— Rasheed" / "— Admin" (for the shared account). Never "— Kaasb Team" — feels corporate.
- **Links**: relative URLs inside Kaasb (kaasb.com/dashboard/payments), absolute for external (https://qi.iq).

---

## Backlog

- [ ] Macros 9-15: order-scope-change, freelancer-overwhelmed, chargeback-notice, legal-inquiry, IP-infringement-claim, welfare-concern, press-inquiry — each tied to a red-flag scenario in support-runbook.md
- [ ] Auto-insertion: admin UI hook that surfaces relevant macros based on ticket category
- [ ] Feedback loop: monthly review of which macros shipped verbatim vs. heavily customized — high customization rate = macro needs refactor
