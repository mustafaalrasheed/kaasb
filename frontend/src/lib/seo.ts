/**
 * Kaasb Platform - SEO Configuration
 * Centralized SEO constants, helpers, metadata generators, and slug utilities.
 */

import type { Metadata } from "next";

// === Site-wide SEO Constants ===

export const SITE_NAME = "Kaasb";
export const SITE_TAGLINE = "Iraq's Leading Freelancing Platform";
export const SITE_DESCRIPTION =
  "Kaasb connects businesses with talented freelancers across Iraq and the Middle East. Post jobs, hire experts, and grow your business with secure payments via Qi Card.";
export const SITE_DESCRIPTION_AR =
  "كاسب يربط الشركات بالمستقلين الموهوبين في العراق والشرق الأوسط. انشر مشاريع، وظّف خبراء، ونمّ أعمالك مع دفعات آمنة عبر كي كارد.";

/** Production domain — used for canonical URLs, OG images, sitemaps */
export const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL || "https://kaasb.com";

export const SITE_LOCALE = "en_US";
export const SITE_LOCALE_AR = "ar_IQ";

/** Default OG image (1200x630) */
export const DEFAULT_OG_IMAGE = `${SITE_URL}/og-default.png`;

// === Social Profiles ===
export const SOCIAL = {
  twitter: "@kaasb_iq",
  facebook: "https://facebook.com/kaasb.iq",
  linkedin: "https://linkedin.com/company/kaasb",
  instagram: "https://instagram.com/kaasb.iq",
  telegram: "https://t.me/kaasb_iq",
  whatsapp: "https://wa.me/9647800000000",
} as const;

// === Keyword Sets ===
export const KEYWORDS: Record<string, string[]> = {
  primary: [
    "Kaasb",
    "freelancing Iraq",
    "hire freelancers Iraq",
    "Iraqi freelancers",
    "remote work Iraq",
    "كاسب",
    "عمل حر العراق",
    "مستقلين العراق",
  ],
  jobs: [
    "find jobs Iraq",
    "freelance jobs",
    "remote jobs Middle East",
    "web development jobs Iraq",
    "graphic design jobs",
    "وظائف عمل حر",
    "فرص عمل العراق",
  ],
  freelancers: [
    "hire freelancer Iraq",
    "find developer Iraq",
    "Iraqi developers",
    "Middle East freelancers",
    "وظّف مستقل",
    "مطورين عراقيين",
  ],
} as const;

// === Helpers ===

/** Build a canonical URL from a path */
export function canonicalUrl(path: string): string {
  const clean = path.startsWith("/") ? path : `/${path}`;
  return `${SITE_URL}${clean}`;
}

/** Build full page title */
export function pageTitle(title: string): string {
  return `${title} | ${SITE_NAME}`;
}

/** Build OG image URL for dynamic pages */
export function ogImageUrl(params: {
  title: string;
  subtitle?: string;
  type?: "job" | "profile" | "page" | "service";
}): string {
  const searchParams = new URLSearchParams({
    title: params.title,
    ...(params.subtitle && { subtitle: params.subtitle }),
    ...(params.type && { type: params.type }),
  });
  return `${SITE_URL}/api/og?${searchParams.toString()}`;
}

// === Slug Utility ===

/**
 * Generate an SEO-friendly slug from any text (supports Arabic + Latin).
 * Arabic characters are preserved; Latin is lowercased; spaces become hyphens.
 * Examples:
 *   "Web Development Job" → "web-development-job"
 *   "تصميم مواقع ويب" → "تصميم-مواقع-ويب"
 *   "Full-Stack Developer (React)" → "full-stack-developer-react"
 */
export function generateSlug(text: string): string {
  return text
    .trim()
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s-]/gu, "") // Keep letters (any script), numbers, spaces, hyphens
    .replace(/\s+/g, "-") // Spaces → hyphens
    .replace(/-+/g, "-") // Collapse multiple hyphens
    .replace(/^-|-$/g, ""); // Trim leading/trailing hyphens
}

/**
 * Generate a URL-safe slug with an ID suffix for uniqueness.
 * Example: "Build a website" + "abc123" → "build-a-website-abc123"
 */
export function generateSlugWithId(text: string, id: string): string {
  const slug = generateSlug(text);
  const shortId = id.slice(0, 8);
  return `${slug}-${shortId}`;
}

// === Meta Tag Templates ===

/**
 * Generate standardized metadata for a job detail page.
 */
export function jobDetailMeta(job: {
  title: string;
  description: string;
  category: string;
  id: string;
  budget?: string;
  skills?: string[];
}): Metadata {
  const truncatedDesc = job.description.length > 155
    ? job.description.slice(0, 152) + "..."
    : job.description;
  const title = `${job.title} - ${job.category} Job`;
  const url = canonicalUrl(`/jobs/${job.id}`);
  const keywords = [
    job.category,
    `${job.category} freelance`,
    `${job.category} Iraq`,
    ...(job.skills || []),
    ...KEYWORDS.primary.slice(0, 3),
  ];

  return {
    title,
    description: truncatedDesc,
    keywords,
    alternates: { canonical: `/jobs/${job.id}` },
    openGraph: {
      title: `${title} | ${SITE_NAME}`,
      description: truncatedDesc,
      url,
      type: "website",
      images: [{
        url: ogImageUrl({ title: job.title, subtitle: `${job.category}${job.budget ? ` · ${job.budget}` : ""}`, type: "job" }),
        width: 1200,
        height: 630,
        alt: job.title,
      }],
    },
    twitter: {
      card: "summary_large_image",
      title: `${title} | ${SITE_NAME}`,
      description: truncatedDesc,
      images: [ogImageUrl({ title: job.title, subtitle: job.category, type: "job" })],
    },
  };
}

/**
 * Generate standardized metadata for a freelancer profile page.
 */
export function profileMeta(profile: {
  name: string;
  username: string;
  title?: string | null;
  bio?: string | null;
  skills?: string[] | null;
  avatarUrl?: string | null;
}): Metadata {
  const jobTitle = profile.title || "Freelancer";
  const titleStr = `${profile.name} - ${jobTitle}`;
  const description = profile.bio
    ? (profile.bio.length > 155 ? profile.bio.slice(0, 152) + "..." : profile.bio)
    : `Hire ${profile.name}, a ${jobTitle} on Kaasb. View skills, ratings, and completed projects.`;
  const url = canonicalUrl(`/profile/${profile.username}`);
  const keywords = [
    profile.name,
    jobTitle,
    `hire ${jobTitle}`,
    `${jobTitle} Iraq`,
    ...(profile.skills || []).slice(0, 5),
    ...KEYWORDS.primary.slice(0, 3),
  ];

  return {
    title: titleStr,
    description,
    keywords,
    alternates: { canonical: `/profile/${profile.username}` },
    openGraph: {
      title: `${titleStr} | ${SITE_NAME}`,
      description,
      url,
      type: "profile",
      images: [{
        url: ogImageUrl({ title: profile.name, subtitle: jobTitle, type: "profile" }),
        width: 1200,
        height: 630,
        alt: `${profile.name} on Kaasb`,
      }],
    },
    twitter: {
      card: "summary_large_image",
      title: `${titleStr} | ${SITE_NAME}`,
      description,
      images: [ogImageUrl({ title: profile.name, subtitle: jobTitle, type: "profile" })],
    },
  };
}

/**
 * Generate standardized metadata for a service (gig) detail page.
 * Mirrors jobDetailMeta shape so both entry points surface the same
 * quality of OG + Twitter preview.
 */
export function serviceDetailMeta(service: {
  title: string;
  description: string;
  slug: string;
  category?: string;
  minPrice?: number;
  freelancerName?: string;
  rating?: number;
  images?: string[];
}): Metadata {
  const truncatedDesc =
    service.description.length > 155
      ? service.description.slice(0, 152) + "..."
      : service.description;
  const category = service.category || "Freelance Service";
  const title = `${service.title} - ${category}`;
  const url = canonicalUrl(`/services/${service.slug}`);
  const priceFragment =
    service.minPrice != null ? ` · From ${service.minPrice.toLocaleString()} IQD` : "";
  const ratingFragment =
    service.rating != null && service.rating > 0
      ? ` · ${service.rating.toFixed(1)}★`
      : "";
  const subtitle = `${category}${priceFragment}${ratingFragment}`;

  const keywords = [
    category,
    `${category} freelance`,
    `${category} Iraq`,
    service.freelancerName || "",
    ...KEYWORDS.primary.slice(0, 3),
  ].filter(Boolean);

  // Prefer uploaded service image over generated OG if present (real
  // product shots convert better on social previews).
  const primaryImage =
    service.images && service.images.length > 0 && service.images[0]?.startsWith("http")
      ? service.images[0]
      : ogImageUrl({ title: service.title, subtitle, type: "service" });

  return {
    title,
    description: truncatedDesc,
    keywords,
    alternates: { canonical: `/services/${service.slug}` },
    openGraph: {
      title: `${title} | ${SITE_NAME}`,
      description: truncatedDesc,
      url,
      type: "website",
      images: [
        {
          url: primaryImage,
          width: 1200,
          height: 630,
          alt: service.title,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: `${title} | ${SITE_NAME}`,
      description: truncatedDesc,
      images: [primaryImage],
    },
  };
}

/**
 * Generate WhatsApp-optimized share URL with proper preview text.
 */
export function whatsappShareUrl(params: {
  text: string;
  url: string;
}): string {
  // WhatsApp previews work best when URL is at the end
  return `https://wa.me/?text=${encodeURIComponent(`${params.text}\n${params.url}`)}`;
}

/**
 * Generate Telegram share URL.
 */
export function telegramShareUrl(params: {
  text: string;
  url: string;
}): string {
  return `https://t.me/share/url?url=${encodeURIComponent(params.url)}&text=${encodeURIComponent(params.text)}`;
}
