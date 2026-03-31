"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/lib/auth-store";
import { useEffect } from "react";
import { cn, backendUrl } from "@/lib/utils";

const sidebarLinks = [
  { href: "/dashboard", label: "Overview", icon: "📊", roles: ["client", "freelancer"] },
  { href: "/dashboard/contracts", label: "Contracts", icon: "📝", roles: ["client", "freelancer"] },
  { href: "/dashboard/payments", label: "Payments", icon: "💰", roles: ["client", "freelancer"] },
  { href: "/dashboard/messages", label: "Messages", icon: "💬", roles: ["client", "freelancer"] },
  { href: "/dashboard/notifications", label: "Notifications", icon: "🔔", roles: ["client", "freelancer"] },
  { href: "/dashboard/reviews", label: "Reviews", icon: "⭐", roles: ["client", "freelancer"] },
  { href: "/dashboard/my-jobs", label: "My Jobs", icon: "📋", roles: ["client"] },
  { href: "/jobs/new", label: "Post a Job", icon: "✏️", roles: ["client"] },
  { href: "/dashboard/gigs", label: "My Gigs", icon: "🛍️", roles: ["freelancer"] },
  { href: "/dashboard/gigs/new", label: "Create Gig", icon: "✨", roles: ["freelancer"] },
  { href: "/dashboard/my-proposals", label: "My Proposals", icon: "📨", roles: ["freelancer"] },
  { href: "/jobs", label: "Find Work", icon: "🔍", roles: ["freelancer"] },
  { href: "/dashboard/profile/edit", label: "Edit Profile", icon: "👤", roles: ["client", "freelancer"] },
  { href: "/dashboard/settings", label: "Settings", icon: "⚙️", roles: ["client", "freelancer"] },
  { href: "/admin", label: "Admin Panel", icon: "🛡️", roles: ["admin"] },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { user, isAuthenticated, isLoading } = useAuthStore();

  useEffect(() => {
    // If initialize() confirmed the session is invalid, do a full-page redirect.
    // window.location.href (not router.push) forces the middleware to re-evaluate
    // with the now-cleared cookie, landing cleanly on /auth/login.
    if (!isLoading && !isAuthenticated) {
      window.location.href = "/auth/login";
    }
  }, [isLoading, isAuthenticated]);

  if (isLoading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  if (!isAuthenticated || !user) return null;

  const filteredLinks = sidebarLinks.filter(
    (link) => link.roles.includes(user.primary_role) || user.is_superuser
  );

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
                <p className="text-xs text-gray-500 capitalize">
                  {user.primary_role}
                </p>
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
                    {link.label}
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
