'use client';

import React, { createContext, useContext, useEffect } from 'react';

interface LocaleContextType {
  locale: 'ar' | 'en';
  isRTL: boolean;
}

const LocaleContext = createContext<LocaleContextType>({
  locale: 'ar',
  isRTL: true,
});

export function useLocale() {
  return useContext(LocaleContext);
}

interface LocaleProviderProps {
  children: React.ReactNode;
  initialLocale: 'ar' | 'en';
}

/**
 * LocaleProvider — wraps the app and exposes the server-determined locale via context.
 *
 * Language switching is done by writing a cookie then calling window.location.reload(),
 * which triggers a full server render with the new locale (see LanguageSwitcher).
 * Because we do a full reload, we never need to update locale state in-place;
 * `initialLocale` is always correct for the current page load.
 *
 * The useEffect below syncs html[dir/lang/class] after hydration as a safeguard —
 * the server already sets these on <html> in layout.tsx but this ensures
 * client-side navigation stays in sync.
 */
export function LocaleProvider({ children, initialLocale }: LocaleProviderProps) {
  // Do NOT use useState here — we never need to update locale after mount.
  // Every locale change is a full page reload, so initialLocale is always correct.
  const isRTL = initialLocale === 'ar';

  useEffect(() => {
    const html = document.documentElement;
    html.dir = isRTL ? 'rtl' : 'ltr';
    html.lang = isRTL ? 'ar' : 'en';
    if (isRTL) {
      html.classList.add('font-arabic');
    } else {
      html.classList.remove('font-arabic');
    }
  }, [isRTL]);

  return (
    <LocaleContext.Provider value={{ locale: initialLocale, isRTL }}>
      {children}
    </LocaleContext.Provider>
  );
}
