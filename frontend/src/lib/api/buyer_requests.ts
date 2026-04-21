import { api } from "./client";

export const buyerRequestsApi = {
  // Freelancer: browse open requests
  list: (params?: { category_id?: string; page?: number; page_size?: number }) =>
    api.get("/buyer-requests", { params }),

  // Get single request
  get: (id: string) => api.get(`/buyer-requests/${id}`),

  // Client: my requests
  myRequests: () => api.get("/buyer-requests/my"),

  // Client: create request
  create: (data: {
    title: string;
    description: string;
    category_id?: string;
    budget_min: number;
    budget_max: number;
    delivery_days: number;
  }) => api.post("/buyer-requests", data),

  // Client: cancel request
  cancel: (id: string) => api.delete(`/buyer-requests/${id}`),

  // Freelancer: send offer
  sendOffer: (requestId: string, data: {
    price: number;
    delivery_days: number;
    message: string;
    service_id?: string;
  }) => api.post(`/buyer-requests/${requestId}/offers`, data),

  // Client: list offers on a request
  listOffers: (requestId: string) => api.get(`/buyer-requests/${requestId}/offers`),

  // Client: accept offer
  acceptOffer: (requestId: string, offerId: string) =>
    api.patch(`/buyer-requests/${requestId}/offers/${offerId}/accept`),

  // Client: reject offer
  rejectOffer: (requestId: string, offerId: string) =>
    api.patch(`/buyer-requests/${requestId}/offers/${offerId}/reject`),
};
