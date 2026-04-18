import { api } from "./client";

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

  getEscrows: () => api.get("/admin/escrows"),

  releaseEscrow: (escrowId: string) =>
    api.post(`/admin/escrows/${escrowId}/release`),

  getPendingGigs: () =>
    api.get("/gigs/admin/pending"),

  approveGig: (gigId: string) =>
    api.post(`/gigs/admin/${gigId}/approve`),

  requestGigRevision: (gigId: string, note: string) =>
    api.post(`/gigs/admin/${gigId}/request-revision`, null, { params: { note } }),

  rejectGig: (gigId: string, reason: string) =>
    api.post(`/gigs/admin/${gigId}/reject`, null, { params: { reason } }),

  getSupportConversations: (params?: {
    only_unread?: boolean;
    page?: number;
    page_size?: number;
  }) => api.get("/admin/support/conversations", { params }),
};
