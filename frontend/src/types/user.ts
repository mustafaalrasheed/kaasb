export interface User {
  id: string;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  display_name: string | null;
  avatar_url: string | null;
  bio: string | null;
  country: string | null;
  city: string | null;
  timezone: string | null;
  phone: string | null;
  primary_role: "client" | "freelancer" | "admin";
  status: "active" | "suspended" | "deactivated" | "pending_verification";
  is_email_verified: boolean;
  is_superuser: boolean;
  title: string | null;
  skills: string[] | null;
  experience_level: "entry" | "intermediate" | "expert" | null;
  portfolio_url: string | null;
  total_earnings: number;
  total_spent: number;
  jobs_completed: number;
  avg_rating: number;
  total_reviews: number;
  is_online: boolean;
  last_login: string | null;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export type UserProfile = Pick<
  User,
  | "id"
  | "username"
  | "first_name"
  | "last_name"
  | "display_name"
  | "avatar_url"
  | "bio"
  | "country"
  | "city"
  | "primary_role"
  | "title"
  | "skills"
  | "experience_level"
  | "portfolio_url"
  | "avg_rating"
  | "total_reviews"
  | "jobs_completed"
  | "is_online"
  | "created_at"
>;
