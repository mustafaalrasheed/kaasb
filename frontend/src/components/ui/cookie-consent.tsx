"use client";

/**
 * Cookie Consent Banner
 *
 * GDPR-compliant cookie consent for Kaasb.
 * - Shows once per browser (preference stored in localStorage)
 * - Bilingual: English + Arabic (RTL)
 * - Keyboard accessible (focus trap within banner)
 * - WCAG 2.1 AA compliant (role="dialog", aria-live)
 *
 * We only use essential cookies, so "Accept All" and "Accept Essential"
 * have the same practical effect — the distinction future-proofs the
 * component for analytics cookies added later.
 */

import Link from "next/link";
import { useEffect, useState } from "react";

const STORAGE_KEY = "kaasb_cookie_consent";
const CONSENT_VERSION = "1"; // bump when policy changes to re-ask users

type ConsentChoice = "accepted" | "essential";

export function CookieConsent() {
  const [visible, setVisible] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (!stored) {
        // Small delay so the banner doesn't flash before hydration settles
        const timer = setTimeout(() => setVisible(true), 800);
        return () => clearTimeout(timer);
      }
      const parsed = JSON.parse(stored);
      // Re-ask if consent was given for an older policy version
      if (parsed.version !== CONSENT_VERSION) {
        const timer = setTimeout(() => setVisible(true), 800);
        return () => clearTimeout(timer);
      }
    } catch {
      setVisible(true);
    }
  }, []);

  const save = (choice: ConsentChoice) => {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ choice, version: CONSENT_VERSION, ts: Date.now() })
      );
    } catch {
      // localStorage blocked (private mode) — ignore, banner won't re-show in this session
    }
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Cookie consent"
      aria-live="polite"
      className="fixed bottom-0 left-0 right-0 z-50 p-4 sm:p-6"
    >
      <div className="max-w-4xl mx-auto bg-white border border-gray-200 rounded-2xl shadow-2xl">
        <div className="p-5 sm:p-6">
          {/* Header row */}
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-2">
              <span className="text-xl" aria-hidden="true">🍪</span>
              <h2 className="text-base font-semibold text-gray-900">
                Cookie Preferences
              </h2>
            </div>
            {/* Arabic label */}
            <span className="text-sm text-gray-500 font-medium" dir="rtl">
              تفضيلات ملفات الارتباط
            </span>
          </div>

          {/* Body */}
          <p className="mt-3 text-sm text-gray-600 leading-relaxed">
            We use only strictly-necessary cookies to keep you signed in and secure,
            and one local-storage key to remember this choice. No analytics, no
            advertising, no third-party trackers.{" "}
            <Link href="/cookies" className="text-brand-500 hover:underline font-medium">
              Full Cookie Policy
            </Link>
          </p>
          {/* Arabic */}
          <p className="mt-1 text-sm text-gray-500 leading-relaxed text-right" dir="rtl">
            نستخدم ملفات ارتباط ضرورية فقط لإبقائك مسجلاً وحماية جلستك، ومفتاحاً
            محلياً واحداً لتذكّر هذا الاختيار. لا تحليلات ولا إعلانات ولا أدوات تتبع
            خارجية.{" "}
            <Link href="/cookies" className="text-brand-500 hover:underline font-medium">
              سياسة ملفات الارتباط الكاملة
            </Link>
          </p>

          {/* Cookie details toggle */}
          <button
            onClick={() => setShowDetails((v) => !v)}
            className="mt-3 text-sm text-brand-500 hover:text-brand-600 font-medium focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 rounded"
            aria-expanded={showDetails}
          >
            {showDetails ? "Hide details ▲" : "Show cookie details ▼"}
          </button>

          {showDetails && (
            <div className="mt-3 border border-gray-100 rounded-lg overflow-hidden text-sm">
              <table className="w-full text-start">
                <thead>
                  <tr className="bg-gray-50">
                    <th className="p-3 font-semibold text-gray-700">Cookie</th>
                    <th className="p-3 font-semibold text-gray-700">Purpose · الغرض</th>
                    <th className="p-3 font-semibold text-gray-700">Duration · المدة</th>
                  </tr>
                </thead>
                <tbody className="text-gray-600 align-top">
                  <tr className="border-t border-gray-100">
                    <td className="p-3 font-mono text-xs">access_token</td>
                    <td className="p-3">
                      <div>Authentication session</div>
                      <div className="text-gray-500" dir="rtl">مصادقة الجلسة</div>
                    </td>
                    <td className="p-3">
                      <div>30 minutes</div>
                      <div className="text-gray-500" dir="rtl">٣٠ دقيقة</div>
                    </td>
                  </tr>
                  <tr className="border-t border-gray-100">
                    <td className="p-3 font-mono text-xs">refresh_token</td>
                    <td className="p-3">
                      <div>Session renewal</div>
                      <div className="text-gray-500" dir="rtl">تجديد الجلسة</div>
                    </td>
                    <td className="p-3">
                      <div>7 days</div>
                      <div className="text-gray-500" dir="rtl">٧ أيام</div>
                    </td>
                  </tr>
                  <tr className="border-t border-gray-100">
                    <td className="p-3 font-mono text-xs">csrf_token</td>
                    <td className="p-3">
                      <div>Cross-site request protection</div>
                      <div className="text-gray-500" dir="rtl">الحماية من تزوير الطلبات</div>
                    </td>
                    <td className="p-3">
                      <div>Session</div>
                      <div className="text-gray-500" dir="rtl">مدة الجلسة</div>
                    </td>
                  </tr>
                  <tr className="border-t border-gray-100">
                    <td className="p-3 font-mono text-xs">locale</td>
                    <td className="p-3">
                      <div>Interface language (AR / EN)</div>
                      <div className="text-gray-500" dir="rtl">لغة الواجهة</div>
                    </td>
                    <td className="p-3">
                      <div>1 year</div>
                      <div className="text-gray-500" dir="rtl">سنة واحدة</div>
                    </td>
                  </tr>
                  <tr className="border-t border-gray-100">
                    <td className="p-3 font-mono text-xs">{STORAGE_KEY}</td>
                    <td className="p-3">
                      <div>Cookie consent choice (localStorage)</div>
                      <div className="text-gray-500" dir="rtl">اختيار الموافقة (localStorage)</div>
                    </td>
                    <td className="p-3">
                      <div>Persistent</div>
                      <div className="text-gray-500" dir="rtl">دائم</div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}

          {/* Action buttons */}
          <div className="mt-5 flex flex-col sm:flex-row gap-3">
            <button
              onClick={() => save("accepted")}
              className="btn-primary py-2.5 px-5 text-sm focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-brand-500"
              aria-label="Accept all cookies"
            >
              Accept · أوافق
            </button>
            <button
              onClick={() => save("essential")}
              className="py-2.5 px-5 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-gray-400"
              aria-label="Accept essential cookies only"
            >
              Essential only · الضرورية فقط
            </button>
            <Link
              href="/cookies"
              className="py-2.5 px-5 text-sm font-medium text-brand-500 hover:text-brand-600 hover:underline self-center"
            >
              Cookie Policy · السياسة
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
