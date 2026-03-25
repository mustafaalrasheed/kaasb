/**
 * Kaasb Platform - Dynamic OG Image Generator
 * Generates Open Graph images for social media sharing.
 *
 * Usage: /api/og?title=Job+Title&subtitle=Category&type=job
 *
 * Optimized for:
 * - WhatsApp (1200x630 preview)
 * - Telegram (1200x630 preview)
 * - Facebook / Twitter / LinkedIn
 *
 * @see https://nextjs.org/docs/app/api-reference/file-conventions/metadata/opengraph-image
 */

import { ImageResponse } from "next/og";
import { type NextRequest } from "next/server";

export const runtime = "edge";

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const title = searchParams.get("title") || "Kaasb";
  const subtitle = searchParams.get("subtitle") || "Iraq's Leading Freelancing Platform";
  const type = searchParams.get("type") || "page";

  // Color scheme based on type
  const colors: Record<string, { bg: string; accent: string }> = {
    job: { bg: "#1e40af", accent: "#3b82f6" },
    profile: { bg: "#059669", accent: "#34d399" },
    page: { bg: "#1e3a5f", accent: "#60a5fa" },
  };
  const { bg, accent } = colors[type] || colors.page;

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "60px 80px",
          background: `linear-gradient(135deg, ${bg} 0%, #0f172a 100%)`,
          fontFamily: "system-ui, -apple-system, sans-serif",
        }}
      >
        {/* Top: Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div
            style={{
              width: "56px",
              height: "56px",
              borderRadius: "12px",
              background: accent,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "28px",
              fontWeight: 800,
              color: "white",
            }}
          >
            K
          </div>
          <span style={{ color: "white", fontSize: "28px", fontWeight: 700 }}>
            Kaasb
          </span>
        </div>

        {/* Middle: Title & Subtitle */}
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div
            style={{
              fontSize: title.length > 40 ? "42px" : "52px",
              fontWeight: 800,
              color: "white",
              lineHeight: 1.2,
              maxWidth: "900px",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {title}
          </div>
          <div
            style={{
              fontSize: "24px",
              color: "#94a3b8",
              maxWidth: "700px",
            }}
          >
            {subtitle}
          </div>
        </div>

        {/* Bottom: URL + Type badge */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span style={{ color: "#64748b", fontSize: "20px" }}>kaasb.com</span>
          <div
            style={{
              padding: "8px 20px",
              borderRadius: "20px",
              background: accent,
              color: "white",
              fontSize: "16px",
              fontWeight: 600,
              textTransform: "uppercase",
            }}
          >
            {type === "job" ? "Job Posting" : type === "profile" ? "Freelancer" : ""}
          </div>
        </div>
      </div>
    ),
    {
      width: 1200,
      height: 630,
    }
  );
}
