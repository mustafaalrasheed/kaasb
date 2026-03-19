import type { Metadata, Viewport } from "next";
import "@/styles/globals.css";
import { Toaster } from "sonner";
import { Navbar } from "@/components/layout/navbar";

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export const metadata: Metadata = {
  title: {
    default: "Kaasb - Freelancing Platform",
    template: "%s | Kaasb",
  },
  description:
    "Connect with talented freelancers worldwide. Post jobs, hire experts, and grow your business with Kaasb.",
  keywords: ["freelancing", "hire freelancers", "remote work", "Kaasb"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50">
        <Navbar />
        <main className="pt-16">{children}</main>
        <Toaster position="top-right" richColors />
      </body>
    </html>
  );
}
