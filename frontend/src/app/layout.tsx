import type { Metadata, Viewport } from "next";
import "@/styles/globals.css";
import { Toaster } from "sonner";
import { Navbar } from "@/components/layout/navbar";
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

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
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
      { url: "/favicon.ico", sizes: "any" },
      { url: "/icon.svg", type: "image/svg+xml" },
    ],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180" }],
  },

  // === Verification (add real IDs when available) ===
  // verification: {
  //   google: "google-site-verification-id",
  //   yandex: "yandex-verification-id",
  // },

  // === Category ===
  category: "technology",

  // === Additional (WhatsApp/Telegram optimization) ===
  other: {
    "mobile-web-app-capable": "yes",
    "apple-mobile-web-app-capable": "yes",
    "apple-mobile-web-app-status-bar-style": "default",
    "apple-mobile-web-app-title": SITE_NAME,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" dir="ltr">
      <head>
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
      <body className="min-h-screen bg-gray-50">
        <Navbar />
        <main className="pt-16">{children}</main>
        <Toaster position="top-right" richColors />
      </body>
    </html>
  );
}
