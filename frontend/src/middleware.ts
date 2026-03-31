import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { jwtVerify } from "jose";

// Routes that require authentication
const PROTECTED_PATHS = ["/dashboard", "/admin"];

// Routes that should redirect to dashboard if already authenticated
const AUTH_PATHS = ["/auth/login", "/auth/register"];

// Allowed redirect targets after login (prevents open redirect)
const SAFE_REDIRECT_PREFIXES = ["/dashboard", "/admin", "/jobs", "/freelancers", "/profile"];

function isValidRedirect(path: string): boolean {
  return SAFE_REDIRECT_PREFIXES.some((prefix) => path.startsWith(prefix));
}

/**
 * Validate the JWT access token using the shared secret.
 * Falls back to "cookie exists" check if SECRET_KEY is not configured
 * (e.g. local dev without the env var set).
 */
async function isTokenValid(token: string): Promise<boolean> {
  const secret = process.env.SECRET_KEY;
  if (!secret) {
    // SECRET_KEY not set — can't validate signature, assume cookie presence is enough.
    // This should not happen in production (SECRET_KEY must be in frontend env).
    return token.length > 0;
  }
  try {
    const key = new TextEncoder().encode(secret);
    await jwtVerify(token, key, { algorithms: ["HS256"] });
    return true;
  } catch {
    // Token is expired, tampered, or otherwise invalid
    return false;
  }
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const tokenCookie = request.cookies.get("access_token")?.value;

  // Validate the token (not just its presence)
  const authenticated = tokenCookie ? await isTokenValid(tokenCookie) : false;

  // Protect dashboard and admin routes
  const isProtected = PROTECTED_PATHS.some((path) => pathname.startsWith(path));
  if (isProtected && !authenticated) {
    const loginUrl = new URL("/auth/login", request.url);
    if (isValidRedirect(pathname)) {
      loginUrl.searchParams.set("next", pathname);
    }
    // Clear the stale cookie so it doesn't keep triggering this redirect
    const response = NextResponse.redirect(loginUrl);
    if (tokenCookie) {
      response.cookies.delete("access_token");
    }
    return response;
  }

  // Redirect authenticated users away from auth pages
  const isAuthPage = AUTH_PATHS.some((path) => pathname.startsWith(path));
  if (isAuthPage && authenticated) {
    const next = request.nextUrl.searchParams.get("next");
    const redirectPath = next && isValidRedirect(next) ? next : "/dashboard";
    return NextResponse.redirect(new URL(redirectPath, request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/admin/:path*", "/auth/:path*"],
};
