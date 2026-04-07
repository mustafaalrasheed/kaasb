/**
 * Jobs listing page — server component wrapper for SEO metadata.
 * The interactive UI is rendered by the client component (jobs-client.tsx).
 */

import type { Metadata } from "next";
import { cookies } from "next/headers";
import JobsClient from "./jobs-client";
import { SITE_URL, KEYWORDS, SITE_NAME, ogImageUrl } from "@/lib/seo";

export async function generateMetadata(): Promise<Metadata> {
  const cookieStore = await cookies();
  const locale = cookieStore.get("locale")?.value === "en" ? "en" : "ar";
  const ar = locale === "ar";

  const title = ar ? "تصفّح الوظائف" : "Browse Freelance Jobs";
  const description = ar
    ? "ابحث عن وظائف عمل حر في تطوير الويب والتصميم وعلوم البيانات والتسويق والمزيد. تصفّح المشاريع وقدّم عروضك على كاسب — منصة العمل الحر الأولى في العراق."
    : "Find freelance jobs in web development, design, data science, marketing, and more. Browse open projects and submit proposals on Kaasb — Iraq's top freelancing platform.";

  return {
    title,
    description,
    keywords: KEYWORDS.jobs,
    alternates: { canonical: "/jobs" },
    openGraph: {
      title: `${title} | ${SITE_NAME}`,
      description,
      url: `${SITE_URL}/jobs`,
      type: "website",
      images: [
        {
          url: ogImageUrl({ title, subtitle: ar ? "ابحث عن مشروعك القادم على كاسب" : "Find your next project on Kaasb", type: "job" }),
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

export default function JobsPage() {
  return <JobsClient />;
}
