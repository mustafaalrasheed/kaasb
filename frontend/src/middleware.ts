import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Routes that require authentication
const PROTECTED_PATHS = ["/dashboard", "/admin"];

// Routes that should redirect to dashboard if already authenticated
const AUTH_PATHS = ["/auth/login", "/auth/register"];

// Allowed redirect targets after login (prevents open redirect)
const SAFE_REDIRECT_PREFIXES = ["/dashboard", "/admin", "/jobs", "/freelancers", "/profile"];

function isValidRedirect(path: string): boolean {
  return SAFE_REDIRECT_PREFIXES.some((prefix) => path.startsWith(prefix));
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const accessToken = request.cookies.get("access_token")?.value;

  // Protect dashboard and admin routes
  const isProtected = PROTECTED_PATHS.some((path) => pathname.startsWith(path));
  if (isProtected && !accessToken) {
    const loginUrl = new URL("/auth/login", request.url);
    // Only set safe internal paths as redirect target
    if (isValidRedirect(pathname)) {
      loginUrl.searchParams.set("next", pathname);
    }
    return NextResponse.redirect(loginUrl);
  }

  // Redirect authenticated users away from auth pages
  const isAuthPage = AUTH_PATHS.some((path) => pathname.startsWith(path));
  if (isAuthPage && accessToken) {
    // Validate the 'next' param before redirecting
    const next = request.nextUrl.searchParams.get("next");
    const redirectPath = next && isValidRedirect(next) ? next : "/dashboard";
    return NextResponse.redirect(new URL(redirectPath, request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/admin/:path*", "/auth/:path*"],
};
