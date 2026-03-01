// === Notification Types ===

export interface NotificationDetail {
  id: string;
  type: string;
  title: string;
  message: string;
  is_read: boolean;
  link_type?: string;
  link_id?: string;
  actor_id?: string;
  created_at: string;
}

export interface NotificationListResponse {
  notifications: NotificationDetail[];
  total: number;
  unread_count: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export const NOTIFICATION_ICONS: Record<string, string> = {
  proposal_received: "📨",
  proposal_accepted: "✅",
  proposal_rejected: "❌",
  proposal_shortlisted: "⭐",
  contract_created: "📝",
  contract_completed: "🎉",
  milestone_funded: "💰",
  milestone_submitted: "📦",
  milestone_approved: "✅",
  milestone_revision: "🔄",
  payment_received: "💵",
  payout_completed: "🏦",
  review_received: "⭐",
  new_message: "💬",
  system_alert: "🔔",
};
