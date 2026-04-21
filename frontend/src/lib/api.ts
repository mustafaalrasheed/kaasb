/**
 * API barrel — all domain API objects are defined in src/lib/api/*.ts.
 * This file re-exports everything so existing `import { X } from "@/lib/api"`
 * imports continue to work without any changes across the codebase.
 */

export { api } from "./api/client";
export { authApi } from "./api/auth";
export { usersApi } from "./api/users";
export { jobsApi } from "./api/jobs";
export { proposalsApi } from "./api/proposals";
export { contractsApi } from "./api/contracts";
export { paymentsApi } from "./api/payments";
export { servicesApi, gigsApi } from "./api/services";
export { adminApi } from "./api/admin";
export { messagesApi } from "./api/messages";
export { notificationsApi } from "./api/notifications";
export { reviewsApi } from "./api/reviews";
export { buyerRequestsApi } from "./api/buyer_requests";

import { api as _apiClient } from "./api/client";
export const healthApi = {
  check: () => _apiClient.get("/health"),
};
