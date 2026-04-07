import type { Metadata } from "next";
import { cookies } from "next/headers";
import { GigsCatalog } from "@/components/gigs/gigs-catalog";
import { gigsApi } from "@/lib/api";
import { SITE_NAME, SITE_URL, ogImageUrl } from "@/lib/seo";

export async function generateMetadata(): Promise<Metadata> {
  const cookieStore = await cookies();
  const locale = cookieStore.get("locale")?.value === "en" ? "en" : "ar";
  const ar = locale === "ar";

  const title = ar ? "الخدمات" : "Services";
  const description = ar
    ? "تصفّح خدمات المستقلين في التصميم والبرمجة والكتابة والترجمة والتسويق والمزيد على كاسب. اطلب خدمتك الآن بأمان عبر كي كارد."
    : "Browse freelancer services in design, programming, writing, translation, marketing, and more on Kaasb. Order securely via Qi Card.";

  return {
    title,
    description,
    alternates: { canonical: "/gigs" },
    openGraph: {
      title: `${title} | ${SITE_NAME}`,
      description,
      url: `${SITE_URL}/gigs`,
      type: "website",
      images: [
        {
          url: ogImageUrl({ title, subtitle: ar ? "خدمات احترافية على كاسب" : "Professional services on Kaasb", type: "page" }),
          width: 1200,
          height: 630,
        },
      ],
    },
  };
}

export default async function GigsPage() {
  let categories: unknown[] = [];
  try {
    const res = await gigsApi.getCategories();
    categories = res.data?.data || res.data || [];
  } catch {}

  return <GigsCatalog initialCategories={categories} />;
}
