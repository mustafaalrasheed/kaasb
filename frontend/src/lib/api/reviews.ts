import { api } from "./client";

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
