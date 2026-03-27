import { create } from "zustand";
import { authApi } from "./api";
import type { User } from "@/types/user";

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  // Actions
  login: (email: string, password: string) => Promise<void>;
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
    // Server sets httpOnly cookies automatically
    await authApi.login({ email, password });

    // Fetch user profile
    const userResponse = await authApi.getMe();
    set({ user: userResponse.data.data, isAuthenticated: true });
  },

  register: async (data) => {
    // Server sets httpOnly cookies automatically
    await authApi.register(data);

    // Fetch user profile
    const userResponse = await authApi.getMe();
    set({ user: userResponse.data.data, isAuthenticated: true });
  },

  logout: () => {
    // Server clears httpOnly cookies
    authApi.logout().catch(() => {});
    set({ user: null, isAuthenticated: false });
    window.location.href = "/";
  },

  fetchUser: async () => {
    try {
      const response = await authApi.getMe();
      set({ user: response.data.data, isAuthenticated: true });
    } catch {
      set({ user: null, isAuthenticated: false });
    }
  },

  initialize: async () => {
    try {
      // Cookie is sent automatically — just check if we have a valid session
      const response = await authApi.getMe();
      set({ user: response.data.data, isAuthenticated: true, isLoading: false });
    } catch {
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },

  reset: () => {
    set({ user: null, isAuthenticated: false, isLoading: false });
  },
}));
