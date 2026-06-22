// Type definitions for the jobs platform API

export interface Company {
  id: string;
  name: string;
  domain?: string | null;
  logo_url?: string | null;
  description?: string | null;
  created_at: string;
  updated_at: string;
}

export interface JobLocation {
  id: string;
  name: string;
  city?: string | null;
  state?: string | null;
  country?: string | null;
}

export interface Job {
  id: string;
  canonical_id: string;
  title: string;
  description: string;
  // Nested company object from the API
  company?: Company | null;
  /** Convenience alias — resolved from company.name in components */
  company_name?: string;
  company_id: string;
  location?: JobLocation | null;
  location_id?: string | null;
  location_city?: string | null;
  is_remote: boolean;
  salary_min?: number | null;
  salary_max?: number | null;
  currency?: string | null;
  source: string;
  url: string;
  status: string;
  posted_at: string;
  created_at: string;
  updated_at: string;
  // Aliases used by components
  title_normalized?: string;
}

/** Shape returned by GET /v1/jobs (PaginatedJobsResponse on backend) */
export interface JobListResponse {
  items: Job[];
  total: number;
  page: number;
  size: number;
  has_next: boolean;
  next_cursor?: string | null;
}

/** Frontend-normalised view (flatten company_name for display) */
export type JobListItem = Job & { company_name: string };

export interface JobListParams {
  q?: string;
  location?: string;
  skill?: string;
  is_remote?: boolean;
  cursor?: string;
  /** Maps to API ?size= param (max 50) */
  size?: number;
}

export interface User {
  id: string;
  email: string;
  name?: string;
  avatar_url?: string;
}

/** Shape returned by POST /v1/auth/register and /v1/auth/login (Token schema) */
export interface AuthResponse {
  access_token: string;
  token_type: string;
  refresh_token?: string | null;
}

export interface RegisterBody {
  email: string;
  password: string;
  name?: string;
}

export interface LoginBody {
  email: string;
  password: string;
}

export interface Application {
  id: string;
  job_id: string;
  job_title?: string;
  company_name?: string;
  status: "saved" | "applied" | "interview" | "offer" | "rejected";
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateApplicationBody {
  job_id: string;
  status?: Application["status"];
  notes?: string;
}
