import { api } from "./client";

export const notificationsApi = {
  getNotifications: (params?: {
    unread_only?: boolean;
    page?: number;
    page_size?: number;
  }) => api.get("/notifications", { params }),

  getUnreadCount: () => api.get("/notifications/unread-count"),

  markRead: (data: { notification_ids: string[] }) =>
    api.post("/notifications/mark-read", data),

  markAllRead: () => api.post("/notifications/mark-all-read"),
};
