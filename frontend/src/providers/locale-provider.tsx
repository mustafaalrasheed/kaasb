'use client';

import React, { createContext, useContext, useState, useEffect, useTransition } from 'react';
import { NextIntlClientProvider } from 'next-intl';
import type { AbstractIntlMessages } from 'next-intl';

interface LocaleContextType {
  locale: 'ar' | 'en';
  setLocale: (locale: 'ar' | 'en') => void;
  isRTL: boolean;
  isPending: boolean;
}

const LocaleContext = createContext<LocaleContextType>({
  locale: 'ar',
  setLocale: () => {},
  isRTL: true,
  isPending: false,
});

export function useLocale() {
  return useContext(LocaleContext);
}

interface LocaleProviderProps {
  children: React.ReactNode;
  initialLocale: 'ar' | 'en';
  messages: AbstractIntlMessages;
}

export function LocaleProvider({ children, initialLocale, messages }: LocaleProviderProps) {
  const [locale, setLocaleState] = useState<'ar' | 'en'>(initialLocale);
  const [currentMessages, setCurrentMessages] = useState<AbstractIntlMessages>(messages);
  const [isPending, startTransition] = useTransition();

  const setLocale = (newLocale: 'ar' | 'en') => {
    startTransition(async () => {
      // Persist in cookie (1 year)
      document.cookie = `locale=${newLocale};path=/;max-age=31536000;samesite=lax`;

      // Load new messages
      const newMessages = (await import(`../messages/${newLocale}.json`)).default;

      setLocaleState(newLocale);
      setCurrentMessages(newMessages);
    });
  };

  // Sync HTML attributes and font class whenever locale changes
  useEffect(() => {
    const html = document.documentElement;
    const isArabic = locale === 'ar';

    html.dir = isArabic ? 'rtl' : 'ltr';
    html.lang = isArabic ? 'ar' : 'en';

    // Toggle Arabic font class
    if (isArabic) {
      html.classList.add('font-arabic');
    } else {
      html.classList.remove('font-arabic');
    }
  }, [locale]);

  return (
    <LocaleContext.Provider value={{ locale, setLocale, isRTL: locale === 'ar', isPending }}>
      <NextIntlClientProvider locale={locale} messages={currentMessages}>
        {children}
      </NextIntlClientProvider>
    </LocaleContext.Provider>
  );
}
