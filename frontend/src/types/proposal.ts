export interface ProposalFreelancerInfo {
  id: string;
  username: string;
  first_name: string;
  last_name: string;
  display_name: string | null;
  avatar_url: string | null;
  title: string | null;
  country: string | null;
  experience_level: string | null;
  skills: string[] | null;
  avg_rating: number;
  total_reviews: number;
  jobs_completed: number;
}

export interface ProposalJobInfo {
  id: string;
  title: string;
  category: string;
  job_type: string;
  budget_min: number | null;
  budget_max: number | null;
  fixed_price: number | null;
  status: string;
}

export interface ProposalDetail {
  id: string;
  cover_letter: string;
  bid_amount: number;
  estimated_duration: string | null;
  status: string;
  client_note: string | null;
  submitted_at: string;
  responded_at: string | null;
  created_at: string;
  freelancer: ProposalFreelancerInfo;
  job: ProposalJobInfo;
}

export interface ProposalSummary {
  id: string;
  bid_amount: number;
  estimated_duration: string | null;
  status: string;
  submitted_at: string;
  freelancer: ProposalFreelancerInfo;
  job: ProposalJobInfo;
}

export interface ProposalListResponse {
  proposals: ProposalSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export const PROPOSAL_STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  shortlisted: "Shortlisted",
  accepted: "Accepted",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
};

export const PROPOSAL_STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-50 text-yellow-700 border-yellow-200",
  shortlisted: "bg-blue-50 text-blue-700 border-blue-200",
  accepted: "bg-green-50 text-green-700 border-green-200",
  rejected: "bg-red-50 text-red-700 border-red-200",
  withdrawn: "bg-gray-100 text-gray-500 border-gray-200",
};
