export interface JobClientInfo {
  id: string;
  username: string;
  first_name: string;
  last_name: string;
  display_name: string | null;
  avatar_url: string | null;
  country: string | null;
  total_spent: number;
  avg_rating: number;
  total_reviews: number;
  created_at: string;
}

export interface JobSummary {
  id: string;
  title: string;
  category: string;
  job_type: "fixed" | "hourly";
  budget_min: number | null;
  budget_max: number | null;
  fixed_price: number | null;
  skills_required: string[] | null;
  experience_level: "entry" | "intermediate" | "expert" | null;
  duration: string | null;
  status: string;
  proposal_count: number;
  view_count: number;
  is_featured: boolean;
  created_at: string;
  published_at: string | null;
  client: JobClientInfo;
}

export interface JobDetail extends JobSummary {
  description: string;
  deadline: string | null;
  closed_at: string | null;
  freelancer_id: string | null;
}

export interface JobListResponse {
  jobs: JobSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export const JOB_CATEGORIES = [
  "Web Development",
  "Mobile Development",
  "UI/UX Design",
  "Graphic Design",
  "Data Science",
  "Machine Learning",
  "DevOps & Cloud",
  "Cybersecurity",
  "Content Writing",
  "Digital Marketing",
  "Video & Animation",
  "Translation",
  "Virtual Assistant",
  "Accounting & Finance",
  "Legal Services",
  "Other",
] as const;

export const DURATION_LABELS: Record<string, string> = {
  less_than_1_week: "Less than 1 week",
  "1_to_4_weeks": "1 to 4 weeks",
  "1_to_3_months": "1 to 3 months",
  "3_to_6_months": "3 to 6 months",
  more_than_6_months: "More than 6 months",
};

export const EXPERIENCE_LABELS: Record<string, string> = {
  entry: "Entry Level",
  intermediate: "Intermediate",
  expert: "Expert",
};
