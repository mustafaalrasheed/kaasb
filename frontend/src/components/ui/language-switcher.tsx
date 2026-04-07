'use client';

import { useState } from 'react';
import { useLocale } from '@/providers/locale-provider';

export function LanguageSwitcher() {
  const { locale } = useLocale();
  const [loading, setLoading] = useState(false);

  const toggle = () => {
    if (loading) return;
    const newLocale = locale === 'ar' ? 'en' : 'ar';
    setLoading(true);
    // 1. Persist choice in a 1-year cookie
    document.cookie = `locale=${newLocale};path=/;max-age=31536000;samesite=lax`;
    // 2. Full page reload — server reads the new cookie and renders everything
    //    (html dir, lang, all text) correctly. Much more reliable than router.refresh()
    //    which doesn't update html attributes or fix useState(initialLocale) staleness.
    window.location.reload();
  };

  return (
    <button
      onClick={toggle}
      disabled={loading}
      aria-label={locale === 'ar' ? 'Switch to English' : 'التبديل إلى العربية'}
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 text-sm font-medium
                 text-gray-700 hover:bg-gray-100 hover:border-gray-300
                 transition-colors duration-150 disabled:opacity-50 min-w-[52px] justify-center"
    >
      {loading ? (
        <span className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
      ) : locale === 'en' ? (
        <span className="font-semibold tracking-wide">عربي</span>
      ) : (
        <span className="font-semibold tracking-wide">EN</span>
      )}
    </button>
  );
}
