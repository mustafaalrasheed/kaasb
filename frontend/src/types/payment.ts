// === Payment Types ===

export interface PaymentAccount {
  id: string;
  provider: string;
  status: string;
  external_account_id?: string;
  qi_card_phone?: string;
  is_default: boolean;
  verified_at?: string;
  created_at: string;
}

export interface TransactionDetail {
  id: string;
  transaction_type: string;
  status: string;
  amount: number;
  currency: string;
  platform_fee: number;
  net_amount: number;
  description?: string;
  external_transaction_id?: string;
  completed_at?: string;
  created_at: string;
}

export interface TransactionListResponse {
  transactions: TransactionDetail[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PaymentSummary {
  total_earned: number;
  total_spent: number;
  pending_escrow: number;
  available_balance: number;
  total_paid_out: number;
  pending_payout: number;
  total_platform_fees: number;
  transaction_count: number;
  payment_accounts: PaymentAccount[];
}

export interface EscrowFundResponse {
  escrow_id: string;
  milestone_id: string;
  amount: number;
  platform_fee: number;
  freelancer_amount: number;
  status: string;
  payment_redirect_url?: string;
  qi_card_payment_id?: string;
  message: string;
}

export interface PayoutResponse {
  transaction_id: string;
  amount: number;
  net_amount: number;
  status: string;
  provider: string;
  message: string;
}

// === Display helpers ===

export const TRANSACTION_TYPE_LABELS: Record<string, string> = {
  escrow_fund: "Escrow Funded",
  escrow_release: "Payment Released",
  escrow_refund: "Escrow Refunded",
  platform_fee: "Platform Fee",
  payout: "Payout",
};

export const TRANSACTION_STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-50 text-yellow-700",
  processing: "bg-blue-50 text-blue-700",
  completed: "bg-green-50 text-green-700",
  failed: "bg-red-50 text-red-700",
  refunded: "bg-gray-100 text-gray-600",
  cancelled: "bg-gray-100 text-gray-500",
};

export const PROVIDER_LABELS: Record<string, string> = {
  qi_card: "Qi Card",
  manual: "Manual",
};
