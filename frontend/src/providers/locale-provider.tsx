'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';

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

export function LocaleProvider({ children, initialLocale }: LocaleProviderProps) {
  const [locale] = useState<'ar' | 'en'>(initialLocale);

  // Sync HTML dir/lang/font after hydration (server already sets these, this is a safeguard)
  useEffect(() => {
    const html = document.documentElement;
    html.dir = locale === 'ar' ? 'rtl' : 'ltr';
    html.lang = locale === 'ar' ? 'ar' : 'en';
    if (locale === 'ar') {
      html.classList.add('font-arabic');
    } else {
      html.classList.remove('font-arabic');
    }
  }, [locale]);

  return (
    <LocaleContext.Provider value={{ locale, isRTL: locale === 'ar' }}>
      {children}
    </LocaleContext.Provider>
  );
}
