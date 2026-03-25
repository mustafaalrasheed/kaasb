"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { usersApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { backendUrl } from "@/lib/utils";
import type { UserProfile } from "@/types/user";
import { Breadcrumbs } from "@/components/seo/breadcrumbs";
import { PersonJsonLd } from "@/components/seo/json-ld";
import { canonicalUrl } from "@/lib/seo";

export default function ProfileClient() {
  const params = useParams();
  const username = params.username as string;
  const { user: currentUser } = useAuthStore();

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadProfile() {
      try {
        const response = await usersApi.getProfile(username);
        setProfile(response.data);
      } catch (err: any) {
        setError(
          err.response?.status === 404
            ? "User not found"
            : "Failed to load profile"
        );
      } finally {
        setIsLoading(false);
      }
    }
    if (username) loadProfile();
  }, [username]);

  if (isLoading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-gray-500">Loading profile...</div>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-center">
          <p className="text-xl font-semibold text-gray-900">{error}</p>
          <Link href="/" className="mt-4 inline-block text-brand-500 hover:text-brand-600">
            Go home
          </Link>
        </div>
      </div>
    );
  }

  const isOwnProfile = currentUser?.username === profile.username;
  const isFreelancer = profile.primary_role === "freelancer";
  const fullName =
    profile.display_name || `${profile.first_name} ${profile.last_name}`;

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Person JSON-LD */}
      <PersonJsonLd
        name={fullName}
        username={profile.username}
        title={profile.title}
        bio={profile.bio}
        avatarUrl={profile.avatar_url ? backendUrl(profile.avatar_url) : null}
        skills={profile.skills}
        country={profile.country}
        city={profile.city}
        hourlyRate={profile.hourly_rate}
        rating={profile.avg_rating}
        reviewCount={profile.total_reviews}
        profileUrl={canonicalUrl(`/profile/${profile.username}`)}
      />

      {/* Breadcrumbs */}
      <Breadcrumbs
        items={[
          ...(isFreelancer
            ? [{ name: "Freelancers", href: "/freelancers" }]
            : []),
          { name: fullName, href: `/profile/${profile.username}` },
        ]}
        className="mb-4"
      />

      {/* Profile Header */}
      <div className="card p-6 sm:p-8">
        <div className="flex flex-col sm:flex-row gap-6">
          {/* Avatar */}
          <div className="shrink-0">
            <div className="w-28 h-28 rounded-full overflow-hidden bg-brand-100 flex items-center justify-center">
              {profile.avatar_url ? (
                <img
                  src={backendUrl(profile.avatar_url)}
                  alt={`${profile.first_name}'s avatar`}
                  className="w-full h-full object-cover"
                />
              ) : (
                <span className="text-4xl font-bold text-brand-500">
                  {profile.first_name[0]}
                  {profile.last_name[0]}
                </span>
              )}
            </div>
          </div>

          {/* Info */}
          <div className="flex-1">
            <div className="flex items-start justify-between">
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  {fullName}
                </h1>
                <p className="text-gray-500">@{profile.username}</p>
                {isFreelancer && profile.title && (
                  <p className="mt-1 text-lg text-gray-700">{profile.title}</p>
                )}
              </div>

              {isOwnProfile && (
                <Link
                  href="/dashboard/profile/edit"
                  className="btn-secondary py-2 px-4 text-sm"
                >
                  Edit Profile
                </Link>
              )}
            </div>

            {/* Location & Status */}
            <div className="mt-3 flex flex-wrap items-center gap-4 text-sm text-gray-600">
              {profile.country && (
                <span className="flex items-center gap-1">
                  📍 {profile.city ? `${profile.city}, ` : ""}
                  {profile.country}
                </span>
              )}
              <span
                className={`flex items-center gap-1 ${
                  profile.is_online ? "text-success-500" : "text-gray-400"
                }`}
              >
                <span
                  className={`inline-block w-2 h-2 rounded-full ${
                    profile.is_online ? "bg-success-500" : "bg-gray-300"
                  }`}
                />
                {profile.is_online ? "Online" : "Offline"}
              </span>
              <span className="text-gray-400">
                Member since{" "}
                <time dateTime={profile.created_at}>
                  {new Date(profile.created_at).toLocaleDateString("en-US", {
                    month: "short",
                    year: "numeric",
                  })}
                </time>
              </span>
            </div>

            {/* Freelancer stats row */}
            {isFreelancer && (
              <div className="mt-4 flex flex-wrap gap-6 text-sm">
                {profile.hourly_rate && (
                  <div>
                    <span className="font-semibold text-gray-900 text-lg">
                      ${profile.hourly_rate}
                    </span>
                    <span className="text-gray-500">/hr</span>
                  </div>
                )}
                <div>
                  <span className="font-semibold text-gray-900">
                    {profile.avg_rating > 0
                      ? `⭐ ${profile.avg_rating.toFixed(1)}`
                      : "No ratings yet"}
                  </span>
                  {profile.total_reviews > 0 && (
                    <span className="text-gray-500">
                      {" "}
                      ({profile.total_reviews} reviews)
                    </span>
                  )}
                </div>
                <div>
                  <span className="font-semibold text-gray-900">
                    {profile.jobs_completed}
                  </span>
                  <span className="text-gray-500"> jobs completed</span>
                </div>
                {profile.experience_level && (
                  <div className="capitalize">
                    <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-brand-50 text-brand-700 border border-brand-200">
                      {profile.experience_level}
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Bio */}
      {profile.bio && (
        <div className="card p-6 mt-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">About</h2>
          <p className="text-gray-700 whitespace-pre-line leading-relaxed">
            {profile.bio}
          </p>
        </div>
      )}

      {/* Skills */}
      {isFreelancer && profile.skills && profile.skills.length > 0 && (
        <div className="card p-6 mt-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Skills</h2>
          <div className="flex flex-wrap gap-2">
            {profile.skills.map((skill) => (
              <span
                key={skill}
                className="px-3 py-1.5 rounded-full text-sm font-medium bg-gray-100 text-gray-700 border border-gray-200"
              >
                {skill}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Portfolio link */}
      {isFreelancer && profile.portfolio_url && (
        <div className="card p-6 mt-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">
            Portfolio
          </h2>
          <a
            href={profile.portfolio_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-brand-500 hover:text-brand-600 font-medium break-all"
          >
            {profile.portfolio_url} →
          </a>
        </div>
      )}

      {/* Share profile */}
      {isFreelancer && (
        <div className="card p-6 mt-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">
            Share Profile
          </h2>
          <div className="flex gap-2">
            <a
              href={`https://wa.me/?text=${encodeURIComponent(`Check out ${fullName} on Kaasb: ${canonicalUrl(`/profile/${profile.username}`)}`)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="py-2 px-4 text-sm rounded-lg bg-green-500 text-white hover:bg-green-600 transition-colors"
              aria-label="Share on WhatsApp"
            >
              WhatsApp
            </a>
            <a
              href={`https://t.me/share/url?url=${encodeURIComponent(canonicalUrl(`/profile/${profile.username}`))}&text=${encodeURIComponent(`${fullName} on Kaasb`)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="py-2 px-4 text-sm rounded-lg bg-blue-500 text-white hover:bg-blue-600 transition-colors"
              aria-label="Share on Telegram"
            >
              Telegram
            </a>
          </div>
        </div>
      )}

      {/* Placeholder for future: Reviews, Job History */}
      <div className="card p-6 mt-6 text-center text-gray-400">
        <p className="text-sm">
          Reviews and job history will appear here once available.
        </p>
      </div>
    </div>
  );
}
