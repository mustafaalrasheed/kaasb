// === Review Types ===

export interface ReviewUserInfo {
  id: string;
  username: string;
  first_name: string;
  last_name: string;
  avatar_url?: string;
}

export interface ReviewContractInfo {
  id: string;
  title: string;
}

export interface ReviewDetail {
  id: string;
  rating: number;
  comment?: string;
  communication_rating?: number;
  quality_rating?: number;
  professionalism_rating?: number;
  timeliness_rating?: number;
  reviewer: ReviewUserInfo;
  reviewee: ReviewUserInfo;
  contract: ReviewContractInfo;
  created_at: string;
}

export interface ReviewListResponse {
  reviews: ReviewDetail[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  average_rating?: number;
}

export interface ReviewStats {
  average_rating: number;
  total_reviews: number;
  rating_distribution: Record<string, number>;
  avg_communication?: number;
  avg_quality?: number;
  avg_professionalism?: number;
  avg_timeliness?: number;
}

// Display helpers
export function renderStars(rating: number): string {
  return "★".repeat(Math.round(rating)) + "☆".repeat(5 - Math.round(rating));
}

export const RATING_LABELS: Record<number, string> = {
  1: "Poor",
  2: "Fair",
  3: "Good",
  4: "Very Good",
  5: "Excellent",
};
