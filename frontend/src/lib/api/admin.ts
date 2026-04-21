import { api } from "./client";

export const adminApi = {
  getStats: () => api.get("/admin/stats"),

  getUsers: (params?: Record<string, string | number>) =>
    api.get("/admin/users", { params }),

  updateUserStatus: (userId: string, data: { status: string }) =>
    api.put(`/admin/users/${userId}/status`, data),

  toggleAdmin: (userId: string) =>
    api.post(`/admin/users/${userId}/toggle-admin`),

  toggleSupport: (userId: string) =>
    api.post(`/admin/users/${userId}/toggle-support`),

  getJobs: (params?: Record<string, string | number>) =>
    api.get("/admin/jobs", { params }),

  updateJobStatus: (jobId: string, data: { status: string }) =>
    api.put(`/admin/jobs/${jobId}/status`, data),

  getTransactions: (params?: Record<string, string | number>) =>
    api.get("/admin/transactions", { params }),

  getEscrows: () => api.get("/admin/escrows"),

  releaseEscrow: (escrowId: string, note?: string) =>
    api.post(`/admin/escrows/${escrowId}/release`, { note: note ?? null }),

  getPendingPayoutApprovals: () =>
    api.get("/admin/payout-approvals/pending"),

  approvePayoutApproval: (approvalId: string, note?: string) =>
    api.post(`/admin/payout-approvals/${approvalId}/approve`, { note: note ?? null }),

  rejectPayoutApproval: (approvalId: string, note: string) =>
    api.post(`/admin/payout-approvals/${approvalId}/reject`, { note }),

  getProcessingPayouts: () =>
    api.get("/admin/payouts/processing"),

  markPayoutPaid: (transactionId: string, note?: string) =>
    api.post(`/admin/payouts/${transactionId}/mark-paid`, { note: note ?? null }),

  getStuckPendingPayments: (minAgeMinutes: number = 30) =>
    api.get("/admin/payments/stuck-pending", { params: { min_age_minutes: minAgeMinutes } }),

  getAuditLogs: (params?: { page?: number; page_size?: number }) =>
    api.get("/admin/audit-logs", { params }),

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

  getOrderConversation: (orderId: string, params?: { page?: number; page_size?: number }) =>
    api.get(`/admin/orders/${orderId}/conversation`, { params }),
};
