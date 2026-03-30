'use client';

import { useLocale } from '@/providers/locale-provider';

export function LanguageSwitcher() {
  const { locale, setLocale, isPending } = useLocale();

  const toggle = () => {
    setLocale(locale === 'ar' ? 'en' : 'ar');
  };

  return (
    <button
      onClick={toggle}
      disabled={isPending}
      aria-label={locale === 'ar' ? 'Switch to English' : 'التبديل إلى العربية'}
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 text-sm font-medium
                 text-gray-700 hover:bg-gray-100 hover:border-gray-300
                 transition-colors duration-150 disabled:opacity-50"
    >
      {locale === 'en' ? (
        <>
          <span className="text-base leading-none">🇮🇶</span>
          <span>عربي</span>
        </>
      ) : (
        <>
          <span className="text-base leading-none">🇬🇧</span>
          <span>English</span>
        </>
      )}
    </button>
  );
}
