import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { useRef, useCallback, useEffect } from "react";

/**
 * Merge Tailwind CSS classes without conflicts.
 * Usage: cn("px-4 py-2", isActive && "bg-blue-500", "text-white")
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

/** Build a full URL for backend-hosted assets (avatars, uploads, etc.) */
export function backendUrl(path: string): string {
  return `${BACKEND_URL}${path}`;
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
