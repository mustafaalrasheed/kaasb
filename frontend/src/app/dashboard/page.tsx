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
          Welcome back, {user?.first_name}!
        </h1>
        <p className="mt-1 text-gray-600">
          Here&apos;s a summary of your Kaasb account.
        </p>
      </div>

      {/* Profile completion prompt */}
      {!profileComplete && (
        <div className="card p-5 border-l-4 border-l-warning-500 bg-warning-50/50">
          <h3 className="font-semibold text-gray-900">
            Complete your profile
          </h3>
          <p className="mt-1 text-sm text-gray-600">
            {isFreelancer
              ? "Add your bio, skills, and hourly rate to start receiving job proposals."
              : "Add your bio and location to help freelancers understand your needs."}
          </p>
          <Link
            href="/dashboard/profile/edit"
            className="inline-block mt-3 btn-primary py-2 px-4 text-sm"
          >
            Complete Profile
          </Link>
        </div>
      )}

      {/* Stats grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {isFreelancer ? (
          <>
            <StatCard
              label="Total Earnings"
              value={`$${(user?.total_earnings ?? 0).toLocaleString()}`}
              icon="💰"
            />
            <StatCard
              label="Jobs Completed"
              value={user?.jobs_completed ?? 0}
              icon="✅"
            />
            <StatCard
              label="Avg Rating"
              value={
                user?.avg_rating ? `${user.avg_rating.toFixed(1)} / 5.0` : "N/A"
              }
              icon="⭐"
            />
            <StatCard
              label="Total Reviews"
              value={user?.total_reviews ?? 0}
              icon="💬"
            />
          </>
        ) : (
          <>
            <StatCard
              label="Total Spent"
              value={`$${(user?.total_spent ?? 0).toLocaleString()}`}
              icon="💳"
            />
            <StatCard
              label="Active Jobs"
              value={0}
              icon="📋"
            />
            <StatCard
              label="Freelancers Hired"
              value={user?.jobs_completed ?? 0}
              icon="🤝"
            />
            <StatCard
              label="Pending Reviews"
              value={0}
              icon="⏳"
            />
          </>
        )}
      </div>

      {/* Quick actions */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Quick Actions
        </h2>
        <div className="flex flex-wrap gap-3">
          {isFreelancer ? (
            <>
              <Link href="/jobs" className="btn-primary py-2 px-5 text-sm">
                Browse Jobs
              </Link>
              <Link
                href="/dashboard/profile/edit"
                className="btn-secondary py-2 px-5 text-sm"
              >
                Edit Profile
              </Link>
            </>
          ) : (
            <>
              <Link href="/jobs/new" className="btn-primary py-2 px-5 text-sm">
                Post a Job
              </Link>
              <Link
                href="/users/freelancers"
                className="btn-secondary py-2 px-5 text-sm"
              >
                Find Freelancers
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
