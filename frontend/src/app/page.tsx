import Link from "next/link";
import type { Metadata } from "next";
import { FaqJsonLd } from "@/components/seo/json-ld";
import {
  SITE_NAME,
  SITE_TAGLINE,
  SITE_DESCRIPTION,
  SITE_URL,
  DEFAULT_OG_IMAGE,
  KEYWORDS,
} from "@/lib/seo";

export const metadata: Metadata = {
  title: `${SITE_NAME} - ${SITE_TAGLINE}`,
  description: SITE_DESCRIPTION,
  keywords: KEYWORDS.primary,
  alternates: { canonical: "/" },
  openGraph: {
    title: `${SITE_NAME} - ${SITE_TAGLINE}`,
    description: SITE_DESCRIPTION,
    url: SITE_URL,
    images: [{ url: DEFAULT_OG_IMAGE, width: 1200, height: 630 }],
  },
};

const FAQ_ITEMS = [
  {
    question: "What is Kaasb?",
    answer:
      "Kaasb is Iraq's leading freelancing platform that connects businesses with talented freelancers across the Middle East. You can post jobs, hire experts, and manage projects with secure payments via Qi Card.",
  },
  {
    question: "How do I hire a freelancer on Kaasb?",
    answer:
      "Simply post your job with a description and budget, review proposals from qualified freelancers, and hire the best fit. Payments are secured through our escrow system.",
  },
  {
    question: "Is Kaasb free to use?",
    answer:
      "Signing up and browsing jobs is completely free. Kaasb charges a small service fee only when a project is completed successfully.",
  },
  {
    question: "What payment methods does Kaasb support?",
    answer:
      "Kaasb supports Qi Card (Iraq's most popular payment card), Wise for international transfers, and other secure payment methods.",
  },
  {
    question: "Can I work as a freelancer from Iraq?",
    answer:
      "Yes! Kaasb is designed specifically for Iraqi freelancers and the Middle East market. Create a free profile, showcase your skills, and start bidding on projects.",
  },
];

export default function HomePage() {
  return (
    <div className="min-h-[calc(100vh-4rem)]">
      {/* FAQ Structured Data */}
      <FaqJsonLd items={FAQ_ITEMS} />

      {/* Hero Section */}
      <section className="bg-gradient-to-br from-brand-500 via-brand-600 to-brand-800 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 lg:py-32">
          <div className="max-w-3xl">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight">
              Find the perfect
              <span className="text-brand-200"> freelancer </span>
              for your project
            </h1>
            <p className="mt-6 text-lg sm:text-xl text-blue-100 leading-relaxed">
              Kaasb connects businesses with talented freelancers across Iraq
              and the Middle East. Post a job, review proposals, and hire the
              best — all in one place.
            </p>
            <div className="mt-10 flex flex-col sm:flex-row gap-4">
              <Link
                href="/auth/register"
                className="btn-primary bg-white text-brand-600 hover:bg-blue-50 text-center text-lg px-8 py-3"
              >
                Get Started Free
              </Link>
              <Link
                href="/jobs"
                className="inline-block border border-white/40 text-white hover:bg-white/10 text-center text-lg px-8 py-3 rounded-lg font-medium transition-colors duration-150"
              >
                Browse Jobs
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-center text-gray-900">
            How Kaasb Works
          </h2>
          <p className="mt-4 text-center text-gray-600 max-w-2xl mx-auto">
            Getting started is simple. Whether you&apos;re hiring or
            freelancing, Kaasb makes it easy.
          </p>

          <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                step: "01",
                title: "Post a Job",
                description:
                  "Describe your project, set your budget, and post it to thousands of freelancers across Iraq.",
                icon: "📝",
              },
              {
                step: "02",
                title: "Review Proposals",
                description:
                  "Receive proposals from qualified freelancers. Compare skills, rates, and reviews.",
                icon: "🔍",
              },
              {
                step: "03",
                title: "Hire & Collaborate",
                description:
                  "Choose the best fit, collaborate through our platform, and pay securely via Qi Card.",
                icon: "🤝",
              },
            ].map((item) => (
              <div key={item.step} className="text-center">
                <div className="text-5xl mb-4" role="img" aria-label={item.title}>
                  {item.icon}
                </div>
                <div className="text-sm font-bold text-brand-500 mb-2">
                  STEP {item.step}
                </div>
                <h3 className="text-xl font-semibold text-gray-900">
                  {item.title}
                </h3>
                <p className="mt-3 text-gray-600">{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ Section (SEO-visible) */}
      <section className="py-20 bg-white border-t border-gray-100">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
            Frequently Asked Questions
          </h2>
          <div className="space-y-6">
            {FAQ_ITEMS.map((faq) => (
              <details
                key={faq.question}
                className="group border border-gray-200 rounded-lg"
              >
                <summary className="flex items-center justify-between cursor-pointer p-5 text-lg font-medium text-gray-900 hover:bg-gray-50 rounded-lg">
                  {faq.question}
                  <span className="ml-4 text-gray-400 group-open:rotate-180 transition-transform">
                    &#9662;
                  </span>
                </summary>
                <p className="px-5 pb-5 text-gray-600 leading-relaxed">
                  {faq.answer}
                </p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-4xl mx-auto text-center px-4">
          <h2 className="text-3xl font-bold text-gray-900">
            Ready to get started?
          </h2>
          <p className="mt-4 text-lg text-gray-600">
            Join thousands of freelancers and businesses on Kaasb.
          </p>
          <div className="mt-8 flex justify-center gap-4">
            <Link
              href="/auth/register"
              className="btn-primary text-lg px-8 py-3"
            >
              Sign Up as Freelancer
            </Link>
            <Link
              href="/auth/register"
              className="btn-secondary text-lg px-8 py-3"
            >
              Hire a Freelancer
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-400 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {/* Brand */}
            <div className="md:col-span-2">
              <div className="text-2xl font-bold text-white">Kaasb</div>
              <p className="mt-2 text-sm max-w-md">
                Iraq&apos;s leading freelancing platform connecting businesses
                with talented professionals across the Middle East.
              </p>
            </div>

            {/* Quick Links */}
            <nav aria-label="Footer navigation">
              <h3 className="text-sm font-semibold text-white uppercase tracking-wider mb-3">
                Quick Links
              </h3>
              <ul className="space-y-2 text-sm">
                <li>
                  <Link href="/jobs" className="hover:text-white transition-colors">
                    Browse Jobs
                  </Link>
                </li>
                <li>
                  <Link href="/freelancers" className="hover:text-white transition-colors">
                    Find Freelancers
                  </Link>
                </li>
                <li>
                  <Link href="/auth/register" className="hover:text-white transition-colors">
                    Sign Up
                  </Link>
                </li>
              </ul>
            </nav>

            {/* Social */}
            <div>
              <h3 className="text-sm font-semibold text-white uppercase tracking-wider mb-3">
                Connect
              </h3>
              <ul className="space-y-2 text-sm">
                <li>
                  <a
                    href="https://t.me/kaasb_iq"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-white transition-colors"
                  >
                    Telegram
                  </a>
                </li>
                <li>
                  <a
                    href="https://wa.me/9647800000000"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-white transition-colors"
                  >
                    WhatsApp
                  </a>
                </li>
                <li>
                  <a
                    href="https://instagram.com/kaasb.iq"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-white transition-colors"
                  >
                    Instagram
                  </a>
                </li>
              </ul>
            </div>
          </div>

          <div className="mt-8 pt-8 border-t border-gray-800 text-center text-sm">
            <p>&copy; {new Date().getFullYear()} Kaasb. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
