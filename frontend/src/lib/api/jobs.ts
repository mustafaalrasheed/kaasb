import type { JobDetail } from "@/types/job";
import { api } from "./client";

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

  getById: (jobId: string) => api.get<{ data: JobDetail }>(`/jobs/${jobId}`),

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
