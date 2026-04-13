import { api } from "./client";

export const usersApi = {
  getProfile: (username: string) => api.get(`/users/profile/${username}`),

  searchFreelancers: (params: {
    q?: string;
    skills?: string;
    experience_level?: string;
    min_rate?: number;
    max_rate?: number;
    country?: string;
    sort_by?: string;
    page?: number;
    page_size?: number;
  }) => api.get("/users/freelancers", { params }),

  updateProfile: (data: Record<string, unknown>) =>
    api.put("/users/profile", data),

  uploadAvatar: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return api.post("/users/avatar", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  removeAvatar: () => api.delete("/users/avatar"),

  changePassword: (data: {
    current_password: string;
    new_password: string;
  }) => api.put("/users/password", data),

  deactivateAccount: () => api.delete("/users/account"),
};
