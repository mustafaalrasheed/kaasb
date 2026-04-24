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

  unsuspendChat: (userId: string) =>
    api.post(`/admin/users/${userId}/unsuspend-chat`),

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

  // Canonical endpoints under /services/* (post-rename 2026-04-21). The old
  // /gigs/admin/* alias router is scheduled for removal in Phase 2 — having
  // this client call the new path keeps the admin UI working past that drop.
  getPendingGigs: () =>
    api.get("/services/admin/pending"),

  approveGig: (gigId: string) =>
    api.post(`/services/admin/${gigId}/approve`),

  requestGigRevision: (gigId: string, note: string) =>
    api.post(`/services/admin/${gigId}/request-revision`, null, { params: { note } }),

  rejectGig: (gigId: string, reason: string) =>
    api.post(`/services/admin/${gigId}/reject`, null, { params: { reason } }),

  getSupportConversations: (params?: {
    only_unread?: boolean;
    status?: "open" | "in_progress" | "resolved";
    mine?: boolean;
    page?: number;
    page_size?: number;
  }) => api.get("/admin/support/conversations", { params }),

  claimSupportTicket: (conversationId: string) =>
    api.post(`/admin/support/conversations/${conversationId}/claim`),

  resolveSupportTicket: (conversationId: string) =>
    api.post(`/admin/support/conversations/${conversationId}/resolve`),

  reopenSupportTicket: (conversationId: string) =>
    api.post(`/admin/support/conversations/${conversationId}/reopen`),

  getOrderConversation: (orderId: string, params?: { page?: number; page_size?: number }) =>
    api.get(`/admin/orders/${orderId}/conversation`, { params }),
};
