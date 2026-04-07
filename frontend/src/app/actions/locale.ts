'use server';

import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

/**
 * Server Action: set locale cookie server-side and redirect.
 *
 * This is the correct Next.js 15 App Router pattern for locale switching:
 * - Cookie is set on the server (no client-side timing issues)
 * - `redirect()` forces a full server re-render of layout.tsx with the new locale
 * - html[dir], html[lang], all text, all React context — all correct in one shot
 */
export async function setLocaleCookie(newLocale: 'ar' | 'en', pathname: string) {
  const cookieStore = await cookies();
  cookieStore.set('locale', newLocale, {
    path: '/',
    maxAge: 60 * 60 * 24 * 365, // 1 year
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
  });
  redirect(pathname);
}
