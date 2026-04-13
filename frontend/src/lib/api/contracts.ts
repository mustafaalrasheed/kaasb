import { api } from "./client";

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
