import { api } from "./client";

export const paymentsApi = {
  getSummary: () => api.get("/payments/summary"),

  getAccounts: () => api.get("/payments/accounts"),

  setupAccount: (data: {
    provider: string;
    qi_card_phone?: string;
  }) => api.post("/payments/accounts", data),

  getTransactions: (params?: {
    type?: string;
    page?: number;
    page_size?: number;
  }) => api.get("/payments/transactions", { params }),

  fundEscrow: (data: {
    milestone_id: string;
    payment_method_id?: string;
  }) => api.post("/payments/escrow/fund", data),

  requestPayout: (data: {
    amount: number;
    payment_account_id: string;
  }) => api.post("/payments/payout", data),
};
