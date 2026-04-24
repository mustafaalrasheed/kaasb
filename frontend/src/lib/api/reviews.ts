import { api } from "./client";

export interface ReviewSubmitBody {
  rating: number;
  comment?: string;
  communication_rating?: number;
  quality_rating?: number;
  professionalism_rating?: number;
  timeliness_rating?: number;
}

export const reviewsApi = {
  getUserReviews: (userId: string, params?: { page?: number; page_size?: number }) =>
    api.get(`/reviews/user/${userId}`, { params }),

  getUserStats: (userId: string) =>
    api.get(`/reviews/user/${userId}/stats`),

  getContractReviews: (contractId: string) =>
    api.get(`/reviews/contract/${contractId}`),

  submitReview: (contractId: string, data: ReviewSubmitBody) =>
    api.post(`/reviews/contract/${contractId}`, data),

  getOrderReviews: (serviceOrderId: string) =>
    api.get(`/reviews/order/${serviceOrderId}`),

  submitOrderReview: (serviceOrderId: string, data: ReviewSubmitBody) =>
    api.post(`/reviews/order/${serviceOrderId}`, data),
};
