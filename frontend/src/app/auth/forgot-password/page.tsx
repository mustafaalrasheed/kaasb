'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useLocale } from '@/providers/locale-provider';
import { authApi } from '@/lib/api';

export default function ForgotPasswordPage() {
  const { locale } = useLocale();
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const t = {
    title: locale === 'ar' ? 'نسيت كلمة المرور؟' : 'Forgot Password?',
    subtitle: locale === 'ar'
      ? 'أدخل بريدك الإلكتروني وسنرسل لك رابطاً لإعادة التعيين.'
      : 'Enter your email and we\'ll send you a reset link.',
    emailLabel: locale === 'ar' ? 'البريد الإلكتروني' : 'Email Address',
    emailPlaceholder: locale === 'ar' ? 'your@email.com' : 'your@email.com',
    submit: locale === 'ar' ? 'إرسال رابط الاستعادة' : 'Send Reset Link',
    loading: locale === 'ar' ? 'جاري الإرسال...' : 'Sending...',
    successTitle: locale === 'ar' ? 'تحقق من بريدك الإلكتروني' : 'Check Your Email',
    successMsg: locale === 'ar'
      ? 'إذا كان هذا البريد الإلكتروني مسجلاً لدينا، ستصلك رسالة لإعادة تعيين كلمة المرور خلال دقائق.'
      : 'If this email is registered with us, you\'ll receive a password reset link within a few minutes.',
    backToLogin: locale === 'ar' ? 'العودة إلى تسجيل الدخول' : 'Back to Login',
    rememberPassword: locale === 'ar' ? 'تذكرت كلمة المرور؟' : 'Remember your password?',
    login: locale === 'ar' ? 'تسجيل الدخول' : 'Log In',
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await authApi.forgotPassword(email);
    } catch {
      // Always show success to prevent email enumeration
    } finally {
      setLoading(false);
      setSubmitted(true);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md w-full">
        <div className="card p-8">
          {!submitted ? (
            <>
              <div className="text-center mb-8">
                <div className="w-14 h-14 bg-brand-50 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-7 h-7 text-brand-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                  </svg>
                </div>
                <h1 className="text-2xl font-bold text-gray-900">{t.title}</h1>
                <p className="text-gray-500 mt-2 text-sm">{t.subtitle}</p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    {t.emailLabel}
                  </label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder={t.emailPlaceholder}
                    className="input-field"
                    dir="ltr"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="btn-primary w-full"
                >
                  {loading ? t.loading : t.submit}
                </button>
              </form>

              <p className="text-center text-sm text-gray-500 mt-6">
                {t.rememberPassword}{' '}
                <Link href="/auth/login" className="text-brand-500 hover:text-brand-600 font-medium">
                  {t.login}
                </Link>
              </p>
            </>
          ) : (
            <div className="text-center">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <h1 className="text-xl font-bold text-gray-900 mb-3">{t.successTitle}</h1>
              <p className="text-gray-500 text-sm mb-6">{t.successMsg}</p>
              <Link href="/auth/login" className="btn-primary inline-block">
                {t.backToLogin}
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
