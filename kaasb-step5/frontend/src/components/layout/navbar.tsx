"use client";

import Link from "next/link";
import { useState } from "react";
import { useAuthStore } from "@/lib/auth-store";

export function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { user, isAuthenticated, logout } = useAuthStore();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2">
            <span className="text-2xl font-bold text-brand-500">Kaasb</span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-8">
            <Link
              href="/jobs"
              className="text-gray-600 hover:text-gray-900 font-medium transition-colors"
            >
              Find Work
            </Link>
            <Link
              href="/freelancers"
              className="text-gray-600 hover:text-gray-900 font-medium transition-colors"
            >
              Find Freelancers
            </Link>

            {isAuthenticated ? (
              <div className="flex items-center gap-4">
                <Link
                  href="/dashboard"
                  className="text-gray-600 hover:text-gray-900 font-medium"
                >
                  Dashboard
                </Link>
                <Link
                  href="/messages"
                  className="text-gray-600 hover:text-gray-900 font-medium"
                >
                  Messages
                </Link>
                <div className="flex items-center gap-3 pl-4 border-l border-gray-200">
                  <div className="w-8 h-8 bg-brand-100 text-brand-600 rounded-full flex items-center justify-center font-semibold text-sm">
                    {user?.first_name?.[0]}
                    {user?.last_name?.[0]}
                  </div>
                  <button
                    onClick={logout}
                    className="text-sm text-gray-500 hover:text-gray-700"
                  >
                    Log out
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-3">
                <Link
                  href="/auth/login"
                  className="text-gray-600 hover:text-gray-900 font-medium"
                >
                  Log In
                </Link>
                <Link href="/auth/register" className="btn-primary py-2 px-5">
                  Sign Up
                </Link>
              </div>
            )}
          </div>

          {/* Mobile menu button */}
          <button
            className="md:hidden p-2"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              {mobileMenuOpen ? (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              ) : (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-white border-t border-gray-100 py-4 px-4 space-y-3">
          <Link href="/jobs" className="block py-2 text-gray-700 font-medium">
            Find Work
          </Link>
          <Link
            href="/freelancers"
            className="block py-2 text-gray-700 font-medium"
          >
            Find Freelancers
          </Link>
          {!isAuthenticated && (
            <>
              <Link
                href="/auth/login"
                className="block py-2 text-gray-700 font-medium"
              >
                Log In
              </Link>
              <Link
                href="/auth/register"
                className="block btn-primary text-center"
              >
                Sign Up
              </Link>
            </>
          )}
        </div>
      )}
    </nav>
  );
}
