import type { User } from "@/types/user";
import { api } from "./client";

export const authApi = {
  register: (data: {
    email: string;
    username: string;
    password: string;
    first_name: string;
    last_name: string;
    primary_role: string;
    terms_accepted: boolean;
  }) => api.post("/auth/register", data),

  login: (data: { email: string; password: string }) =>
    api.post("/auth/login", data),

  refresh: () =>
    api.post("/auth/refresh", { refresh_token: "" }),

  getMe: () => api.get<User>("/auth/me"),

  logout: () => api.post("/auth/logout", { refresh_token: "" }),

  verifyEmail: (token: string) =>
    api.post("/auth/verify-email", { token }),

  resendVerification: (email: string) =>
    api.post("/auth/resend-verification", { email }),

  forgotPassword: (email: string) =>
    api.post("/auth/forgot-password", { email }),

  resetPassword: (token: string, new_password: string) =>
    api.post("/auth/reset-password", { token, new_password }),

  socialLogin: (data: {
    provider: "google" | "facebook";
    token: string;
    role?: string;
    terms_accepted?: boolean;
  }) => api.post("/auth/social", data),

  sendPhoneOtp: (phone: string) =>
    api.post("/auth/phone/send-otp", { phone }),

  verifyPhoneOtp: (phone: string, otp: string) =>
    api.post("/auth/phone/verify-otp", { phone, otp }),

  getWsTicket: () =>
    api.post<{ ticket: string; expires_in: number }>("/auth/ws-ticket"),

  clearSession: () =>
    api.post("/auth/clear-session", {}),

  listSessions: () =>
    api.get<Session[]>("/auth/sessions"),

  revokeSession: (id: string) =>
    api.delete(`/auth/sessions/${id}`),

  revokeOtherSessions: () =>
    api.post<{ revoked: number }>("/auth/sessions/revoke-others"),
};

export interface Session {
  id: string;
  user_agent: string | null;
  ip_address: string | null;
  created_at: string;
  last_used_at: string | null;
  expires_at: string;
  is_current: boolean;
}
