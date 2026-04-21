export type BuyerRequestStatus = "open" | "filled" | "expired" | "cancelled";
export type BuyerRequestOfferStatus = "pending" | "accepted" | "rejected";

export interface BuyerRequestCategory {
  id: string;
  name_en: string;
  name_ar: string;
  slug: string;
}

export interface BuyerRequestClient {
  id: string;
  username: string;
  first_name: string;
  last_name: string;
  avatar_url?: string;
}

export interface BuyerRequestService {
  id: string;
  title: string;
  slug: string;
  thumbnail_url?: string;
}

export interface BuyerRequestFreelancer {
  id: string;
  username: string;
  first_name: string;
  last_name: string;
  avatar_url?: string;
  avg_rating?: number;
}

export interface BuyerRequest {
  id: string;
  client_id: string;
  title: string;
  description: string;
  category_id?: string;
  budget_min: number;
  budget_max: number;
  delivery_days: number;
  status: BuyerRequestStatus;
  expires_at: string;
  created_at: string;
  updated_at: string;
  client?: BuyerRequestClient;
  category?: BuyerRequestCategory;
  offer_count: number;
}

export interface BuyerRequestOffer {
  id: string;
  request_id: string;
  freelancer_id: string;
  service_id?: string;
  /** @deprecated — backend still emits gig_id during rename deprecation window */
  gig_id?: string;
  price: number;
  delivery_days: number;
  message: string;
  status: BuyerRequestOfferStatus;
  created_at: string;
  updated_at: string;
  freelancer?: BuyerRequestFreelancer;
  service?: BuyerRequestService;
  /** @deprecated — backend still emits `gig` during rename deprecation window */
  gig?: BuyerRequestService;
}

export interface BuyerRequestListResponse {
  items: BuyerRequest[];
  total: number;
  page: number;
  page_size: number;
}
