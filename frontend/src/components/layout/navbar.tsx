"use client";

import Link from "next/link";
import { useState, useCallback, useEffect } from "react";
import { useAuthStore } from "@/lib/auth-store";
import { LanguageSwitcher } from "@/components/ui/language-switcher";
import { NotificationBell } from "@/components/ui/notification-bell";
import { useLocale } from "@/providers/locale-provider";
import { usePathname } from "next/navigation";
import { backendUrl } from "@/lib/utils";

export function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);
  const { user, isAuthenticated, isLoading, logout, initialize } = useAuthStore();
  const toggleMobileMenu = useCallback(() => setMobileMenuOpen((prev) => !prev), []);
  const { locale } = useLocale();
  const pathname = usePathname();
  const isAdminPage = pathname?.startsWith("/admin");

  // Initialize auth state once on mount — skip on auth pages (login/register/etc.)
  // to avoid a redirect loop: getMe→401→refresh→401→redirect to /auth/login→repeat.
  useEffect(() => {
    if (!pathname?.startsWith("/auth")) {
      initialize();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const t = {
    findWork:         locale === "ar" ? "ابحث عن عمل"       : "Find Work",
    findFreelancers:  locale === "ar" ? "ابحث عن مستقلين"   : "Find Freelancers",
    services:         locale === "ar" ? "الخدمات"            : "Services",
    requests:         locale === "ar" ? "طلبات العملاء"      : "Client Requests",
    dashboard:        locale === "ar" ? "لوحة التحكم"        : "Dashboard",
    messages:         locale === "ar" ? "الرسائل"            : "Messages",
    notifications:    locale === "ar" ? "الإشعارات"         : "Notifications",
    admin:            locale === "ar" ? "الإدارة"            : "Admin",
    logout:           locale === "ar" ? "تسجيل الخروج"      : "Log out",
    login:            locale === "ar" ? "تسجيل الدخول"      : "Log In",
    register:         locale === "ar" ? "إنشاء حساب"        : "Sign Up",
    menu:             locale === "ar" ? "القائمة"            : "Menu",
  };

  const isRTL = locale === "ar";

  const role = user?.primary_role; // "client" | "freelancer" | undefined (guest)
  const showFindWork = !isAuthenticated || role === "freelancer";
  const showFindFreelancers = !isAuthenticated || role === "client";
  const showPostJob = isAuthenticated && role === "client";
  const showRequests = !isAuthenticated || role === "freelancer";

  return (
    <nav className="fixed top-0 inset-x-0 z-50 bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Main bar: flex-row in LTR, flex-row-reverse in RTL so logo is always outer */}
        <div className={`flex items-center h-16 ${isRTL ? "flex-row-reverse" : "flex-row"} justify-between`}>

          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 shrink-0">
            <span className="text-2xl font-bold text-brand-500">
              {isRTL ? "كاسب" : "Kaasb"}
            </span>
          </Link>

          {/* Desktop Navigation */}
          <div className={`hidden md:flex items-center gap-6 ${isRTL ? "flex-row-reverse" : "flex-row"}`}>
            {/* Public links — hidden on admin pages, role-gated for authenticated users */}
            {!isAdminPage && (
              <>
                {showFindWork && (
                  <Link href="/jobs" className="text-gray-600 hover:text-gray-900 font-medium transition-colors">
                    {t.findWork}
                  </Link>
                )}
                {showFindFreelancers && (
                  <Link href="/freelancers" className="text-gray-600 hover:text-gray-900 font-medium transition-colors">
                    {t.findFreelancers}
                  </Link>
                )}
                <Link href="/gigs" className="text-gray-600 hover:text-gray-900 font-medium transition-colors">
                  {t.services}
                </Link>
                {showRequests && (
                  <Link href="/requests" className="text-gray-600 hover:text-gray-900 font-medium transition-colors">
                    {t.requests}
                  </Link>
                )}
                {showPostJob && (
                  <Link href="/jobs/new" className="text-gray-600 hover:text-gray-900 font-medium transition-colors">
                    {isRTL ? "نشر وظيفة" : "Post a Job"}
                  </Link>
                )}
              </>
            )}

            {isLoading ? (
              /* Placeholder during hydration — prevents sign-in/sign-up flash */
              <div className="w-32 h-8" />
            ) : isAuthenticated ? (
              <div className={`flex items-center gap-4 ${isRTL ? "flex-row-reverse" : "flex-row"}`}>
                {!isAdminPage && (
                  <>
                    <Link href="/dashboard" className="text-gray-600 hover:text-gray-900 font-medium">
                      {t.dashboard}
                    </Link>
                    <Link href="/dashboard/messages" className="text-gray-600 hover:text-gray-900 font-medium">
                      {t.messages}
                    </Link>
                  </>
                )}
                {isAdminPage && (
                  <span className="text-xs font-semibold uppercase tracking-wider text-red-600 bg-red-50 px-2 py-1 rounded">
                    {locale === "ar" ? "لوحة الإدارة" : "Admin Panel"}
                  </span>
                )}
                {user?.is_superuser && (
                  <Link href="/admin" className="text-red-600 hover:text-red-800 font-medium text-sm">
                    {t.admin}
                  </Link>
                )}
                <NotificationBell />
                <div className={`flex items-center gap-2 ${isRTL ? "pe-4 border-e" : "ps-4 border-s"} border-gray-200 ${isRTL ? "flex-row-reverse" : "flex-row"}`}>
                  {/* Avatar or initials */}
                  <div className="w-8 h-8 rounded-full overflow-hidden bg-brand-100 text-brand-600 flex items-center justify-center font-semibold text-sm shrink-0">
                    {user?.avatar_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={`${backendUrl(user.avatar_url)}?v=${new Date(user.updated_at).getTime()}`}
                        alt={user.first_name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <>{user?.first_name?.[0]}{user?.last_name?.[0]}</>
                    )}
                  </div>
                  {/* Name */}
                  <span className="text-sm font-medium text-gray-900 max-w-[120px] truncate">
                    {user?.display_name || user?.first_name}
                  </span>
                  <button onClick={logout} className="text-sm text-gray-400 hover:text-gray-600">
                    {t.logout}
                  </button>
                </div>
              </div>
            ) : (
              <div className={`flex items-center gap-3 ${isRTL ? "flex-row-reverse" : "flex-row"}`}>
                <Link href="/auth/login" className="text-gray-600 hover:text-gray-900 font-medium">
                  {t.login}
                </Link>
                <Link href="/auth/register" className="btn-primary py-2 px-5">
                  {t.register}
                </Link>
              </div>
            )}

            <LanguageSwitcher />
          </div>

          {/* Mobile: language + hamburger */}
          <div className={`md:hidden flex items-center gap-2 ${isRTL ? "flex-row-reverse" : "flex-row"}`}>
            <LanguageSwitcher />
            <button
              className="p-2"
              onClick={toggleMobileMenu}
              aria-label={t.menu}
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
        <div className={`md:hidden bg-white border-t border-gray-100 py-4 px-4 space-y-1 ${isRTL ? "text-right" : "text-left"}`}>
          {!isAdminPage && (
            <>
              {showFindWork && (
                <Link href="/jobs" className="block py-2.5 px-3 rounded-lg text-gray-700 font-medium hover:bg-gray-50">
                  {t.findWork}
                </Link>
              )}
              {showFindFreelancers && (
                <Link href="/freelancers" className="block py-2.5 px-3 rounded-lg text-gray-700 font-medium hover:bg-gray-50">
                  {t.findFreelancers}
                </Link>
              )}
              <Link href="/gigs" className="block py-2.5 px-3 rounded-lg text-gray-700 font-medium hover:bg-gray-50">
                {t.services}
              </Link>
              {showRequests && (
                <Link href="/requests" className="block py-2.5 px-3 rounded-lg text-gray-700 font-medium hover:bg-gray-50">
                  {t.requests}
                </Link>
              )}
              {showPostJob && (
                <Link href="/jobs/new" className="block py-2.5 px-3 rounded-lg text-gray-700 font-medium hover:bg-gray-50">
                  {isRTL ? "نشر وظيفة" : "Post a Job"}
                </Link>
              )}
            </>
          )}
          {isAuthenticated ? (
            <>
              {!isAdminPage && (
                <>
                  <Link href="/dashboard" className="block py-2.5 px-3 rounded-lg text-gray-700 font-medium hover:bg-gray-50">
                    {t.dashboard}
                  </Link>
                  <Link href="/dashboard/messages" className="block py-2.5 px-3 rounded-lg text-gray-700 font-medium hover:bg-gray-50">
                    {t.messages}
                  </Link>
                  <Link href="/dashboard/notifications" className="block py-2.5 px-3 rounded-lg text-gray-700 font-medium hover:bg-gray-50">
                    {t.notifications}
                  </Link>
                </>
              )}
              {user?.is_superuser && (
                <Link href="/admin" className="block py-2.5 px-3 rounded-lg text-red-600 font-medium hover:bg-red-50">
                  {t.admin}
                </Link>
              )}
              <div className="border-t border-gray-100 mt-2 pt-2">
                <div className={`flex items-center gap-3 px-3 py-2 ${isRTL ? "flex-row-reverse" : "flex-row"}`}>
                  <div className="w-8 h-8 rounded-full overflow-hidden bg-brand-100 text-brand-600 flex items-center justify-center font-semibold text-sm shrink-0">
                    {user?.avatar_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={`${backendUrl(user.avatar_url)}?v=${new Date(user.updated_at).getTime()}`}
                        alt={user.first_name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <>{user?.first_name?.[0]}{user?.last_name?.[0]}</>
                    )}
                  </div>
                  <span className="text-sm font-medium text-gray-900">
                    {user?.display_name || `${user?.first_name} ${user?.last_name}`}
                  </span>
                </div>
                <button
                  onClick={logout}
                  className="block w-full py-2.5 px-3 rounded-lg text-gray-700 font-medium hover:bg-gray-50 text-start"
                >
                  {t.logout}
                </button>
              </div>
            </>
          ) : (
            <>
              <Link href="/auth/login" className="block py-2.5 px-3 rounded-lg text-gray-700 font-medium hover:bg-gray-50">
                {t.login}
              </Link>
              <Link href="/auth/register" className="block mt-2 btn-primary text-center">
                {t.register}
              </Link>
            </>
          )}
        </div>
      )}
    </nav>
  );
}
