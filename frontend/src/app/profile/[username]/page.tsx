/**
 * Public profile page — server component with dynamic metadata.
 * Fetches user profile server-side via generateMetadata() for proper OG tags.
 */

import type { Metadata } from "next";
import ProfileClient from "./profile-client";
import {
  SITE_NAME,
  SITE_URL,
  ogImageUrl,
  profileMeta,
} from "@/lib/seo";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

/** Fetch profile data server-side for metadata generation */
async function fetchProfileForMeta(username: string) {
  try {
    const res = await fetch(`${API_URL}/users/profile/${username}`, {
      next: { revalidate: 600 }, // Cache for 10 minutes
    });
    if (!res.ok) return null;
    const json = await res.json();
    return json.data || json;
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ username: string }>;
}): Promise<Metadata> {
  const { username } = await params;
  const profile = await fetchProfileForMeta(username);

  // Fallback to generic metadata if API is unavailable
  if (!profile) {
    return {
      title: "Freelancer Profile",
      description:
        "View freelancer profile, skills, ratings, and completed projects on Kaasb — Iraq's leading freelancing platform.",
      openGraph: {
        title: `Freelancer Profile | ${SITE_NAME}`,
        description:
          "View freelancer profile, skills, and ratings on Kaasb.",
        url: `${SITE_URL}/freelancers`,
        type: "profile",
        images: [
          {
            url: ogImageUrl({
              title: "Freelancer Profile",
              subtitle: "View skills and ratings on Kaasb",
              type: "profile",
            }),
            width: 1200,
            height: 630,
          },
        ],
      },
    };
  }

  const name =
    profile.display_name ||
    `${profile.first_name} ${profile.last_name}`;

  return profileMeta({
    name,
    username: profile.username,
    title: profile.title,
    bio: profile.bio,
    skills: profile.skills,
    avatarUrl: profile.avatar_url,
  });
}

export default function PublicProfilePage() {
  return <ProfileClient />;
}
