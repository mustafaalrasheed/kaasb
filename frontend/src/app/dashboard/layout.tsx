"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/lib/auth-store";
import { useEffect } from "react";
import { cn, backendUrl } from "@/lib/utils";

const sidebarLinks = [
  { href: "/dashboard", labelAr: "نظرة عامة", labelEn: "Overview", icon: "📊", roles: ["client", "freelancer"] },
  { href: "/dashboard/contracts", labelAr: "العقود", labelEn: "Contracts", icon: "📝", roles: ["client", "freelancer"] },
  { href: "/dashboard/payments", labelAr: "المدفوعات", labelEn: "Payments", icon: "💰", roles: ["client", "freelancer"] },
  { href: "/dashboard/messages", labelAr: "الرسائل", labelEn: "Messages", icon: "💬", roles: ["client", "freelancer"] },
  { href: "/dashboard/notifications", labelAr: "الإشعارات", labelEn: "Notifications", icon: "🔔", roles: ["client", "freelancer"] },
  { href: "/dashboard/reviews", labelAr: "التقييمات", labelEn: "Reviews", icon: "⭐", roles: ["client", "freelancer"] },
  { href: "/dashboard/my-jobs", labelAr: "وظائفي", labelEn: "My Jobs", icon: "📋", roles: ["client"] },
  { href: "/jobs/new", labelAr: "نشر وظيفة", labelEn: "Post a Job", icon: "✏️", roles: ["client"] },
  { href: "/dashboard/gigs", labelAr: "خدماتي", labelEn: "My Gigs", icon: "🛍️", roles: ["freelancer"] },
  { href: "/dashboard/gigs/new", labelAr: "إنشاء خدمة", labelEn: "Create Gig", icon: "✨", roles: ["freelancer"] },
  { href: "/dashboard/gigs/orders", labelAr: "طلبات الخدمات", labelEn: "Gig Orders", icon: "📦", roles: ["client", "freelancer"] },
  { href: "/dashboard/my-proposals", labelAr: "عروضي", labelEn: "My Proposals", icon: "📨", roles: ["freelancer"] },
  { href: "/jobs", labelAr: "ابحث عن عمل", labelEn: "Find Work", icon: "🔍", roles: ["freelancer"] },
  { href: "/dashboard/profile/edit", labelAr: "تعديل الملف", labelEn: "Edit Profile", icon: "👤", roles: ["client", "freelancer"] },
  { href: "/dashboard/settings", labelAr: "الإعدادات", labelEn: "Settings", icon: "⚙️", roles: ["client", "freelancer"] },
  { href: "/admin", labelAr: "لوحة الإدارة", labelEn: "Admin Panel", icon: "🛡️", roles: ["admin"] },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { user, isAuthenticated, isLoading } = useAuthStore();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      window.location.href = "/auth/login";
    }
  }, [isLoading, isAuthenticated]);

  if (isLoading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <p className="text-gray-500">جاري التحميل...</p>
      </div>
    );
  }

  if (!isAuthenticated || !user) return null;

  const filteredLinks = sidebarLinks.filter(
    (link) => link.roles.includes(user.primary_role) || user.is_superuser
  );

  const roleLabel =
    user.primary_role === "client"
      ? "عميل"
      : user.primary_role === "freelancer"
      ? "مستقل"
      : "مدير";

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex flex-col md:flex-row gap-8">
        {/* Sidebar */}
        <aside className="w-full md:w-64 shrink-0">
          <div className="card p-4 sticky top-24">
            {/* User info */}
            <div className="flex items-center gap-3 mb-6 pb-4 border-b border-gray-100">
              <div className="w-10 h-10 rounded-full overflow-hidden bg-brand-100 flex items-center justify-center shrink-0">
                {user.avatar_url ? (
                  <img
                    src={backendUrl(user.avatar_url)}
                    alt={`${user.first_name} ${user.last_name}`}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <span className="text-sm font-bold text-brand-500">
                    {user.first_name[0]}
                    {user.last_name[0]}
                  </span>
                )}
              </div>
              <div className="min-w-0">
                <p className="font-medium text-gray-900 truncate">
                  {user.display_name || `${user.first_name} ${user.last_name}`}
                </p>
                <p className="text-xs text-gray-500">{roleLabel}</p>
              </div>
            </div>

            {/* Navigation */}
            <nav className="space-y-1">
              {filteredLinks.map((link) => {
                const isActive =
                  link.href === "/dashboard"
                    ? pathname === "/dashboard"
                    : pathname.startsWith(link.href);

                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={cn(
                      "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                      isActive
                        ? "bg-brand-50 text-brand-700"
                        : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                    )}
                  >
                    <span className="text-base">{link.icon}</span>
                    {link.labelAr}
                  </Link>
                );
              })}
            </nav>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 min-w-0">{children}</main>
      </div>
    </div>
  );
}
