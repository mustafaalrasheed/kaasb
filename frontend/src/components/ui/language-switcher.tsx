'use client';

import { useRouter } from 'next/navigation';
import { useLocale } from '@/providers/locale-provider';
import { useTransition } from 'react';

export function LanguageSwitcher() {
  const { locale } = useLocale();
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  const toggle = () => {
    const newLocale = locale === 'ar' ? 'en' : 'ar';
    // Persist in cookie (1 year)
    document.cookie = `locale=${newLocale};path=/;max-age=31536000;samesite=lax`;
    // Trigger server re-render — layout.tsx reads the cookie and re-renders everything
    startTransition(() => {
      router.refresh();
    });
  };

  return (
    <button
      onClick={toggle}
      disabled={isPending}
      aria-label={locale === 'ar' ? 'Switch to English' : 'التبديل إلى العربية'}
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 text-sm font-medium
                 text-gray-700 hover:bg-gray-100 hover:border-gray-300
                 transition-colors duration-150 disabled:opacity-50 min-w-[52px] justify-center"
    >
      {isPending ? (
        <span className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
      ) : locale === 'en' ? (
        <span className="font-semibold tracking-wide">عربي</span>
      ) : (
        <span className="font-semibold tracking-wide">EN</span>
      )}
    </button>
  );
}
