// === Message & Conversation Types ===

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

export interface ConversationSummary {
  id: string;
  other_user: MessageUserInfo;
  job?: ConversationJobInfo;
  last_message_text?: string;
  last_message_at?: string;
  message_count: number;
  unread_count: number;
  created_at: string;
}

export interface MessageDetail {
  id: string;
  content: string;
  is_read: boolean;
  sender: MessageUserInfo;
  created_at: string;
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
