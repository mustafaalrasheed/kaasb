// === Contract Types ===

export interface ContractUserInfo {
  id: string;
  username: string;
  first_name: string;
  last_name: string;
  display_name?: string;
  avatar_url?: string;
}

export interface ContractJobInfo {
  id: string;
  title: string;
  category: string;
  job_type: string;
}

export interface MilestoneDetail {
  id: string;
  title: string;
  description?: string;
  amount: number;
  order: number;
  status: string;
  due_date?: string;
  submitted_at?: string;
  approved_at?: string;
  paid_at?: string;
  submission_note?: string;
  feedback?: string;
  created_at: string;
}

export interface ContractDetail {
  id: string;
  title: string;
  description?: string;
  total_amount: number;
  amount_paid: number;
  status: string;
  started_at: string;
  completed_at?: string;
  deadline?: string;
  created_at: string;
  client: ContractUserInfo;
  freelancer: ContractUserInfo;
  job: ContractJobInfo;
  milestones: MilestoneDetail[];
}

export interface ContractSummary {
  id: string;
  title: string;
  total_amount: number;
  amount_paid: number;
  status: string;
  started_at: string;
  client: ContractUserInfo;
  freelancer: ContractUserInfo;
  job: ContractJobInfo;
  milestone_count: number;
  completed_milestones: number;
}

export interface ContractListResponse {
  contracts: ContractSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// === Status display helpers ===

export const CONTRACT_STATUS_LABELS: Record<string, string> = {
  active: "نشط",
  completed: "مكتمل",
  cancelled: "ملغى",
  disputed: "متنازع عليه",
  paused: "موقوف",
};

export const CONTRACT_STATUS_COLORS: Record<string, string> = {
  active: "bg-blue-50 text-blue-700 border-blue-200",
  completed: "bg-green-50 text-green-700 border-green-200",
  cancelled: "bg-gray-100 text-gray-500 border-gray-200",
  disputed: "bg-red-50 text-red-700 border-red-200",
  paused: "bg-yellow-50 text-yellow-700 border-yellow-200",
};

export const MILESTONE_STATUS_LABELS: Record<string, string> = {
  pending: "معلق",
  in_progress: "جارٍ",
  submitted: "مُقدَّم",
  revision_requested: "طلب مراجعة",
  approved: "موافق عليه",
  paid: "مدفوع",
};

export const MILESTONE_STATUS_COLORS: Record<string, string> = {
  pending: "bg-gray-100 text-gray-600",
  in_progress: "bg-blue-50 text-blue-700",
  submitted: "bg-purple-50 text-purple-700",
  revision_requested: "bg-orange-50 text-orange-700",
  approved: "bg-green-50 text-green-700",
  paid: "bg-green-100 text-green-800",
};
