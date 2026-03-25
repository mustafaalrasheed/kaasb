/**
 * Register page — server component wrapper for SEO metadata + client form.
 */

import type { Metadata } from "next";
import { SITE_NAME, SITE_URL, KEYWORDS, ogImageUrl } from "@/lib/seo";
import RegisterClient from "./register-client";

export const metadata: Metadata = {
  title: "Create Account",
  description: `Sign up for ${SITE_NAME} — Iraq's leading freelancing platform. Create a free account to hire freelancers or start earning as a freelancer.`,
  keywords: [
    "register Kaasb",
    "sign up freelancer Iraq",
    "create account Kaasb",
    "تسجيل كاسب",
    "إنشاء حساب",
    ...KEYWORDS.primary.slice(0, 3),
  ],
  alternates: { canonical: "/auth/register" },
  robots: { index: true, follow: true },
  openGraph: {
    title: `Create Account | ${SITE_NAME}`,
    description: `Join ${SITE_NAME} and start your freelancing journey. Sign up free as a freelancer or client.`,
    url: `${SITE_URL}/auth/register`,
    type: "website",
    images: [{
      url: ogImageUrl({ title: "Join Kaasb", subtitle: "Create your free account", type: "page" }),
      width: 1200,
      height: 630,
    }],
  },
};

export default function RegisterPage() {
  return <RegisterClient />;
}
