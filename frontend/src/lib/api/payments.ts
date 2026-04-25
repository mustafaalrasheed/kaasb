import { api } from "./client";

export const paymentsApi = {
  getSummary: () => api.get("/payments/summary"),

  getAccounts: () => api.get("/payments/accounts"),

  setupAccount: (data: {
    provider: string;
    qi_card_phone?: string;
    qi_card_holder_name?: string;
    qi_card_account_number?: string;
  }) => api.post("/payments/accounts", data),

  getTransactions: (params?: {
    type?: string;
    page?: number;
    page_size?: number;
  }) => api.get("/payments/transactions", { params }),

  fundEscrow: (data: {
    milestone_id: string;
    /** Payment gateway. Defaults to qi_card on the server if omitted. */
    provider?: "qi_card" | "zain_cash";
    payment_method_id?: string;
  }) => api.post("/payments/escrow/fund", data),

  requestPayout: (data: {
    amount: number;
    payment_account_id: string;
  }) => api.post("/payments/payout", data),
};
