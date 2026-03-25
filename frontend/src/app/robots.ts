/**
 * Kaasb Platform - robots.txt
 * Controls search engine crawling.
 * @see https://nextjs.org/docs/app/api-reference/file-conventions/metadata/robots
 */

import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/seo";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: ["/", "/jobs", "/freelancers", "/profile"],
        disallow: [
          "/dashboard",
          "/admin",
          "/auth",
          "/api",
          "/_next",
          "/uploads/private",
        ],
      },
      {
        // Block AI training crawlers from scraping user content
        userAgent: ["GPTBot", "ChatGPT-User", "CCBot", "anthropic-ai"],
        disallow: ["/"],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
