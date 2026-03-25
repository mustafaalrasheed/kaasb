/**
 * Job detail page — server component with dynamic metadata.
 * Fetches job data server-side via generateMetadata() for proper OG tags,
 * title, and description that crawlers and social media previews can read.
 */

import type { Metadata } from "next";
import JobDetailClient from "./job-detail-client";
import {
  SITE_NAME,
  SITE_URL,
  ogImageUrl,
  jobDetailMeta,
  canonicalUrl,
} from "@/lib/seo";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

/** Fetch job data server-side for metadata generation */
async function fetchJobForMeta(id: string) {
  try {
    const res = await fetch(`${API_URL}/jobs/${id}`, {
      next: { revalidate: 300 }, // Cache for 5 minutes
    });
    if (!res.ok) return null;
    const json = await res.json();
    return json.data || json;
  } catch {
    return null;
  }
}

function formatBudgetStr(job: {
  job_type: string;
  fixed_price?: number | null;
  budget_min?: number | null;
  budget_max?: number | null;
}): string {
  if (job.job_type === "fixed" && job.fixed_price) {
    return `$${job.fixed_price.toLocaleString()}`;
  }
  if (job.budget_min && job.budget_max) {
    return `$${job.budget_min} - $${job.budget_max}/hr`;
  }
  if (job.budget_min) return `From $${job.budget_min}/hr`;
  return "";
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const job = await fetchJobForMeta(id);

  // Fallback to generic metadata if API is unavailable
  if (!job) {
    return {
      title: "Job Details",
      description:
        "View job details, requirements, and budget. Submit your proposal and start freelancing on Kaasb.",
      openGraph: {
        title: `Job Details | ${SITE_NAME}`,
        description:
          "View job details, requirements, and budget on Kaasb — Iraq's leading freelancing platform.",
        url: `${SITE_URL}/jobs`,
        type: "website",
        images: [
          {
            url: ogImageUrl({
              title: "Job Details",
              subtitle: "View requirements and submit your proposal",
              type: "job",
            }),
            width: 1200,
            height: 630,
          },
        ],
      },
    };
  }

  return jobDetailMeta({
    title: job.title,
    description: job.description,
    category: job.category,
    id: id,
    budget: formatBudgetStr(job),
    skills: job.skills_required,
  });
}

export default function JobDetailPage() {
  return <JobDetailClient />;
}
