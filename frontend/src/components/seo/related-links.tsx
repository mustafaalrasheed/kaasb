/**
 * Kaasb Platform - Internal Linking Component
 * Boosts SEO by providing contextual internal links to related content.
 * Used on job detail, profile, and category pages.
 */

import Link from "next/link";
import { JOB_CATEGORIES } from "@/types/job";

// === Related Categories ===

interface RelatedCategoriesProps {
  currentCategory?: string;
  className?: string;
}

/**
 * Displays related job categories as internal links.
 * Excludes the current category and shows up to 6 related ones.
 */
export function RelatedCategories({
  currentCategory,
  className = "",
}: RelatedCategoriesProps) {
  const categories = JOB_CATEGORIES.filter((c) => c !== currentCategory).slice(
    0,
    6
  );

  return (
    <nav aria-label="Related categories" className={className}>
      <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
        Browse by Category
      </h3>
      <div className="flex flex-wrap gap-2">
        {categories.map((category) => (
          <Link
            key={category}
            href={`/jobs?category=${encodeURIComponent(category)}`}
            className="px-3 py-1.5 text-sm rounded-full bg-gray-100 text-gray-700 border border-gray-200 hover:bg-brand-50 hover:text-brand-700 hover:border-brand-200 transition-colors"
          >
            {category}
          </Link>
        ))}
      </div>
    </nav>
  );
}

// === Related Jobs ===

interface RelatedJob {
  id: string;
  title: string;
  category: string;
  budget?: string;
}

interface RelatedJobsProps {
  jobs: RelatedJob[];
  className?: string;
}

/**
 * Displays related job links.
 * Pass in a list of related jobs (typically same category, fetched from API).
 */
export function RelatedJobs({ jobs, className = "" }: RelatedJobsProps) {
  if (jobs.length === 0) return null;

  return (
    <nav aria-label="Related jobs" className={className}>
      <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
        Similar Jobs
      </h3>
      <ul className="space-y-2">
        {jobs.map((job) => (
          <li key={job.id}>
            <Link
              href={`/jobs/${job.id}`}
              className="block p-3 rounded-lg hover:bg-gray-50 transition-colors group"
            >
              <span className="text-sm font-medium text-gray-900 group-hover:text-brand-600 transition-colors line-clamp-1">
                {job.title}
              </span>
              <span className="text-xs text-gray-500 mt-0.5 flex items-center gap-2">
                <span>{job.category}</span>
                {job.budget && (
                  <>
                    <span className="text-gray-300">·</span>
                    <span>{job.budget}</span>
                  </>
                )}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}

// === Explore Links (for footer/404) ===

interface ExploreLinkItem {
  label: string;
  href: string;
  description?: string;
}

const DEFAULT_EXPLORE_LINKS: ExploreLinkItem[] = [
  {
    label: "Browse All Jobs",
    href: "/jobs",
    description: "Find freelance opportunities across Iraq",
  },
  {
    label: "Find Freelancers",
    href: "/freelancers",
    description: "Hire talented professionals for your project",
  },
  {
    label: "Web Development",
    href: "/jobs?category=Web+Development",
    description: "Frontend, backend, and full-stack jobs",
  },
  {
    label: "Graphic Design",
    href: "/jobs?category=Graphic+Design",
    description: "Logo design, branding, and visual identity",
  },
  {
    label: "Digital Marketing",
    href: "/jobs?category=Digital+Marketing",
    description: "SEO, social media, and content marketing",
  },
  {
    label: "Translation",
    href: "/jobs?category=Translation",
    description: "Arabic-English translation services",
  },
];

interface ExploreLinksProps {
  links?: ExploreLinkItem[];
  className?: string;
}

/**
 * Grid of explore links — used on 404, empty states, and footer.
 * Provides crawlable internal links for SEO.
 */
export function ExploreLinks({
  links = DEFAULT_EXPLORE_LINKS,
  className = "",
}: ExploreLinksProps) {
  return (
    <nav aria-label="Explore Kaasb" className={className}>
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Explore Kaasb
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="block p-4 rounded-lg border border-gray-200 hover:border-brand-200 hover:bg-brand-50 transition-colors group"
          >
            <span className="text-sm font-medium text-gray-900 group-hover:text-brand-700">
              {link.label}
            </span>
            {link.description && (
              <span className="block text-xs text-gray-500 mt-1">
                {link.description}
              </span>
            )}
          </Link>
        ))}
      </div>
    </nav>
  );
}
