import { api } from "./client";

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
