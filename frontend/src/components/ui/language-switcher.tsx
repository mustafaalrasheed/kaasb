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
    startTransition(async () => {
      // Authenticated users: persist the preference to the backend first so
      // server-emitted notifications (bell + email) pick the right locale.
      // Fire-and-forget — a failed PUT shouldn't block the UI toggle because
      // the cookie drives UI rendering regardless.
      if (user) {
        try {
          await usersApi.updateLocale(newLocale);
        } catch {
          // Silent — the server action below still flips the UI.
        }
      }
      // Server Action: sets cookie server-side → redirects → server re-renders layout
      // with correct html[dir/lang], all text, all context — guaranteed correct
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
