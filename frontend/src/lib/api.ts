import axios from "axios";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
});

// === Request Interceptor: Attach JWT token ===
api.interceptors.request.use(
  (config) => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("access_token");
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// === Response Interceptor: Handle 401 & token refresh ===
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const refreshToken = localStorage.getItem("refresh_token");
        if (!refreshToken) throw new Error("No refresh token");

        const response = await axios.post(`${API_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        });

        const { access_token, refresh_token: newRefreshToken } = response.data;
        localStorage.setItem("access_token", access_token);
        localStorage.setItem("refresh_token", newRefreshToken);

        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return api(originalRequest);
      } catch (refreshError) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        if (typeof window !== "undefined") {
          window.location.href = "/auth/login";
        }
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

// === Auth API ===

export const authApi = {
  register: (data: {
    email: string;
    username: string;
    password: string;
    first_name: string;
    last_name: string;
    primary_role: string;
  }) => api.post("/auth/register", data),

  login: (data: { email: string; password: string }) =>
    api.post("/auth/login", data),

  refresh: (refreshToken: string) =>
    api.post("/auth/refresh", { refresh_token: refreshToken }),

  getMe: () => api.get("/auth/me"),
};

// === Users API ===

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

// === Jobs API ===

export const jobsApi = {
  search: (params: {
    q?: string;
    category?: string;
    job_type?: string;
    skills?: string;
    experience_level?: string;
    budget_min?: number;
    budget_max?: number;
    duration?: string;
    sort_by?: string;
    page?: number;
    page_size?: number;
  }) => api.get("/jobs", { params }),

  getById: (jobId: string) => api.get(`/jobs/${jobId}`),

  create: (data: {
    title: string;
    description: string;
    category: string;
    job_type: string;
    budget_min?: number;
    budget_max?: number;
    fixed_price?: number;
    skills_required?: string[];
    experience_level?: string;
    duration?: string;
    deadline?: string;
  }) => api.post("/jobs", data),

  update: (jobId: string, data: Record<string, unknown>) =>
    api.put(`/jobs/${jobId}`, data),

  close: (jobId: string) => api.post(`/jobs/${jobId}/close`),

  delete: (jobId: string) => api.delete(`/jobs/${jobId}`),

  getMyJobs: (params?: {
    status?: string;
    page?: number;
    page_size?: number;
  }) => api.get("/jobs/my/posted", { params }),
};

// === Proposals API ===

export const proposalsApi = {
  submit: (jobId: string, data: {
    cover_letter: string;
    bid_amount: number;
    estimated_duration?: string;
  }) => api.post(`/proposals/jobs/${jobId}`, data),

  getMyProposals: (params?: {
    status?: string;
    page?: number;
    page_size?: number;
  }) => api.get("/proposals/my", { params }),

  update: (proposalId: string, data: Record<string, unknown>) =>
    api.put(`/proposals/${proposalId}`, data),

  withdraw: (proposalId: string) =>
    api.post(`/proposals/${proposalId}/withdraw`),

  getJobProposals: (jobId: string, params?: {
    status?: string;
    sort_by?: string;
    page?: number;
    page_size?: number;
  }) => api.get(`/proposals/jobs/${jobId}/list`, { params }),

  respond: (proposalId: string, data: {
    status: string;
    client_note?: string;
  }) => api.post(`/proposals/${proposalId}/respond`, data),

  getById: (proposalId: string) => api.get(`/proposals/${proposalId}`),
};

// === Contracts API ===

export const contractsApi = {
  getMyContracts: (params?: {
    status?: string;
    page?: number;
    page_size?: number;
  }) => api.get("/contracts/my", { params }),

  getById: (contractId: string) => api.get(`/contracts/${contractId}`),

  addMilestones: (contractId: string, data: {
    milestones: Array<{
      title: string;
      description?: string;
      amount: number;
      due_date?: string;
      order?: number;
    }>;
  }) => api.post(`/contracts/${contractId}/milestones`, data),

  updateMilestone: (milestoneId: string, data: Record<string, unknown>) =>
    api.put(`/contracts/milestones/${milestoneId}`, data),

  deleteMilestone: (milestoneId: string) =>
    api.delete(`/contracts/milestones/${milestoneId}`),

  startMilestone: (milestoneId: string) =>
    api.post(`/contracts/milestones/${milestoneId}/start`),

  submitMilestone: (milestoneId: string, data: {
    submission_note?: string;
  }) => api.post(`/contracts/milestones/${milestoneId}/submit`, data),

  reviewMilestone: (milestoneId: string, data: {
    action: string;
    feedback?: string;
  }) => api.post(`/contracts/milestones/${milestoneId}/review`, data),
};

// === Health API ===

export const healthApi = {
  check: () => api.get("/health"),
};

// === Payments API ===

export const paymentsApi = {
  getSummary: () => api.get("/payments/summary"),

  getAccounts: () => api.get("/payments/accounts"),

  setupAccount: (data: {
    provider: string;
    wise_email?: string;
    wise_currency?: string;
  }) => api.post("/payments/accounts", data),

  getTransactions: (params?: {
    type?: string;
    page?: number;
    page_size?: number;
  }) => api.get("/payments/transactions", { params }),

  fundEscrow: (data: {
    milestone_id: string;
    payment_method_id?: string;
  }) => api.post("/payments/escrow/fund", data),

  requestPayout: (data: {
    amount: number;
    payment_account_id: string;
  }) => api.post("/payments/payout", data),
};

// === Reviews API ===

export const reviewsApi = {
  getUserReviews: (userId: string, params?: { page?: number; page_size?: number }) =>
    api.get(`/reviews/user/${userId}`, { params }),

  getUserStats: (userId: string) =>
    api.get(`/reviews/user/${userId}/stats`),

  getContractReviews: (contractId: string) =>
    api.get(`/reviews/contract/${contractId}`),

  submitReview: (contractId: string, data: {
    rating: number;
    comment?: string;
    communication_rating?: number;
    quality_rating?: number;
    professionalism_rating?: number;
    timeliness_rating?: number;
  }) => api.post(`/reviews/contract/${contractId}`, data),
};

// === Notifications API ===

export const notificationsApi = {
  getNotifications: (params?: {
    unread_only?: boolean;
    page?: number;
    page_size?: number;
  }) => api.get("/notifications", { params }),

  getUnreadCount: () => api.get("/notifications/unread-count"),

  markRead: (data: { notification_ids: string[] }) =>
    api.post("/notifications/mark-read", data),

  markAllRead: () => api.post("/notifications/mark-all-read"),
};

// === Messages API ===

export const messagesApi = {
  getConversations: (params?: { page?: number; page_size?: number }) =>
    api.get("/messages/conversations", { params }),

  startConversation: (data: {
    recipient_id: string;
    job_id?: string;
    initial_message: string;
  }) => api.post("/messages/conversations", data),

  getMessages: (conversationId: string, params?: { page?: number; page_size?: number }) =>
    api.get(`/messages/conversations/${conversationId}`, { params }),

  sendMessage: (conversationId: string, data: { content: string }) =>
    api.post(`/messages/conversations/${conversationId}`, data),
};

// === Admin API ===

export const adminApi = {
  getStats: () => api.get("/admin/stats"),

  getUsers: (params?: Record<string, string | number>) =>
    api.get("/admin/users", { params }),

  updateUserStatus: (userId: string, data: { status: string }) =>
    api.put(`/admin/users/${userId}/status`, data),

  toggleAdmin: (userId: string) =>
    api.post(`/admin/users/${userId}/toggle-admin`),

  getJobs: (params?: Record<string, string | number>) =>
    api.get("/admin/jobs", { params }),

  updateJobStatus: (jobId: string, data: { status: string }) =>
    api.put(`/admin/jobs/${jobId}/status`, data),

  getTransactions: (params?: Record<string, string | number>) =>
    api.get("/admin/transactions", { params }),
};
