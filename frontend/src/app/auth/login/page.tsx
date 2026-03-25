/**
 * Login page — server component wrapper for SEO metadata + client form.
 */

import type { Metadata } from "next";
import { SITE_NAME, SITE_URL, KEYWORDS, ogImageUrl } from "@/lib/seo";
import LoginClient from "./login-client";

export const metadata: Metadata = {
  title: "Log In",
  description: `Log in to your ${SITE_NAME} account. Access your dashboard, manage projects, and connect with freelancers across Iraq.`,
  keywords: ["login Kaasb", "freelancer login Iraq", "تسجيل دخول كاسب", ...KEYWORDS.primary.slice(0, 3)],
  alternates: { canonical: "/auth/login" },
  robots: { index: true, follow: true },
  openGraph: {
    title: `Log In | ${SITE_NAME}`,
    description: `Log in to ${SITE_NAME} to manage your freelancing projects and proposals.`,
    url: `${SITE_URL}/auth/login`,
    type: "website",
    images: [{
      url: ogImageUrl({ title: "Log In", subtitle: "Access your Kaasb account", type: "page" }),
      width: 1200,
      height: 630,
    }],
  },
};

export default function LoginPage() {
  return <LoginClient />;
}
