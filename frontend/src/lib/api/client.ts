import axios from "axios";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
  withCredentials: true, // Send httpOnly cookies with every request
});

// Prevents concurrent refresh calls — if multiple requests 401 at the same time,
// only one refresh call is made and all others wait for it.
let _refreshPromise: Promise<void> | null = null;

// === Response Interceptor: silent token refresh on 401 ===
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      // Endpoints that should never trigger a silent refresh
      const isAuthEndpoint =
        originalRequest.url?.includes("/auth/refresh") ||
        originalRequest.url?.includes("/auth/login") ||
        originalRequest.url?.includes("/auth/register") ||
        originalRequest.url?.includes("/auth/social") ||
        originalRequest.url?.includes("/auth/phone") ||
        originalRequest.url?.includes("/auth/clear-session");
      if (isAuthEndpoint) {
        return Promise.reject(error);
      }

      try {
        if (!_refreshPromise) {
          _refreshPromise = axios
            .post(`${API_URL}/auth/refresh`, {}, { withCredentials: true })
            .then(() => { _refreshPromise = null; })
            .catch((e) => { _refreshPromise = null; throw e; });
        }
        await _refreshPromise;
        return api(originalRequest);
      } catch {
        await axios
          .post(`${API_URL}/auth/clear-session`, {}, { withCredentials: true })
          .catch(() => {});
        if (typeof window !== "undefined") {
          const p = window.location.pathname;
          const isProtected = p.startsWith("/dashboard") || p.startsWith("/admin");
          if (isProtected) {
            window.location.href = "/auth/login";
          }
        }
        return Promise.reject(error);
      }
    }

    return Promise.reject(error);
  }
);
