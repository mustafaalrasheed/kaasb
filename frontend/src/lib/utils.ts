import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { useRef, useCallback, useEffect } from "react";
import type { AxiosError } from "axios";

/**
 * Merge Tailwind CSS classes without conflicts.
 * Usage: cn("px-4 py-2", isActive && "bg-blue-500", "text-white")
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "";

/**
 * Build a URL for backend-hosted assets (avatars, uploads, etc.).
 *
 * - Empty/null path → "" (caller renders a placeholder)
 * - Absolute URL (http://, https://, data:) → returned unchanged (e.g. Google OAuth avatars)
 * - Relative path + NEXT_PUBLIC_BACKEND_URL set → prefixed (useful in local dev where
 *   frontend :3000 and backend :8000 are different origins)
 * - Relative path + no env var → returned as-is so the browser resolves to the current
 *   origin (production: nginx routes /uploads/ to the backend on the same origin)
 */
export function backendUrl(path: string | null | undefined): string {
  if (!path) return "";
  if (/^(https?:|data:|blob:)/i.test(path)) return path;
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return BACKEND_URL ? `${BACKEND_URL}${normalized}` : normalized;
}

/**
 * Hook: Debounce a callback — prevents rapid-fire API calls on search input.
 * Reduces network requests by ~90% on fast typers (only fires after user pauses).
 * @param callback The function to debounce
 * @param delay Milliseconds to wait (default: 300ms — optimal for search UX)
 */
export function useDebouncedCallback<T extends (...args: unknown[]) => void>(
  callback: T,
  delay: number = 300,
): T {
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const callbackRef = useRef(callback);

  // Keep callback ref current without re-creating the debounced function
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  return useCallback(
    (...args: Parameters<T>) => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      timeoutRef.current = setTimeout(() => callbackRef.current(...args), delay);
    },
    [delay],
  ) as T;
}

interface PydanticError {
  loc?: (string | number)[];
  msg?: string;
}

/**
 * Extract a human-readable error message from an Axios API error.
 * Handles both plain string details and Pydantic validation error arrays.
 */
export function getApiError(
  err: unknown,
  fallback = "An unexpected error occurred. Please try again.",
): string {
  const detail = (err as AxiosError<{ detail?: string | PydanticError[] }>)
    ?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => {
        const field = d.loc?.[d.loc.length - 1] ?? "field";
        const msg = (d.msg ?? "Invalid value").replace("Value error, ", "");
        return `${field}: ${msg}`;
      })
      .join("\n");
  }
  return fallback;
}

/** Extract HTTP status code from an Axios error (returns null for non-HTTP errors). */
export function getApiStatus(err: unknown): number | null {
  return (err as AxiosError)?.response?.status ?? null;
}
