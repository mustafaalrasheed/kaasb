"use client";

import { useAuthStore } from "@/lib/auth-store";
import { useLocale } from "@/providers/locale-provider";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import Link from "next/link";

export default function DashboardPage() {
  const { user } = useAuthStore();
  const { locale } = useLocale();
  const router = useRouter();
  const ar = locale === "ar";

  // Admins have no business on the user dashboard — send them to admin panel
  useEffect(() => {
    if (user?.is_superuser) {
      router.replace("/admin");
    }
  }, [user, router]);

  if (user?.is_superuser) return null;

  const isFreelancer = user?.primary_role === "freelancer";
  const profileComplete = Boolean(
    user?.bio && user?.country && (isFreelancer ? user?.skills?.length : true)
  );

  const currency = ar ? "د.ع" : "IQD";
  const numLocale = ar ? "ar-IQ" : "en-US";

  return (
    <div className="space-y-6">
      {/* Welcome header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          {ar ? `أهلاً بعودتك، ${user?.first_name}!` : `Welcome back, ${user?.first_name}!`}
        </h1>
        <p className="mt-1 text-gray-600">
          {ar ? "إليك ملخص حسابك على كاسب." : "Here's a summary of your Kaasb account."}
        </p>
      </div>

      {/* Profile completion prompt */}
      {!profileComplete && (
        <div className="card p-5 border-s-4 border-s-warning-500 bg-warning-50/50">
          <h3 className="font-semibold text-gray-900">
            {ar ? "أكمل ملفك الشخصي" : "Complete your profile"}
          </h3>
          <p className="mt-1 text-sm text-gray-600">
            {isFreelancer
              ? (ar ? "أضف نبذتك ومهاراتك ومستوى خبرتك لبدء استقبال العروض."
                     : "Add your bio, skills and experience level to start receiving offers.")
              : (ar ? "أضف نبذتك وموقعك لمساعدة المستقلين على فهم احتياجاتك."
                     : "Add your bio and location to help freelancers understand your needs.")}
          </p>
          <Link href="/dashboard/profile/edit" className="inline-block mt-3 btn-primary py-2 px-4 text-sm">
            {ar ? "إكمال الملف الشخصي" : "Complete profile"}
          </Link>
        </div>
      )}

      {/* Stats grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {isFreelancer ? (
          <>
            <StatCard label={ar ? "إجمالي الأرباح" : "Total Earnings"}
              value={`${(user?.total_earnings ?? 0).toLocaleString(numLocale)} ${currency}`} icon="💰" />
            <StatCard label={ar ? "الوظائف المنجزة" : "Jobs Completed"}
              value={user?.jobs_completed ?? 0} icon="✅" />
            <StatCard label={ar ? "متوسط التقييم" : "Avg. Rating"}
              value={user?.avg_rating ? `${user.avg_rating.toFixed(1)} / 5` : "—"} icon="⭐" />
            <StatCard label={ar ? "عدد التقييمات" : "Total Reviews"}
              value={user?.total_reviews ?? 0} icon="💬" />
          </>
        ) : (
          <>
            <StatCard label={ar ? "إجمالي الإنفاق" : "Total Spent"}
              value={`${(user?.total_spent ?? 0).toLocaleString(numLocale)} ${currency}`} icon="💳" />
            <StatCard label={ar ? "التقييمات المُعطاة" : "Reviews Given"}
              value={user?.total_reviews ?? 0} icon="🤝" />
            <StatCard label={ar ? "متوسط التقييم" : "Avg. Rating"}
              value={user?.avg_rating ? `${user.avg_rating.toFixed(1)} / 5` : "—"} icon="⭐" />
            <StatCard label={ar ? "الوظائف المنشورة" : "Jobs Posted"}
              value="—" icon="📋" />
          </>
        )}
      </div>

      {/* Quick actions */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          {ar ? "إجراءات سريعة" : "Quick Actions"}
        </h2>
        <div className="flex flex-wrap gap-3">
          {isFreelancer ? (
            <>
              <Link href="/jobs" className="btn-primary py-2 px-5 text-sm">
                {ar ? "استعراض الوظائف" : "Browse Jobs"}
              </Link>
              <Link href="/dashboard/profile/edit" className="btn-secondary py-2 px-5 text-sm">
                {ar ? "تعديل الملف الشخصي" : "Edit Profile"}
              </Link>
            </>
          ) : (
            <>
              <Link href="/jobs/new" className="btn-primary py-2 px-5 text-sm">
                {ar ? "نشر وظيفة" : "Post a Job"}
              </Link>
              <Link href="/freelancers" className="btn-secondary py-2 px-5 text-sm">
                {ar ? "البحث عن مستقلين" : "Find Freelancers"}
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, icon }: { label: string; value: string | number; icon: string }) {
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">{label}</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">{value}</p>
        </div>
        <span className="text-3xl">{icon}</span>
      </div>
    </div>
  );
}
