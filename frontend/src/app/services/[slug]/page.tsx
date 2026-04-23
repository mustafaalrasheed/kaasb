/**
 * Service detail page — server component with dynamic metadata.
 *
 * Fetches service data server-side via generateMetadata() for proper OG tags,
 * title, and description that crawlers and social media previews can read.
 * Also emits JSON-LD Service schema for Google/Bing rich results.
 *
 * Interactive UI (image carousel, package tabs, order modal, retry logic)
 * lives in the client component. This file exists purely so search engines
 * and link-unfurlers see rendered metadata before any JS runs.
 */

import type { Metadata } from "next";
import ServiceDetailClient from "./service-detail-client";
import { SITE_NAME, SITE_URL, serviceDetailMeta, canonicalUrl } from "@/lib/seo";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface ServicePackageShape {
  price: number;
  delivery_days: number;
  tier: string;
}

interface ServiceShape {
  id: string;
  slug: string;
  title: string;
  description: string;
  tags?: string[];
  images?: string[];
  packages?: ServicePackageShape[];
  freelancer?: {
    first_name: string;
    last_name: string;
    display_name?: string;
  };
  category_name_en?: string;
  category_name_ar?: string;
  avg_rating?: number;
  review_count?: number;
}

/** Fetch service data server-side for metadata generation. */
async function fetchServiceForMeta(slug: string): Promise<ServiceShape | null> {
  try {
    const res = await fetch(`${API_URL}/services/${encodeURIComponent(slug)}`, {
      next: { revalidate: 300 }, // 5-minute ISR cache
    });
    if (!res.ok) return null;
    const json = await res.json();
    return (json.data || json) as ServiceShape;
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const service = await fetchServiceForMeta(slug);

  // Fallback to generic metadata if API is unavailable or service not found.
  if (!service) {
    return {
      title: "Service",
      description:
        "Browse freelance services on Kaasb — Iraq's leading marketplace for creative and technical work.",
      alternates: { canonical: `/services/${slug}` },
      openGraph: {
        title: `Service | ${SITE_NAME}`,
        description:
          "Browse freelance services on Kaasb — Iraq's leading freelancing marketplace.",
        url: canonicalUrl(`/services/${slug}`),
        type: "website",
      },
    };
  }

  const minPrice =
    service.packages && service.packages.length > 0
      ? Math.min(...service.packages.map((p) => p.price))
      : undefined;
  const freelancerName =
    service.freelancer?.display_name ||
    (service.freelancer
      ? `${service.freelancer.first_name} ${service.freelancer.last_name}`
      : undefined);

  return serviceDetailMeta({
    title: service.title,
    description: service.description,
    slug: service.slug,
    category: service.category_name_en,
    minPrice,
    freelancerName,
    rating: service.avg_rating,
    images: service.images,
  });
}

/**
 * JSON-LD Service schema — emitted inside the rendered HTML so search
 * engines can surface rich results (price, rating, provider).
 * https://schema.org/Service
 */
function ServiceJsonLd({ service }: { service: ServiceShape }) {
  const minPrice =
    service.packages && service.packages.length > 0
      ? Math.min(...service.packages.map((p) => p.price))
      : undefined;
  const freelancerName =
    service.freelancer?.display_name ||
    (service.freelancer
      ? `${service.freelancer.first_name} ${service.freelancer.last_name}`
      : "Kaasb freelancer");

  const schema: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "Service",
    name: service.title,
    description: service.description,
    url: canonicalUrl(`/services/${service.slug}`),
    serviceType: service.category_name_en || "Freelance service",
    provider: {
      "@type": "Person",
      name: freelancerName,
    },
    areaServed: {
      "@type": "Country",
      name: "Iraq",
    },
  };

  if (minPrice !== undefined) {
    schema.offers = {
      "@type": "Offer",
      price: minPrice,
      priceCurrency: "IQD",
      availability: "https://schema.org/InStock",
      url: canonicalUrl(`/services/${service.slug}`),
    };
  }

  if (service.avg_rating && service.avg_rating > 0 && service.review_count && service.review_count > 0) {
    schema.aggregateRating = {
      "@type": "AggregateRating",
      ratingValue: service.avg_rating,
      reviewCount: service.review_count,
      bestRating: 5,
      worstRating: 1,
    };
  }

  if (service.images && service.images.length > 0) {
    schema.image = service.images;
  }

  return (
    <script
      type="application/ld+json"
      // JSON.stringify on a plain object is XSS-safe here.
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}

export default async function ServiceDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const service = await fetchServiceForMeta(slug);

  return (
    <>
      {service && <ServiceJsonLd service={service} />}
      <ServiceDetailClient />
    </>
  );
}
