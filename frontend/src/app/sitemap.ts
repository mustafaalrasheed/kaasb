/**
 * Kaasb Platform - Dynamic Sitemap
 * Generates sitemap.xml with static + dynamic routes.
 * Fetches active jobs and freelancer profiles from the backend API.
 *
 * @see https://nextjs.org/docs/app/api-reference/file-conventions/metadata/sitemap
 */

import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/seo";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

/** Safely fetch JSON from backend — returns null on failure */
async function safeFetch<T>(url: string): Promise<T | null> {
  try {
    const res = await fetch(url, {
      next: { revalidate: 3600 }, // Re-generate sitemap every hour
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date().toISOString();

  // === Static Pages ===
  const staticRoutes: MetadataRoute.Sitemap = [
    {
      url: SITE_URL,
      lastModified: now,
      changeFrequency: "daily",
      priority: 1.0,
    },
    {
      url: `${SITE_URL}/services`,
      lastModified: now,
      changeFrequency: "hourly",
      priority: 0.9,
    },
    {
      url: `${SITE_URL}/jobs`,
      lastModified: now,
      changeFrequency: "hourly",
      priority: 0.9,
    },
    {
      url: `${SITE_URL}/freelancers`,
      lastModified: now,
      changeFrequency: "daily",
      priority: 0.8,
    },
    {
      url: `${SITE_URL}/how-it-works`,
      lastModified: now,
      changeFrequency: "monthly",
      priority: 0.6,
    },
    {
      url: `${SITE_URL}/faq`,
      lastModified: now,
      changeFrequency: "monthly",
      priority: 0.6,
    },
    {
      url: `${SITE_URL}/help`,
      lastModified: now,
      changeFrequency: "monthly",
      priority: 0.5,
    },
    {
      url: `${SITE_URL}/privacy`,
      lastModified: now,
      changeFrequency: "yearly",
      priority: 0.3,
    },
    {
      url: `${SITE_URL}/terms`,
      lastModified: now,
      changeFrequency: "yearly",
      priority: 0.3,
    },
    {
      url: `${SITE_URL}/auth/login`,
      lastModified: now,
      changeFrequency: "monthly",
      priority: 0.3,
    },
    {
      url: `${SITE_URL}/auth/register`,
      lastModified: now,
      changeFrequency: "monthly",
      priority: 0.4,
    },
  ];

  // === Dynamic Routes: Jobs ===
  const jobsData = await safeFetch<{
    jobs: Array<{
      id: string;
      updated_at?: string;
      created_at: string;
      published_at?: string;
    }>;
  }>(`${API_URL}/jobs?page_size=500&status=open`);

  const jobRoutes: MetadataRoute.Sitemap = jobsData?.jobs
    ? jobsData.jobs.map((job) => ({
        url: `${SITE_URL}/jobs/${job.id}`,
        lastModified: job.updated_at || job.published_at || job.created_at,
        changeFrequency: "daily" as const,
        priority: 0.7,
      }))
    : [];

  // === Dynamic Routes: Freelancer Profiles ===
  const freelancersData = await safeFetch<{
    users: Array<{
      username: string;
      updated_at?: string;
      created_at: string;
    }>;
  }>(`${API_URL}/users/freelancers?page_size=500`);

  const profileRoutes: MetadataRoute.Sitemap = freelancersData?.users
    ? freelancersData.users.map((user) => ({
        url: `${SITE_URL}/profile/${user.username}`,
        lastModified: user.updated_at || user.created_at,
        changeFrequency: "weekly" as const,
        priority: 0.6,
      }))
    : [];

  // === Dynamic Routes: Services (gigs) ===
  const servicesData = await safeFetch<{
    services: Array<{
      slug: string;
      updated_at?: string;
      created_at: string;
    }>;
  }>(`${API_URL}/services?page_size=500&status=active`);

  const serviceRoutes: MetadataRoute.Sitemap = servicesData?.services
    ? servicesData.services.map((s) => ({
        url: `${SITE_URL}/services/${s.slug}`,
        lastModified: s.updated_at || s.created_at,
        changeFrequency: "weekly" as const,
        priority: 0.7,
      }))
    : [];

  return [...staticRoutes, ...jobRoutes, ...profileRoutes, ...serviceRoutes];
}
