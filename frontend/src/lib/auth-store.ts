import { create } from "zustand";
import { authApi } from "./api";
import type { User } from "@/types/user";

// Decode the access_token cookie expiry without verifying the signature.
// Returns seconds until expiry, or null if the cookie is absent/malformed.
function getAccessTokenTtl(): number | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|;\s*)access_token=([^;]+)/);
  if (!match) return null;
  try {
    const parts = match[1].split(".");
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")));
    return typeof payload.exp === "number" ? payload.exp - Date.now() / 1000 : null;
  } catch {
    return null;
  }
}

// Refresh token 5 minutes before expiry. Called once on initialize and then
// re-scheduled after every successful refresh.
let _refreshTimer: ReturnType<typeof setTimeout> | null = null;
// Timestamp when the tab was hidden — used to calculate how long the browser
// was closed or backgrounded so we can proactively refresh on return.
let _hiddenAt: number | null = null;
let _visibilityListenerAttached = false;

function scheduleRefresh() {
  if (_refreshTimer) clearTimeout(_refreshTimer);
  const ttl = getAccessTokenTtl();
  // Access token is httpOnly — JS can't actually read it. The TTL check
  // above will return null in production. In that case we fall back to
  // refreshing every 25 minutes (access token lifetime is 30 min).
  const refreshIn = ttl != null ? Math.max(ttl - 300, 60) : 25 * 60;
  _refreshTimer = setTimeout(async () => {
    try {
      await authApi.refresh();
      scheduleRefresh(); // reschedule after successful refresh
    } catch {
      // Refresh failed — user will be signed out on next 401
    }
  }, refreshIn * 1000);
}

// When the user returns to a backgrounded tab (or reopens the browser),
// check how long the page was hidden. If it was hidden for more than
// 20 minutes the access token may have expired, so refresh proactively
// instead of waiting for the next scheduled tick or a 401.
// Using _hiddenAt (set when the tab hides) is correct — _lastActivity
// (mouse/keyboard) would wrongly count idle-but-visible time as hidden time.
function setupVisibilityRefresh() {
  if (typeof document === "undefined" || _visibilityListenerAttached) return;
  _visibilityListenerAttached = true;

  document.addEventListener("visibilitychange", async () => {
    if (document.visibilityState === "hidden") {
      // Record when the page was hidden (tab switch, browser minimize, close).
      _hiddenAt = Date.now();
      return;
    }

    if (document.visibilityState !== "visible") return;

    // Calculate how long the page was actually hidden.
    const hiddenDuration = _hiddenAt != null ? Date.now() - _hiddenAt : 0;
    _hiddenAt = null; // reset for next hide/show cycle

    // If hidden for >20 min, proactively refresh before the next API call fails.
    if (hiddenDuration > 20 * 60 * 1000) {
      try {
        await authApi.refresh();
        scheduleRefresh();
      } catch {
        // Session truly expired — the next API call's 401 interceptor handles redirect
      }
    }
  });
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  // Actions
  login: (email: string, password: string) => Promise<void>;
  socialLogin: (provider: "google" | "facebook", token: string, role?: string) => Promise<void>;
  register: (data: {
    email: string;
    username: string;
    password: string;
    first_name: string;
    last_name: string;
    primary_role: string;
  }) => Promise<void>;
  logout: () => void;
  reset: () => void;
  fetchUser: () => Promise<void>;
  initialize: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,

  login: async (email, password) => {
    await authApi.login({ email, password });
    const userResponse = await authApi.getMe();
    set({ user: userResponse.data, isAuthenticated: true, isLoading: false });
    scheduleRefresh();
    setupVisibilityRefresh();
  },

  socialLogin: async (provider, token, role = "freelancer") => {
    await authApi.socialLogin({ provider, token, role });
    const userResponse = await authApi.getMe();
    set({ user: userResponse.data, isAuthenticated: true, isLoading: false });
    scheduleRefresh();
    setupVisibilityRefresh();
  },

  register: async (data) => {
    await authApi.register(data);
    const userResponse = await authApi.getMe();
    set({ user: userResponse.data, isAuthenticated: true, isLoading: false });
    scheduleRefresh();
    setupVisibilityRefresh();
  },

  logout: () => {
    if (_refreshTimer) { clearTimeout(_refreshTimer); _refreshTimer = null; }
    authApi.logout().catch(() => {});
    set({ user: null, isAuthenticated: false });
    window.location.href = "/";
  },

  fetchUser: async () => {
    try {
      const response = await authApi.getMe();
      set({ user: response.data, isAuthenticated: true });
    } catch {
      set({ user: null, isAuthenticated: false });
    }
  },

  initialize: async () => {
    try {
      // Try /auth/me. The 401 interceptor will silently refresh if the access
      // token has expired, so this succeeds as long as the refresh token is valid.
      const response = await authApi.getMe();
      set({ user: response.data, isAuthenticated: true, isLoading: false });
      scheduleRefresh();
      setupVisibilityRefresh(); // sliding session: refresh on tab restore
    } catch {
      // Not authenticated — render in logged-out state.
      // The interceptor already called clear-session if a refresh was attempted.
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },

  reset: () => {
    set({ user: null, isAuthenticated: false, isLoading: false });
  },
}));
