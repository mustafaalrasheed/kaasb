import { api } from "./client";

export const servicesApi = {
  // Public
  getCategories: () => api.get("/services/categories"),

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
  }) => api.get("/services", { params }),

  getBySlug: (slug: string) => api.get(`/services/${slug}`),

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
  }) => api.post("/services", data),

  update: (serviceId: string, data: Record<string, unknown>) =>
    api.put(`/services/${serviceId}`, data),

  delete: (serviceId: string) => api.delete(`/services/${serviceId}`),

  pause: (serviceId: string) => api.post(`/services/${serviceId}/pause`),
  resume: (serviceId: string) => api.post(`/services/${serviceId}/resume`),

  myServices: () => api.get("/services/my"),

  getMine: (serviceId: string) => api.get(`/services/my/${serviceId}`),

  // Orders
  placeOrder: (data: { service_id: string; package_id: string; requirements?: string }) =>
    api.post("/services/orders", data),

  myOrdersAsBuyer: () => api.get("/services/orders/buying"),
  myOrdersAsSeller: () => api.get("/services/orders/selling"),

  markDelivered: (orderId: string, data: { message: string; files?: string[] }) =>
    api.post(`/services/orders/${orderId}/deliver`, {
      message: data.message,
      files: data.files ?? [],
    }),
  listDeliveries: (orderId: string) =>
    api.get(`/services/orders/${orderId}/deliveries`),
  requestRevision: (orderId: string) => api.post(`/services/orders/${orderId}/revision`),
  completeOrder: (orderId: string) => api.post(`/services/orders/${orderId}/complete`),

  // F3: Client submits answers to service requirement questions
  submitRequirements: (
    orderId: string,
    answers: { question: string; answer: string }[],
  ) => api.post(`/services/orders/${orderId}/requirements`, { answers }),

  raiseDispute: (orderId: string, reason: string) =>
    api.post(`/services/orders/${orderId}/dispute`, { reason }),

  // Admin dispute management
  listDisputedOrders: () => api.get("/services/admin/disputes"),
  resolveDispute: (orderId: string, resolution: "release" | "refund", adminNote?: string) =>
    api.post(`/services/admin/orders/${orderId}/resolve-dispute`, {
      resolution,
      admin_note: adminNote ?? "",
    }),

  // Images
  uploadImage: (serviceId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post(`/services/${serviceId}/images`, form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  deleteImage: (serviceId: string, index: number) =>
    api.delete(`/services/${serviceId}/images/${index}`),

  // Admin
  pendingReview: () => api.get("/services/admin/pending"),
  approve: (serviceId: string) => api.post(`/services/admin/${serviceId}/approve`),
  reject: (serviceId: string, reason: string) =>
    api.post(`/services/admin/${serviceId}/reject`, null, { params: { reason } }),
};

// Legacy alias — kept so existing imports (`gigsApi`) keep working during the
// rename deprecation window. Remove once all call sites migrate to servicesApi.
export const gigsApi = servicesApi;
