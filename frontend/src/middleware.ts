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

/**
 * Decode a JWT payload without verifying the signature.
 * Used to check the `exp` claim — the backend is the authority on signature validity.
 * We only need to know if the token is expired to avoid the redirect loop.
 */
function getJwtExpiry(token: string): number | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    // Base64url decode the payload (part 1)
    const payload = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const json = atob(payload);
    const data = JSON.parse(json);
    return typeof data.exp === "number" ? data.exp : null;
  } catch {
    return null;
  }
}

function isTokenExpired(token: string): boolean {
  const exp = getJwtExpiry(token);
  if (exp === null) return true; // malformed = treat as expired
  // exp is in seconds; add 5s buffer for clock skew
  return Date.now() / 1000 > exp - 5;
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const tokenCookie = request.cookies.get("access_token")?.value;

  // A token is "valid" if it exists AND is not expired
  const authenticated = tokenCookie ? !isTokenExpired(tokenCookie) : false;

  // Protect dashboard and admin routes
  const isProtected = PROTECTED_PATHS.some((path) => pathname.startsWith(path));
  if (isProtected && !authenticated) {
    const loginUrl = new URL("/auth/login", request.url);
    if (isValidRedirect(pathname)) {
      loginUrl.searchParams.set("next", pathname);
    }
    // Delete the stale cookie so this redirect only happens once
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
