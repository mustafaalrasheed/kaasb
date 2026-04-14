'use client';

import { Suspense, useState } from 'react';
import Link from 'next/link';
import { useSearchParams, useRouter } from 'next/navigation';
import { useLocale } from '@/providers/locale-provider';
import { authApi } from '@/lib/api';

function ResetPasswordContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { locale } = useLocale();
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const t = {
    title: locale === 'ar' ? 'إعادة تعيين كلمة المرور' : 'Reset Your Password',
    subtitle: locale === 'ar' ? 'أدخل كلمة مرور جديدة لحسابك.' : 'Enter a new password for your account.',
    newPassword: locale === 'ar' ? 'كلمة المرور الجديدة' : 'New Password',
    confirmPassword: locale === 'ar' ? 'تأكيد كلمة المرور' : 'Confirm Password',
    submit: locale === 'ar' ? 'تعيين كلمة المرور' : 'Set New Password',
    loading: locale === 'ar' ? 'جاري الحفظ...' : 'Saving...',
    mismatch: locale === 'ar' ? 'كلمتا المرور غير متطابقتين.' : 'Passwords do not match.',
    tooShort: locale === 'ar' ? 'يجب أن تتكون كلمة المرور من 8 أحرف على الأقل.' : 'Password must be at least 8 characters.',
    invalidToken: locale === 'ar' ? 'رابط إعادة التعيين غير صالح أو منتهي الصلاحية.' : 'The reset link is invalid or has expired.',
    successTitle: locale === 'ar' ? 'تم تعيين كلمة المرور!' : 'Password Updated!',
    successMsg: locale === 'ar'
      ? 'تم تعيين كلمة مرورك الجديدة بنجاح. يمكنك الآن تسجيل الدخول.'
      : 'Your new password has been set. You can now log in.',
    goToLogin: locale === 'ar' ? 'تسجيل الدخول' : 'Go to Login',
    noToken: locale === 'ar' ? 'رابط إعادة التعيين مفقود.' : 'Reset link is missing.',
    requestNew: locale === 'ar' ? 'طلب رابط جديد' : 'Request a new link',
    passwordHint: locale === 'ar' ? '8 أحرف على الأقل' : 'Minimum 8 characters',
  };

  const token = searchParams.get('token');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password.length < 8) {
      setError(t.tooShort);
      return;
    }
    if (password !== confirm) {
      setError(t.mismatch);
      return;
    }
    if (!token) {
      setError(t.noToken);
      return;
    }

    setLoading(true);
    try {
      await authApi.resetPassword(token, password);
      setSuccess(true);
      setTimeout(() => router.push('/auth/login'), 3000);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '';
      if (detail.includes('expired') || detail.includes('invalid')) {
        setError(t.invalidToken);
      } else {
        setError(detail || t.invalidToken);
      }
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="max-w-md w-full card p-8 text-center">
          <p className="text-gray-600 mb-4">{t.noToken}</p>
          <Link href="/auth/forgot-password" className="btn-primary inline-block">
            {t.requestNew}
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md w-full">
        <div className="card p-8">
          {!success ? (
            <>
              <div className="text-center mb-8">
                <div className="w-14 h-14 bg-brand-50 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-7 h-7 text-brand-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </div>
                <h1 className="text-2xl font-bold text-gray-900">{t.title}</h1>
                <p className="text-gray-500 mt-2 text-sm">{t.subtitle}</p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    {t.newPassword}
                  </label>
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="input-field"
                    dir="ltr"
                  />
                  <p className="text-xs text-gray-400 mt-1">{t.passwordHint}</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    {t.confirmPassword}
                  </label>
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={confirm}
                    onChange={(e) => setConfirm(e.target.value)}
                    className="input-field"
                    dir="ltr"
                  />
                </div>

                {error && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="btn-primary w-full"
                >
                  {loading ? t.loading : t.submit}
                </button>
              </form>

              <p className="text-center text-sm text-gray-500 mt-6">
                <Link href="/auth/forgot-password" className="text-brand-500 hover:text-brand-600">
                  {t.requestNew}
                </Link>
              </p>
            </>
          ) : (
            <div className="text-center">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h1 className="text-xl font-bold text-gray-900 mb-3">{t.successTitle}</h1>
              <p className="text-gray-500 text-sm mb-6">{t.successMsg}</p>
              <Link href="/auth/login" className="btn-primary inline-block">
                {t.goToLogin}
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-10 h-10 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <ResetPasswordContent />
    </Suspense>
  );
}
