"use client";

import Link from "next/link";
import { useState, useCallback, useEffect } from "react";
import { useAuthStore } from "@/lib/auth-store";
import { LanguageSwitcher } from "@/components/ui/language-switcher";
import { NotificationBell } from "@/components/ui/notification-bell";
import { useLocale } from "@/providers/locale-provider";

export function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);
  const { user, isAuthenticated, logout, initialize } = useAuthStore();
  const toggleMobileMenu = useCallback(() => setMobileMenuOpen((prev) => !prev), []);

  // Initialize auth state once on mount — resolves isLoading for all pages
  useEffect(() => {
    initialize();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const { locale } = useLocale();
  const t = {
    findWork: locale === "ar" ? "ابحث عن عمل" : "Find Work",
    findFreelancers: locale === "ar" ? "ابحث عن مستقلين" : "Find Freelancers",
    services: locale === "ar" ? "الخدمات" : "Services",
    dashboard: locale === "ar" ? "لوحة التحكم" : "Dashboard",
    messages: locale === "ar" ? "الرسائل" : "Messages",
    logout: locale === "ar" ? "تسجيل الخروج" : "Log out",
    login: locale === "ar" ? "تسجيل الدخول" : "Log In",
    register: locale === "ar" ? "إنشاء حساب" : "Sign Up",
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2">
            <span className="text-2xl font-bold text-brand-500">
              {locale === "ar" ? "كاسب" : "Kaasb"}
            </span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-6">
            <Link
              href="/jobs"
              className="text-gray-600 hover:text-gray-900 font-medium transition-colors"
            >
              {t.findWork}
            </Link>
            <Link
              href="/freelancers"
              className="text-gray-600 hover:text-gray-900 font-medium transition-colors"
            >
              {t.findFreelancers}
            </Link>
            <Link
              href="/gigs"
              className="text-gray-600 hover:text-gray-900 font-medium transition-colors"
            >
              {t.services}
            </Link>

            {isAuthenticated ? (
              <div className="flex items-center gap-4">
                <Link
                  href="/dashboard"
                  className="text-gray-600 hover:text-gray-900 font-medium"
                >
                  {t.dashboard}
                </Link>
                <Link
                  href="/dashboard/messages"
                  className="text-gray-600 hover:text-gray-900 font-medium"
                >
                  {t.messages}
                </Link>
                {user?.is_superuser && (
                  <Link
                    href="/admin"
                    className="text-red-600 hover:text-red-800 font-medium text-sm"
                  >
                    {locale === "ar" ? "الإدارة" : "Admin"}
                  </Link>
                )}
                <NotificationBell />
                <div className="flex items-center gap-3 pl-4 border-l border-gray-200">
                  <div className="w-8 h-8 bg-brand-100 text-brand-600 rounded-full flex items-center justify-center font-semibold text-sm">
                    {user?.first_name?.[0]}
                    {user?.last_name?.[0]}
                  </div>
                  <button
                    onClick={logout}
                    className="text-sm text-gray-500 hover:text-gray-700"
                  >
                    {t.logout}
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-3">
                <Link
                  href="/auth/login"
                  className="text-gray-600 hover:text-gray-900 font-medium"
                >
                  {t.login}
                </Link>
                <Link href="/auth/register" className="btn-primary py-2 px-5">
                  {t.register}
                </Link>
              </div>
            )}

            <LanguageSwitcher />
          </div>

          {/* Mobile: language + menu button */}
          <div className="md:hidden flex items-center gap-2">
            <LanguageSwitcher />
            <button
              className="p-2"
              onClick={toggleMobileMenu}
              aria-label="Toggle mobile menu"
              aria-expanded={mobileMenuOpen}
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                {mobileMenuOpen ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-white border-t border-gray-100 py-4 px-4 space-y-3">
          <Link href="/jobs" className="block py-2 text-gray-700 font-medium">
            {t.findWork}
          </Link>
          <Link href="/freelancers" className="block py-2 text-gray-700 font-medium">
            {t.findFreelancers}
          </Link>
          <Link href="/gigs" className="block py-2 text-gray-700 font-medium">
            {t.services}
          </Link>
          {isAuthenticated ? (
            <>
              <Link href="/dashboard" className="block py-2 text-gray-700 font-medium">
                {t.dashboard}
              </Link>
              <Link href="/dashboard/messages" className="block py-2 text-gray-700 font-medium">
                {t.messages}
              </Link>
              <Link href="/dashboard/notifications" className="block py-2 text-gray-700 font-medium">
                {locale === "ar" ? "الإشعارات" : "Notifications"}
              </Link>
              {user?.is_superuser && (
                <Link href="/admin" className="block py-2 text-red-600 font-medium">
                  {locale === "ar" ? "الإدارة" : "Admin"}
                </Link>
              )}
              <button
                onClick={logout}
                className="block w-full text-start py-2 text-gray-700 font-medium"
              >
                {t.logout}
              </button>
            </>
          ) : (
            <>
              <Link href="/auth/login" className="block py-2 text-gray-700 font-medium">
                {t.login}
              </Link>
              <Link href="/auth/register" className="block btn-primary text-center">
                {t.register}
              </Link>
            </>
          )}
        </div>
      )}
    </nav>
  );
}
