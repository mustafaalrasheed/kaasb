import { api } from "./client";

export const gigsApi = {
  // Public
  getCategories: () => api.get("/gigs/categories"),

  search: (params?: {
    q?: string;
    category_id?: string;
    subcategory_id?: string;
    min_price?: number;
    max_price?: number;
    delivery_days?: number;
    sort_by?: string;
    page?: number;
    page_size?: number;
  }) => api.get("/gigs", { params }),

  getBySlug: (slug: string) => api.get(`/gigs/${slug}`),

  // Freelancer management
  create: (data: {
    title: string;
    description: string;
    category_id: string;
    subcategory_id?: string;
    tags?: string[];
    packages: {
      tier: string;
      name: string;
      description: string;
      price: number;
      delivery_days: number;
      revisions?: number;
      features?: string[];
    }[];
  }) => api.post("/gigs", data),

  update: (gigId: string, data: Record<string, unknown>) =>
    api.put(`/gigs/${gigId}`, data),

  delete: (gigId: string) => api.delete(`/gigs/${gigId}`),

  pause: (gigId: string) => api.post(`/gigs/${gigId}/pause`),
  resume: (gigId: string) => api.post(`/gigs/${gigId}/resume`),

  myGigs: () => api.get("/gigs/my"),

  getMine: (gigId: string) => api.get(`/gigs/my/${gigId}`),

  // Orders
  placeOrder: (data: { gig_id: string; package_id: string; requirements?: string }) =>
    api.post("/gigs/orders", data),

  myOrdersAsBuyer: () => api.get("/gigs/orders/buying"),
  myOrdersAsSeller: () => api.get("/gigs/orders/selling"),

  markDelivered: (orderId: string) => api.post(`/gigs/orders/${orderId}/deliver`),
  requestRevision: (orderId: string) => api.post(`/gigs/orders/${orderId}/revision`),
  completeOrder: (orderId: string) => api.post(`/gigs/orders/${orderId}/complete`),

  raiseDispute: (orderId: string, reason: string) =>
    api.post(`/gigs/orders/${orderId}/dispute`, { reason }),

  // Admin dispute management
  listDisputedOrders: () => api.get("/gigs/admin/disputes"),
  resolveDispute: (orderId: string, resolution: "release" | "refund", adminNote?: string) =>
    api.post(`/gigs/admin/orders/${orderId}/resolve-dispute`, {
      resolution,
      admin_note: adminNote ?? "",
    }),

  // Images
  uploadImage: (gigId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post(`/gigs/${gigId}/images`, form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  deleteImage: (gigId: string, index: number) =>
    api.delete(`/gigs/${gigId}/images/${index}`),

  // Admin
  pendingReview: () => api.get("/gigs/admin/pending"),
  approve: (gigId: string) => api.post(`/gigs/admin/${gigId}/approve`),
  reject: (gigId: string, reason: string) =>
    api.post(`/gigs/admin/${gigId}/reject`, null, { params: { reason } }),
};
