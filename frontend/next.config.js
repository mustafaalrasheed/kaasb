/** @type {import('next').NextConfig} */

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
const IS_PRODUCTION = process.env.NODE_ENV === "production";

const nextConfig = {
  // Enable React strict mode for better development experience
  reactStrictMode: true,

  // Standalone output for Docker production builds
  output: "standalone",

  // Image optimization — restrict to known hosts
  images: {
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

  // Security headers
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
    ];
  },

  // Environment variables available on the client
  env: {
    NEXT_PUBLIC_API_URL:
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
    NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME || "Kaasb",
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
