/**
 * Freelancers listing page — server component wrapper for SEO metadata.
 */

import type { Metadata } from "next";
import FreelancersClient from "./freelancers-client";
import { SITE_NAME, SITE_URL, KEYWORDS, ogImageUrl } from "@/lib/seo";

export const metadata: Metadata = {
  title: "Find Freelancers",
  description:
    "Hire talented freelancers in Iraq and the Middle East. Browse developers, designers, writers, and more on Kaasb. Filter by skills, experience, and ratings.",
  keywords: KEYWORDS.freelancers,
  alternates: { canonical: "/freelancers" },
  openGraph: {
    title: `Find Freelancers | ${SITE_NAME}`,
    description:
      "Hire talented freelancers in Iraq and the Middle East on Kaasb.",
    url: `${SITE_URL}/freelancers`,
    type: "website",
    images: [
      {
        url: ogImageUrl({ title: "Find Freelancers", subtitle: "Hire talented professionals on Kaasb", type: "profile" }),
        width: 1200,
        height: 630,
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: `Find Freelancers | ${SITE_NAME}`,
    description:
      "Hire talented freelancers in Iraq and the Middle East on Kaasb.",
  },
};

export default function FreelancersPage() {
  return <FreelancersClient />;
}
