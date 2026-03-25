/**
 * Jobs listing page — server component wrapper for SEO metadata.
 * The interactive UI is rendered by the client component (jobs-client.tsx).
 */

import type { Metadata } from "next";
import JobsClient from "./jobs-client";
import { SITE_URL, KEYWORDS, SITE_NAME, ogImageUrl } from "@/lib/seo";

export const metadata: Metadata = {
  title: "Browse Freelance Jobs",
  description:
    "Find freelance jobs in web development, design, data science, marketing, and more. Browse open projects and submit proposals on Kaasb — Iraq's top freelancing platform.",
  keywords: KEYWORDS.jobs,
  alternates: { canonical: "/jobs" },
  openGraph: {
    title: `Browse Freelance Jobs | ${SITE_NAME}`,
    description:
      "Find freelance jobs in web development, design, data science, marketing, and more on Kaasb.",
    url: `${SITE_URL}/jobs`,
    type: "website",
    images: [
      {
        url: ogImageUrl({ title: "Browse Freelance Jobs", subtitle: "Find your next project on Kaasb", type: "job" }),
        width: 1200,
        height: 630,
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: `Browse Freelance Jobs | ${SITE_NAME}`,
    description:
      "Find freelance jobs in web development, design, data science, marketing, and more on Kaasb.",
  },
};

export default function JobsPage() {
  return <JobsClient />;
}
