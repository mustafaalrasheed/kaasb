'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useLocale } from '@/providers/locale-provider';
import { authApi } from '@/lib/api';

type Status = 'verifying' | 'success' | 'error' | 'expired';

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { locale } = useLocale();
  const [status, setStatus] = useState<Status>('verifying');
  const [errorMsg, setErrorMsg] = useState('');

  const t = {
    verifying: locale === 'ar' ? 'جاري التحقق من بريدك الإلكتروني...' : 'Verifying your email...',
    success: locale === 'ar' ? 'تم التحقق من بريدك الإلكتروني بنجاح!' : 'Email verified successfully!',
    successSub: locale === 'ar' ? 'يمكنك الآن تسجيل الدخول والبدء في استخدام كاسب.' : 'You can now log in and start using Kaasb.',
    goToLogin: locale === 'ar' ? 'تسجيل الدخول' : 'Go to Login',
    expired: locale === 'ar' ? 'انتهت صلاحية رابط التحقق.' : 'The verification link has expired.',
    expiredSub: locale === 'ar' ? 'يمكنك طلب رابط تحقق جديد.' : 'You can request a new verification link.',
    resend: locale === 'ar' ? 'إعادة إرسال رابط التحقق' : 'Resend Verification Link',
    error: locale === 'ar' ? 'فشل التحقق من البريد الإلكتروني.' : 'Email verification failed.',
    noToken: locale === 'ar' ? 'رابط التحقق غير صالح.' : 'Invalid verification link.',
    backToHome: locale === 'ar' ? 'العودة إلى الرئيسية' : 'Back to Home',
  };

  useEffect(() => {
    const token = searchParams.get('token');
    if (!token) {
      setStatus('error');
      setErrorMsg(t.noToken);
      return;
    }

    authApi.verifyEmail(token)
      .then(() => {
        setStatus('success');
        setTimeout(() => router.push('/auth/login'), 3000);
      })
      .catch((err) => {
        const detail = err?.response?.data?.detail || '';
        if (detail.includes('expired') || detail.includes('انتهت')) {
          setStatus('expired');
        } else {
          setStatus('error');
          setErrorMsg(detail || t.error);
        }
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md w-full">
        <div className="card p-8 text-center">
          {status === 'verifying' && (
            <>
              <div className="w-16 h-16 border-4 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <p className="text-gray-600">{t.verifying}</p>
            </>
          )}

          {status === 'success' && (
            <>
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h1 className="text-xl font-bold text-gray-900 mb-2">{t.success}</h1>
              <p className="text-gray-500 mb-6">{t.successSub}</p>
              <Link href="/auth/login" className="btn-primary inline-block">
                {t.goToLogin}
              </Link>
            </>
          )}

          {status === 'expired' && (
            <>
              <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h1 className="text-xl font-bold text-gray-900 mb-2">{t.expired}</h1>
              <p className="text-gray-500 mb-6">{t.expiredSub}</p>
              <Link href="/auth/login" className="btn-secondary inline-block mb-3">
                {t.resend}
              </Link>
            </>
          )}

          {status === 'error' && (
            <>
              <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
              <h1 className="text-xl font-bold text-gray-900 mb-2">{t.error}</h1>
              {errorMsg && <p className="text-gray-500 mb-6">{errorMsg}</p>}
              <Link href="/" className="btn-secondary inline-block">
                {t.backToHome}
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-10 h-10 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <VerifyEmailContent />
    </Suspense>
  );
}
