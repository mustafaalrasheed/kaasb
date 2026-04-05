"use client";

import { useAuthStore } from "@/lib/auth-store";
import Link from "next/link";

export default function DashboardPage() {
  const { user } = useAuthStore();

  const isFreelancer = user?.primary_role === "freelancer";
  const profileComplete = Boolean(
    user?.bio && user?.country && (isFreelancer ? user?.skills?.length : true)
  );

  return (
    <div className="space-y-6">
      {/* Welcome header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          أهلاً بعودتك، {user?.first_name}!
        </h1>
        <p className="mt-1 text-gray-600">
          إليك ملخص حسابك على كاسب.
        </p>
      </div>

      {/* Profile completion prompt */}
      {!profileComplete && (
        <div className="card p-5 border-r-4 border-r-warning-500 bg-warning-50/50">
          <h3 className="font-semibold text-gray-900">
            أكمل ملفك الشخصي
          </h3>
          <p className="mt-1 text-sm text-gray-600">
            {isFreelancer
              ? "أضف نبذتك ومهاراتك وسعر الساعة لبدء استقبال العروض."
              : "أضف نبذتك وموقعك لمساعدة المستقلين على فهم احتياجاتك."}
          </p>
          <Link
            href="/dashboard/profile/edit"
            className="inline-block mt-3 btn-primary py-2 px-4 text-sm"
          >
            إكمال الملف الشخصي
          </Link>
        </div>
      )}

      {/* Stats grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {isFreelancer ? (
          <>
            <StatCard
              label="إجمالي الأرباح"
              value={`${(user?.total_earnings ?? 0).toLocaleString("ar-IQ")} د.ع`}
              icon="💰"
            />
            <StatCard
              label="الوظائف المنجزة"
              value={user?.jobs_completed ?? 0}
              icon="✅"
            />
            <StatCard
              label="متوسط التقييم"
              value={user?.avg_rating ? `${user.avg_rating.toFixed(1)} / 5` : "—"}
              icon="⭐"
            />
            <StatCard
              label="عدد التقييمات"
              value={user?.total_reviews ?? 0}
              icon="💬"
            />
          </>
        ) : (
          <>
            <StatCard
              label="إجمالي الإنفاق"
              value={`${(user?.total_spent ?? 0).toLocaleString("ar-IQ")} د.ع`}
              icon="💳"
            />
            <StatCard
              label="الوظائف النشطة"
              value={0}
              icon="📋"
            />
            <StatCard
              label="المستقلون الموظَّفون"
              value={user?.jobs_completed ?? 0}
              icon="🤝"
            />
            <StatCard
              label="التقييمات المعلقة"
              value={0}
              icon="⏳"
            />
          </>
        )}
      </div>

      {/* Quick actions */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          إجراءات سريعة
        </h2>
        <div className="flex flex-wrap gap-3">
          {isFreelancer ? (
            <>
              <Link href="/jobs" className="btn-primary py-2 px-5 text-sm">
                استعراض الوظائف
              </Link>
              <Link
                href="/dashboard/profile/edit"
                className="btn-secondary py-2 px-5 text-sm"
              >
                تعديل الملف الشخصي
              </Link>
            </>
          ) : (
            <>
              <Link href="/jobs/new" className="btn-primary py-2 px-5 text-sm">
                نشر وظيفة
              </Link>
              <Link
                href="/freelancers"
                className="btn-secondary py-2 px-5 text-sm"
              >
                البحث عن مستقلين
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: string | number;
  icon: string;
}) {
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
