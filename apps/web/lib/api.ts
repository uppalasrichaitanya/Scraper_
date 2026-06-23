import type {
  Job,
  JobListParams,
  JobListResponse,
  User,
  AuthResponse,
  RegisterBody,
  LoginBody,
  Application,
  CreateApplicationBody,
  ResumeUploadResponse,
  ParseStatusResponse,
  ProfileResponse,
  SavedJobsListResponse,
  SavedJobStatus,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include", // send httpOnly cookie for auth
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new ApiError(res.status, err.detail ?? "Request failed");
  }

  return res.json() as Promise<T>;
}

/** Upload helper — sends FormData (no JSON content-type override). */
async function apiUpload<T>(path: string, formData: FormData): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    credentials: "include",
    body: formData,
    // Don't set Content-Type — the browser will set multipart/form-data with boundary
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new ApiError(res.status, err.detail ?? "Upload failed");
  }

  return res.json() as Promise<T>;
}

export const api = {
  jobs: {
    list: (params: JobListParams) => {
      // Build query params — skip undefined, convert booleans to strings
      const query = new URLSearchParams();
      for (const [k, v] of Object.entries(params)) {
        if (v !== undefined && v !== null && v !== "") {
          query.set(k, String(v));
        }
      }
      return apiFetch<JobListResponse>(`/v1/jobs?${query.toString()}`);
    },
    get: (id: string) => apiFetch<Job>(`/v1/jobs/${id}`),
  },

  auth: {
    register: (body: RegisterBody) =>
      apiFetch<AuthResponse>("/v1/auth/register", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    login: (body: LoginBody) =>
      apiFetch<AuthResponse>("/v1/auth/login", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    logout: () => apiFetch("/v1/auth/logout", { method: "POST" }),
    me: () => apiFetch<User>("/v1/users/me"),
  },

  applications: {
    list: () => apiFetch<Application[]>("/v1/applications"),
    create: (body: CreateApplicationBody) =>
      apiFetch<Application>("/v1/applications", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    update: (id: string, body: Partial<Application>) =>
      apiFetch<Application>(`/v1/applications/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
  },

  // ── Saved Jobs (Phase E backend) ────────────────────────────────
  savedJobs: {
    list: (status?: SavedJobStatus) => {
      const query = status ? `?status=${status}` : "";
      return apiFetch<SavedJobsListResponse>(`/v1/saved-jobs${query}`);
    },
    save: (jobId: string) =>
      apiFetch<{ saved: boolean; job_id: string }>(`/v1/saved-jobs/${jobId}`, {
        method: "POST",
      }),
    unsave: (jobId: string) =>
      apiFetch<{ saved: boolean; job_id: string }>(`/v1/saved-jobs/${jobId}`, {
        method: "DELETE",
      }),
    updateStatus: (jobId: string, body: { status: SavedJobStatus; note?: string }) =>
      apiFetch<{ updated: boolean; job_id: string; status: string }>(
        `/v1/saved-jobs/${jobId}/status`,
        { method: "PATCH", body: JSON.stringify(body) },
      ),
  },

  // ── Resume & Profile ────────────────────────────────────────────
  resume: {
    upload: (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return apiUpload<ResumeUploadResponse>("/v1/users/resume", formData);
    },
    status: () => apiFetch<ParseStatusResponse>("/v1/users/resume/status"),
    profile: () => apiFetch<ProfileResponse>("/v1/users/profile"),
  },
};
