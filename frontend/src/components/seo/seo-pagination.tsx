/**
 * Kaasb Platform - SEO-Friendly Pagination
 * Adds link rel="prev"/"next" and canonical tags for paginated pages.
 * These help search engines understand pagination and avoid duplicate content.
 *
 * Usage: <SeoPagination basePath="/jobs" currentPage={2} totalPages={10} />
 */

import { SITE_URL } from "@/lib/seo";

interface SeoPaginationProps {
  /** Base path without query params, e.g. "/jobs" */
  basePath: string;
  /** Current page number (1-based) */
  currentPage: number;
  /** Total number of pages */
  totalPages: number;
  /** Additional query params to preserve */
  queryParams?: Record<string, string>;
}

function buildPageUrl(
  basePath: string,
  page: number,
  queryParams: Record<string, string> = {}
): string {
  const params = new URLSearchParams(queryParams);
  if (page > 1) {
    params.set("page", String(page));
  }
  const qs = params.toString();
  return `${SITE_URL}${basePath}${qs ? `?${qs}` : ""}`;
}

/**
 * Renders <link rel="prev/next/canonical"> tags in <head> for paginated pages.
 * Must be placed inside a server component or <head> element.
 */
export function SeoPagination({
  basePath,
  currentPage,
  totalPages,
  queryParams = {},
}: SeoPaginationProps) {
  const canonicalUrl = buildPageUrl(basePath, currentPage, queryParams);
  const hasPrev = currentPage > 1;
  const hasNext = currentPage < totalPages;

  return (
    <>
      <link rel="canonical" href={canonicalUrl} />
      {hasPrev && (
        <link
          rel="prev"
          href={buildPageUrl(basePath, currentPage - 1, queryParams)}
        />
      )}
      {hasNext && (
        <link
          rel="next"
          href={buildPageUrl(basePath, currentPage + 1, queryParams)}
        />
      )}
    </>
  );
}
