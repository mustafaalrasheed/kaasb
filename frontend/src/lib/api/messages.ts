import { api } from "./client";

export const messagesApi = {
  getConversations: (params?: { page?: number; page_size?: number }) =>
    api.get("/messages/conversations", { params }),

  startConversation: (data: {
    recipient_id: string;
    job_id?: string;
    initial_message: string;
  }) => api.post("/messages/conversations", data),

  getMessages: (conversationId: string, params?: { page?: number; page_size?: number }) =>
    api.get(`/messages/conversations/${conversationId}`, { params }),

  sendMessage: (conversationId: string, data: { content: string }) =>
    api.post(`/messages/conversations/${conversationId}`, data),

  // Batch presence lookup — used when rendering the conversation list to show
  // the green dot on online users and a "Last seen ..." subtitle otherwise.
  getPresence: (userIds: string[]) =>
    api.get("/messages/presence", { params: { user_ids: userIds } }),

  // Contact support — no admin ID required; backend finds one automatically.
  contactSupport: (message: string, orderId?: string) =>
    api.post("/messages/support", { message, order_id: orderId ?? null }),
};
