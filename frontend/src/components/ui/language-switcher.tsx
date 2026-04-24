'use client';

import { usePathname } from 'next/navigation';
import { useTransition } from 'react';
import { useLocale } from '@/providers/locale-provider';
import { setLocaleCookie } from '@/app/actions/locale';
import { useAuthStore } from '@/lib/auth-store';
import { usersApi } from '@/lib/api';

export function LanguageSwitcher() {
  const { locale } = useLocale();
  const pathname = usePathname();
  const [isPending, startTransition] = useTransition();
  const user = useAuthStore((s) => s.user);

  const toggle = () => {
    const newLocale = locale === 'ar' ? 'en' : 'ar';

    // Fire-and-forget the backend preference update. An auth refresh loop
    // or slow backend would otherwise hang the whole toggle for axios's
    // 30s timeout — the cookie-based UI doesn't depend on this succeeding,
    // so we must not await it.
    if (user) {
      usersApi.updateLocale(newLocale).catch(() => {
        // Silent — cookie-based UI still flips regardless.
      });
    }

    startTransition(async () => {
      // Server Action: sets cookie server-side → redirects → server re-renders
      // layout with correct html[dir/lang], all text, all context.
      await setLocaleCookie(newLocale, pathname);
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
