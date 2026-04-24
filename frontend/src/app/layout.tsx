import type { Metadata, Viewport } from "next";
import "@/styles/globals.css";

// The layout reads cookies() to determine locale, which automatically opts into
// dynamic rendering. No explicit `export const dynamic` is needed here.
// Individual pages (e.g. /services catalog) can still use ISR/static where they
// don't read cookies themselves — Next.js only forces dynamic at the segment
// that actually calls cookies()/headers().
import Link from "next/link";
import { Toaster } from "sonner";
import { Navbar } from "@/components/layout/navbar";
import { CookieConsent } from "@/components/ui/cookie-consent";
import {
  OrganizationJsonLd,
  WebSiteJsonLd,
} from "@/components/seo/json-ld";
import {
  SITE_NAME,
  SITE_TAGLINE,
  SITE_DESCRIPTION,
  SITE_URL,
  SITE_LOCALE,
  SITE_LOCALE_AR,
  DEFAULT_OG_IMAGE,
  KEYWORDS,
  SOCIAL,
} from "@/lib/seo";
import { cookies } from "next/headers";
import { LocaleProvider } from "@/providers/locale-provider";

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#2188cb" },
    { media: "(prefers-color-scheme: dark)", color: "#0f172a" },
  ],
};

export const metadata: Metadata = {
  // === Core ===
  title: {
    default: `${SITE_NAME} - ${SITE_TAGLINE}`,
    template: `%s | ${SITE_NAME}`,
  },
  description: SITE_DESCRIPTION,
  keywords: [...KEYWORDS.primary, ...KEYWORDS.jobs, ...KEYWORDS.freelancers],
  authors: [{ name: SITE_NAME, url: SITE_URL }],
  creator: SITE_NAME,
  publisher: SITE_NAME,

  // === Canonical & Alternates ===
  metadataBase: new URL(SITE_URL),
  alternates: {
    canonical: "/",
    languages: {
      "en-US": "/",
      "ar-IQ": "/ar",
    },
  },

  // === Open Graph (Facebook, WhatsApp, Telegram) ===
  openGraph: {
    type: "website",
    siteName: SITE_NAME,
    title: `${SITE_NAME} - ${SITE_TAGLINE}`,
    description: SITE_DESCRIPTION,
    url: SITE_URL,
    locale: SITE_LOCALE,
    alternateLocale: [SITE_LOCALE_AR],
    images: [
      {
        url: DEFAULT_OG_IMAGE,
        width: 1200,
        height: 630,
        alt: `${SITE_NAME} - ${SITE_TAGLINE}`,
        type: "image/png",
      },
    ],
  },

  // === Twitter Card ===
  twitter: {
    card: "summary_large_image",
    site: SOCIAL.twitter,
    creator: SOCIAL.twitter,
    title: `${SITE_NAME} - ${SITE_TAGLINE}`,
    description: SITE_DESCRIPTION,
    images: [DEFAULT_OG_IMAGE],
  },

  // === Robots ===
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },

  // === App Manifest ===
  manifest: "/manifest.json",

  // === Icons ===
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "16x16 32x32 48x48" },
      { url: "/icon-192.png", type: "image/png", sizes: "192x192" },
      { url: "/icon-512.png", type: "image/png", sizes: "512x512" },
    ],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180" }],
  },

  category: "technology",

  other: {
    "mobile-web-app-capable": "yes",
    "apple-mobile-web-app-capable": "yes",
    "apple-mobile-web-app-status-bar-style": "default",
    "apple-mobile-web-app-title": SITE_NAME,
  },
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const cookieStore = await cookies();
  const localeCookie = cookieStore.get("locale")?.value;
  const locale = (localeCookie === "en" ? "en" : "ar") as "ar" | "en";
  const dir = locale === "ar" ? "rtl" : "ltr";
  const htmlLang = locale === "ar" ? "ar" : "en";

  return (
    <html lang={htmlLang} dir={dir} className={locale === "ar" ? "font-arabic" : ""}>
      <head>
        {/* Google Fonts — Tajawal for Arabic (root layout is the correct place; eslint false-positive) */}
        {/* eslint-disable @next/next/no-page-custom-font */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700;900&display=swap"
          rel="stylesheet"
        />
        {/* eslint-enable @next/next/no-page-custom-font */}

        {/* Structured Data */}
        <OrganizationJsonLd />
        <WebSiteJsonLd />

        {/* hreflang for Arabic/English */}
        <link rel="alternate" hrefLang="en" href={SITE_URL} />
        <link rel="alternate" hrefLang="ar" href={`${SITE_URL}/ar`} />
        <link rel="alternate" hrefLang="x-default" href={SITE_URL} />

        {/* Preconnect to backend for faster API calls */}
        <link
          rel="preconnect"
          href={process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"}
        />
        <link rel="dns-prefetch" href="//kaasb.com" />
      </head>
      <body className="min-h-screen bg-gray-50 flex flex-col">
        <LocaleProvider initialLocale={locale}>
          <Navbar />
          <main className="pt-16 flex-1">{children}</main>

          {/* Site Footer */}
          <footer className="bg-white border-t border-gray-200 mt-auto">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
              <div className={`flex flex-col gap-6 ${locale === "ar" ? "sm:flex-row-reverse" : "sm:flex-row"} justify-between items-start`}>
                {/* Brand */}
                <div>
                  <span className="text-lg font-bold text-brand-500">
                    {locale === "ar" ? "كاسب" : "Kaasb"}
                  </span>
                  <p className="mt-1 text-gray-400 text-sm max-w-xs">
                    {locale === "ar"
                      ? "منصة المستقلين العراقية — ربط الأعمال بالمواهب"
                      : "Iraq's Freelancing Platform — connecting businesses with talent"}
                  </p>
                </div>

                {/* Nav links */}
                <nav className="flex flex-wrap gap-x-8 gap-y-3 text-sm text-gray-500" aria-label="Footer navigation">
                  <Link href="/jobs" className="hover:text-gray-800 transition-colors">
                    {locale === "ar" ? "ابحث عن عمل" : "Find Work"}
                  </Link>
                  <Link href="/freelancers" className="hover:text-gray-800 transition-colors">
                    {locale === "ar" ? "ابحث عن مستقلين" : "Find Freelancers"}
                  </Link>
                  <Link href="/services" className="hover:text-gray-800 transition-colors">
                    {locale === "ar" ? "الخدمات" : "Services"}
                  </Link>
                  <Link href="/how-it-works" className="hover:text-gray-800 transition-colors">
                    {locale === "ar" ? "كيف يعمل كاسب" : "How It Works"}
                  </Link>
                  <Link href="/faq" className="hover:text-gray-800 transition-colors">
                    {locale === "ar" ? "الأسئلة الشائعة" : "FAQ"}
                  </Link>
                  <Link href="/help" className="hover:text-gray-800 transition-colors">
                    {locale === "ar" ? "مركز المساعدة" : "Help Center"}
                  </Link>
                  <Link href="/privacy" className="hover:text-gray-800 transition-colors">
                    {locale === "ar" ? "سياسة الخصوصية" : "Privacy Policy"}
                  </Link>
                  <Link href="/terms" className="hover:text-gray-800 transition-colors">
                    {locale === "ar" ? "شروط الخدمة" : "Terms of Service"}
                  </Link>
                  <Link href="/cookies" className="hover:text-gray-800 transition-colors">
                    {locale === "ar" ? "ملفات الارتباط" : "Cookies"}
                  </Link>
                  <Link href="/refunds" className="hover:text-gray-800 transition-colors">
                    {locale === "ar" ? "سياسة الاسترداد" : "Refunds"}
                  </Link>
                  <Link href="/acceptable-use" className="hover:text-gray-800 transition-colors">
                    {locale === "ar" ? "الاستخدام المقبول" : "Acceptable Use"}
                  </Link>
                  <a href="mailto:support@kaasb.com" className="hover:text-gray-800 transition-colors">
                    {locale === "ar" ? "الدعم" : "Support"}
                  </a>
                </nav>

                {/* Social */}
                <div className="flex gap-4 text-sm text-gray-500">
                  <a href="https://t.me/kaasb_iq" target="_blank" rel="noopener noreferrer" className="hover:text-gray-800 transition-colors" aria-label="Telegram">
                    Telegram
                  </a>
                  <a href="https://wa.me/9647800000000" target="_blank" rel="noopener noreferrer" className="hover:text-gray-800 transition-colors" aria-label="WhatsApp">
                    WhatsApp
                  </a>
                  <a href="https://instagram.com/kaasb.iq" target="_blank" rel="noopener noreferrer" className="hover:text-gray-800 transition-colors" aria-label="Instagram">
                    Instagram
                  </a>
                </div>
              </div>

              <p className="mt-6 pt-6 border-t border-gray-100 text-center text-xs text-gray-400">
                &copy; {new Date().getFullYear()} Kaasb Technology LLC.{" "}
                {locale === "ar" ? "جميع الحقوق محفوظة." : "All rights reserved."}
              </p>
            </div>
          </footer>

          <Toaster position={locale === "ar" ? "top-left" : "top-right"} richColors />
          <CookieConsent />
        </LocaleProvider>
      </body>
    </html>
  );
}
