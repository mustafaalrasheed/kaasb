// === Notification Types ===

/**
 * Every NotificationType value the backend can emit. Keep this in lock-step
 * with backend/app/models/notification.py — anything the backend sends that
 * is not in this union renders with the fallback bell icon.
 */
export type NotificationType =
  // Proposals
  | "proposal_received"
  | "proposal_accepted"
  | "proposal_rejected"
  | "proposal_shortlisted"
  // Contracts
  | "contract_created"
  | "contract_completed"
  // Milestones
  | "milestone_funded"
  | "milestone_submitted"
  | "milestone_approved"
  | "milestone_revision"
  // Payments
  | "payment_received"
  | "payout_completed"
  // Reviews & messages
  | "review_received"
  | "new_message"
  // Gigs
  | "gig_approved"
  | "gig_rejected"
  | "gig_submitted"
  | "gig_needs_revision"
  // Disputes
  | "dispute_opened"
  | "dispute_resolved"
  // Buyer requests
  | "buyer_request_offer_received"
  | "buyer_request_offer_accepted"
  | "buyer_request_offer_rejected"
  // Order lifecycle
  | "order_requirements_submitted"
  | "order_delivered"
  | "order_auto_completed"
  // Seller levels, anti-abuse
  | "seller_level_upgraded"
  | "chat_violation_warning"
  // System
  | "system_alert";

export interface NotificationDetail {
  id: string;
  type: NotificationType;
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

export const NOTIFICATION_ICONS: Record<NotificationType, string> = {
  // Proposals
  proposal_received: "📨",
  proposal_accepted: "✅",
  proposal_rejected: "❌",
  proposal_shortlisted: "⭐",
  // Contracts
  contract_created: "📝",
  contract_completed: "🎉",
  // Milestones
  milestone_funded: "💰",
  milestone_submitted: "📦",
  milestone_approved: "✅",
  milestone_revision: "🔄",
  // Payments
  payment_received: "💵",
  payout_completed: "🏦",
  // Reviews & messages
  review_received: "⭐",
  new_message: "💬",
  // Gigs
  gig_approved: "✅",
  gig_rejected: "❌",
  gig_submitted: "🆕",
  gig_needs_revision: "✏️",
  // Disputes
  dispute_opened: "⚠️",
  dispute_resolved: "⚖️",
  // Buyer requests
  buyer_request_offer_received: "📨",
  buyer_request_offer_accepted: "✅",
  buyer_request_offer_rejected: "❌",
  // Order lifecycle
  order_requirements_submitted: "📝",
  order_delivered: "📦",
  order_auto_completed: "⏰",
  // Seller levels, anti-abuse
  seller_level_upgraded: "🎖️",
  chat_violation_warning: "🚫",
  // System
  system_alert: "🔔",
};
