/**
 * Kaasb Platform - JSON-LD Structured Data Components
 * Provides search engine-readable structured data for rich results.
 *
 * @see https://schema.org
 * @see https://developers.google.com/search/docs/appearance/structured-data
 */

import { SITE_URL, SITE_NAME, SOCIAL, SITE_DESCRIPTION } from "@/lib/seo";

// === Type Definitions ===

interface JsonLdProps {
  data: Record<string, unknown>;
}

/** Renders a <script type="application/ld+json"> tag */
function JsonLd({ data }: JsonLdProps) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}

// === Organization Schema (site-wide) ===

export function OrganizationJsonLd() {
  return (
    <JsonLd
      data={{
        "@context": "https://schema.org",
        "@type": "Organization",
        name: SITE_NAME,
        url: SITE_URL,
        logo: `${SITE_URL}/logo.png`,
        description: SITE_DESCRIPTION,
        foundingDate: "2024",
        foundingLocation: {
          "@type": "Place",
          name: "Baghdad, Iraq",
        },
        areaServed: [
          { "@type": "Country", name: "Iraq" },
          { "@type": "GeoShape", name: "Middle East" },
        ],
        sameAs: [
          SOCIAL.facebook,
          SOCIAL.linkedin,
          SOCIAL.instagram,
          SOCIAL.telegram,
        ],
        contactPoint: {
          "@type": "ContactPoint",
          contactType: "customer service",
          availableLanguage: ["English", "Arabic"],
        },
      }}
    />
  );
}

// === WebSite Schema (enables sitelinks search box in Google) ===

export function WebSiteJsonLd() {
  return (
    <JsonLd
      data={{
        "@context": "https://schema.org",
        "@type": "WebSite",
        name: SITE_NAME,
        url: SITE_URL,
        description: SITE_DESCRIPTION,
        inLanguage: ["en", "ar"],
        potentialAction: {
          "@type": "SearchAction",
          target: {
            "@type": "EntryPoint",
            urlTemplate: `${SITE_URL}/jobs?q={search_term_string}`,
          },
          "query-input": "required name=search_term_string",
        },
      }}
    />
  );
}

// === JobPosting Schema ===

interface JobJsonLdProps {
  title: string;
  description: string;
  publishedAt: string;
  category: string;
  jobType: "fixed" | "hourly";
  budgetMin?: number | null;
  budgetMax?: number | null;
  fixedPrice?: number | null;
  experienceLevel?: string | null;
  skills?: string[] | null;
  deadline?: string | null;
  clientName: string;
  jobUrl: string;
}

export function JobPostingJsonLd(props: JobJsonLdProps) {
  const salary: Record<string, unknown> = {
    "@type": "MonetaryAmount",
    currency: "IQD",
  };

  if (props.jobType === "fixed" && props.fixedPrice) {
    salary.value = {
      "@type": "QuantitativeValue",
      value: props.fixedPrice,
      unitText: "PROJECT",
    };
  } else if (props.budgetMin || props.budgetMax) {
    salary.value = {
      "@type": "QuantitativeValue",
      minValue: props.budgetMin || 0,
      maxValue: props.budgetMax || props.budgetMin || 0,
      unitText: "HOUR",
    };
  }

  return (
    <JsonLd
      data={{
        "@context": "https://schema.org",
        "@type": "JobPosting",
        title: props.title,
        description: props.description,
        datePosted: props.publishedAt,
        ...(props.deadline && { validThrough: props.deadline }),
        employmentType: "CONTRACTOR",
        jobLocationType: "TELECOMMUTE",
        baseSalary: salary,
        hiringOrganization: {
          "@type": "Organization",
          name: props.clientName,
          sameAs: SITE_URL,
        },
        applicantLocationRequirements: {
          "@type": "Country",
          name: "Iraq",
        },
        industry: props.category,
        ...(props.skills &&
          props.skills.length > 0 && {
            skills: props.skills.join(", "),
          }),
        ...(props.experienceLevel && {
          experienceRequirements: props.experienceLevel,
        }),
        url: props.jobUrl,
      }}
    />
  );
}

// === Service Schema (for gig/service listings) ===

interface ServiceJsonLdProps {
  name: string;
  description: string;
  category: string;
  providerName: string;
  providerUrl: string;
  url: string;
  price?: number | null;
  priceCurrency?: string;
  rating?: number;
  reviewCount?: number;
  areaServed?: string;
}

export function ServiceJsonLd(props: ServiceJsonLdProps) {
  return (
    <JsonLd
      data={{
        "@context": "https://schema.org",
        "@type": "Service",
        name: props.name,
        description:
          props.description.length > 250
            ? props.description.slice(0, 247) + "..."
            : props.description,
        serviceType: props.category,
        provider: {
          "@type": "Person",
          name: props.providerName,
          url: props.providerUrl,
        },
        url: props.url,
        areaServed: {
          "@type": "Country",
          name: props.areaServed || "Iraq",
        },
        ...(props.price && {
          offers: {
            "@type": "Offer",
            price: props.price,
            priceCurrency: props.priceCurrency || "IQD",
            availability: "https://schema.org/InStock",
          },
        }),
        ...(props.reviewCount &&
          props.reviewCount > 0 && {
            aggregateRating: {
              "@type": "AggregateRating",
              ratingValue: props.rating,
              reviewCount: props.reviewCount,
              bestRating: 5,
              worstRating: 1,
            },
          }),
      }}
    />
  );
}

// === Person Schema (Freelancer Profile) ===

interface PersonJsonLdProps {
  name: string;
  username: string;
  title?: string | null;
  bio?: string | null;
  avatarUrl?: string | null;
  skills?: string[] | null;
  country?: string | null;
  city?: string | null;
  hourlyRate?: number | null;
  rating?: number;
  reviewCount?: number;
  profileUrl: string;
}

export function PersonJsonLd(props: PersonJsonLdProps) {
  return (
    <JsonLd
      data={{
        "@context": "https://schema.org",
        "@type": "Person",
        name: props.name,
        url: props.profileUrl,
        ...(props.title && { jobTitle: props.title }),
        ...(props.bio && { description: props.bio }),
        ...(props.avatarUrl && { image: props.avatarUrl }),
        ...(props.skills &&
          props.skills.length > 0 && { knowsAbout: props.skills }),
        ...(props.country && {
          address: {
            "@type": "PostalAddress",
            addressCountry: props.country,
            ...(props.city && { addressLocality: props.city }),
          },
        }),
        ...(props.hourlyRate && {
          makesOffer: {
            "@type": "Offer",
            priceSpecification: {
              "@type": "UnitPriceSpecification",
              price: props.hourlyRate,
              priceCurrency: "IQD",
              unitCode: "HUR",
            },
          },
        }),
        ...(props.reviewCount &&
          props.reviewCount > 0 && {
            aggregateRating: {
              "@type": "AggregateRating",
              ratingValue: props.rating,
              reviewCount: props.reviewCount,
              bestRating: 5,
              worstRating: 1,
            },
          }),
        memberOf: {
          "@type": "Organization",
          name: SITE_NAME,
          url: SITE_URL,
        },
      }}
    />
  );
}

// === AggregateRating Schema (standalone) ===

interface AggregateRatingJsonLdProps {
  itemName: string;
  itemType: "Organization" | "Person" | "Product" | "Service";
  ratingValue: number;
  reviewCount: number;
  bestRating?: number;
  worstRating?: number;
}

export function AggregateRatingJsonLd(props: AggregateRatingJsonLdProps) {
  return (
    <JsonLd
      data={{
        "@context": "https://schema.org",
        "@type": props.itemType,
        name: props.itemName,
        aggregateRating: {
          "@type": "AggregateRating",
          ratingValue: props.ratingValue,
          reviewCount: props.reviewCount,
          bestRating: props.bestRating || 5,
          worstRating: props.worstRating || 1,
        },
      }}
    />
  );
}

// === BreadcrumbList Schema ===

interface BreadcrumbItem {
  name: string;
  href: string;
}

export function BreadcrumbJsonLd({ items }: { items: BreadcrumbItem[] }) {
  return (
    <JsonLd
      data={{
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        itemListElement: items.map((item, i) => ({
          "@type": "ListItem",
          position: i + 1,
          name: item.name,
          item: `${SITE_URL}${item.href}`,
        })),
      }}
    />
  );
}

// === FAQ Schema (for landing pages) ===

interface FaqItem {
  question: string;
  answer: string;
}

export function FaqJsonLd({ items }: { items: FaqItem[] }) {
  return (
    <JsonLd
      data={{
        "@context": "https://schema.org",
        "@type": "FAQPage",
        mainEntity: items.map((item) => ({
          "@type": "Question",
          name: item.question,
          acceptedAnswer: {
            "@type": "Answer",
            text: item.answer,
          },
        })),
      }}
    />
  );
}

// === ItemList Schema (for listing pages with SEO-friendly pagination) ===

interface ItemListJsonLdProps {
  name: string;
  description: string;
  items: Array<{
    name: string;
    url: string;
    position: number;
    image?: string;
    description?: string;
  }>;
  totalItems?: number;
  url: string;
}

export function ItemListJsonLd(props: ItemListJsonLdProps) {
  return (
    <JsonLd
      data={{
        "@context": "https://schema.org",
        "@type": "ItemList",
        name: props.name,
        description: props.description,
        url: props.url,
        numberOfItems: props.totalItems || props.items.length,
        itemListElement: props.items.map((item) => ({
          "@type": "ListItem",
          position: item.position,
          name: item.name,
          url: item.url,
          ...(item.image && { image: item.image }),
          ...(item.description && { description: item.description }),
        })),
      }}
    />
  );
}
