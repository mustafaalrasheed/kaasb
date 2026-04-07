/**
 * Freelancers listing page — server component wrapper for SEO metadata.
 */

import type { Metadata } from "next";
import { cookies } from "next/headers";
import FreelancersClient from "./freelancers-client";
import { SITE_NAME, SITE_URL, KEYWORDS, ogImageUrl } from "@/lib/seo";

export async function generateMetadata(): Promise<Metadata> {
  const cookieStore = await cookies();
  const locale = cookieStore.get("locale")?.value === "en" ? "en" : "ar";
  const ar = locale === "ar";

  const title = ar ? "ابحث عن مستقلين" : "Find Freelancers";
  const description = ar
    ? "وظّف مستقلين موهوبين في العراق والشرق الأوسط. تصفّح المطورين والمصممين والكتّاب والمزيد على كاسب. فلتر حسب المهارات والخبرة والتقييمات."
    : "Hire talented freelancers in Iraq and the Middle East. Browse developers, designers, writers, and more on Kaasb. Filter by skills, experience, and ratings.";

  return {
    title,
    description,
    keywords: KEYWORDS.freelancers,
    alternates: { canonical: "/freelancers" },
    openGraph: {
      title: `${title} | ${SITE_NAME}`,
      description,
      url: `${SITE_URL}/freelancers`,
      type: "website",
      images: [
        {
          url: ogImageUrl({ title, subtitle: ar ? "وظّف محترفين موهوبين على كاسب" : "Hire talented professionals on Kaasb", type: "profile" }),
          width: 1200,
          height: 630,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: `${title} | ${SITE_NAME}`,
      description,
    },
  };
}

export default function FreelancersPage() {
  return <FreelancersClient />;
}
