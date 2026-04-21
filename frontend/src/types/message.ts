// === Message & Conversation Types ===

export type ConversationType = "user" | "order" | "support";
export type SenderRole = "client" | "freelancer" | "admin" | "system";
export type SupportTicketStatus = "open" | "in_progress" | "resolved";

export interface MessageUserInfo {
  id: string;
  username: string;
  first_name: string;
  last_name: string;
  avatar_url?: string;
}

export interface ConversationJobInfo {
  id: string;
  title: string;
}

export interface ConversationOrderInfo {
  id: string;
  status: string;
}

export interface MessageAttachment {
  url: string;
  filename: string;
  mime_type?: string;
  size_bytes?: number;
}

export interface ConversationSummary {
  id: string;
  conversation_type?: ConversationType;
  other_user: MessageUserInfo;
  job?: ConversationJobInfo;
  order?: ConversationOrderInfo;
  last_message_text?: string;
  last_message_at?: string;
  message_count: number;
  unread_count: number;
  created_at: string;
  support_status?: SupportTicketStatus | null;
  support_assignee?: MessageUserInfo | null;
}

export interface MessageDetail {
  id: string;
  content: string;
  is_read: boolean;
  read_at?: string | null;
  is_system?: boolean;
  sender_role?: SenderRole;
  attachments?: MessageAttachment[];
  sender: MessageUserInfo;
  created_at: string;
  // Present on the response to the sender when their message was a first-time
  // off-platform violation — delivered with contact info masked. UI uses these
  // to surface an escalation warning.
  chat_warning_code?: "email" | "phone" | "url" | "external_app" | null;
  chat_violation_count?: number | null;
}

export interface MessageListResponse {
  messages: MessageDetail[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ConversationListResponse {
  conversations: ConversationSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PresenceInfo {
  user_id: string;
  is_online: boolean;
  last_seen_at?: string | null;
}

export interface PresenceListResponse {
  users: PresenceInfo[];
}
