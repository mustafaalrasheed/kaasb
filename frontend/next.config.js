/** @type {import('next').NextConfig} */

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
const IS_PRODUCTION = process.env.NODE_ENV === "production";
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://kaasb.com";

const nextConfig = {
  // Warnings only — don't fail the production build on lint issues
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },

  // Enable React strict mode for better development experience
  reactStrictMode: true,

  // Standalone output for Docker production builds
  output: "standalone",

  // Trailing slash consistency (SEO: avoid duplicate content)
  trailingSlash: false,

  // Powered-by header removal (security + cleaner responses)
  poweredByHeader: false,

  // Image optimization — restrict to known hosts + prefer modern formats
  images: {
    formats: ["image/avif", "image/webp"], // Serve AVIF (50% smaller) with WebP fallback
    minimumCacheTTL: 3600, // Cache optimized images for 1 hour (default: 60s)
    remotePatterns: [
      ...(IS_PRODUCTION
        ? []
        : [{ protocol: "http", hostname: "localhost", port: "8000" }]),
      {
        protocol: "https",
        hostname: "kaasb.com",
      },
      {
        protocol: "https",
        hostname: "*.kaasb.com",
      },
    ],
  },

  // Security + SEO headers
  async headers() {
    const imgSrc = IS_PRODUCTION
      ? "img-src 'self' data: blob: https://kaasb.com https://*.kaasb.com"
      : `img-src 'self' data: blob: ${BACKEND_URL} https://kaasb.com https://*.kaasb.com`;

    const connectSrc = IS_PRODUCTION
      ? "connect-src 'self' https://kaasb.com https://*.kaasb.com https://api.stripe.com"
      : `connect-src 'self' ${BACKEND_URL} https://kaasb.com https://*.kaasb.com https://api.stripe.com`;

    return [
      {
        source: "/(.*)",
        headers: [
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
          {
            key: "X-XSS-Protection",
            value: "1; mode=block",
          },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline'",
              "style-src 'self' 'unsafe-inline'",
              imgSrc,
              "font-src 'self'",
              connectSrc,
              "frame-ancestors 'none'",
              "base-uri 'self'",
              "form-action 'self'",
            ].join("; "),
          },
        ],
      },
      // Cache static assets aggressively
      {
        source: "/(.*)\\.(ico|svg|png|jpg|jpeg|gif|webp|avif|woff|woff2)",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=31536000, immutable",
          },
        ],
      },
      // SEO: Ensure sitemap and robots.txt are not cached too long
      {
        source: "/(sitemap.xml|robots.txt)",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=3600, s-maxage=3600",
          },
        ],
      },
      // SEO: Add Vary header for language-specific content
      {
        source: "/(.*)",
        headers: [
          {
            key: "Vary",
            value: "Accept-Language",
          },
        ],
      },
    ];
  },

  // SEO redirects — normalize common URL patterns
  async redirects() {
    return [
      // Redirect trailing slashes to non-trailing (canonical)
      {
        source: "/jobs/",
        destination: "/jobs",
        permanent: true,
      },
      {
        source: "/freelancers/",
        destination: "/freelancers",
        permanent: true,
      },
      {
        source: "/profile/:username/",
        destination: "/profile/:username",
        permanent: true,
      },
      // Common misspellings / old routes
      {
        source: "/browse-jobs",
        destination: "/jobs",
        permanent: true,
      },
      {
        source: "/find-freelancers",
        destination: "/freelancers",
        permanent: true,
      },
      {
        source: "/signup",
        destination: "/auth/register",
        permanent: true,
      },
      {
        source: "/signin",
        destination: "/auth/login",
        permanent: true,
      },
      {
        source: "/login",
        destination: "/auth/login",
        permanent: true,
      },
      {
        source: "/register",
        destination: "/auth/register",
        permanent: true,
      },
      // Arabic URL aliases → English canonical
      {
        source: "/وظائف",
        destination: "/jobs",
        permanent: true,
      },
      {
        source: "/مستقلين",
        destination: "/freelancers",
        permanent: true,
      },
    ];
  },

  // Environment variables available on the client
  env: {
    NEXT_PUBLIC_API_URL:
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
    NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME || "Kaasb",
    NEXT_PUBLIC_SITE_URL: SITE_URL,
  },

  // Proxy API requests in development to avoid CORS issues
  async rewrites() {
    if (IS_PRODUCTION) return [];
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
};

module.exports = nextConfig;
