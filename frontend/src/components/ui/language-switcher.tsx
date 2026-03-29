'use client';

import { useLocale } from '@/providers/locale-provider';
import { Globe } from 'lucide-react';

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
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium
                 text-gray-600 hover:text-gray-900 hover:bg-gray-100
                 transition-colors duration-150 disabled:opacity-50"
    >
      <Globe className="w-4 h-4" />
      <span>{locale === 'ar' ? 'English' : 'عربي'}</span>
    </button>
  );
}
