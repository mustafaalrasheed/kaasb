/**
 * Kaasb Platform - Shared Constants
 * Centralized magic numbers and strings used across the frontend.
 */

// === Pagination ===
export const DEFAULT_PAGE_SIZE = 20;
export const MAX_PAGE_SIZE = 50;

// === Polling ===
export const MESSAGE_POLL_INTERVAL_MS = 3000;
export const NOTIFICATION_POLL_INTERVAL_MS = 30000;

// === Debounce ===
export const SEARCH_DEBOUNCE_MS = 300;

// === File Upload ===
export const MAX_AVATAR_SIZE_MB = 5;
export const MAX_AVATAR_SIZE_BYTES = MAX_AVATAR_SIZE_MB * 1024 * 1024;
export const ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];

// === UI ===
export const TOAST_DURATION_MS = 4000;

// === Routes ===
export const ROUTES = {
  HOME: "/",
  LOGIN: "/auth/login",
  REGISTER: "/auth/register",
  DASHBOARD: "/dashboard",
  JOBS: "/jobs",
  FREELANCERS: "/freelancers",
  MESSAGES: "/dashboard/messages",
  NOTIFICATIONS: "/dashboard/notifications",
  SETTINGS: "/dashboard/settings",
  ADMIN: "/admin",
} as const;

// === Status Colors (Tailwind classes) ===
export const STATUS_COLORS: Record<string, string> = {
  active: "bg-green-100 text-green-800",
  completed: "bg-blue-100 text-blue-800",
  cancelled: "bg-red-100 text-red-800",
  pending: "bg-yellow-100 text-yellow-800",
  in_progress: "bg-purple-100 text-purple-800",
  suspended: "bg-red-100 text-red-800",
  draft: "bg-gray-100 text-gray-800",
  open: "bg-green-100 text-green-800",
  closed: "bg-gray-100 text-gray-800",
  disputed: "bg-orange-100 text-orange-800",
  paused: "bg-yellow-100 text-yellow-800",
} as const;
