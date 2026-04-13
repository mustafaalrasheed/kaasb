// Barrel: re-export everything so `import { authApi } from "@/lib/api"` continues to work
// when using the sub-directory import path `@/lib/api/index`.

export { api } from "./client";
export { authApi } from "./auth";
export { usersApi } from "./users";
export { jobsApi } from "./jobs";
export { proposalsApi } from "./proposals";
export { contractsApi } from "./contracts";
export { paymentsApi } from "./payments";
export { gigsApi } from "./gigs";
export { adminApi } from "./admin";
export { messagesApi } from "./messages";
export { notificationsApi } from "./notifications";
export { reviewsApi } from "./reviews";

// Health (inline — too small to split)
import { api as _api } from "./client";
export const healthApi = {
  check: () => _api.get("/health"),
};
