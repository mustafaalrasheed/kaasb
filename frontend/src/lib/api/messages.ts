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
};
