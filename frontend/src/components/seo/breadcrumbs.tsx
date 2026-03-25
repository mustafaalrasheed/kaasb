/**
 * Kaasb Platform - Breadcrumb Navigation
 * Visual breadcrumbs + structured data for SEO.
 */

import Link from "next/link";
import { BreadcrumbJsonLd } from "./json-ld";

export interface BreadcrumbItem {
  name: string;
  href: string;
}

interface BreadcrumbsProps {
  items: BreadcrumbItem[];
  className?: string;
}

export function Breadcrumbs({ items, className = "" }: BreadcrumbsProps) {
  // Always include Home as the first item
  const allItems: BreadcrumbItem[] = [{ name: "Home", href: "/" }, ...items];

  return (
    <>
      {/* JSON-LD for search engines */}
      <BreadcrumbJsonLd items={allItems} />

      {/* Visual breadcrumbs */}
      <nav
        aria-label="Breadcrumb"
        className={`text-sm text-gray-500 ${className}`}
      >
        <ol className="flex flex-wrap items-center gap-1" itemScope itemType="https://schema.org/BreadcrumbList">
          {allItems.map((item, i) => {
            const isLast = i === allItems.length - 1;
            return (
              <li
                key={item.href}
                className="flex items-center gap-1"
                itemProp="itemListElement"
                itemScope
                itemType="https://schema.org/ListItem"
              >
                {i > 0 && (
                  <span className="text-gray-300 mx-1" aria-hidden="true">
                    /
                  </span>
                )}
                {isLast ? (
                  <span
                    className="text-gray-900 font-medium"
                    itemProp="name"
                    aria-current="page"
                  >
                    {item.name}
                  </span>
                ) : (
                  <Link
                    href={item.href}
                    className="hover:text-brand-600 transition-colors"
                    itemProp="item"
                  >
                    <span itemProp="name">{item.name}</span>
                  </Link>
                )}
                <meta itemProp="position" content={String(i + 1)} />
              </li>
            );
          })}
        </ol>
      </nav>
    </>
  );
}
